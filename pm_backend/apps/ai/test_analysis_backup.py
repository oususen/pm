"""AI分析のテンプレート・実行履歴の書き出し・復元(analysis_backup と export/import コマンド)を検証する。

DBを作らない(SimpleTestCase)。モデルのクエリは偽物に差し替え、DBへは接続しない。
"""
import datetime as dt
import json
import tempfile
import uuid
from decimal import Decimal
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import models
from django.test import SimpleTestCase, override_settings

from ai.management.commands import export_ai_analysis_data as export_cmd
from ai.management.commands import import_ai_analysis_data as import_cmd
from ai.models import AIAnalysisRun, AIAnalysisTemplate
from ai.services import analysis_backup as backup

MAP = {backup.KIND_TEMPLATE: AIAnalysisTemplate, backup.KIND_RUN: AIAnalysisRun}
NOW = dt.datetime(2026, 10, 12, 9, 30, 15, 123456)
IMPORT_MOD = 'ai.management.commands.import_ai_analysis_data'
EXPORT_MOD = 'ai.management.commands.export_ai_analysis_data'


def sample_value(f, n):
    """フィールドの型ごとの代表値。マイクロ秒つきの日時・入れ子のJSON・UUIDなどを含める。"""
    if isinstance(f, models.DateTimeField):
        return dt.datetime(2026, 10, 1, 8, 5, 3, 654321) + dt.timedelta(days=n)
    if isinstance(f, models.DateField):
        return dt.date(2026, 9, 1) + dt.timedelta(days=n)
    if isinstance(f, models.UUIDField):
        return uuid.UUID(int=n + 1)
    if isinstance(f, models.JSONField):
        return {'日本語': [1, 2.5, None, {'a': True}], 'n': n}
    if isinstance(f, models.FloatField):
        return 1.25 + n
    if isinstance(f, (models.IntegerField, models.PositiveBigIntegerField)):
        return n + 1
    if isinstance(f, models.CharField):
        return f'{f.name}-{n}'[:f.max_length]
    if isinstance(f, models.TextField):
        return f'{f.name}の本文\n{n}'
    return None


def make_obj(model, n, **overrides):
    values = {}
    for f in model._meta.concrete_fields:
        values[f.attname] = sample_value(f, n)
        if f.is_relation:
            values[f.attname] = None
    values['id'] = n
    values['sql_sha256'] = None
    values.update(overrides)
    return SimpleNamespace(**values)


def template_obj(n, **kw):
    kw.setdefault('approved_by_id', 10)
    kw.setdefault('reviewed_by_id', 11)
    kw.setdefault('family_id', uuid.UUID(int=n))
    kw.setdefault('source_plan_id', f'plan-{n}')
    kw.setdefault('content_sha256', f'c{n}')
    return make_obj(AIAnalysisTemplate, n, **kw)


def run_obj(n, **kw):
    kw.setdefault('user_id', 10)
    return make_obj(AIAnalysisRun, n, **kw)


USERS = {10: 'alice', 11: 'bob'}


def to_rows(model, objs, users=USERS):
    rows = [backup.instance_to_row(model, o, users) for o in objs]
    return json.loads(json.dumps(rows))  # JSONを経由する


def empty_existing():
    return {backup.KIND_TEMPLATE: set(), backup.KIND_RUN: set()}


def empty_unique():
    return {k: {names: set() for names in backup.unique_field_sets(m)} for k, m in MAP.items()}


def make_plan(templates, runs, users=None, existing=None, unique=None):
    return backup.build_plan(
        MAP, templates, runs, users if users is not None else {'alice': 1, 'bob': 2},
        existing or empty_existing(), unique or empty_unique())


