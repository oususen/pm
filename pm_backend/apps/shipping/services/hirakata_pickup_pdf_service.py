# apps/shipping/services/hirakata_pickup_pdf_service.py
"""枚方集荷依頼書PDF生成サービス"""

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Table, TableStyle
from datetime import date, timedelta
from typing import List, Dict, Tuple, Optional
from django.db import connection
from io import BytesIO
import os
import math
import pandas as pd
from masters.models import Calendar
from orders.utils.calendar_utils import WorkingDayCalculator


class HirakataPickupPDFService:
    """枚方集荷依頼書PDF生成サービス"""

    # 固定情報
    COMPANY_NAME = "ダイソウ工業株式会社"
    CONTACT_PERSON = "辻岡(ツジオカ)"
    PICKUP_LOCATION = "ダイソウ工業（株）三重県津市芸濃町北神山１４７０－３"
    DELIVERY_LOCATION = "ロジスクエア枚方"
    TRANSPORT_COMPANY = "大友ﾛｼﾞｽﾃｨｸｽｻｰﾋﾞｽ(株)京都営業所 配車担当者 御中"
    EMAIL = "kyouto03@otomo-logi.co.jp"
    DESTINATION = "枚方製造所行き"
    TARGET_GROUP_NAME_KEYWORD = "枚方"
    TARGET_GROUP_CODE_KEYWORD = "HIRAKATA"
    WORKING_CALENDAR_CODE = "kubota_hirakata"

    def __init__(self):
        self._register_font()

    def _register_font(self):
        """日本語フォントを登録"""
        # 既に登録済みの場合はスキップ
        if 'JapaneseFont' in pdfmetrics.getRegisteredFontNames():
            return

        # 日本語フォントパス（優先順位順）
        font_paths = [
            # Linux（Docker）用フォント - Debian/Ubuntu系
            ('/usr/share/fonts/truetype/takao-gothic/TakaoPGothic.ttf', 'Takao Gothic'),
            ('/usr/share/fonts/opentype/ipafont-gothic/ipagp.ttf', 'IPA Gothic P'),
            ('/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf', 'IPA Gothic'),
            ('/usr/share/fonts/truetype/fonts-japanese-gothic.ttf/TakaoPGothic.ttf', 'Takao Gothic (alt)'),
            ('/usr/share/fonts/truetype/fonts-takao-gothic/TakaoPGothic.ttf', 'Takao Gothic (alt2)'),
            ('/usr/share/fonts/truetype/fonts-ipafont-gothic/ipag.ttf', 'IPA Gothic (alt)'),
            ('/usr/share/fonts/opentype/ipaexfont-gothic/ipaexg.ttf', 'IPAex Gothic'),
            ('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc', 'Noto Sans CJK'),
            # Windows標準フォント（開発環境用）
            ('C:/Windows/Fonts/msgothic.ttc', 'MS Gothic'),
            ('C:/Windows/Fonts/GOTHIC.TTF', 'MS Gothic'),
            ('C:/Windows/Fonts/BIZ-UDGothicR.ttc', 'BIZ UD Gothic'),
            # プロジェクト内のフォント
            (os.path.join(os.path.dirname(__file__), '..', '..', '..', 'fonts', 'ipaexg.ttf'), 'IPAex Gothic')
        ]

        for font_path, font_name in font_paths:
            if os.path.exists(font_path):
                try:
                    pdfmetrics.registerFont(TTFont('JapaneseFont', font_path))
                    print(f"✅ フォント登録成功: {font_name} ({font_path})")
                    return
                except Exception as e:
                    print(f"⚠️ フォント登録失敗 ({font_name}): {e}")
                    continue

        # フォントが見つからない場合はエラー
        raise FileNotFoundError(
            "日本語フォントが見つかりません。\n"
            "MS Gothic、BIZ UD Gothic、またはJapaneseFontフォントをインストールしてください。"
        )

    def generate_pickup_request_pdf(self, start_date: date, end_date: date) -> BytesIO:
        """
        枚方集荷依頼書PDFを生成

        Args:
            start_date: 開始日
            end_date: 終了日

        Returns:
            BytesIO: PDF データ
        """
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4
        self._canvas = c

        # 依頼日（今日）
        request_date = date.today()

        # ヘッダー
        self._draw_header(c, width, height, request_date)

        # 固定情報
        self._draw_fixed_info(c, width, height)

        # 納品日ごとのデータを取得して描画
        y_position = height - 250

        # 稼働日リスト（納品日）を取得
        working_dates, working_set = self._get_working_dates(start_date, end_date)

        for delivery_date in working_dates:
            container_data, max_lead_time = self._get_container_data_for_date(delivery_date)

            # 製品の設定リードタイム（日数）を考慮して集荷日を算出
            lead_days = max(int(max_lead_time or 1), 1)
            pickup_date = self._subtract_working_days(delivery_date, lead_days, working_set)

            y_position = self._draw_date_section(
                c, width, y_position,
                pickup_date, delivery_date,
                container_data
            )

            # ページ下部に余白が無ければ改ページ
            if y_position < 150:
                c.showPage()
                y_position = height - 100

        # フッター
        self._draw_footer(c, width, 100)

        c.save()
        buffer.seek(0)
        return buffer

    def _draw_header(self, c: canvas.Canvas, width: float, height: float, request_date: date):
        """ヘッダー描画"""
        c.setFont("JapaneseFont", 20)
        c.drawString(100, height - 80, "集荷依頼書")

        # 依頼日
        c.setFont("JapaneseFont", 10)
        date_x = width - 250
        c.drawString(date_x, height - 50, f"ご依頼日: {request_date.year} 年")
        c.drawString(date_x + 100, height - 50, f"{request_date.month} 月")
        c.drawString(date_x + 150, height - 50, f"{request_date.day} 日")

        # 宛先
        c.setFont("JapaneseFont", 10)
        c.drawString(100, height - 100, self.TRANSPORT_COMPANY)

        # 赤文字で「枚方製造所行き」
        c.setFillColor(colors.red)
        c.setFont("JapaneseFont", 12)
        c.drawString(100, height - 120, self.DESTINATION)
        c.setFillColor(colors.black)

    def _draw_fixed_info(self, c: canvas.Canvas, width: float, height: float):
        """固定情報描画"""
        c.setFont("JapaneseFont", 10)

        # 発信者
        c.drawString(250, height - 120, f"発信者: {self.COMPANY_NAME}　{self.CONTACT_PERSON}")

        # テーブル形式で集荷場所と納入先を描画
        table_data = [
            ["集荷場所:", self.PICKUP_LOCATION],
            ["納入先:", self.DELIVERY_LOCATION]
        ]

        table = Table(table_data, colWidths=[80, 400])
        table.setStyle(TableStyle([
            ('FONT', (0, 0), (-1, -1), 'JapaneseFont', 10),
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ]))

        table.wrapOn(c, width, height)
        table.drawOn(c, 100, height - 200)

    def _draw_date_section(self, c: canvas.Canvas, width: float, y_position: float,
                           pickup_date: date, delivery_date: date,
                           container_data: List[Dict]) -> float:
        """
        日付ごとの集荷依頼セクションを描画
        """

        rows = []
        # 行の列数をテーブル全体で統一（6列）
        rows.append([
            "集 荷 日:",
            f"{pickup_date.year}", "年",
            f"{pickup_date.month}", "月",
            f"{pickup_date.day} 日"
        ])

        # 当日の出荷製品に紐づく容器コードを動的に抽出（重複除去）
        container_types: List[str] = []
        for container_item in container_data:
            code = container_item.get('container_code') or 'UNKNOWN'
            if code not in container_types:
                container_types.append(code)
        # 該当が無い場合のみ従来のデフォルトを表示
        if not container_types:
            container_types = ["アミ", "グレー（小）", "グレー", "青"]

        handled_codes = set()
        row_index = 1
        for container_code in container_types:
            container_info = next((c for c in container_data if c.get('container_code') == container_code), None)
            handled_codes.add(container_code)

            if container_info:
                container_name = container_info.get('container_name') or container_code
                container_color = container_info.get('color', '')
                quantity = int(container_info.get('total_containers', 0) or 0)
                # アミ容器の場合は常に単位を「アミ」に設定（出荷なしでも）
                if 'アミ' in container_name or container_code == 'AMI':
                    unit = 'アミ'
                else:
                    unit = container_info.get('unit', 'ポリ')
            else:
                container_name = container_code
                container_color = ''
                quantity = 0
                # アミ容器の場合は常に単位を「アミ」に設定
                if 'アミ' in container_code or container_code == 'AMI':
                    unit = 'アミ'
                else:
                    unit = 'ポリ'

            rows.append([
                f"容    器{row_index}:",
                container_name,
                container_color,
                str(quantity),
                unit,
                "kg"
            ])
            row_index += 1

        rows.append([
            "納 品 日:",
            f"{delivery_date.year}", "年",
            f"{delivery_date.month}", "月",
            f"{delivery_date.day} 日"
        ])

        table = Table(rows, colWidths=[80, 90, 25, 60, 25, 60])
        styles = [
            ('FONT', (0, 0), (-1, -1), 'JapaneseFont', 10),
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('BACKGROUND', (0, 0), (0, 0), colors.white),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ]
        container_start = 1
        container_end = max(container_start, len(rows) - 2)  # コンテナ行の最終インデックス
        if container_end >= container_start:
            styles.append(('ALIGN', (3, container_start), (3, container_end), 'RIGHT'))
        table.setStyle(TableStyle(styles))

        table.wrapOn(c, width, 800)
        table.drawOn(c, 100, y_position - 120)

        return y_position - 140

    def _draw_footer(self, c: canvas.Canvas, width: float, y_position: float):
        """フッター描画"""
        c.setFont("JapaneseFont", 9)
        c.drawString(100, y_position, "集荷前日の17時までに下記アドレスにメールにてご依頼ください")
        c.drawString(100, y_position - 15, f"E-MAIL  {self.EMAIL}")

    def _get_container_data_for_date(self, target_date: date) -> Tuple[List[Dict], int]:
        """
        指定日の容器別集計データを取得

        Args:
            target_date: 対象日

        Returns:
            Tuple[List[Dict], int]: 容器コード、容器名、必要容器数の集計、リードタイム最大値
        """
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT
                    cc.container_code,
                    cc.name AS container_name,
                    COALESCE(p.capacity, 0) AS capacity_per_container,
                    COALESCE(NULLIF(p.standard_lt_days, 0), 1) AS lead_time_days,
                    COALESCE(NULLIF(ol.quantity, 0), 0) AS effective_quantity
                FROM t_order_line ol
                INNER JOIN t_order o ON ol.order_id = o.id
                LEFT JOIN m_product p
                    ON p.id = ol.product_id
                    OR (ol.product_id IS NULL AND p.product_code = ol.product_code)
                LEFT JOIN m_product_group pg ON p.product_group_id = pg.id
                LEFT JOIN m_container_capacity cc ON p.used_container_id = cc.id
                WHERE DATE(ol.due_date) = %s
                  AND o.status = 'OPEN'
                  AND (
                        ol.order_type = 'FIRM'
                        OR (ol.order_type IS NULL AND o.order_type = 'FIRM')
                  )
                  AND (
                        pg.group_name LIKE %s
                        OR UPPER(pg.group_code) LIKE %s
                  )
                  AND COALESCE(NULLIF(ol.quantity, 0), 0) > 0
            """, [
                target_date,
                f"%{self.TARGET_GROUP_NAME_KEYWORD}%",
                f"%{self.TARGET_GROUP_CODE_KEYWORD}%"
            ])

            rows = cursor.fetchall()

        container_totals: Dict[str, Dict] = {}
        max_lead_time = 1
        for row in rows:
            container_code = row[0] or 'UNKNOWN'
            container_name = row[1] or '不明容器'
            capacity = int(row[2] or 0)
            lead_time_days = int(row[3] or 1)
            max_lead_time = max(max_lead_time, lead_time_days)
            quantity = int(row[4] or 0)

            effective_capacity = capacity if capacity > 0 else 1
            containers_needed = math.ceil(quantity / effective_capacity) if quantity > 0 else 0

            if containers_needed <= 0:
                continue

            if container_code not in container_totals:
                container_totals[container_code] = {
                    'container_code': container_code,
                    'container_name': container_name,
                    'total_containers': 0
                }
            container_totals[container_code]['total_containers'] += containers_needed

        return sorted(container_totals.values(), key=lambda x: x['container_code']), max_lead_time

    def _get_working_dates(self, start_date: date, end_date: date) -> Tuple[List[date], set]:
        """
        クボタ向けカレンダを基準に稼働日を取得する。

        カレンダ未設定時や日別設定が無い日は、既存のクボタ系処理と同様に
        平日（月〜金）を稼働日として扱う。
        """
        buffer_days = 14  # リードタイムさかのぼり用に少し前から取得
        start_buf = start_date - timedelta(days=buffer_days)
        kubota_calendar = Calendar.objects.filter(
            calendar_code=self.WORKING_CALENDAR_CODE
        ).first()
        calculator = WorkingDayCalculator(kubota_calendar)

        working_set = set()
        dates: List[date] = []
        current = start_buf
        while current <= end_date:
            if calculator.is_working_day(current):
                working_set.add(current)
                if start_date <= current <= end_date:
                    dates.append(current)
            current += timedelta(days=1)

        return dates, working_set

    def _subtract_working_days(self, base_date: date, days: int, working_set: set) -> date:
        """
        稼働日ベースで日数をさかのぼる（working_set が空なら暦日で計算）。
        """
        if days <= 0:
            return base_date

        current = base_date
        remaining = days
        while remaining > 0:
            current -= timedelta(days=1)
            if not working_set or current in working_set:
                remaining -= 1
        return current

    def get_pickup_date_range(self, start_date: date, end_date: date) -> Optional[Tuple[date, date]]:
        """対象期間の集荷日レンジを算出"""
        working_dates, working_set = self._get_working_dates(start_date, end_date)
        pickup_dates: List[date] = []

        for delivery_date in working_dates:
            container_data, max_lead_time = self._get_container_data_for_date(delivery_date)
            if not container_data:
                continue
            lead_days = max(int(max_lead_time or 1), 1)
            pickup_dates.append(self._subtract_working_days(delivery_date, lead_days, working_set))

        if not pickup_dates:
            return None
        return min(pickup_dates), max(pickup_dates)

    def generate_product_details_excel(
        self,
        start_date: date,
        end_date: date,
        daily_products: Optional[Dict[date, List[Dict]]] = None
    ) -> BytesIO:
        """
        対象期間の製品明細をExcelで生成

        Args:
            start_date: 開始日
            end_date: 終了日
            daily_products: 事前取得済みの日別製品リスト（省略可）

        Returns:
            BytesIO: Excel データ
        """
        products_by_date = daily_products if daily_products is not None else self.get_daily_product_list(start_date, end_date)

        rows = []
        for delivery_date in sorted(products_by_date.keys()):
            for product in products_by_date[delivery_date]:
                rows.append({
                    '納品日': delivery_date,
                    '製品コード': product.get('product_code', ''),
                    '製品名': product.get('product_name', ''),
                    '数量': int(product.get('quantity', 0) or 0),
                    '必要容器数': int(product.get('containers_needed', 0) or 0),
                    '容器コード': product.get('container_code', ''),
                    '容器名': product.get('container_name', '')
                })

        # 明細シート（該当なしの場合もヘッダ付きで出力）
        detail_df = pd.DataFrame(rows, columns=[
            '納品日', '製品コード', '製品名', '数量', '必要容器数', '容器コード', '容器名'
        ])
        if detail_df.empty:
            detail_df = pd.DataFrame([{
                '納品日': '',
                '製品コード': '対象データなし',
                '製品名': '',
                '数量': 0,
                '必要容器数': 0,
                '容器コード': '',
                '容器名': ''
            }])

        # サマリシート
        summary_rows = []
        for delivery_date in sorted(products_by_date.keys()):
            products = products_by_date[delivery_date]
            summary_rows.append({
                '納品日': delivery_date,
                '製品種類数': len(products),
                '合計数量': sum(int(p.get('quantity', 0) or 0) for p in products),
                '合計容器数': sum(int(p.get('containers_needed', 0) or 0) for p in products)
            })
        if not summary_rows:
            summary_rows = [{
                '納品日': '',
                '製品種類数': 0,
                '合計数量': 0,
                '合計容器数': 0
            }]
        summary_df = pd.DataFrame(summary_rows, columns=['納品日', '製品種類数', '合計数量', '合計容器数'])

        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            detail_df.to_excel(writer, sheet_name='集荷製品明細', index=False)
            summary_df.to_excel(writer, sheet_name='日別サマリ', index=False)

        output.seek(0)
        return output

    def get_daily_product_list(self, start_date: date, end_date: date) -> Dict[date, List[Dict]]:
        """
        指定期間の日別製品リストを取得

        Args:
            start_date: 開始日
            end_date: 終了日

        Returns:
            Dict[date, List[Dict]]: 日付ごとの製品リスト
        """
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT
                    DATE(ol.due_date) AS delivery_date,
                    COALESCE(p.product_code, ol.product_code) AS product_code,
                    COALESCE(p.product_name, '') AS product_name,
                    COALESCE(p.capacity, 0) AS capacity,
                    cc.container_code,
                    cc.name AS container_name,
                    COALESCE(NULLIF(ol.quantity, 0), 0) AS effective_quantity
                FROM t_order_line ol
                INNER JOIN t_order o ON ol.order_id = o.id
                LEFT JOIN m_product p
                    ON p.id = ol.product_id
                    OR (ol.product_id IS NULL AND p.product_code = ol.product_code)
                LEFT JOIN m_product_group pg ON p.product_group_id = pg.id
                LEFT JOIN m_container_capacity cc ON p.used_container_id = cc.id
                WHERE DATE(ol.due_date) BETWEEN %s AND %s
                  AND o.status = 'OPEN'
                  AND (
                        ol.order_type = 'FIRM'
                        OR (ol.order_type IS NULL AND o.order_type = 'FIRM')
                  )
                  AND (
                        pg.group_name LIKE %s
                        OR UPPER(pg.group_code) LIKE %s
                  )
                  AND COALESCE(NULLIF(ol.quantity, 0), 0) > 0
                ORDER BY delivery_date, p.product_code
            """, [
                start_date,
                end_date,
                f"%{self.TARGET_GROUP_NAME_KEYWORD}%",
                f"%{self.TARGET_GROUP_CODE_KEYWORD}%"
            ])
            rows = cursor.fetchall()

        # 日付ごとにグループ化
        daily_products: Dict[date, List[Dict]] = {}
        for row in rows:
            delivery_date = row[0]
            product_code = row[1] or ''
            product_name = row[2] or ''
            capacity = int(row[3] or 0)
            container_code = row[4] or '不明'
            container_name = row[5] or '不明容器'
            quantity = int(row[6] or 0)

            effective_capacity = capacity if capacity > 0 else 1
            containers_needed = math.ceil(quantity / effective_capacity) if quantity > 0 else 0

            if delivery_date not in daily_products:
                daily_products[delivery_date] = []

            daily_products[delivery_date].append({
                'product_code': product_code,
                'product_name': product_name,
                'quantity': quantity,
                'container_code': container_code,
                'container_name': container_name,
                'containers_needed': containers_needed
            })

        return daily_products
