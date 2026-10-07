from datetime import date, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from production import views_laser_weekly_plan as weekly


class HolidayQueryCaptured(Exception):
    pass


class LaserWeeklyFrequencyTest(SimpleTestCase):
    def _holiday_query(self, start, processing_starts):
        targets = [SimpleNamespace(
            id=index, laser_pattern_id=index,
            laser_pattern=SimpleNamespace(processing_start_date=processing_start),
        ) for index, processing_start in enumerate(processing_starts)]
        target_query = MagicMock()
        target_query.select_related.return_value.prefetch_related.return_value = targets
        request = SimpleNamespace(query_params={'start_date': start.isoformat()})
        # 取得条件を実listで構築させ、DBアクセス前に停止する。
        with patch.object(weekly, '_resolve_laser_calendar_id', return_value=9), \
                patch.object(weekly, '_build_workday_helpers', return_value=(lambda day: day.weekday() < 5,)), \
                patch.object(weekly.LaserWeeklyPlanTarget.objects, 'filter', return_value=target_query) as target_filter, \
                patch.object(weekly.LaserWeeklyPlanManualQuantity.objects, 'filter', return_value=[]), \
                patch.object(weekly.LaserWeeklyPatternManualQuantity.objects, 'filter', return_value=[]), \
                patch.object(weekly.CalendarDay.objects, 'filter', side_effect=HolidayQueryCaptured) as calendar_filter:
            with self.assertRaises(HolidayQueryCaptured):
                weekly.LaserWeeklyPlanViewSet().list(request)
        target_filter.assert_called_once_with(is_active=True)
        return calendar_filter.call_args.kwargs

    def test_holiday_range_includes_earliest_processing_start_and_retains_existing_end(self):
        start = date(2026, 10, 5)
        previous = start - timedelta(days=7)
        cases = [
            ([], previous), ([None], previous),
            ([date(2026, 10, 1)], previous),
            ([date(2026, 8, 31)], date(2026, 8, 31)),
            ([None, date(2026, 9, 1), date(2026, 8, 28)], date(2026, 8, 28)),
        ]
        for processing_starts, expected_start in cases:
            with self.subTest(processing_starts=processing_starts):
                self.assertEqual(self._holiday_query(start, processing_starts), {
                    'calendar_id': 9,
                    'is_holiday_work': True,
                    'target_date__range': (expected_start, date(2026, 11, 13)),
                })

    def test_6002_frequency_phase_is_equal_for_overlapping_internal_dates(self):
        processing_start = date(2026, 8, 31)
        holiday_work = date(2026, 9, 23)
        pattern = {
            'pattern_no': '6002', 'freq_type': 'EVERY_N_DAYS',
            'freq_interval_days': 2, 'freq_start_date': processing_start,
        }
        results = []
        for start in [date(2026, 9, 28), date(2026, 10, 5)]:
            query = self._holiday_query(start, [processing_start])
            lower, upper = query['target_date__range']
            holiday_dates = {holiday_work} if lower <= holiday_work <= upper else set()
            self.assertIn(holiday_work, holiday_dates)
            dates = [start + timedelta(days=index) for index in range(28)
                     if (start + timedelta(days=index)).weekday() < 5]
            daily = {day.isoformat(): {'automatic_sheets': 1} for day in dates}
            results.append(weekly.LaserWeeklyPlanViewSet()._calc_freq_sheets(
                pattern, daily, dates, lambda day: day.weekday() < 5,
                field='automatic_sheets', holiday_work_dates=holiday_dates,
            ))
        common_days = [(date(2026, 10, 5) + timedelta(days=index)).isoformat() for index in range(5)]
        self.assertEqual([results[0][day] for day in common_days], [2, 0, 2, 0, 2])
        self.assertEqual([results[0][day] for day in common_days],
                         [results[1][day] for day in common_days])