class SerializeTests(SimpleTestCase):
    def test_roundtrip_values_are_identical(self):
        obj = template_obj(1)
        row = to_rows(AIAnalysisTemplate, [obj])[0]
        kwargs, reason, _ = backup.row_to_kwargs(AIAnalysisTemplate, row, {'alice': 1, 'bob': 2})
        self.assertIsNone(reason)
        for f in AIAnalysisTemplate._meta.concrete_fields:
            if f.name in ('approved_by', 'reviewed_by'):
                continue
            self.assertEqual(kwargs[f.attname], getattr(obj, f.attname), f.name)
        self.assertEqual(kwargs['approved_by_id'], 1)
        self.assertEqual(kwargs['reviewed_by_id'], 2)

    def test_microseconds_json_none_survive(self):
        obj = run_obj(3, finished_at=None, approved_counts=None, fetch_seconds=None)
        row = to_rows(AIAnalysisRun, [obj])[0]
        kwargs, reason, _ = backup.row_to_kwargs(AIAnalysisRun, row, {'alice': 1})
        self.assertIsNone(reason)
        self.assertEqual(kwargs['started_at'], obj.started_at)
        self.assertEqual(kwargs['started_at'].microsecond, 654321)
        self.assertEqual(kwargs['views'], obj.views)
        self.assertIsNone(kwargs['finished_at'])
        self.assertIsNone(kwargs['approved_counts'])
        self.assertIsNone(kwargs['fetch_seconds'])
        self.assertEqual(kwargs['python_seconds'], obj.python_seconds)

    def test_decimal_and_uuid_are_strings_and_restore(self):
        self.assertEqual(backup.serialize_value(Decimal('1.10')), '1.10')
        self.assertEqual(models.DecimalField(max_digits=5, decimal_places=2).to_python('1.10'), Decimal('1.10'))
        self.assertEqual(backup.serialize_value(uuid.UUID(int=5)), str(uuid.UUID(int=5)))
        self.assertEqual(backup.serialize_value(dt.date(2026, 1, 2)), '2026-01-02')

    def test_users_are_written_as_login_id_not_user_id(self):
        row = to_rows(AIAnalysisRun, [run_obj(1, user_id=10)])[0]
        self.assertEqual(row['user_username'], 'alice')
        self.assertNotIn('user_id', row)
        self.assertNotIn('user', row)
        trow = to_rows(AIAnalysisTemplate, [template_obj(1)])[0]
        self.assertEqual((trow['approved_by_username'], trow['reviewed_by_username']), ('alice', 'bob'))
        self.assertNotIn('approved_by_id', trow)
        self.assertNotIn(10, row.values())

    def test_null_user_is_none(self):
        row = to_rows(AIAnalysisRun, [run_obj(1, user_id=None)])[0]
        self.assertIsNone(row['user_username'])

    def test_every_model_field_is_exported(self):
        for kind, model in MAP.items():
            names = {f.attname for f in model._meta.concrete_fields}
            keys = set(backup.row_keys(model))
            plain = {k for k in keys if not k.endswith('_username')}
            self.assertTrue(names - {'user_id', 'approved_by_id', 'reviewed_by_id'} <= plain, kind)
        self.assertEqual(backup.self_fk_key(AIAnalysisRun), 'refined_from_run_id')
        self.assertEqual(backup.self_fk_key(AIAnalysisTemplate), 'replaces_id')

    def test_ids_and_references_are_kept(self):
        runs = [run_obj(5, refined_from_run_id=2, template_id=77), run_obj(2)]
        rows = to_rows(AIAnalysisRun, runs)
        self.assertEqual([r['id'] for r in rows], [5, 2])
        self.assertEqual(rows[0]['refined_from_run_id'], 2)
        self.assertEqual(rows[0]['template_id'], 77)


