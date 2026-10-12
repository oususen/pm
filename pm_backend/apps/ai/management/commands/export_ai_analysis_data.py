"""AI分析のテンプレートと実行履歴を、JSONへ書き出す管理コマンド(DBは読み取りのみ)。

開発DBへ本番ダンプをインポートする前に実行する。復元は import_ai_analysis_data。
書き出し先は、既定で <リポジトリ>/output/ai_backup/<日時>/ 。実行のたびに新しい日時のフォルダへ書き、
既存のバックアップは上書きも削除もしない。仕様は仕様書/AI分析_開発DB再取り込み手順.md。
"""
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from ai.models import AIAnalysisRun, AIAnalysisTemplate
from ai.services import analysis_backup as backup

MODEL_MAP = {backup.KIND_TEMPLATE: AIAnalysisTemplate, backup.KIND_RUN: AIAnalysisRun}


def default_backup_dir():
    return Path(settings.BASE_DIR).parent / 'output' / 'ai_backup'


class Command(BaseCommand):
    help = 'AI分析のテンプレートと実行履歴を、JSON(templates.json・runs.json・manifest.json)へ書き出す(DBは読み取りのみ)'

    def add_arguments(self, parser):
        parser.add_argument('--output-dir', help='書き出し先(既定は <リポジトリ>/output/ai_backup)。この下に日時のフォルダを作る')
        parser.add_argument(
            '--allow-empty', action='store_true',
            help='テンプレートも履歴も0件のときも書き出す(既定は中止。ダンプのインポート後に空のバックアップを作らないため)')

    def handle(self, *args, **options):
        base = Path(options['output_dir']) if options.get('output_dir') else default_backup_dir()
        now = datetime.now()  # USE_TZ=False。timezone.now() は使わない
        objs = {kind: list(model.objects.order_by('id')) for kind, model in MODEL_MAP.items()}
        counts = {kind: len(v) for kind, v in objs.items()}
        if not any(counts.values()) and not options['allow_empty']:
            raise CommandError('テンプレートも実行履歴も0件です。インポート後に実行していないか確認してください(空のまま書く場合は --allow-empty)')

        user_ids = set()
        for kind, model in MODEL_MAP.items():
            user_ids |= backup.user_ids_in(model, objs[kind])
        user_model = get_user_model()
        username_by_id = dict(user_model.objects.filter(pk__in=user_ids).values_list('pk', 'username'))

        rows = {kind: [backup.instance_to_row(MODEL_MAP[kind], o, username_by_id) for o in objs[kind]] for kind in MODEL_MAP}
        manifest = backup.build_manifest(MODEL_MAP, counts, connection.settings_dict.get('NAME'), now)
        target = base / now.strftime('%Y%m%d_%H%M%S')
        if target.exists():
            raise CommandError(f'書き出し先が既にあります(上書きしません): {target}')
        backup.write_backup(target, manifest, rows[backup.KIND_TEMPLATE], rows[backup.KIND_RUN])

        self.stdout.write(f'書き出し先: {target}')
        self.stdout.write(f'テンプレート: {counts[backup.KIND_TEMPLATE]} 件')
        self.stdout.write(f'実行履歴: {counts[backup.KIND_RUN]} 件')
        self.stdout.write(f'スキーマの版: {manifest["schema_hash"][:12]}')
