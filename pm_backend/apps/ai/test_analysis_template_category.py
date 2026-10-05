"""テンプレートのカテゴリ(入荷・出荷・在庫・生産・品質・その他。BOSS承認 2026-10-05)を、実ユーザー・実効権限・一時SQLiteで検証する。

保存時の必須・固定の6つ、既存の行の初期値、一覧の絞り込み、作成者と管理者による後からの変更(内容・状態は変えない)、AI相談の推薦への表示。
"""
import json
from unittest.mock import patch

from accounts.models import UserPermission
from ai.models import AIAnalysisTemplate
from ai.services import analysis_template_service as service
from ai.services.analysis_plan_store import AnalysisPlanStore
from ai.test_analysis_template_review import ReviewBase
from ai.test_analysis_templates import make_plan

CATEGORIES = {'receipt': '入荷', 'shipment': '出荷', 'inventory': '在庫', 'production': '生産', 'quality': '品質', 'other': 'その他'}


class CategoryBase(ReviewBase):
    def save(self, user, plan=None, **body):
        plan = plan or make_plan(user.pk)
        data = {'plan_id': plan['id'], 'revision': plan['revision'], **body}
        with patch.object(service.AnalysisPlanStore, 'get', lambda _s, pid, owner: AnalysisPlanStore._decode(json.dumps(plan), owner)):
            return self.call('ai-analysis-templates', user, data=data)

    def change(self, user, template, category='quality', **extra):
        return self.call('ai-analysis-template-category', user, data={'category': category, **extra}, template_id=template.pk)


class SaveCategoryTests(CategoryBase):
    def test_all_six_fixed_categories_can_be_saved_and_are_shown_with_a_label(self):
        for key, label in CATEGORIES.items():
            with self.subTest(category=key):
                response = self.save(self.creator, make_plan(self.creator.pk), category=key)
                self.assertEqual(response.status_code, 201)
                self.assertEqual((response.data['category'], response.data['category_label']), (key, label))
                self.assertEqual(AIAnalysisTemplate.objects.get(pk=response.data['id']).category, key)

    def test_category_is_required_and_only_the_fixed_six_are_accepted(self):
        before = AIAnalysisTemplate.objects.count()
        for body in ({}, {'category': 'shippment'}, {'category': ''}, {'category': None}, {'category': 5}, {'category': ['shipment']}, {'category': '出荷'}):
            with self.subTest(body=body):
                self.assertEqual(self.save(self.creator, **body).status_code, 400)
        self.assertEqual(AIAnalysisTemplate.objects.count(), before)

    def test_a_resave_of_the_same_content_returns_the_existing_row_without_changing_its_category(self):
        plan = make_plan(self.creator.pk)
        first = self.save(self.creator, plan, category='shipment')
        again = self.save(self.creator, plan, category='quality')
        self.assertEqual((first.status_code, again.status_code, again.data['id']), (201, 200, first.data['id']))
        self.assertEqual(AIAnalysisTemplate.objects.get(pk=first.data['id']).category, 'shipment')

    def test_a_correction_takes_the_requested_category(self):
        old = self.row(category='shipment')
        self.assertEqual(self.reject(self.admin, old).status_code, 200)
        plan = make_plan(self.admin.pk, revision=2)
        plan['proposal'] = {**plan['proposal'], 'title': '訂正した分析'}
        response = self.save(self.admin, plan, category='inventory', replaces=old.pk)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['category'], 'inventory')
        old.refresh_from_db()
        self.assertEqual(old.category, 'shipment')

    def test_existing_rows_default_to_other(self):
        self.assertEqual(self.row().category, 'other')
        self.assertEqual(AIAnalysisTemplate._meta.get_field('category').default, 'other')


