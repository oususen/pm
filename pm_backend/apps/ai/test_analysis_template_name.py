"""テンプレートの名称(保存時の入力・承認前の変更・同じ名称の警告。BOSS承認 2026-10-08、変更は案C=承認前だけ)を検証する。

名称は承認対象のハッシュに入るため、変更するときはハッシュを計算し直し、状態の版を進める(古い内容を見たままの承認を、409で防ぐ)。
"""
from ai.models import AIAnalysisTemplate
from ai.services import analysis_template_service as service
from ai.test_analysis_template_category import CategoryBase
from ai.services.analysis_template_review_service import _stored_hash  # 読み戻した値からのハッシュの再計算が、一致することの確認に使う
from ai.test_analysis_templates import make_plan


class SaveNameTests(CategoryBase):
    def test_the_entered_name_is_saved_and_goes_into_the_hash(self):
        plan = make_plan(self.creator.pk)
        named = self.save(self.creator, plan, category='shipment', name='  8月の日別出荷  ')
        self.assertEqual(named.status_code, 201)
        self.assertEqual(named.data['name'], '8月の日別出荷')  # 前後の空白は除く
        row = AIAnalysisTemplate.objects.get(pk=named.data['id'])
        self.assertEqual(row.name, '8月の日別出荷')
        self.assertEqual(_stored_hash(row), row.content_sha256)  # 名称を含めて、読み戻した値のハッシュと一致する

    def test_without_a_name_the_plan_title_is_used_as_before(self):
        response = self.save(self.creator, make_plan(self.creator.pk), category='shipment')
        self.assertEqual(response.data['name'], '日別出荷の分析')

    def test_invalid_names_are_rejected_and_nothing_is_saved(self):
        before = AIAnalysisTemplate.objects.count()
        for name in ('', '   ', 5, None, ['a'], 'a\nb', 'a\x00b', 'あ' * 301):
            with self.subTest(name=name):
                body = {'category': 'shipment', 'name': name}
                self.assertEqual(self.save(self.creator, **body).status_code, 400)
        self.assertEqual(AIAnalysisTemplate.objects.count(), before)
        self.assertEqual(self.save(self.creator, make_plan(self.creator.pk), category='shipment', name='あ' * 300).status_code, 201)  # 上限ちょうどは可

    def test_the_response_counts_same_names_in_the_visible_range(self):
        # 一覧は、承認待ちの行も、名称・目的・状態・カテゴリだけは、全員に見せる(全文は、作成者と管理者だけ)。数えるのは、一覧で見える範囲
        self.row(name='同じ名前', status='approved')
        self.row(name='同じ名前', status='pending_admin')
        self.row(name='同じ名前', status='rejected')
        mine = self.save(self.creator, make_plan(self.creator.pk), category='shipment', name='同じ名前')
        visible_before = service.visible_templates(self.creator, False).filter(name='同じ名前').count() - 1  # 今保存した行を除く
        self.assertEqual(mine.data['same_name_count'], visible_before)
        self.assertGreaterEqual(mine.data['same_name_count'], 2)
        theirs = self.save(self.other, make_plan(self.other.pk), category='shipment', name='同じ名前')
        self.assertEqual(theirs.data['same_name_count'], service.visible_templates(self.other, False).filter(name='同じ名前').count() - 1)

    def test_the_list_can_be_filtered_by_exact_name_within_the_visible_range(self):
        self.row(name='重複確認', status='approved')
        self.row(name='重複確認', status='pending_admin')
        self.row(name='別の名前', status='approved')
        for user in (self.other, self.admin):
            with self.subTest(user=user.username):
                found = self.call('ai-analysis-templates', user, method='get', data={'name': '重複確認'})
                self.assertEqual(found.data['count'], service.visible_templates(user, user is self.admin).filter(name='重複確認').count())
                self.assertEqual({row['name'] for row in found.data['results']}, {'重複確認'})
        self.assertEqual(self.call('ai-analysis-templates', self.other, method='get', data={'name': ' '}).status_code, 400)


