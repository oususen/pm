from datetime import date

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIRequestFactory

from masters.models import Equipment, Line, Process, Product
from production.models_laser_actual import LaserActual
from production.models_laser_pattern import (
    LaserPattern,
    LaserPatternComponent,
    LaserPatternFinishedProduct,
)
from production.models_line_backlog import LineBacklog
from production.serializers import LaserActualSerializer
from production.views import LaserActualViewSet


class LaserActualBacklogSyncTest(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.line = Line.objects.create(
            line_code='L-LASER-T',
            line_name='レーザ試験ライン',
        )
        self.process = Process.objects.create(
            process_code='P-LASER-T',
            process_name='レーザ試験工程',
            line=self.line,
        )
        self.equipment = Equipment.objects.create(
            equipment_code='EQ-LASER-T',
            equipment_name='レーザ設備試験',
            line=self.line,
            process=self.process,
        )
        self.material = Product.objects.create(
            product_code='MAT-LASER-T',
            product_name='レーザ材料試験',
        )
        self.component = Product.objects.create(
            product_code='CMP-LASER-T',
            product_name='レーザ構成部品試験',
        )
        self.finished = Product.objects.create(
            product_code='FIN-LASER-T',
            product_name='レーザ完成品試験',
        )

        self.pattern = LaserPattern.objects.create(
            pattern_no='PT-LASER-T',
            material=self.material,
            equipment=self.equipment,
            process_time_min=1,
        )
        LaserPatternComponent.objects.create(
            pattern=self.pattern,
            component_product=self.component,
            take_qty=3,
        )
        LaserPatternFinishedProduct.objects.create(
            pattern=self.pattern,
            finished_product=self.finished,
            units_per_shot=1,
        )

    def _create_actual(self, shot_count=2, action='END', component_scraps=None):
        action_upper = str(action or '').upper()
        reason = '設備トラブル' if action_upper in {'PAUSE', 'TEMP_END'} else ''
        serializer = LaserActualSerializer(data={
            'work_date': date(2026, 3, 14),
            'equipment': self.equipment.id,
            'pattern': self.pattern.id,
            'shot_count': shot_count,
            'operator_action': action_upper,
            'operator_action_reason': reason,
            'component_scraps': component_scraps or [],
            'remarks': '',
        })
        self.assertTrue(serializer.is_valid(), serializer.errors)
        return serializer.save()

    def _get_backlog(self):
        return LineBacklog.objects.get(
            plan_date=date(2026, 3, 14),
            line=self.line,
            process=self.process,
            product=self.component,
            sequence_no=0,
        )

    def test_create_reflects_component_qty_to_backlog(self):
        self._create_actual(shot_count=2, action='END')
        backlog = self._get_backlog()
        self.assertEqual(backlog.actual_qty, 6)

    def test_update_replaces_backlog_qty_with_delta(self):
        actual = self._create_actual(shot_count=2, action='END')
        serializer = LaserActualSerializer(
            actual,
            data={
                'work_date': date(2026, 3, 14),
                'equipment': self.equipment.id,
                'pattern': self.pattern.id,
                'shot_count': 5,
                'operator_action': 'PAUSE',
                'operator_action_reason': '設備トラブル',
                'remarks': '',
            },
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()

        backlog = self._get_backlog()
        self.assertEqual(backlog.actual_qty, 15)

    def test_scrap_is_subtracted_from_component_actual_qty(self):
        self._create_actual(
            shot_count=3,
            action='END',
            component_scraps=[{
                'product': self.component.id,
                'scrap_qty': 2,
                'scrap_reason': 'キズ',
            }],
        )
        backlog = self._get_backlog()
        self.assertEqual(backlog.actual_qty, 7)

    def test_destroy_rolls_back_backlog_qty(self):
        actual = self._create_actual(shot_count=4, action='PAUSE')
        backlog = self._get_backlog()
        self.assertEqual(backlog.actual_qty, 12)

        view = LaserActualViewSet.as_view({'delete': 'destroy'})
        request = self.factory.delete(f'/api/laser-actuals/{actual.id}/')
        response = view(request, pk=actual.id)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        backlog.refresh_from_db()
        self.assertEqual(backlog.actual_qty, 0)
        self.assertFalse(LaserActual.objects.filter(id=actual.id).exists())
