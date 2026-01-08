# -*- coding: utf-8 -*-
"""
出荷指示書サービス
delivery_progressとproductsから出荷指示書用のデータを取得・振り分け
"""

from datetime import date
from typing import List, Dict, Any, Optional
import pandas as pd
import re
import math
from fractions import Fraction
from django.db.models import Q, Sum, F
from orders.models import DeliveryProgress
from masters.models import Product, ProductGroup, ContainerCapacity


class ShippingOrderService:
    """出荷指示書データを取得・振り分けるサービス（Django版）"""

    def get_shipping_data_by_date(self, target_date: date, customer: str = 'tiera') -> Dict[str, Any]:
        """
        指定日の出荷指示書データを取得し、4便に振り分ける（Tiera製品のみ）

        Args:
            target_date: 対象日付
            customer: 顧客名（デフォルト: 'tiera'）

        Returns:
            {
                'date': date,
                'trip1': [...],  # 06:00便
                'trip2': [...],  # 06:30便
                'trip3': [...],  # 10:00便
                'trip4': [...]   # 13:00便
            }
        """
        # Tiera製品のみを対象とする
        # 出荷指示書の対象製品（容器4-5T、特定機種名、製品群SEATBASE/TANK/SUB_BLADE）
        deliveries = DeliveryProgress.objects.filter(
            order_date__date=target_date,
            order_quantity__gt=0
        ).exclude(
            product__product_code='YD40003261'  # YD40003261は別途注意事項として表示
        ).select_related(
            'product',
            'product__product_group',
            'product__used_container'
        ).filter(
            Q(product__used_container__name__icontains='4-5T') |
            Q(product__model_name__iregex=r'^(391|17U|20U|26U|19-6|390|KOTEIKYAKU)$') |
            Q(product__product_group__group_code__iregex=r'^(SEATBASE|TANK|SIGA|KANTATSU|SUB_BLADE)$')
        ).order_by('product__product_code')

        # YD40003261（YD40003117に付ける製品）の受注数を取得
        attachment_qty = DeliveryProgress.objects.filter(
            order_date__date=target_date,
            product__product_code='YD40003261',
            order_quantity__gt=0
        ).aggregate(total=Sum('order_quantity'))['total'] or 0
        attachment_qty = int(attachment_qty)

        if not deliveries.exists():
            return {
                'date': target_date,
                'trip1': [],
                'trip2': [],
                'trip3': [],
                'trip4': [],
                'trip2_special_annotations': [],
                'attachment_note': f'YD40003261 {attachment_qty}個あり' if attachment_qty > 0 else None
            }

        # DataFrameに変換
        df_data = []
        for dp in deliveries:
            product = dp.product
            df_data.append({
                'order_id': dp.id,
                'product_id': product.id if product else None,
                'product_code': product.product_code if product else '',
                'product_name': product.product_name if product else '',
                'model_name': product.model_name or '',
                'order_quantity': dp.order_quantity,
                'capacity': product.capacity or 0,
                'container_id': product.used_container.id if product and product.used_container else None,
                'container_name': product.used_container.name if product and product.used_container else '',
                'product_group_id': product.product_group.id if product and product.product_group else None,
                'group_code': product.product_group.group_code if product and product.product_group else '',
                'group_name': product.product_group.group_name if product and product.product_group else ''
            })

        df = pd.DataFrame(df_data)

        # 便ごとに振り分け
        trip1_data = self._filter_trip1(df)
        trip2_data = self._filter_trip2(df)
        trip3_data = self._filter_trip3(df)
        trip4_data = self._split_trip1_to_trip4(trip1_data)
        trip2_special = self._build_trip2_special_annotations(trip2_data)

        return {
            'date': target_date,
            'trip1': trip1_data,
            'trip2': trip2_data,
            'trip3': trip3_data,
            'trip4': trip4_data,
            'trip2_special_annotations': trip2_special,
            'attachment_note': f'YD40003261 {attachment_qty}個あり' if attachment_qty > 0 else None
        }

    def _filter_trip1(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        1便目: 容器名が「4-5T」の製品
        """
        filtered = df[df['container_name'].str.contains('4-5T', case=False, na=False)]
        return filtered.to_dict('records')

    def _filter_trip2(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        2便目: 機種名が特定の7種、または製品群がSIGA/KANTATSU/SUB_BLADE
        ['391', '17U', '20U', '26U', '19-6', '390', 'KOTEIKYAKU']
        SUB_BLADE製品群: 専用容器なし、MAIN機種名の容器を使用
        """
        target_models = ['391', '17U', '20U', '26U', '19-6', '390', 'KOTEIKYAKU']
        special_groups = ['SIGA', 'KANTATSU', 'SUB_BLADE']

        # 機種名を正規化（大文字・小文字、空白を統一）
        df['model_name_normalized'] = df['model_name'].str.strip().str.upper()
        df['group_code_normalized'] = df['group_code'].str.strip().str.upper()

        # 完全一致または部分一致で検索
        filtered = df[
            df['model_name_normalized'].isin([m.upper() for m in target_models]) |
            df['group_code_normalized'].isin(special_groups)
        ]

        return filtered.to_dict('records')

    def _filter_trip3(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        3便目: 製品群コードが「SEATBASE」または「TANK」
        """
        target_groups = ['SEATBASE', 'TANK']

        # group_codeを正規化
        df['group_code_normalized'] = df['group_code'].str.strip().str.upper()

        filtered = df[df['group_code_normalized'].isin([g.upper() for g in target_groups])]

        return filtered.to_dict('records')

    def _split_trip1_to_trip4(self, trip1_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        4便目: 1便目と同じ製品、容器数を均等に分割

        全体の容器数を計算し、目標容器数に達するまで製品を1便目に割り当て、
        残りを4便目に割り当てることで、容器数を均等に分配する
        """
        if not trip1_data:
            return []

        # 各製品の「使用コンテナ数」（小数含む）を算出
        normalized_products = []
        total_container_usage = Fraction(0, 1)

        for item in trip1_data:
            capacity = int(item.get('capacity') or 0)
            if capacity <= 0:
                capacity = 1

            qty = int(item.get('order_quantity') or 0)
            if qty < 0:
                qty = 0

            container_usage = Fraction(qty, capacity)
            total_container_usage += container_usage

            normalized_products.append({
                'item': item,
                'original_qty': qty,
                'capacity': capacity,
                'container_usage': container_usage
            })

        # 容器は整数個なので切り上げ
        total_containers = math.ceil(total_container_usage)

        # 目標容器数（4便目がやや多め）
        target_trip1_containers = math.floor(total_containers / 2)

        # 1便目と4便目に振り分け（コンテナを共有する前提で小数管理）
        trip1_usage = Fraction(0, 1)
        trip4_data = []

        for prod_info in normalized_products:
            item = prod_info['item']
            original_qty = prod_info['original_qty']
            capacity = prod_info['capacity']
            if original_qty <= 0:
                # 0台の場合も表示整合のため4便目へコピー
                item_copy = item.copy()
                item_copy['order_quantity'] = 0
                trip4_data.append(item_copy)
                continue

            remaining_container_quota = Fraction(target_trip1_containers, 1) - trip1_usage

            if remaining_container_quota <= 0:
                # 1便目の枠がないため全量を4便目へ
                item['order_quantity'] = 0
                item_copy = item.copy()
                item_copy['order_quantity'] = original_qty
                trip4_data.append(item_copy)
                continue

            # 小数コンテナ枠を製品ごとの数量へ換算
            max_qty_for_trip1 = int(remaining_container_quota * capacity)
            max_qty_for_trip1 = min(original_qty, max_qty_for_trip1)

            if max_qty_for_trip1 <= 0:
                # 利用可能な枠が1台分に満たない場合
                item['order_quantity'] = 0
                item_copy = item.copy()
                item_copy['order_quantity'] = original_qty
                trip4_data.append(item_copy)
                continue

            trip4_qty = original_qty - max_qty_for_trip1
            item['order_quantity'] = max_qty_for_trip1

            item_copy = item.copy()
            item_copy['order_quantity'] = trip4_qty
            trip4_data.append(item_copy)

            trip1_usage += Fraction(max_qty_for_trip1, capacity)

        # 1便目の枠が余った場合は残りを順次追加（余剰を解消）
        if trip1_usage < target_trip1_containers:
            remaining_quota = Fraction(target_trip1_containers, 1) - trip1_usage
            for prod_info in normalized_products:
                if remaining_quota <= 0:
                    break

                item = prod_info['item']
                capacity = prod_info['capacity']
                original_qty = prod_info['original_qty']
                current_qty = item.get('order_quantity', 0)
                remaining_qty = max(0, original_qty - current_qty)
                if remaining_qty <= 0:
                    continue

                max_extra = int(remaining_quota * capacity)
                if max_extra <= 0:
                    continue

                add_qty = min(remaining_qty, max_extra)
                item['order_quantity'] += add_qty

                # 対応する4便目レコードも減算
                item_order_id = item.get('order_id')
                for trip4_item in trip4_data:
                    if trip4_item.get('order_id') == item_order_id:
                        trip4_item['order_quantity'] = max(0, trip4_item['order_quantity'] - add_qty)
                        break

                trip1_usage += Fraction(add_qty, capacity)
                remaining_quota = Fraction(target_trip1_containers, 1) - trip1_usage
                if remaining_quota <= 0:
                    break

        return trip4_data


    def _build_trip2_special_annotations(self, trip2_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        2便目用の特記事項（SIGA/KANTATSU）を作成
        """
        if not trip2_data:
            return []

        special_groups = ['SIGA', 'KANTATSU']
        annotations: List[Dict[str, Any]] = []

        for group_code in special_groups:
            total_containers = 0
            for item in trip2_data:
                item_group = str(item.get('group_code', '') or '').strip().upper()
                if item_group != group_code:
                    continue

                qty = int(item.get('order_quantity') or 0)
                capacity = int(item.get('capacity') or 1)
                if capacity <= 0:
                    capacity = 1

                containers = (qty + capacity - 1) // capacity
                total_containers += max(1, containers)

            if total_containers > 0:
                annotations.append({
                    'group_code': group_code,
                    'containers': total_containers
                })

        order = {'SIGA': 0, 'KANTATSU': 1}
        annotations.sort(key=lambda ann: order.get(ann.get('group_code', '').upper(), 99))
        return annotations

    def get_available_dates(self) -> List[date]:
        """
        delivery_progressに存在する日付一覧を取得
        """
        dates = DeliveryProgress.objects.filter(
            order_quantity__gt=0
        ).values('order_date__date').annotate(
        ).distinct().order_by('-order_date__date')[:30]

        return [d['order_date__date'] for d in dates]

    def _extract_main_model_name(self, model_name: str) -> str:
        """
        SUB製品の機種名からMAIN機種名を抽出
        例: '17U-L' -> '17U', '20U-R' -> '20U'

        Args:
            model_name: SUB製品の機種名

        Returns:
            MAIN機種名（-L/-Rを除いた部分）
        """
        if not model_name:
            return ''

        # -L または -R を除去
        main_name = re.sub(r'-[LR]$', '', model_name.strip(), flags=re.IGNORECASE)
        return main_name.upper()

    def get_main_container_info(self, sub_product_id: int) -> Optional[Dict[str, Any]]:
        """
        SUB製品のMAIN機種名に対応する容器情報を取得

        Args:
            sub_product_id: SUB製品のID

        Returns:
            容器情報（容器名、入り数）またはNone
        """
        try:
            sub_product = Product.objects.get(id=sub_product_id)
            if not sub_product.model_name:
                return None

            # MAIN機種名を抽出
            main_model_name = self._extract_main_model_name(sub_product.model_name)

            if not main_model_name:
                return None

            # MAIN機種名に該当する製品の容器情報を取得
            main_product = Product.objects.filter(
                model_name__iexact=main_model_name,
                capacity__isnull=False,
                capacity__gt=0
            ).select_related('used_container').first()

            if main_product:
                return {
                    'capacity': main_product.capacity,
                    'container_name': main_product.used_container.name if main_product.used_container else '',
                    'container_id': main_product.used_container.id if main_product.used_container else None
                }

            return None

        except Product.DoesNotExist:
            return None