class PlanTests(SimpleTestCase):
    def test_user_resolved_by_login_id(self):
        rows = to_rows(AIAnalysisRun, [run_obj(1, user_id=10)])
        plan = make_plan([], rows, users={'alice': 999})
        self.assertEqual(plan.runs[0][1]['user_id'], 999)

    def test_missing_user_rows_are_skipped_and_reported_not_substituted(self):
        t_rows = to_rows(AIAnalysisTemplate, [template_obj(1), template_obj(2, approved_by_id=11)])
        r_rows = to_rows(AIAnalysisRun, [run_obj(1, user_id=10), run_obj(2, user_id=11)])
        plan = make_plan(t_rows, r_rows, users={'alice': 1})  # bob がいない
        self.assertEqual([i for i, _ in plan.templates], [])  # 両方とも reviewed_by=bob
        self.assertEqual([i for i, _ in plan.runs], [1])
        reasons = {(s.kind, s.row_id, s.reason) for s in plan.skipped}
        self.assertIn(('run', 2, backup.SKIP_USER_NOT_FOUND), reasons)
        self.assertIn(('template', 1, backup.SKIP_USER_NOT_FOUND), reasons)
        self.assertTrue(any('bob' in s.detail for s in plan.skipped))
        for _i, k in plan.runs + plan.templates:
            self.assertNotIn('bob', k.values())
        self.assertEqual(len(plan.skipped), 3)

    def test_ids_are_preserved(self):
        rows = to_rows(AIAnalysisRun, [run_obj(41), run_obj(7)])
        plan = make_plan([], rows)
        self.assertEqual([(i, k['id']) for i, k in plan.runs], [(41, 41), (7, 7)])

    def test_refined_parent_is_inserted_before_child(self):
        rows = to_rows(AIAnalysisRun, [run_obj(9, refined_from_run_id=3), run_obj(3, refined_from_run_id=1), run_obj(1)])
        plan = make_plan([], rows)
        order = [i for i, _ in plan.runs]
        self.assertEqual(order, [1, 3, 9])
        self.assertEqual(dict(plan.runs)[9]['refined_from_run_id'], 3)

    def test_child_of_skipped_parent_is_skipped(self):
        rows = to_rows(AIAnalysisRun, [run_obj(1, user_id=11), run_obj(2, refined_from_run_id=1)])
        plan = make_plan([], rows, users={'alice': 1})
        self.assertEqual([i for i, _ in plan.runs], [])
        self.assertEqual({(s.row_id, s.reason) for s in plan.skipped},
                         {(1, backup.SKIP_USER_NOT_FOUND), (2, backup.SKIP_PARENT)})

    def test_parent_in_existing_rows_is_allowed(self):
        rows = to_rows(AIAnalysisRun, [run_obj(2, refined_from_run_id=1)])
        existing = {backup.KIND_TEMPLATE: set(), backup.KIND_RUN: {1}}
        plan = make_plan([], rows, existing=existing)
        self.assertEqual([i for i, _ in plan.runs], [2])

    def test_id_conflict_is_skipped_and_existing_not_overwritten(self):
        rows = to_rows(AIAnalysisRun, [run_obj(1), run_obj(2)])
        plan = make_plan([], rows, existing={backup.KIND_TEMPLATE: set(), backup.KIND_RUN: {1}})
        self.assertEqual([i for i, _ in plan.runs], [2])
        self.assertEqual([(s.row_id, s.reason) for s in plan.skipped], [(1, backup.SKIP_ID_CONFLICT)])

    def test_unique_conflict_with_other_id_is_skipped(self):
        rows = to_rows(AIAnalysisTemplate, [template_obj(1), template_obj(2, family_id=uuid.UUID(int=1), version=2)])
        plan = make_plan(rows, [])
        self.assertEqual([i for i, _ in plan.templates], [1])
        self.assertEqual(plan.skipped[0].reason, backup.SKIP_UNIQUE_CONFLICT)

    def test_dangling_template_id_warns_but_keeps_value(self):
        rows = to_rows(AIAnalysisRun, [run_obj(1, template_id=500)])
        plan = make_plan([], rows)
        self.assertEqual(plan.runs[0][1]['template_id'], 500)
        self.assertEqual(len(plan.warnings), 1)

    def test_missing_required_field_skipped(self):
        row = to_rows(AIAnalysisRun, [run_obj(1)])[0]
        del row['plan_id']
        plan = make_plan([], [row])
        self.assertEqual(plan.skipped[0].reason, backup.SKIP_MISSING_FIELD)

    def test_bad_value_skipped(self):
        row = to_rows(AIAnalysisRun, [run_obj(1)])[0]
        row['started_at'] = 'not-a-date'
        plan = make_plan([], [row])
        self.assertEqual(plan.skipped[0].reason, backup.SKIP_BAD_VALUE)

    def test_templates_inserted_before_runs(self):
        plan = make_plan(to_rows(AIAnalysisTemplate, [template_obj(1)]), to_rows(AIAnalysisRun, [run_obj(1)]))
        calls = []
        counts = backup.execute_plan(plan, lambda kind, kw: calls.append((kind, kw['id'])))
        self.assertEqual(calls, [('template', 1), ('run', 1)])
        self.assertEqual(counts, {'template': 1, 'run': 1})


