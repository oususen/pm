from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from masters.models import Line, Process, Product
from production.models_brake_line_record import BrakeLineRecord
from production.models_line_backlog import LineBacklog
from production.models_record_inquiry_setting import ProductionRecordInquirySetting


class BackfillSpotLineActualQtyCommandTest(TestCase):
    def setUp(self):
        self.line = Line.objects.create(
            line_code='L0013',
            line_name='スポット試験ライン',
        )
        self.other_line = Line.objects.create(
            line_code='L0999',
            line_name='対象外ライン',
        )
        self.process = Process.objects.create(
            process_code='4013',
            process_name='ナットスポット',
            line=self.line,
        )
        self.other_process = Process.objects.create(
            process_code='4999',
            process_name='対象外工程',
            line=self.line,
        )
        self.product = Product.objects.create(
            product_code='YD40007244-00S',
            product_name='試験品番',
        )
        self.other_product = Product.objects.create(
            product_code='TEST-OTHER',
            product_name='対象外品番',
        )
        ProductionRecordInquirySetting.objects.create(
            tab_key=ProductionRecordInquirySetting.TAB_SPOT,
            target_line_codes=['L0013'],
        )

        LineBacklog.objects.create(
            plan_date='2026-03-24',
            line=self.line,
            process=self.process,
            product=self.product,
            sequence_no=0,
            actual_qty=0,
        )
        LineBacklog.objects.create(
            plan_date='2026-03-24',
            line=self.line,
            process=self.process,
            product=self.product,
            sequence_no=1,
            plan_qty=38,
            actual_qty=0,
        )
        LineBacklog.objects.create(
            plan_date='2026-03-24',
            line=self.line,
            process=self.process,
            product=self.other_product,
            sequence_no=0,
            actual_qty=999,
        )

        BrakeLineRecord.objects.create(
            plan_date='2026-03-24',
            line=self.line,
            process=self.process,
            product=self.product,
            product_code=self.product.product_code,
            operator_action=BrakeLineRecord.OPERATOR_ACTION_START,
            qty=0,
            sequence_no=1,
        )
        BrakeLineRecord.objects.create(
            plan_date='2026-03-24',
            line=self.line,
            process=self.process,
            product=self.product,
            product_code=self.product.product_code,
            operator_action=BrakeLineRecord.OPERATOR_ACTION_PAUSE,
            qty=10,
            sequence_no=1,
        )
        BrakeLineRecord.objects.create(
            plan_date='2026-03-24',
            line=self.line,
            process=self.process,
            product=self.product,
            product_code=self.product.product_code,
            operator_action=BrakeLineRecord.OPERATOR_ACTION_END,
            qty=28,
            sequence_no=1,
        )
        BrakeLineRecord.objects.create(
            plan_date='2026-03-24',
            line=self.other_line,
            process=self.process,
            product=self.other_product,
            product_code=self.other_product.product_code,
            operator_action=BrakeLineRecord.OPERATOR_ACTION_END,
            qty=99,
            sequence_no=1,
        )
        BrakeLineRecord.objects.create(
            plan_date='2026-03-24',
            line=self.line,
            process=self.other_process,
            product=self.other_product,
            product_code=self.other_product.product_code,
            operator_action=BrakeLineRecord.OPERATOR_ACTION_END,
            qty=77,
            sequence_no=1,
        )

    def test_command_updates_seq0_actual_qty_from_spot_records(self):
        stdout = StringIO()

        call_command(
            'backfill_spot_line_actual_qty',
            '--date', '2026-03-24',
            '--process-code', '4013',
            stdout=stdout,
        )

        seq0 = LineBacklog.objects.get(
            plan_date='2026-03-24',
            line=self.line,
            process=self.process,
            product=self.product,
            sequence_no=0,
        )
        seq1 = LineBacklog.objects.get(
            plan_date='2026-03-24',
            line=self.line,
            process=self.process,
            product=self.product,
            sequence_no=1,
        )

        self.assertEqual(seq0.actual_qty, 38)
        self.assertEqual(seq1.actual_qty, 0)
        self.assertIn('created=0 updated=1 unchanged=0 reset=0', stdout.getvalue())

    def test_command_can_reset_missing_seq0_actuals(self):
        call_command(
            'backfill_spot_line_actual_qty',
            '--date', '2026-03-24',
            '--process-code', '4013',
            '--reset-missing',
        )

        extra_seq0 = LineBacklog.objects.get(
            plan_date='2026-03-24',
            line=self.line,
            process=self.process,
            product=self.other_product,
            sequence_no=0,
        )
        target_seq0 = LineBacklog.objects.get(
            plan_date='2026-03-24',
            line=self.line,
            process=self.process,
            product=self.product,
            sequence_no=0,
        )

        self.assertEqual(extra_seq0.actual_qty, 0)
        self.assertEqual(target_seq0.actual_qty, 38)
