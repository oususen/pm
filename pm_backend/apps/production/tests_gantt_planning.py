from datetime import date, datetime
from types import SimpleNamespace

from django.test import SimpleTestCase

from production.services.gantt_planning import (
    ProcessSpec,
    _collapse_duplicate_display_specs,
    _merge_consecutive_subprocess_entries,
    _select_steps_for_gantt_product,
)


class MergeConsecutiveSubprocessEntriesTest(SimpleTestCase):
    def test_different_process_number_is_not_merged(self):
        plans = [{
            'plan_id': 'PLAN-1',
            'plan_date': date(2026, 7, 27),
            'processes_plan': [
                {
                    'process_id': 25,
                    'output_product_id': 463,
                    'process_number': 2001,
                    'parallel_group': 1,
                    'quantity': 12.0,
                    'total_minutes_required': 720.0,
                    'effective_minutes': 720.0,
                    'start_time': '2026-07-27T12:49:00',
                    'end_time': '2026-07-28T02:04:00',
                },
                {
                    'process_id': 25,
                    'output_product_id': 463,
                    'process_number': 6001,
                    'parallel_group': 1,
                    'quantity': 12.0,
                    'total_minutes_required': 120.0,
                    'effective_minutes': 120.0,
                    'start_time': '2026-07-28T02:04:00',
                    'end_time': '2026-07-28T04:04:00',
                },
            ],
        }]

        merged = _merge_consecutive_subprocess_entries(plans)

        self.assertEqual(len(merged[0]['processes_plan']), 2)
        self.assertEqual(merged[0]['processes_plan'][0]['process_number'], 2001)
        self.assertEqual(merged[0]['processes_plan'][1]['process_number'], 6001)

    def test_same_process_number_and_parallel_group_is_merged(self):
        plans = [
            {
                'plan_id': 'PLAN-1',
                'plan_date': date(2026, 7, 27),
                'processes_plan': [
                    {
                        'process_id': 48,
                        'output_product_id': 4065,
                        'process_number': 3000,
                        'parallel_group': 27,
                        'quantity': 12.0,
                        'total_minutes_required': 120.0,
                        'effective_minutes': 120.0,
                        'start_time': '2026-07-27T15:59:00',
                        'end_time': '2026-07-27T18:09:00',
                    },
                ],
            },
            {
                'plan_id': 'PLAN-2',
                'plan_date': date(2026, 7, 27),
                'processes_plan': [
                    {
                        'process_id': 48,
                        'output_product_id': 4065,
                        'process_number': 3000,
                        'parallel_group': 27,
                        'quantity': 12.0,
                        'total_minutes_required': 120.0,
                        'effective_minutes': 120.0,
                        'start_time': '2026-07-27T18:09:00',
                        'end_time': '2026-07-27T20:19:00',
                    },
                ],
            },
        ]

        merged = _merge_consecutive_subprocess_entries(plans)

        self.assertEqual(len(merged[0]['processes_plan']), 1)
        proc = merged[0]['processes_plan'][0]
        self.assertEqual(proc['quantity'], 24.0)
        self.assertEqual(proc['total_minutes_required'], 240.0)
        self.assertEqual(proc['effective_minutes'], 240.0)


class SelectStepsForGanttProductTest(SimpleTestCase):
    def test_invalid_routing_is_excluded_by_plan_date(self):
        product = SimpleNamespace(id=463)
        old_routing = SimpleNamespace(
            product_id=463,
            is_active=True,
            valid_from_datetime=datetime(2026, 4, 19, 9, 0),
            valid_to_datetime=datetime(2026, 7, 1, 15, 0),
        )
        current_routing = SimpleNamespace(
            product_id=463,
            is_active=True,
            valid_from_datetime=datetime(2026, 7, 2, 8, 0),
            valid_to_datetime=None,
        )
        old_step = SimpleNamespace(
            id=10496,
            step_no=2001,
            parallel_group=1,
            routing=old_routing,
            routing_id=130,
        )
        current_step = SimpleNamespace(
            id=15737,
            step_no=6001,
            parallel_group=1,
            routing=current_routing,
            routing_id=667,
        )

        selected = _select_steps_for_gantt_product(
            product,
            {463: [old_step, current_step]},
            False,
            date(2026, 7, 27),
        )

        self.assertEqual([step.id for step in selected], [15737])


class CollapseDuplicateDisplaySpecsTest(SimpleTestCase):
    def test_specs_without_display_target_are_left_as_is(self):
        first_spec = ProcessSpec(
            process_id=48,
            process_code='4051-2',
            process_name='5連2ST',
            process_number=3000,
            cycle_time_minutes=10.0,
            setup_time_minutes=0.0,
            parallel_count=1,
            parallel_group=27,
            output_product_id=None,
            output_product_code='',
            output_product_name='',
            representative_part=False,
            source_step_id=15729,
        )
        second_spec = ProcessSpec(
            process_id=48,
            process_code='4051-2',
            process_name='5連2ST',
            process_number=4000,
            cycle_time_minutes=60.0,
            setup_time_minutes=0.0,
            parallel_count=1,
            parallel_group=31,
            output_product_id=None,
            output_product_code='',
            output_product_name='',
            representative_part=False,
            source_step_id=15733,
        )

        collapsed = _collapse_duplicate_display_specs(
            [first_spec, second_spec],
            is_l2201_line=False,
            coproduct_parent_map={},
            display_map={},
            all_display_ids={},
        )

        self.assertEqual(collapsed, [first_spec, second_spec])

    def test_representative_step_is_preferred_for_same_display_product(self):
        display_product = SimpleNamespace(
            id=9001,
            product_code='STYD40002876-2ST',
            product_name='ブラケット ジグ 2ST',
        )
        representative_spec = ProcessSpec(
            process_id=48,
            process_code='4051-2',
            process_name='5連2ST',
            process_number=3000,
            cycle_time_minutes=10.0,
            setup_time_minutes=0.0,
            parallel_count=1,
            parallel_group=27,
            output_product_id=4065,
            output_product_code='STYD40002876-2ST-1',
            output_product_name='ブラケット ジグ 2ST-1',
            representative_part=True,
            source_step_id=15729,
        )
        non_representative_spec = ProcessSpec(
            process_id=48,
            process_code='4051-2',
            process_name='5連2ST',
            process_number=4000,
            cycle_time_minutes=60.0,
            setup_time_minutes=0.0,
            parallel_count=1,
            parallel_group=31,
            output_product_id=4066,
            output_product_code='STYD40002876-2ST',
            output_product_name='ブラケット ジグ 2ST',
            representative_part=False,
            source_step_id=15733,
        )

        collapsed = _collapse_duplicate_display_specs(
            [representative_spec, non_representative_spec],
            is_l2201_line=False,
            coproduct_parent_map={},
            display_map={48: display_product},
            all_display_ids={48: {9001}},
        )

        self.assertEqual(len(collapsed), 1)
        self.assertEqual(collapsed[0].process_number, 3000)
        self.assertEqual(collapsed[0].cycle_time_minutes, 10.0)
        self.assertTrue(collapsed[0].representative_part)
