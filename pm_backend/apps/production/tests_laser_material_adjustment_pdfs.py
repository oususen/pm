from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from production.views_laser_weekly_plan import LaserWeeklyPlanViewSet, ApprovalRequest


def approval(approval_id, start='2026-10-12', end='2026-10-16', saved_at='2026-10-14T09:30:00', supplier='MEISEI'):
    return SimpleNamespace(id=approval_id, context={
        'supplier': supplier, 'lock_start_date': start, 'lock_end_date': end,
        'material_order_adjustment_pdf_files': {supplier: {'url': f'/media/adjustment-{approval_id}.pdf', 'saved_at': saved_at}},
    })


class LaserMaterialAdjustmentPdfsTest(SimpleTestCase):
    # ORMを差し替え、読み取りAPIの契約のみを検証する。テストDBは作らない。
    def get_response(self, supplier=None, rows=()):
        request = APIRequestFactory().get('/api/laser-weekly-plans/material-order-adjustment-pdfs/',
                                          {} if supplier is None else {'supplier': supplier})
        force_authenticate(request, user=SimpleNamespace(is_authenticated=True))
        with patch.object(ApprovalRequest.objects, 'filter', return_value=rows) as query:
            response = LaserWeeklyPlanViewSet.as_view({'get': 'material_order_adjustment_pdfs'})(request)
        return response, query

    def test_supplier_required_and_invalid_rejected_without_query(self):
        for supplier in (None, '', 'OTHER', 'meisei'):
            with self.subTest(supplier=supplier):
                response, query = self.get_response(supplier)
                self.assertEqual(response.status_code, 400)
                query.assert_not_called()

    def test_all_periods_descending_and_no_status_or_active_or_week_filter(self):
        rows = [approval(8, '2026-09-28', '2026-10-02'), approval(14), approval(12, '2026-10-05', '2026-10-09')]
        response, query = self.get_response('MEISEI', rows)
        self.assertEqual(response.status_code, 200)
        query.assert_called_once_with(route_config__item_key='laser_material_order', context__supplier='MEISEI')
        self.assertEqual([item['approval_id'] for item in response.data['items']], [14, 12, 8])
        self.assertEqual(response.data['items'][0], {
            'approval_id': 14, 'start_date': '2026-10-12', 'end_date': '2026-10-16',
            'saved_at': '2026-10-14T09:30:00', 'url': '/media/adjustment-14.pdf',
        })

    def test_same_period_latest_saved_time_then_highest_id(self):
        rows = [approval(20, saved_at='2026-10-14T08:30:00'), approval(14), approval(15)]
        response, _ = self.get_response('MEISEI', rows)
        self.assertEqual([item['approval_id'] for item in response.data['items']], [15])

    def test_supplier_separation_empty_and_saved_url_only(self):
        response, query = self.get_response('SATO', [approval(8), approval(9, supplier='SATO')])
        query.assert_called_once_with(route_config__item_key='laser_material_order', context__supplier='SATO')
        self.assertEqual([item['approval_id'] for item in response.data['items']], [9])
        response, _ = self.get_response('SATO')
        self.assertEqual(response.data, {'items': []})

    def test_invalid_metadata_is_not_repaired_or_replaced_with_original_pdf(self):
        rows = []
        for index, (key, value) in enumerate([
            ('material_order_adjustment_pdf_files', None),
            ('material_order_adjustment_pdf_files', []),
            ('material_order_adjustment_pdf_files', {'MEISEI': []}),
            ('material_order_adjustment_pdf_files', {'MEISEI': {'url': ''}}),
            ('lock_start_date', None), ('lock_end_date', 'invalid'),
            ('lock_end_date', '2026-10-01'),
            ('material_order_adjustment_pdf_files', {'MEISEI': {'url': '/media/saved.pdf', 'saved_at': 'invalid'}}),
            ('material_order_adjustment_pdf_files', {'MEISEI': {'url': '/media/saved.pdf', 'saved_at': '2026-10-14T09:30:00+09:00'}}),
        ]):
            row = approval(index)
            row.context[key] = value
            row.context['material_order_pdf_files'] = {'MEISEI': {'url': '/media/original.pdf'}}
            rows.append(row)
        rows.append(SimpleNamespace(id=99, context=[]))
        response, _ = self.get_response('MEISEI', rows)
        self.assertEqual(response.data, {'items': []})

    def test_more_than_default_page_size_is_returned_without_limit(self):
        rows = [approval(index, f'2026-09-{index:02d}', f'2026-09-{index:02d}') for index in range(1, 31)]
        response, _ = self.get_response('MEISEI', rows)
        self.assertEqual(len(response.data['items']), 30)

    def test_post_is_not_supported(self):
        request = APIRequestFactory().post('/api/laser-weekly-plans/material-order-adjustment-pdfs/', {'supplier': 'MEISEI'})
        force_authenticate(request, user=SimpleNamespace(is_authenticated=True))
        with patch.object(ApprovalRequest.objects, 'filter') as query:
            response = LaserWeeklyPlanViewSet.as_view({'get': 'material_order_adjustment_pdfs'})(request)
        self.assertEqual(response.status_code, 405)
        query.assert_not_called()
