from django.test import TestCase
from datetime import date
from openpyxl import Workbook

from outsource.models import OutsourceOrder
from outsource.services.csv_import import import_fb_csv, import_fb_excel


class FBOrderImportServiceTest(TestCase):
    def test_import_fb_csv_creates_order(self):
        content = (
            '品目コード,品目名称,塗装名,塗装日,数量\n'
            'B850070311091,FBR-ﾒｲﾝﾌﾚｰﾑRﾌﾞｸﾐ,FBR GY,2026/6/9,150\n'
        ).encode('utf-8')

        result = import_fb_csv(content, encoding='utf-8')

        self.assertEqual(len(result['created']), 1)
        order = OutsourceOrder.objects.get()
        self.assertEqual(order.case_no, '20260609-B850070311091')
        self.assertEqual(order.painting_name, 'FBR GY')
        self.assertEqual(order.order_qty, 150)

    def test_import_fb_excel_creates_orders_and_carries_forward_denpyo_info(self):
        wb = Workbook()
        ws = wb.active
        ws.append(['伝票区分', '伝票タイプ', '品目コード', '品目名称', '発注数', '納入期日'])
        ws.append(['302490-260707', 'ZNB3', 'B852950411090', '品目A', 100, '20260707'])
        ws.append([None, None, 'B852950421091', '品目B', 150, '20260707'])

        from io import BytesIO
        buf = BytesIO()
        wb.save(buf)

        result = import_fb_excel(buf.getvalue())

        self.assertEqual(len(result['created']), 2)
        orders = list(OutsourceOrder.objects.order_by('item_code'))
        self.assertEqual(orders[0].painting_name, 'ZNB3 / 302490-260707')
        self.assertEqual(orders[1].painting_name, 'ZNB3 / 302490-260707')
        self.assertEqual(orders[1].case_no, '20260707-B852950421091')

    def test_first_article_candidate_is_collected_when_no_recent_order(self):
        content = (
            '品目コード,品目名称,塗装名,塗装日,数量\n'
            'B850070311091,FBR-ﾒｲﾝﾌﾚｰﾑRﾌﾞｸﾐ,FBR GY,2026/6/9,150\n'
        ).encode('utf-8')

        result = import_fb_csv(content, encoding='utf-8')

        self.assertEqual(len(result['first_article_candidates']), 1)
        candidate = result['first_article_candidates'][0]
        self.assertEqual(candidate['product_number'], '850070-3110')
        self.assertEqual(candidate['case_no'], '20260609-B850070311091')

    def test_first_article_candidate_is_not_collected_when_recent_order_exists(self):
        OutsourceOrder.objects.create(
            case_no='20260415-B850070311091',
            item_code='B850070311091',
            item_name='既存品',
            order_qty=100,
            painting_name='既存',
            painting_date=date(2026, 4, 15),
            status='IMPORTED',
        )

        content = (
            '品目コード,品目名称,塗装名,塗装日,数量\n'
            'B850070311091,FBR-ﾒｲﾝﾌﾚｰﾑRﾌﾞｸﾐ,FBR GY,2026/6/9,150\n'
        ).encode('utf-8')

        result = import_fb_csv(content, encoding='utf-8')

        self.assertEqual(result['first_article_candidates'], [])