class ListAndDetailTests(CategoryBase):
    def test_list_and_detail_show_the_category_and_the_list_can_be_filtered(self):
        ship = self.row(status='approved', category='shipment')
        recv = self.row(status='approved', category='receipt')
        rows = self.call('ai-analysis-templates', self.other, 'get').data['results']
        self.assertEqual({(r['id'], r['category'], r['category_label']) for r in rows}, {(ship.pk, 'shipment', '出荷'), (recv.pk, 'receipt', '入荷')})
        filtered = self.call('ai-analysis-templates', self.other, 'get', {'category': 'shipment'}).data['results']
        self.assertEqual([r['id'] for r in filtered], [ship.pk])
        detail = self.call('ai-analysis-template', self.other, 'get', template_id=ship.pk).data
        self.assertEqual((detail['category'], detail['category_label']), ('shipment', '出荷'))

    def test_an_invalid_filter_is_refused_and_the_filter_never_widens_visibility(self):
        self.row(status='rejected', category='quality')
        self.assertEqual(self.call('ai-analysis-templates', self.other, 'get', {'category': 'x'}).status_code, 400)
        self.assertEqual(self.call('ai-analysis-templates', self.other, 'get', {'category': 'quality'}).data['results'], [])
        self.assertEqual(len(self.call('ai-analysis-templates', self.creator, 'get', {'category': 'quality'}).data['results']), 1)
        self.assertEqual(len(self.call('ai-analysis-templates', self.admin, 'get', {'category': 'quality'}).data['results']), 1)

    def test_the_change_flag_is_only_for_the_creator_and_admins(self):
        row = self.row(status='approved')
        for user, expected in ((self.creator, True), (self.admin, True), (self.other, False)):
            with self.subTest(user=user.username):
                data = self.call('ai-analysis-template', user, 'get', template_id=row.pk).data
                self.assertEqual(data.get('can_change_category', False), expected)


class ChangeCategoryTests(CategoryBase):
    def test_creator_and_admin_can_change_it_without_touching_content_status_or_revision(self):
        for user in (self.creator, self.admin):
            with self.subTest(user=user.username):
                row = self.row(status='approved')
                before = AIAnalysisTemplate.objects.values('content_sha256', 'status', 'state_revision', 'name', 'python_code').get(pk=row.pk)
                response = self.change(user, row, 'quality')
                self.assertEqual(response.status_code, 200)
                self.assertEqual((response.data['category'], response.data['category_label']), ('quality', '品質'))
                after = AIAnalysisTemplate.objects.values('content_sha256', 'status', 'state_revision', 'name', 'python_code', 'category').get(pk=row.pk)
                self.assertEqual({k: after[k] for k in before}, before)
                self.assertEqual(after['category'], 'quality')

    def test_it_can_be_changed_in_every_state(self):
        for status in ('pending_admin', 'approved', 'rejected', 'superseded'):
            with self.subTest(status=status):
                row = self.row(status=status)
                self.assertEqual(self.change(self.creator, row, 'inventory').status_code, 200)

    def test_others_get_404_without_a_change_and_the_edit_permission_is_required(self):
        row = self.row(status='approved', category='shipment')
        self.assertEqual(self.change(self.other, row).status_code, 404)
        self.assertEqual(self.call('ai-analysis-template-category', None, data={'category': 'quality'}, template_id=row.pk).status_code, 403)
        UserPermission.objects.filter(user=self.creator, resource='ai.analysis').update(can_edit=False)
        self.assertEqual(self.change(self.creator, row).status_code, 403)
        self.assertEqual(self.change(self.admin, self.row(status='approved'), 'receipt').status_code, 200)
        row.refresh_from_db()
        self.assertEqual(row.category, 'shipment')
        self.assertEqual(self.change(self.admin, row.__class__(pk=999999)).status_code, 404)

    def test_invalid_values_and_extra_keys_are_refused(self):
        row = self.row(status='approved', category='shipment')
        for category in ('x', '', None, 5, '出荷'):
            with self.subTest(category=category):
                self.assertEqual(self.change(self.creator, row, category).status_code, 400)
        self.assertEqual(self.change(self.creator, row, 'quality', status='approved').status_code, 400)
        self.assertEqual(self.call('ai-analysis-template-category', self.creator, data={}, template_id=row.pk).status_code, 400)
        row.refresh_from_db()
        self.assertEqual(row.category, 'shipment')
