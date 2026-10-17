"""社内AIの生産数・中断理由集計の定義を検証する。"""
from datetime import date, datetime
from unittest.mock import patch

from django.test import TestCase

from ai.services.chat_service import (
    _agent_business_data,
    _build_facts,
    _interruption_facts,
    _production_facts,
)
from masters.models import Line, Process, Product
from production.models_brake_line_record import BrakeLineRecord
from production.models_process_realtime import ProcessRealtimeRecord


class ProductionFactsBrakeTest(TestCase):
    def setUp(self):
        # テスト用SQLiteではAI専用接続(ai_reader)を別接続にできないため、同じ接続で集計する
        patcher = patch('ai.services.chat_service.AI_DB_ALIAS', 'default')
        patcher.start()
        self.addCleanup(patcher.stop)
        self.line = Line.objects.create(line_code='AI-BRK', line_name='ブレーキ', line_type='PROD')
        self.process = Process.objects.create(process_code='AI-BP', process_name='ブレーキ工程', line=self.line)
        self.product = Product.objects.create(product_code='AI-BRAKE-01', product_name='ブレーキ品')
        self.day = date(2026, 9, 16)

    def _record(self, action, qty):
        BrakeLineRecord.objects.create(
            plan_date=self.day, line=self.line, process=self.process, product=self.product,
            product_code=self.product.product_code, operator='作業者', operator_action=action, qty=qty,
        )

    def test_brake_quantity_sums_end_and_pause(self):
        # 開始→中断(40)→再開→終了(60)→開始→強制終了 の作業区間
        for action, qty in (('START', 0), ('PAUSE', 40), ('RESUME', 0), ('END', 60), ('START', 0), ('TEMP_END', 0)):
            self._record(action, qty)

        facts = _production_facts(self.day, self.day, product_code=self.product.product_code)

        self.assertEqual(facts['brake_total'], 100)
        self.assertEqual(facts['brake_records'], 2)
        self.assertEqual(facts['total'], 100)
        self.assertEqual(facts['source'], 'ブレーキ実績（終了・中断時の加工数）')

    def test_purchase_records_are_not_production(self):
        ProcessRealtimeRecord.objects.create(
            process=self.process, product=self.product, product_code=self.product.product_code,
            record_type='PRODUCTION', qty=7, event_data={'source': 'OPERATOR_ACTION_END'},
        )
        ProcessRealtimeRecord.objects.create(
            process=self.process, product=self.product, product_code=self.product.product_code,
            record_type='PURCHASE', qty=50,
            event_data={'source': 'PURCHASE_ACTUAL_INPUT', 'line_id': self.line.id},
        )
        today = ProcessRealtimeRecord.objects.first().timestamp.date()

        facts = _production_facts(today, today, product_code=self.product.product_code)

        self.assertEqual(facts['source'], '工程実績')
        self.assertEqual(facts['total'], 7)


