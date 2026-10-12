"""親品ID切替の仕様をSQLiteメモリDBで検証する。実DBには接続しない。"""
import importlib
import json
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.db.models.deletion import ProtectedError
from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from masters.models import BOM, BOMItem, Process, Product, Routing, RoutingStep, RoutingStepMaterial
from masters.serializers import RoutingStepSerializer
from masters.views import BOMViewSet, ProductViewSet, RoutingStepViewSet


class RoutingParentProductTest(TestCase):
    def setUp(self):
        self.parent = Product.objects.create(product_code='PARENT', product_name='親品')
        self.child = Product.objects.create(product_code='CHILD', product_name='子品')
        self.other = Product.objects.create(product_code='OTHER', product_name='別親')
        self.process = Process.objects.create(process_code='PROCESS', process_name='工程')
        self.routing = Routing.objects.create(product=self.other, routing_code='ROUTE')
        self.parent_step = RoutingStep.objects.create(
            routing=self.routing, step_no=2, process=self.process,
            output_product=self.parent, parent_product=self.parent, hierarchy_path='1',
        )
        self.step = RoutingStep.objects.create(
            routing=self.routing, step_no=1, process=self.process, output_product=self.child,
            parent_product=self.parent, hierarchy_path='1.1', remark='旧親品の復旧値',
        )
        self.material = RoutingStepMaterial.objects.create(routing_step=self.parent_step, component=self.child, quantity=3)
        self.bom = BOM.objects.create(parent_product=self.parent, version='v1', valid_from='2026-01-01')
        self.item = BOMItem.objects.create(bom=self.bom, child_product=self.child, quantity=3, process=self.process)
        self.factory = APIRequestFactory()
        self.user = get_user_model().objects.create_user(username='parent_test')
        # 各移行試験は専用承認表を設定し、本番36表を小さいfixtureへ適用しない。
        mapping_patch = patch('masters.management.commands.migrate_routing_parent_products.MAPPING_PATH')
        self.mapping = mapping_patch.start()
        self.mapping.read_text.return_value = '[]'
        self.addCleanup(mapping_patch.stop)

    def approved_row(self):
        return {
            'step_id': self.step.id, 'routing_id': self.routing.id,
            'routing_code': self.routing.routing_code, 'routing_product_code': self.other.product_code,
            'output_product_id': self.child.id, 'output_product_code': self.child.product_code,
            'hierarchy_path': self.step.hierarchy_path, 'current_parent_code': 'OLD-MISSING',
            'hierarchy_parent_code': self.parent.product_code,
        }

    def request(self, view, method, data=None, pk=None):
        req = getattr(self.factory, method)('/', data or {}, format='json')
        force_authenticate(req, user=self.user)
        action = {'post': 'create', 'patch': 'partial_update', 'delete': 'destroy'}[method]
        return view.as_view({method: action})(req, **({'pk': pk} if pk else {}))

    def test_code_rename_reflects_api_and_usage_without_rewriting_legacy(self):
        self.parent.product_code = 'RENAMED'
        self.parent.save(update_fields=['product_code'])
        self.step.refresh_from_db()
        data = RoutingStepSerializer(self.step).data
        self.assertEqual(data['parent_product'], self.parent.id)
        self.assertEqual(data['parent_product_code'], 'RENAMED')
        self.assertEqual(data['parent_product_name'], '親品')
        self.assertEqual(data['usage_quantity'], 3)
        self.assertEqual(self.step.remark, '旧親品の復旧値')

    def test_parent_protect_blocks_model_and_api_delete(self):
        with self.assertRaises(ProtectedError):
            self.parent.delete()
        response = self.request(ProductViewSet, 'delete', pk=self.parent.id)
        self.assertEqual(response.status_code, 400)
        self.assertIn('参照中', response.data['detail'])
        self.assertTrue(Product.objects.filter(id=self.parent.id).exists())

    def test_unknown_id_and_legacy_input_are_rejected(self):
        for payload, field in (({'parent_product': 999999}, 'parent_product'), ({'remark': 'PARENT'}, 'remark')):
            response = self.request(RoutingStepViewSet, 'patch', payload, self.step.id)
            self.assertEqual(response.status_code, 400)
            self.assertIn(field, response.data)
        self.step.refresh_from_db()
        self.assertEqual(self.step.parent_product_id, self.parent.id)

    def test_actual_hierarchy_parent_mismatch_rejected_and_self_parent_allowed(self):
        response = self.request(RoutingStepViewSet, 'patch', {'parent_product': self.other.id}, self.step.id)
        self.assertEqual(response.status_code, 400)
        response = self.request(RoutingStepViewSet, 'patch', {'parent_product': self.child.id}, self.step.id)
        self.assertEqual(response.status_code, 200)
        self.step.refresh_from_db()
        self.assertEqual(self.step.parent_product_id, self.child.id)
        self.assertIsNone(self.step.source_bom_item_id)
        self.assertFalse(BOMItem.objects.filter(bom__parent_product=self.child, child_product=self.child).exists())

    def test_parent_optional_create_and_clear(self):
        data = {'routing': self.routing.id, 'step_no': 8, 'parallel_group': 1, 'process': self.process.id, 'hierarchy_path': '8', 'output_product': self.child.id, 'parent_product': None}
        response = self.request(RoutingStepViewSet, 'post', data)
        self.assertEqual(response.status_code, 201, response.data)
        self.assertIsNone(response.data['parent_product'])
        response = self.request(RoutingStepViewSet, 'patch', {'parent_product': None}, self.step.id)
        self.assertEqual(response.status_code, 200, response.data)
        self.step.refresh_from_db()
        self.assertIsNone(self.step.parent_product_id)

    def test_manual_create_stores_id_and_links_bom_with_usage(self):
        response = self.request(RoutingStepViewSet, 'post', {
            'routing': self.routing.id, 'step_no': 7, 'parallel_group': 1,
            'process': self.process.id, 'hierarchy_path': '1.2',
            'output_product': self.child.id, 'parent_product': self.parent.id, 'usage_quantity': 4,
        })
        self.assertEqual(response.status_code, 201, response.data)
        step = RoutingStep.objects.get(id=response.data['id'])
        self.assertEqual(step.parent_product_id, self.parent.id)
        self.assertEqual(step.source_bom_item_id, self.item.id)
        self.assertIsNone(step.remark)
        self.item.refresh_from_db()
        self.assertEqual(self.item.quantity, 4)

    def test_update_failure_rolls_back_step_and_bom(self):
        self.step.source_bom_item = self.item
        self.step.save(update_fields=['source_bom_item'])
        with patch.object(RoutingStepViewSet, '_sync_step_usage_quantity', side_effect=RuntimeError('関連保存失敗')):
            with self.assertRaises(RuntimeError):
                self.request(RoutingStepViewSet, 'patch', {'lead_time_days': 9, 'usage_quantity': 4}, self.step.id)
        self.step.refresh_from_db(); self.item.refresh_from_db()
        self.assertEqual(self.step.lead_time_days, 0)
        self.assertEqual(self.item.lead_time_days, 0)
        self.assertEqual(self.item.quantity, 3)

    def test_bom_sync_matches_id_after_code_rename(self):
        self.parent.product_code = 'CHANGED'
        self.parent.save(update_fields=['product_code'])
        from masters.views import BOMItemViewSet
        view = BOMItemViewSet()
        self.assertIn(self.step.id, view._select_sync_target_steps(self.item).values_list('id', flat=True))

    def test_bom_generation_stores_parent_id_including_final_self_parent(self):
        self.item.time_unit = 'DAY'
        self.item.save(update_fields=['time_unit'])
        req = self.factory.post('/', {
            'routing_code': 'GENERATED', 'final_process_id': self.process.id,
            'final_time_unit': 'DAY', 'final_lead_time_days': 0,
        }, format='json')
        force_authenticate(req, user=self.user)
        response = BOMViewSet.as_view({'post': 'generate_routing'})(req, pk=self.bom.id)
        self.assertEqual(response.status_code, 201, response.data)
        routing = Routing.objects.get(routing_code='GENERATED')
        generated = list(routing.steps.all())
        self.assertEqual(len(generated), 2)
        self.assertTrue(all(s.parent_product_id == self.parent.id for s in generated))
        self.assertTrue(all(s.remark is None for s in generated))
        final = next(s for s in generated if s.hierarchy_path == 'final')
        self.assertEqual(final.parent_product_id, final.output_product_id)

    def test_migration_dry_run_and_unknown_code_stop_all_updates(self):
        RoutingStep.objects.update(parent_product=None, remark='PARENT')
        output = StringIO()
        call_command('migrate_routing_parent_products', stdout=output, stderr=StringIO())
        self.assertFalse(RoutingStep.objects.exclude(parent_product=None).exists())
        self.step.remark = 'UNKNOWN'
        self.step.parent_product = None
        self.step.save(update_fields=['remark', 'parent_product'])
        with self.assertRaises(CommandError):
            call_command('migrate_routing_parent_products', apply=True, stdout=StringIO(), stderr=StringIO())
        self.assertFalse(RoutingStep.objects.exclude(parent_product=None).exists())

    def test_registered_code_migration_and_existing_fk_apply_refusal(self):
        RoutingStep.objects.update(parent_product=None, remark='PARENT')
        call_command('migrate_routing_parent_products', apply=True, stdout=StringIO(), stderr=StringIO())
        self.assertEqual(RoutingStep.objects.filter(parent_product=self.parent).count(), 2)
        with self.assertRaises(CommandError):
            call_command('migrate_routing_parent_products', apply=True, stdout=StringIO(), stderr=StringIO())

    def test_usage_priority_hierarchy_then_parent_id_then_bom(self):
        self.material.quantity = 5
        self.material.save(update_fields=['quantity'])
        self.item.quantity = 7
        self.item.save(update_fields=['quantity'])
        self.assertEqual(RoutingStepSerializer(self.step).data['usage_quantity'], 5)
        self.step.hierarchy_path = '8'
        self.step.save(update_fields=['hierarchy_path'])
        self.assertEqual(RoutingStepSerializer(self.step).data['usage_quantity'], 5)
        self.material.delete()
        self.assertEqual(RoutingStepSerializer(self.step).data['usage_quantity'], 7)

    def test_approved_correction_rechecks_context_and_uses_current_product_id(self):
        RoutingStep.objects.update(parent_product=None, remark='PARENT')
        self.step.parent_product = None
        self.step.remark = 'OLD-MISSING'
        self.step.save(update_fields=['parent_product', 'remark'])
        row = self.approved_row()
        with patch('masters.management.commands.migrate_routing_parent_products.MAPPING_PATH') as mapping:
            mapping.read_text.return_value = json.dumps([row])
            call_command('migrate_routing_parent_products', apply=True, stdout=StringIO(), stderr=StringIO())
        self.step.refresh_from_db()
        self.assertEqual(self.step.parent_product_id, self.parent.id)
        self.assertEqual(self.step.remark, 'OLD-MISSING')

    def test_approved_target_registered_self_or_empty_change_stops_every_write(self):
        RoutingStep.objects.update(parent_product=None, remark='PARENT')
        self.mapping.read_text.return_value = json.dumps([self.approved_row()])
        for changed_code in (self.child.product_code, '', self.other.product_code):
            with self.subTest(changed_code=changed_code):
                RoutingStep.objects.filter(pk=self.step.id).update(remark=changed_code)
                with self.assertRaises(CommandError):
                    call_command('migrate_routing_parent_products', apply=True, stdout=StringIO(), stderr=StringIO())
                self.assertFalse(RoutingStep.objects.exclude(parent_product=None).exists())

    def test_approved_target_missing_stops_every_write(self):
        RoutingStep.objects.update(parent_product=None, remark='PARENT')
        self.mapping.read_text.return_value = json.dumps([self.approved_row()])
        self.step.delete()
        with self.assertRaises(CommandError):
            call_command('migrate_routing_parent_products', apply=True, stdout=StringIO(), stderr=StringIO())
        self.assertFalse(RoutingStep.objects.exclude(parent_product=None).exists())

    def test_already_corrected_approved_code_still_passes_context_and_material_bom_checks(self):
        RoutingStep.objects.update(parent_product=None, remark='PARENT')
        self.mapping.read_text.return_value = json.dumps([self.approved_row()])
        call_command('migrate_routing_parent_products', apply=True, stdout=StringIO(), stderr=StringIO())
        self.step.refresh_from_db()
        self.assertEqual(self.step.parent_product_id, self.parent.id)

    def test_approved_target_context_changed_stops_every_write(self):
        RoutingStep.objects.update(parent_product=None, remark='PARENT')
        self.mapping.read_text.return_value = json.dumps([self.approved_row()])
        RoutingStep.objects.filter(pk=self.step.id).update(hierarchy_path='8')
        with self.assertRaises(CommandError):
            call_command('migrate_routing_parent_products', apply=True, stdout=StringIO(), stderr=StringIO())
        self.assertFalse(RoutingStep.objects.exclude(parent_product=None).exists())

    def test_fk_state_read_check_never_uses_or_resurrects_legacy_parent(self):
        RoutingStep.objects.filter(pk=self.step.id).update(parent_product=None, remark='UNKNOWN-LEGACY')
        self.mapping.read_text.return_value = json.dumps([self.approved_row()])
        output = StringIO()
        call_command('migrate_routing_parent_products', stdout=output, stderr=StringIO())
        self.assertIn('FK状態読取点検', output.getvalue())
        self.assertIn('移行対象=0', output.getvalue())
        self.step.refresh_from_db()
        self.assertIsNone(self.step.parent_product_id)

    def test_inline_and_standalone_admin_forms_reject_wrong_parent_allow_valid_and_exceptions(self):
        from django.contrib import admin
        from django.forms.models import model_to_dict
        from masters.admin import RoutingStepAdmin, RoutingStepInlineForm
        request = self.factory.get('/')
        request.user = self.user
        standalone = RoutingStepAdmin(RoutingStep, admin.site)
        for kind in ('inline', 'standalone'):
            for parent_id, valid in ((self.other.id, False), (self.parent.id, True), (self.child.id, True), (None, True)):
                with self.subTest(kind=kind, parent_id=parent_id):
                    instance = RoutingStep.objects.get(pk=self.step.id)
                    data = model_to_dict(instance)
                    data['parent_product'] = parent_id
                    form_class = RoutingStepInlineForm if kind == 'inline' else standalone.get_form(request, obj=instance)
                    form = form_class(data=data, instance=instance)
                    self.assertEqual(form.is_valid(), valid, form.errors)
                    if not valid:
                        self.assertIn('parent_product', form.errors)
            # 直上工程が既存データに無い場合は誤って拒否しない。
            instance = RoutingStep.objects.get(pk=self.step.id)
            instance.hierarchy_path = '8.1'
            data = model_to_dict(instance)
            data['parent_product'] = self.other.id
            form_class = RoutingStepInlineForm if kind == 'inline' else standalone.get_form(request, obj=instance)
            form = form_class(data=data, instance=instance)
            self.assertTrue(form.is_valid(), form.errors)

    def test_data_migration_failure_rolls_back_all_writes(self):
        RoutingStep.objects.update(parent_product=None, remark='PARENT')
        def fail_after_one(*_args, **_kwargs):
            RoutingStep.objects.filter(pk=self.parent_step.id).update(parent_product=self.parent)
            raise RuntimeError('一括更新失敗')
        with patch.object(RoutingStep.objects, 'bulk_update', side_effect=fail_after_one):
            with self.assertRaises(RuntimeError):
                call_command('migrate_routing_parent_products', apply=True, stdout=StringIO(), stderr=StringIO())
        self.assertFalse(RoutingStep.objects.exclude(parent_product=None).exists())

    def test_schema_and_ai_view_row_counts_columns_and_rename(self):
        field = RoutingStep._meta.get_field('parent_product')
        self.assertTrue(field.null)
        self.assertEqual(field.column, 'parent_product_id')
        self.assertIs(field.remote_field.on_delete, __import__('django.db.models', fromlist=['PROTECT']).PROTECT)
        new = importlib.import_module('ai.migrations.0051_routing_parent_product_views')
        old_step = importlib.import_module('ai.migrations.0042_ai_routing_step_view')
        old_material = importlib.import_module('ai.migrations.0043_ai_routing_step_material_view')
        with connection.cursor() as cur:
            for sql, old, view, base, count in ((new.STEP_VIEW, old_step.CREATE_VIEW, 'v_ai_routing_step', 'm_routing_step', 33), (new.MATERIAL_VIEW, old_material.CREATE_VIEW, 'v_ai_routing_step_material', 'm_routing_step_material', 20)):
                # SQLiteはCREATE OR REPLACE VIEWを持たないため作成構文だけ変える。
                cur.execute(f'DROP VIEW IF EXISTS {view}')
                cur.execute(old.replace('CREATE OR REPLACE VIEW', 'CREATE VIEW'))
                cur.execute(f'SELECT * FROM {view}')
                original_columns = [d[0] for d in cur.description]
                cur.execute(f'DROP VIEW {view}')
                cur.execute(sql.replace('CREATE OR REPLACE VIEW', 'CREATE VIEW'))
                cur.execute(f'SELECT * FROM {view}')
                self.assertEqual([d[0] for d in cur.description], original_columns)
                self.assertEqual(len(cur.description), count)
                cur.execute(f'SELECT COUNT(*) FROM {view}'); total = cur.fetchone()[0]
                cur.execute(f'SELECT COUNT(*) FROM {base}'); self.assertEqual(total, cur.fetchone()[0])
            self.parent.product_code = 'AI-RENAMED'
            self.parent.save(update_fields=['product_code'])
            cur.execute('SELECT parent_product_code FROM v_ai_routing_step WHERE id=%s', [self.step.id])
            self.assertEqual(cur.fetchone()[0], 'AI-RENAMED')
            cur.execute('SELECT step_parent_product_code FROM v_ai_routing_step_material WHERE id=%s', [self.material.id])
            self.assertEqual(cur.fetchone()[0], 'AI-RENAMED')

    def test_release_sql_source_contains_current_views_and_owner_column_changes(self):
        source = Path(__file__).resolve().parents[3] / 'scripts' / 'routing_parent_ai_views_definer.sql.txt'
        text = source.read_text(encoding='utf-8')
        new = importlib.import_module('ai.migrations.0051_routing_parent_product_views')
        self.assertIn("GRANT SELECT (`parent_product_id`)", text)
        self.assertIn("REVOKE SELECT (`remark`)", text)
        for view in (new.STEP_VIEW, new.MATERIAL_VIEW):
            expected = view.replace('CREATE OR REPLACE VIEW', "CREATE OR REPLACE DEFINER = 'pm_ai_view_owner'@'localhost' SQL SECURITY DEFINER VIEW").strip()
            self.assertIn(expected, text)