class RenameTests(CategoryBase):
    def rename(self, user, template, name='新しい名前', **extra):
        return self.call('ai-analysis-template-name', user, data={'name': name, **extra}, template_id=template.pk)

    def test_creator_and_admin_can_rename_before_approval_and_the_hash_is_recomputed(self):
        for user in (self.creator, self.admin):
            with self.subTest(user=user.username):
                row = self.row(name='元の名前', status='pending_admin')
                old_hash, old_revision = row.content_sha256, row.state_revision
                response = self.rename(user, row, name=f'{user.username}の名前')
                self.assertEqual(response.status_code, 200)
                row.refresh_from_db()
                self.assertEqual(row.name, f'{user.username}の名前')
                self.assertNotEqual(row.content_sha256, old_hash)
                self.assertEqual(_stored_hash(row), row.content_sha256)       # 再利用の照合が、通る
                self.assertEqual(row.state_revision, old_revision + 1)        # 古い内容を見たままの承認を、防ぐ
                self.assertEqual(row.status, 'pending_admin')

    def test_a_stale_approval_after_rename_is_rejected_with_409(self):
        row = self.row(name='元の名前', status='pending_admin')
        seen_revision = row.state_revision
        self.assertEqual(self.rename(self.creator, row).status_code, 200)
        self.assertEqual(self.approve(self.admin, row, revision=seen_revision).status_code, 409)
        row.refresh_from_db()
        self.assertEqual(row.status, 'pending_admin')

    def test_other_users_get_404_and_the_row_is_unchanged(self):
        row = self.row(name='元の名前', status='pending_admin')
        self.assertEqual(self.rename(self.other, row).status_code, 404)
        self.assertEqual(self.rename(None, row).status_code, 403)
        row.refresh_from_db()
        self.assertEqual(row.name, '元の名前')

    def test_approved_rejected_and_superseded_cannot_be_renamed(self):
        for status in ('approved', 'rejected', 'superseded'):
            with self.subTest(status=status):
                row = self.row(name='元の名前', status=status)
                before = row.content_sha256
                self.assertEqual(self.rename(self.admin, row).status_code, 409)
                row.refresh_from_db()
                self.assertEqual((row.name, row.content_sha256), ('元の名前', before))

    def test_invalid_names_and_extra_keys_are_rejected(self):
        row = self.row(name='元の名前', status='pending_admin')
        for name in ('', '  ', 5, None, 'a\nb', 'あ' * 301):
            with self.subTest(name=name):
                self.assertEqual(self.rename(self.creator, row, name=name).status_code, 400)
        self.assertEqual(self.call('ai-analysis-template-name', self.creator, data={'name': 'x', 'status': 'approved'}, template_id=row.pk).status_code, 400)
        row.refresh_from_db()
        self.assertEqual(row.name, '元の名前')

    def test_rename_does_not_change_the_other_content_or_the_category(self):
        row = self.row(name='元の名前', status='pending_admin', category='quality')
        before = {field: getattr(row, field) for field in ('purpose', 'sql_steps', 'python_code', 'executed_code_sha256', 'sql_sha256', 'python_sha256', 'category')}
        self.assertEqual(self.rename(self.creator, row).status_code, 200)
        row.refresh_from_db()
        self.assertEqual({field: getattr(row, field) for field in before}, before)

    def test_the_detail_shows_can_rename_only_before_approval(self):
        pending = self.row(status='pending_admin')
        approved = self.row(status='approved')
        self.assertTrue(self.call('ai-analysis-template', self.creator, method='get', template_id=pending.pk).data['can_rename'])
        self.assertFalse(self.call('ai-analysis-template', self.admin, method='get', template_id=approved.pk).data['can_rename'])
        self.assertNotIn('can_rename', self.call('ai-analysis-template', self.other, method='get', template_id=approved.pk).data)

    def test_the_renamed_template_can_still_be_reused(self):
        # 名称を変えてもハッシュが整合しているため、再利用の照合(保存ハッシュの再計算)が、通る
        row = self.row(name='元の名前', status='pending_admin')
        self.assertEqual(self.rename(self.creator, row).status_code, 200)
        row.refresh_from_db()
        self.assertEqual(service._content_sha256({
            'name': row.name, 'purpose': row.purpose, 'procedure': row.procedure, 'output_spec': row.output_spec, 'conditions': row.conditions,
            'datasets': row.datasets, 'date_from': row.date_from, 'date_to': row.date_to, 'sql_steps': row.sql_steps, 'python_code': row.python_code,
            'wrapper_version': row.wrapper_version, 'executed_code_sha256': row.executed_code_sha256, 'parameters': row.parameters}), row.content_sha256)
