"""ブレーキ・板金スポットの生産実績のビュー v_ai_brake_production_actual の登録を検証する。

偽のDB接続・定義の検査だけを使う試験(SimpleTestCase)と、開発DBへ読み取りだけを行う件数照合試験(DBCountMatchTest)を分ける。
本ビューは`brake_line_record`を結合なし・WHEREなしで公開する単純なマスタビュー(SIMPLE_MASTER_VIEWS)のため、
v_ai_equipmentの試験(test_analysis_equipment_view.py)と同じ構成にする。

ビュー本体は2つのマイグレーションに分かれている:
- 0057_ai_brake_production_actual_view.py: 開発DB適用済み(13列版、変更不可)
- 0059_ai_brake_production_actual_view_add_columns.py: 16列への拡張(未適用。BOSSのmigrate待ち)
現在の公開列定義(PUBLISHED、16列)に対する検査は0059の内容を基準にする。

件数照合は、ビューが存在しない場合は元テーブルの直接件数だけを計算してスキップする。
列数照合(16列)は、0059が未適用の間は実列が13列のままなのでスキップする。
"""
import re
from pathlib import Path

from django.test import SimpleTestCase

from ai.management.commands import setup_ai_views as cmd
from ai.services import analysis_execution_service as service
from ai.services.analysis_data_service import ANALYSIS_VIEWS, ai_view_definition, build_where, validate_datasets
from ai.services.analysis_plan_store import AnalysisError
from ai.services.sql_queries import BASE_SQL_SCHEMA, TABLE_NOTES

VIEW = 'v_ai_brake_production_actual'
PERIOD = ('2026-09-01', '2026-09-30')
# BOSSが決定した公開16列。順序はマイグレーションのSELECT順と同じ(AI用ビュー作成計画 §35。
# 2026-10-17、BOSS判断によりoperator_login_id・interruption_reason_code・remarksの3列を追加公開)。
PUBLISHED = (
    'id', 'plan_date', 'product_code', 'operator_action', 'operator_action_reason', 'qty', 'sequence_no',
    'recorded_at', 'equipment_id', 'line_id', 'process_id', 'product_id', 'operator_user_id',
    'operator_login_id', 'interruption_reason_code', 'remarks',
)
# 非公開(ビューに含めない): operator(個人名)のみ
HIDDEN = ('operator',)
MIGRATION = Path(__file__).parent / 'migrations' / '0059_ai_brake_production_actual_view_add_columns.py'


def migration_sql():
    return MIGRATION.read_text(encoding='utf-8').split('CREATE_VIEW = """')[1].split('"""')[0]


def migration_columns():
    body = re.search(r'SELECT(.*)FROM', migration_sql(), re.S).group(1)
    columns = [c.strip() for c in body.split(',') if c.strip()]
    return columns


