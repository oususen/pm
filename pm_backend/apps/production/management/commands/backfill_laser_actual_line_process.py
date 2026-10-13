"""レーザー実績 t_laser_actual の line / process 未設定行を補完する。既定では更新しない。

補完値は、定数コード(L0801 / 0801)で引いた Line / Process のID。
設備マスタの現在値のIDはコピーしない。
設備の現在の line / process が L0801 / 0801 でない行は更新せず一覧表示する。
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q

from masters.models import Line, Process
from production.models_laser_actual import LASER_LINE_CODE, LASER_PROCESS_CODE, LaserActual


class Command(BaseCommand):
    help = 'レーザー実績の line / process 未設定行を L0801 / 0801 で補完（更新は --apply 指定時のみ）'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help='設備の現在値が L0801/0801 の行のみ更新する')

    def handle(self, *args, **options):
        line = Line.objects.filter(line_code=LASER_LINE_CODE).first()
        process = Process.objects.filter(process_code=LASER_PROCESS_CODE).first()
        if line is None:
            raise CommandError(f'ラインマスタ(line_code={LASER_LINE_CODE})が見つかりません。')
        if process is None:
            raise CommandError(f'工程マスタ(process_code={LASER_PROCESS_CODE})が見つかりません。')

        targets = LaserActual.objects.filter(
            Q(line_id__isnull=True) | Q(process_id__isnull=True)
        ).select_related('equipment')
        target_count = targets.count()
        candidate_count = mismatch_count = updated_count = 0
        with transaction.atomic():
            for actual in targets.order_by('pk').iterator():
                equipment = actual.equipment
                if equipment.line_id == line.id and equipment.process_id == process.id:
                    candidate_count += 1
                    if options['apply']:
                        updated_count += LaserActual.objects.filter(
                            pk=actual.pk,
                        ).filter(
                            Q(line_id__isnull=True) | Q(process_id__isnull=True)
                        ).update(line=line, process=process)
                else:
                    mismatch_count += 1
                    self.stdout.write(
                        f'不一致: id={actual.pk} work_date={actual.work_date} '
                        f'equipment_code={equipment.equipment_code!r} '
                        f'設備のline_id={equipment.line_id} 設備のprocess_id={equipment.process_id} '
                        f'(期待 line_id={line.id} process_id={process.id})'
                    )

        remaining = LaserActual.objects.filter(
            Q(line_id__isnull=True) | Q(process_id__isnull=True)
        ).count()
        self.stdout.write(
            f'対象件数={target_count} 候補件数={candidate_count} '
            f'不一致件数={mismatch_count} 更新件数={updated_count} 未補完件数={remaining}'
        )
