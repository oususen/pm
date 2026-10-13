"""既存仕損の表示名を完全一致で照合する。既定では更新しない。"""
from collections import defaultdict

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from quality.models_scrap import ScrapRecord


class Command(BaseCommand):
    help = '仕損の記入者を姓名の完全一致で照合（更新は --apply 指定時のみ）'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help='一人に確定した記入者ログインIDのみ適用')

    def handle(self, *args, **options):
        users_by_name = defaultdict(list)
        for user in get_user_model().objects.all().iterator():
            full_name = f'{user.last_name or ""} {user.first_name or ""}'.strip()
            if full_name:
                users_by_name[full_name].append(user.username)

        targets = ScrapRecord.objects.filter(operator_login_id__isnull=True)
        target_count = targets.count()
        candidate_count = ambiguous_count = unmatched_count = updated_count = 0
        with transaction.atomic():
            for record in targets.iterator():
                matches = users_by_name.get(record.operator_name, [])
                if len(matches) == 1:
                    candidate_count += 1
                    if options['apply']:
                        updated_count += ScrapRecord.objects.filter(
                            pk=record.pk, operator_login_id__isnull=True,
                        ).update(operator_login_id=matches[0])
                else:
                    kind = '曖昧' if matches else '不一致'
                    if matches:
                        ambiguous_count += 1
                    else:
                        unmatched_count += 1
                    self.stdout.write(f'{kind}: id={record.pk} operator_name={record.operator_name!r} 一致件数={len(matches)}')

        self.stdout.write(
            f'対象件数={target_count} 候補件数={candidate_count} 曖昧件数={ambiguous_count} '
            f'不一致件数={unmatched_count} 更新件数={updated_count} '
            f'未補完件数={ScrapRecord.objects.filter(operator_login_id__isnull=True).count()}'
        )