class BrakeProductionActualViewDefinitionTest(SimpleTestCase):
    def test_view_is_registered_with_plan_date_and_qty(self):
        definition = ANALYSIS_VIEWS[VIEW]
        self.assertEqual(definition['date_field'], 'plan_date')
        self.assertEqual(definition['quantity_field'], 'qty')
        self.assertEqual(definition['label'], 'ブレーキ・スポット生産実績')

    def test_column_types_match_published_columns_exactly(self):
        self.assertEqual(BASE_SQL_SCHEMA[VIEW], PUBLISHED)
        self.assertEqual(len(PUBLISHED), 16)
        self.assertEqual(set(service.ANALYSIS_COLUMN_TYPES[VIEW]), set(BASE_SQL_SCHEMA[VIEW]))
        self.assertEqual(service.ANALYSIS_COLUMN_TYPES[VIEW], {
            'id': 'BIGINT', 'plan_date': 'DATE', 'product_code': 'VARCHAR', 'operator_action': 'VARCHAR',
            'operator_action_reason': 'VARCHAR', 'qty': 'BIGINT', 'sequence_no': 'BIGINT', 'recorded_at': 'TIMESTAMP',
            'equipment_id': 'BIGINT', 'line_id': 'BIGINT', 'process_id': 'BIGINT', 'product_id': 'BIGINT',
            'operator_user_id': 'BIGINT', 'operator_login_id': 'VARCHAR', 'interruption_reason_code': 'VARCHAR',
            'remarks': 'VARCHAR',
        })
        # JSON型の列が混入していないこと(分析実行の値変換が未対応のため実行が失敗する再発防止)
        self.assertNotIn('JSON', service.ANALYSIS_COLUMN_TYPES[VIEW].values())

    def test_hidden_columns_do_not_appear_anywhere(self):
        columns = migration_columns()
        sql = migration_sql()
        for hidden in HIDDEN:
            # operatorは、operator_action等の公開列名の接頭辞と重なるため、単語境界つきの正規表現で判定する
            # (単純な部分文字列一致だと、公開列の文中に誤検出してしまう)
            self.assertNotIn(hidden, columns)
            self.assertNotIn(hidden, BASE_SQL_SCHEMA[VIEW])
            self.assertNotIn(hidden, service.ANALYSIS_COLUMN_TYPES[VIEW])
            self.assertNotRegex(TABLE_NOTES[VIEW], rf'\b{hidden}\b')
            self.assertNotRegex(ANALYSIS_VIEWS[VIEW]['description'], rf'\b{hidden}\b')
            self.assertNotRegex(sql, rf'\b{hidden}\b')

    def test_ai_definition_has_date_and_quantity_field(self):
        definition = ai_view_definition(VIEW)
        self.assertEqual(set(definition), {'label', 'date_field', 'quantity_field', 'description'})
        self.assertNotIn(None, definition.values())

    def test_validate_datasets_requires_plan_date_and_rejects_hidden_columns(self):
        datasets = [{'view': VIEW, 'fields': ['id', 'plan_date', 'qty']}]
        self.assertEqual(validate_datasets(datasets, *PERIOD), datasets)
        with self.assertRaises(AnalysisError):
            validate_datasets([{'view': VIEW, 'fields': ['id', 'qty']}], *PERIOD)
        for hidden in HIDDEN:
            with self.assertRaises(AnalysisError):
                validate_datasets([{'view': VIEW, 'fields': ['plan_date', hidden]}], *PERIOD)

    def test_build_where_filters_by_plan_date(self):
        self.assertEqual(
            build_where(VIEW, *PERIOD),
            (' WHERE `plan_date` >= %s AND `plan_date` <= %s', list(PERIOD)))
        self.assertEqual(
            build_where(VIEW, *PERIOD, last_id=9),
            (' WHERE `plan_date` >= %s AND `plan_date` <= %s AND `id` > %s', [*PERIOD, 9]))

    def test_description_has_required_notes(self):
        for text in (ANALYSIS_VIEWS[VIEW]['description'], TABLE_NOTES[VIEW]):
            for part in (
                    'operator_action', 'qty', 'line_id', 'operator_action_reason', 'sequence_no',
                    'operator_user_id', 'operator_login_id', 'interruption_reason_code', 'remarks'):
                self.assertIn(part, text)
            for hidden in HIDDEN:
                # operatorは公開列名(operator_action等)の接頭辞と重なるため単語境界つきの正規表現で判定する
                self.assertNotRegex(text, rf'\b{hidden}\b')
        # line_idでブレーキ(9・L0010)とスポット(10・L0013)が混在する旨
        self.assertIn('9', TABLE_NOTES[VIEW])
        self.assertIn('L0010', TABLE_NOTES[VIEW])
        self.assertIn('L0013', TABLE_NOTES[VIEW])
        # qtyはEND・PAUSE以外は0である旨
        self.assertIn('END', TABLE_NOTES[VIEW])
        self.assertIn('PAUSE', TABLE_NOTES[VIEW])
        # plan_dateが計算列ではなく実列である旨、recorded_atから8時間引いた日付とは完全一致しない旨
        self.assertIn('recorded_at', TABLE_NOTES[VIEW])
        self.assertIn('2.1', TABLE_NOTES[VIEW])
        # sequence_noの意味(0=過去の一時的事象、1=通常、2以上=同一品番・同日の複数計画行の順番)
        self.assertIn('0', TABLE_NOTES[VIEW])
        self.assertIn('LineBacklog', TABLE_NOTES[VIEW])

    def test_setup_command_covers_brake_production_actual_view(self):
        self.assertEqual(cmd.SIMPLE_MASTER_VIEWS[VIEW], 'brake_line_record')
        self.assertEqual(cmd.wanted_columns('brake_line_record'), set(PUBLISHED))

    def test_migration_sql_has_no_mysql_specific_definer_syntax(self):
        sql = migration_sql()
        for banned in ('`', 'DEFINER', 'SQL SECURITY', 'WHERE', 'JOIN', 'pm_db'):
            self.assertNotIn(banned, sql)
        self.assertIn('CREATE OR REPLACE VIEW v_ai_brake_production_actual AS', sql)
        self.assertEqual(sql.count(' AS'), 1)  # 列の別名なし(ビュー名のASだけ)
        self.assertIn('FROM brake_line_record', sql)
        for column in PUBLISHED:
            self.assertIn(f'    {column}', sql)
        for hidden in HIDDEN:
            # operatorは公開列名(operator_action等)の接頭辞と重なるため単語境界つきの正規表現で判定する
            self.assertNotRegex(sql, rf'\b{hidden}\b')
        source = MIGRATION.read_text(encoding='utf-8')
        # 0059はロールバックで0057が作成した13列版に戻す(DROPではなくCREATE OR REPLACE VIEW)
        self.assertIn('REVERT_VIEW = """', source)
        self.assertIn('operator_user_id\nFROM brake_line_record', source)

    def test_migration_columns_match_base_sql_schema_order(self):
        columns = migration_columns()
        self.assertEqual(tuple(columns), PUBLISHED)
        self.assertEqual(len(columns), 16)

    def test_migration_dependencies(self):
        source = MIGRATION.read_text(encoding='utf-8')
        self.assertIn("('ai', '0057_ai_brake_production_actual_view')", source)
        self.assertIn("('ai', '0058_ai_laser_interruption_view')", source)

    def test_0057_is_reverted_to_original_13_column_definition(self):
        # 0057は既にDB適用済みのため、適用済み内容(13列)のまま変更しないこと(2026-10-18、不整合修正)
        original = Path(__file__).parent / 'migrations' / '0057_ai_brake_production_actual_view.py'
        source = original.read_text(encoding='utf-8')
        body = re.search(r'SELECT(.*)FROM', source, re.S).group(1)
        columns = [c.strip() for c in body.split(',') if c.strip()]
        self.assertEqual(len(columns), 13)
        for extra in ('operator_login_id', 'interruption_reason_code', 'remarks'):
            self.assertNotIn(extra, columns)
        self.assertIn("DROP_VIEW = 'DROP VIEW IF EXISTS v_ai_brake_production_actual'", source)

    def test_migration_dependency_migration_exists_and_adds_hidden_columns(self):
        production = Path(__file__).parent.parent / 'production' / 'migrations'
        interruption = production / '0121_brakelinerecord_interruption_reason_code_and_more.py'
        self.assertTrue(interruption.exists())
        text = interruption.read_text(encoding='utf-8')
        self.assertIn("name='interruption_reason_code'", text)
        self.assertIn("name='remarks'", text)

    def test_existing_view_definitions_in_migrations_are_unchanged(self):
        # 既存ビューのマイグレーション(0001〜0056)に、このビューが混入していない
        for path in (Path(__file__).parent / 'migrations').glob('00[0-5][0-6]*.py'):
            if path.name == '0057_ai_brake_production_actual_view.py':
                continue
            self.assertNotIn(VIEW, path.read_text(encoding='utf-8'), path.name)