class ManifestAndFilesTests(SimpleTestCase):
    def test_manifest(self):
        m = backup.build_manifest(MAP, {'template': 2, 'run': 5}, 'pm_db', NOW)
        self.assertEqual(m['exported_at'], '2026-10-12T09:30:15.123456')
        self.assertEqual(m['counts'], {'template': 2, 'run': 5})
        self.assertEqual(m['db_name'], 'pm_db')
        self.assertEqual(m['schema_hash'], backup.schema_hash(MAP))
        self.assertIn('user_username', m['schema_fields']['run'])

    def test_schema_hash_changes_when_fields_change(self):
        h = backup.schema_hash(MAP)
        with patch.object(backup, 'row_keys', lambda model: ['id']):
            self.assertNotEqual(backup.schema_hash(MAP), h)
        self.assertIsNone(backup.check_schema({'schema_hash': h}, MAP))
        self.assertIn('スキーマの版', backup.check_schema({'schema_hash': 'x'}, MAP))

    def test_schema_mismatch_message_lists_field_names_only(self):
        fields = backup.schema_fields(MAP)
        old = {k: [n for n in v if n != 'purpose'] + ['legacy_col'] for k, v in fields.items()}
        msg = backup.check_schema({'schema_hash': 'x', 'schema_fields': old}, MAP)
        self.assertIn('legacy_col', msg)
        self.assertIn('purpose', msg)

    def test_write_load_roundtrip_and_latest_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            t = to_rows(AIAnalysisTemplate, [template_obj(1)])
            r = to_rows(AIAnalysisRun, [run_obj(1)])
            m = backup.build_manifest(MAP, {'template': 1, 'run': 1}, 'db', NOW)
            backup.write_backup(base / '20261012_090000', m, t, r)
            backup.write_backup(base / '20261012_100000', m, t, r)
            (base / '20261012_110000').mkdir()  # manifest のない途中のフォルダは無視される
            self.assertEqual(backup.resolve_input_dir(base).name, '20261012_100000')
            manifest, t2, r2 = backup.load_backup(base / '20261012_100000')
            self.assertEqual((t2, r2), (t, r))
            self.assertEqual(manifest['counts'], {'template': 1, 'run': 1})
            with self.assertRaises(FileExistsError):
                backup.write_backup(base / '20261012_100000', m, t, r)  # 既存は潰さない

    def test_count_mismatch_aborts(self):
        with tempfile.TemporaryDirectory() as tmp:
            m = backup.build_manifest(MAP, {'template': 5, 'run': 0}, 'db', NOW)
            backup.write_backup(Path(tmp) / 'a', m, [], [])
            with self.assertRaises(ValueError):
                backup.load_backup(Path(tmp) / 'a')

    def test_suspended_auto_now_restores(self):
        created = AIAnalysisTemplate._meta.get_field('created_at')
        self.assertTrue(created.auto_now_add)
        with backup.suspended_auto_now(AIAnalysisTemplate):
            self.assertFalse(created.auto_now_add)
        self.assertTrue(created.auto_now_add)
        with self.assertRaises(RuntimeError):
            with backup.suspended_auto_now(AIAnalysisTemplate):
                raise RuntimeError
        self.assertTrue(created.auto_now_add)
        self.assertTrue(AIAnalysisTemplate._meta.get_field('updated_at').auto_now)


def fake_manager(objs=(), uniques=None, ids=()):
    """objs は order_by の結果(書き出し用)、ids は既存の行のID(復元用)。"""
    mgr = MagicMock()
    mgr.order_by.return_value = list(objs)

    def values_list(*args, **kwargs):
        if kwargs.get('flat'):
            return list(ids)
        return (uniques or {}).get(args, [])
    mgr.values_list.side_effect = values_list
    return mgr


def fake_user_model(users):
    model = MagicMock()
    model.objects.filter.return_value.values_list.return_value = [(pk, name) for name, pk in users.items()]
    return model