class InterruptionFactsTest(TestCase):
    def setUp(self):
        # テスト用SQLiteではAI専用接続(ai_reader)を別接続にできないため、同じ接続で集計する
        patcher = patch('ai.services.chat_service.AI_DB_ALIAS', 'default')
        patcher.start()
        self.addCleanup(patcher.stop)
        self.line = Line.objects.create(line_code='AI-INT', line_name='中断集計', line_type='PROD')
        self.process = Process.objects.create(process_code='AI-IP', process_name='一般工程', line=self.line)
        self.product = Product.objects.create(product_code='AI-INT-01', product_name='中断集計品')
        self.day = date(2026, 10, 17)

    def _brake_record(self, action, reason, *, plan_date=None):
        return BrakeLineRecord.objects.create(
            plan_date=plan_date or self.day,
            line=self.line,
            process=self.process,
            product=self.product,
            product_code=self.product.product_code,
            operator='作業者',
            operator_action=action,
            operator_action_reason=reason,
        )

    def _process_record(self, event_data, *, record_type='OPERATOR_ACTION', timestamp=None):
        record = ProcessRealtimeRecord.objects.create(
            process=self.process,
            product=self.product,
            product_code=self.product.product_code,
            record_type=record_type,
            event_data=event_data,
        )
        ProcessRealtimeRecord.objects.filter(pk=record.pk).update(
            timestamp=timestamp or datetime(2026, 10, 17, 12, 0, 0)
        )
        return record

    def test_brake_only_result_keeps_existing_structure_and_values(self):
        self._brake_record('PAUSE', '設備トラブル')
        self._brake_record('PAUSE', '設備トラブル')
        self._brake_record('TEMP_END', '材料不足')
        self._brake_record('START', '対象外')

        facts = _interruption_facts(self.day, self.day)

        self.assertEqual(set(facts), {'total', 'labels', 'values', 'items'})
        self.assertEqual(facts['total'], 3)
        self.assertEqual(facts['labels'], ['設備トラブル', '材料不足'])
        self.assertEqual(facts['values'], [2, 1])
        self.assertEqual(facts['items'], [
            {'reason': '設備トラブル', 'action': '中断', 'records': 2},
            {'reason': '材料不足', 'action': '強制終了', 'records': 1},
        ])

    def test_brake_reason_keeps_whitespace_and_empty_reason_compatibility(self):
        self._brake_record('PAUSE', '設備トラブル')
        self._brake_record('PAUSE', ' 設備トラブル ')
        self._brake_record('PAUSE', '')

        facts = _interruption_facts(self.day, self.day)

        self.assertEqual(facts['total'], 3)
        self.assertEqual(facts['items'], [
            {'reason': ' 設備トラブル ', 'action': '中断', 'records': 1},
            {'reason': '理由未登録', 'action': '中断', 'records': 1},
            {'reason': '設備トラブル', 'action': '中断', 'records': 1},
        ])

    def test_process_records_are_added_and_same_reason_action_is_combined(self):
        self._brake_record('PAUSE', '設備トラブル')
        self._process_record({'action': 'PAUSE', 'pause_reason': '設備トラブル'})
        self._process_record({'action': 'TEMP_END', 'temp_end_reason': '設備トラブル'})

        facts = _interruption_facts(self.day, self.day)

        self.assertEqual(facts['total'], 3)
        self.assertEqual(facts['items'], [
            {'reason': '設備トラブル', 'action': '中断', 'records': 2},
            {'reason': '設備トラブル', 'action': '強制終了', 'records': 1},
        ])

    def test_process_reason_priority_fallback_and_empty_reason(self):
        self._process_record({
            'action': 'PAUSE',
            'pause_reason': '  中断優先  ',
            'operator_action_reason': '中断代替',
        })
        self._process_record({
            'action': 'PAUSE',
            'pause_reason': ' ',
            'operator_action_reason': '中断代替',
        })
        self._process_record({
            'action': 'TEMP_END',
            'temp_end_reason': '  強制終了優先  ',
            'operator_action_reason': '強制終了代替',
        })
        self._process_record({
            'action': 'TEMP_END',
            'operator_action_reason': '強制終了代替',
        })
        self._process_record({'action': 'PAUSE', 'pause_reason': ''})

        facts = _interruption_facts(self.day, self.day)

        self.assertEqual(facts['total'], 5)
        self.assertEqual(facts['items'], [
            {'reason': '中断代替', 'action': '中断', 'records': 1},
            {'reason': '中断優先', 'action': '中断', 'records': 1},
            {'reason': '強制終了代替', 'action': '強制終了', 'records': 1},
            {'reason': '強制終了優先', 'action': '強制終了', 'records': 1},
            {'reason': '理由未登録', 'action': '中断', 'records': 1},
        ])

    def test_non_target_and_invalid_process_records_are_excluded(self):
        self._process_record({'action': 'PAUSE', 'pause_reason': '対象'})
        self._process_record({'action': 'START', 'pause_reason': '対象外操作'})
        self._process_record({'action': 'PAUSE', 'pause_reason': '対象外種別'}, record_type='PRODUCTION')
        self._process_record('不正なイベントデータ')
        self._process_record(None)
        self._process_record(
            {'action': 'TEMP_END', 'temp_end_reason': '期間外'},
            timestamp=datetime(2026, 10, 16, 23, 59, 59),
        )

        facts = _interruption_facts(self.day, self.day)

        self.assertEqual(facts['total'], 1)
        self.assertEqual(facts['items'], [
            {'reason': '対象', 'action': '中断', 'records': 1},
        ])

    def test_top_eight_and_tie_order_are_deterministic(self):
        reasons = ['理由A', '理由B', '理由C', '理由D', '理由E', '理由F', '理由G', '理由H', '理由I']
        for reason in reversed(reasons):
            self._process_record({'action': 'PAUSE', 'pause_reason': reason})
        self._process_record({'action': 'TEMP_END', 'temp_end_reason': '理由A'})

        facts = _interruption_facts(self.day, self.day)

        self.assertEqual(facts['total'], 10)
        self.assertEqual(len(facts['items']), 8)
        self.assertEqual(facts['items'][:2], [
            {'reason': '理由A', 'action': '中断', 'records': 1},
            {'reason': '理由A', 'action': '強制終了', 'records': 1},
        ])
        self.assertEqual(facts['labels'], ['理由A', '理由A', '理由B', '理由C', '理由D', '理由E', '理由F', '理由G'])

    @patch('ai.services.chat_service._interruption_facts')
    def test_callers_show_brake_spot_and_general_process_source(self, interruption_facts):
        interruption_facts.return_value = {'total': 0, 'labels': [], 'values': [], 'items': []}

        data, chart, period = _agent_business_data(
            {'intent': 'interruption', 'start_date': '2026-10-17', 'end_date': '2026-10-17'},
            set(),
            {'allowed_intents': {'interruption'}},
        )
        source, raw_data, facts = _build_facts({
            'intent': 'interruption',
            'start_date': self.day,
            'end_date': self.day,
        })

        self.assertEqual(data['source'], 'ブレーキ・スポット／一般工程（中断・強制終了）')
        self.assertEqual(source, 'ブレーキ・スポット／一般工程（中断・強制終了）')
        self.assertEqual(chart, {'labels': [], 'values': [], 'series_label': '件'})
        self.assertEqual(period, {'start_date': '2026-10-17', 'end_date': '2026-10-17'})
        self.assertEqual(raw_data, interruption_facts.return_value)
        self.assertEqual(facts, {'中断・強制終了件数': 0, '理由別': []})