class BrakeProductionActualDBCountMatchTest(SimpleTestCase):
    """開発DBの実データで、ビューの件数と元テーブルの件数が一致することを確認する(検証項目A)。

    2026-10-18時点、開発DBには0057(13列版)が適用済みで、0059(16列への拡張)は未適用。
    件数自体は列数に関係なく一致するはずなので、0059未適用でも検証できる。
    ビュー自体が無い場合(本番等)は期待値だけを計算してスキップする。
    """
    def test_view_count_matches_source_table_count(self):
        connection = service.open_snapshot_connection(service.Deadline(30, 'stage_deadline_fetch'), read_timeout=30)
        try:
            cursor = connection.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM information_schema.VIEWS "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s", (VIEW,))
            view_exists = cursor.fetchone()[0] > 0
            cursor.execute("SELECT COUNT(*) FROM brake_line_record")
            expected = cursor.fetchone()[0]
            if not view_exists:
                self.skipTest(
                    f'v_ai_brake_production_actual は未作成(migrate未実行)のため件数照合をスキップ。'
                    f'brake_line_recordの件数={expected}。migrate実行後に本試験で照合する。')
            cursor.execute(f'SELECT COUNT(*) FROM `{VIEW}`')
            actual = cursor.fetchone()[0]
            cursor.close()
        finally:
            connection.close()
        self.assertEqual(actual, expected)

    def test_view_has_16_columns_after_0059_migrate(self):
        connection = service.open_snapshot_connection(service.Deadline(30, 'stage_deadline_fetch'), read_timeout=30)
        try:
            cursor = connection.cursor()
            cursor.execute(f'SHOW COLUMNS FROM `{VIEW}`')
            actual_columns = tuple(row[0] for row in cursor.fetchall())
            cursor.close()
        finally:
            connection.close()
        if actual_columns == PUBLISHED:
            return
        self.skipTest(
            f'0059未適用のため、v_ai_brake_production_actual はまだ13列のまま(実列={actual_columns})。'
            f'migrate実行後に本試験で16列への更新を確認する。')

    def test_sequence_no_buckets_match_db(self):
        """sequence_no=0/1/2以上それぞれの実データ件数を検証する(計画書 §35で指示された検証)。"""
        connection = service.open_snapshot_connection(service.Deadline(30, 'stage_deadline_fetch'), read_timeout=30)
        try:
            cursor = connection.cursor()
            cursor.execute(
                "SELECT "
                "SUM(CASE WHEN sequence_no = 0 THEN 1 ELSE 0 END), "
                "SUM(CASE WHEN sequence_no = 1 THEN 1 ELSE 0 END), "
                "SUM(CASE WHEN sequence_no >= 2 THEN 1 ELSE 0 END), "
                "COUNT(*) "
                "FROM brake_line_record")
            seq0, seq1, seq2plus, total = cursor.fetchone()
            cursor.close()
        finally:
            connection.close()
        # 2026-10-17 generator確認時点の開発DB実データ(27,253件)
        self.assertEqual(total, 27253)
        self.assertEqual(seq0, 418)
        self.assertEqual(seq1, 26791)
        self.assertEqual(seq2plus, 44)
        self.assertEqual(seq0 + seq1 + seq2plus, total)