class CommandTests(SimpleTestCase):
    def make_backup(self, tmp, templates=(), runs=()):
        t = to_rows(AIAnalysisTemplate, list(templates))
        r = to_rows(AIAnalysisRun, list(runs))
        m = backup.build_manifest(MAP, {'template': len(t), 'run': len(r)}, 'prod_copy', NOW)
        backup.write_backup(Path(tmp) / '20261012_090000', m, t, r)
        return tmp

    def run_import(self, tmp, existing_t=(), existing_r=(), users=None, **opts):
        out = StringIO()
        saves = []
        self.auto_states = []
        users = {'alice': 1, 'bob': 2} if users is None else users
        opts.setdefault('i_am_on_dev', True)
        t_mgr, r_mgr = fake_manager(ids=existing_t), fake_manager(ids=existing_r)

        def fake_save(self_, *a, **kw):
            # 保存の時点で auto_now / auto_now_add が止まっていること(日時を元のまま戻すため)
            # (履歴モデルには created_at / updated_at がないため、テンプレートだけ記録する)
            if type(self_) is AIAnalysisTemplate:
                meta = type(self_)._meta
                self.auto_states.append((meta.get_field('created_at').auto_now_add, meta.get_field('updated_at').auto_now))
            saves.append((type(self_).__name__, self_.pk, kw))
        with patch.object(AIAnalysisTemplate, 'objects', t_mgr), patch.object(AIAnalysisRun, 'objects', r_mgr), \
                patch.object(AIAnalysisTemplate, 'save', fake_save), patch.object(AIAnalysisRun, 'save', fake_save), \
                patch(f'{IMPORT_MOD}.get_user_model', return_value=fake_user_model(users)), \
                patch(f'{IMPORT_MOD}.transaction') as tx, override_settings(DEBUG=True):
            try:
                call_command('import_ai_analysis_data', input_dir=tmp, stdout=out, **opts)
            finally:
                self.tx = tx
        return out.getvalue(), saves

    def test_import_inserts_with_original_ids_in_transaction(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.make_backup(tmp, [template_obj(4)], [run_obj(8, refined_from_run_id=6), run_obj(6)])
            out, saves = self.run_import(tmp)
        self.assertEqual([(n, pk) for n, pk, _ in saves],
                         [('AIAnalysisTemplate', 4), ('AIAnalysisRun', 6), ('AIAnalysisRun', 8)])
        self.assertTrue(all(kw == {'force_insert': True} for *_x, kw in saves))
        self.tx.atomic.assert_called_once()
        self.assertEqual(self.auto_states, [(False, False)])  # 保存中は auto_now 系が止まっている
        # 保存後は元に戻っている
        self.assertTrue(AIAnalysisTemplate._meta.get_field('created_at').auto_now_add)
        self.assertTrue(AIAnalysisTemplate._meta.get_field('updated_at').auto_now)
        self.assertIn('復元した 1 件', out)
        self.assertIn('スキップ: 0 件', out)

    def test_existing_rows_abort_without_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.make_backup(tmp, [template_obj(4)], [run_obj(8)])
            for kwargs in ({'existing_t': [1]}, {'existing_r': [99]}):
                with self.assertRaises(CommandError) as cm:
                    self.run_import(tmp, **kwargs)
                self.assertIn('既存の行', str(cm.exception))

    def test_abort_leaves_no_saves(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.make_backup(tmp, [template_obj(4)], [run_obj(8)])
            saves = []
            with patch.object(AIAnalysisRun, 'save', lambda *a, **k: saves.append(1)):
                with self.assertRaises(CommandError):
                    self.run_import(tmp, existing_r=[1])
            self.assertEqual(saves, [])

    def test_force_merge_adds_only_non_conflicting(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.make_backup(tmp, [template_obj(4)], [run_obj(8), run_obj(9)])
            out, saves = self.run_import(tmp, existing_r=[8], force_merge=True)
        self.assertEqual([(n, pk) for n, pk, _ in saves], [('AIAnalysisTemplate', 4), ('AIAnalysisRun', 9)])
        self.assertIn('同じIDの行が既にある', out)

    def test_skipped_user_reported_in_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.make_backup(tmp, [], [run_obj(8, user_id=10), run_obj(9, user_id=11)])
            out, saves = self.run_import(tmp, users={'alice': 1})
        self.assertEqual([pk for _n, pk, _ in saves], [8])
        self.assertIn('スキップ: 1 件', out)
        self.assertIn('ログインIDのユーザーが開発DBにない', out)
        self.assertIn('user=bob', out)

    def test_schema_mismatch_always_aborts(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.make_backup(tmp, [], [run_obj(8)])
            mpath = Path(tmp) / '20261012_090000' / 'manifest.json'
            m = json.loads(mpath.read_text(encoding='utf-8'))
            m['schema_hash'] = 'different'
            m['schema_fields']['run'] = [n for n in m['schema_fields']['run'] if n != 'purpose'] + ['legacy_col']
            mpath.write_text(json.dumps(m), encoding='utf-8')
            for opts in ({}, {'dry_run': True, 'i_am_on_dev': False}, {'force_merge': True}):
                with self.assertRaises(CommandError) as cm:
                    self.run_import(tmp, **opts)
                self.assertIn('スキーマの版', str(cm.exception))
                self.assertIn('legacy_col', str(cm.exception))
                self.assertIn('purpose', str(cm.exception))

    def test_ignore_schema_mismatch_option_does_not_exist(self):
        parser = import_cmd.Command().create_parser('manage.py', 'import_ai_analysis_data')
        self.assertNotIn('--ignore-schema-mismatch', parser.format_help())
        with tempfile.TemporaryDirectory() as tmp:
            self.make_backup(tmp, [], [run_obj(8)])
            with self.assertRaises(TypeError):
                self.run_import(tmp, ignore_schema_mismatch=True)

    def test_missing_field_is_not_filled_with_default(self):
        row = to_rows(AIAnalysisRun, [run_obj(1)])[0]
        del row['conditions']  # 既定値のある項目でも、埋めずにスキップする
        plan = make_plan([], [row])
        self.assertEqual(plan.runs, [])
        self.assertEqual(plan.skipped[0].reason, backup.SKIP_MISSING_FIELD)

    def test_dry_run_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.make_backup(tmp, [template_obj(4)], [run_obj(8), run_obj(9, user_id=11)])
            out, saves = self.run_import(tmp, users={'alice': 1}, dry_run=True, i_am_on_dev=False)
        self.assertEqual(saves, [])
        self.tx.atomic.assert_not_called()
        self.assertIn('復元できる', out)
        self.assertIn('スキップ: 2 件', out)  # テンプレートの reviewed_by=bob と履歴9

    def test_requires_dev_flag_and_debug(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.make_backup(tmp, [], [run_obj(8)])
            with self.assertRaises(CommandError) as cm:
                self.run_import(tmp, i_am_on_dev=False)
            self.assertIn('--i-am-on-dev', str(cm.exception))
            with override_settings(DEBUG=False), self.assertRaises(CommandError) as cm:
                call_command('import_ai_analysis_data', input_dir=tmp, i_am_on_dev=True, stdout=StringIO())
            self.assertIn('DEBUG=False', str(cm.exception))

    def test_export_writes_files_with_login_ids(self):
        objs_t, objs_r = [template_obj(1)], [run_obj(2, refined_from_run_id=1), run_obj(1)]
        with tempfile.TemporaryDirectory() as tmp, \
                patch.object(AIAnalysisTemplate, 'objects', fake_manager(objs_t)), \
                patch.object(AIAnalysisRun, 'objects', fake_manager(objs_r)), \
                patch(f'{EXPORT_MOD}.get_user_model', return_value=fake_user_model({n: i for i, n in USERS.items()})), \
                patch(f'{EXPORT_MOD}.datetime') as dtm:
            dtm.now.return_value = NOW
            out = StringIO()
            call_command('export_ai_analysis_data', output_dir=tmp, stdout=out)
            target = Path(tmp) / '20261012_093015'
            manifest, t, r = backup.load_backup(target)
            self.assertEqual(manifest['counts'], {'template': 1, 'run': 2})
            self.assertEqual(manifest['exported_at'], NOW.isoformat())
            self.assertEqual(r[0]['user_username'], 'alice')
            self.assertEqual(r[0]['refined_from_run_id'], 1)
            # 同じ秒に再実行しても、既存のバックアップを潰さない
            with self.assertRaises(CommandError):
                call_command('export_ai_analysis_data', output_dir=tmp, stdout=out)
            self.assertEqual(backup.load_backup(target)[0]['counts'], {'template': 1, 'run': 2})

    def test_export_aborts_when_empty(self):
        with tempfile.TemporaryDirectory() as tmp, \
                patch.object(AIAnalysisTemplate, 'objects', fake_manager([])), \
                patch.object(AIAnalysisRun, 'objects', fake_manager([])):
            with self.assertRaises(CommandError):
                call_command('export_ai_analysis_data', output_dir=tmp, stdout=StringIO())
            self.assertEqual(list(Path(tmp).iterdir()), [])
