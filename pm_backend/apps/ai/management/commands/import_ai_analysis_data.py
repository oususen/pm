"""export_ai_analysis_data が書き出したテンプレートと実行履歴を、開発DBへ復元する管理コマンド。

- 既定で、対象テーブルに行が1件でもあれば中止する。--force-merge のときだけ、既存のIDと衝突しない行を追加する(既存の行は上書きしない)。
- ユーザーはログインIDで引き当てる。引き当てられない行はスキップして報告する(代わりのユーザーで埋めない)。
- 元のIDで INSERT する。全体を1つのトランザクションで行い、エラーなら全体をロールバックする。
- 書き込むときは --i-am-on-dev が必須。DEBUG=False の環境(本番)では書き込まない。--dry-run は読み取りのみ。
仕様は仕様書/AI分析_開発DB再取り込み手順.md。
"""
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from ai.management.commands.export_ai_analysis_data import MODEL_MAP, default_backup_dir
from ai.services import analysis_backup as backup


class Command(BaseCommand):
    help = '書き出したAI分析のテンプレートと実行履歴を、開発DBへ復元する(既定は対象テーブルが空のときだけ)'

    def add_arguments(self, parser):
        parser.add_argument('--input-dir', help='読み込み元(既定は <リポジトリ>/output/ai_backup の最新のフォルダ)')
        parser.add_argument('--dry-run', action='store_true', help='書き込まずに、復元できる件数・スキップする件数だけ表示する')
        parser.add_argument('--force-merge', action='store_true', help='既存の行があっても、IDなどが衝突しない行だけを追加する(既存の行は上書きしない)')
        parser.add_argument('--i-am-on-dev', action='store_true', help='開発DBであることの確認(書き込むときは必須)')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        if not dry_run:
            if not options['i_am_on_dev']:
                raise CommandError('書き込むには --i-am-on-dev が必要です(開発DBであることを確認してから付けてください)')
            if not settings.DEBUG:
                raise CommandError('DEBUG=False の環境(本番の可能性)では書き込みません')

        try:
            directory = backup.resolve_input_dir(options['input_dir'] or default_backup_dir())
            manifest, templates, runs = backup.load_backup(directory)
        except (ValueError, OSError) as exc:
            raise CommandError(str(exc))
        self.stdout.write(f'読み込み元: {directory}(書き出し日時 {manifest.get("exported_at")}・書き出し元DB {manifest.get("db_name")})')

        # スキーマの版が違えば、必ず中止する(続行する手段はない)
        mismatch = backup.check_schema(manifest, MODEL_MAP)
        if mismatch:
            raise CommandError(mismatch)

        existing = {kind: set(model.objects.values_list('pk', flat=True)) for kind, model in MODEL_MAP.items()}
        if any(existing.values()) and not options['force_merge']:
            raise CommandError(
                f'対象テーブルに既存の行があります(テンプレート {len(existing[backup.KIND_TEMPLATE])} 件・'
                f'履歴 {len(existing[backup.KIND_RUN])} 件)。中止します。既存の行を残して追加する場合は --force-merge')
        existing_unique = {
            kind: {names: set(model.objects.values_list(*names)) for names in backup.unique_field_sets(model)}
            for kind, model in MODEL_MAP.items()
        }

        usernames = set()
        for rows, kind in ((templates, backup.KIND_TEMPLATE), (runs, backup.KIND_RUN)):
            for _f, fkind, key in backup.field_specs(MODEL_MAP[kind]):
                if fkind == 'user':
                    usernames.update(r.get(key) for r in rows if r.get(key) is not None)
        user_id_by_name = {name: pk for pk, name in get_user_model().objects.filter(username__in=usernames).values_list('pk', 'username')}

        plan = backup.build_plan(MODEL_MAP, templates, runs, user_id_by_name, existing, existing_unique)

        if dry_run:
            counts = {backup.KIND_TEMPLATE: len(plan.templates), backup.KIND_RUN: len(plan.runs)}
            self.stdout.write('--dry-run: 書き込みません')
        else:
            def insert(kind, kwargs):
                model = MODEL_MAP[kind]
                with backup.suspended_auto_now(model):
                    model(**kwargs).save(force_insert=True)

            with transaction.atomic():
                counts = backup.execute_plan(plan, insert)

        verb = '復元できる' if dry_run else '復元した'
        self.stdout.write(f'テンプレート: {verb} {counts[backup.KIND_TEMPLATE]} 件(ファイル {len(templates)} 件)')
        self.stdout.write(f'実行履歴: {verb} {counts[backup.KIND_RUN]} 件(ファイル {len(runs)} 件)')
        self.report_skips(plan)

    def report_skips(self, plan):
        if not plan.skipped:
            self.stdout.write('スキップ: 0 件')
        else:
            self.stdout.write(self.style.WARNING(f'スキップ: {len(plan.skipped)} 件'))
            for (kind, reason), n in sorted(backup.summarize_skips(plan.skipped).items()):
                self.stdout.write(f'  {kind} / {backup.SKIP_REASON_TEXT.get(reason, reason)}: {n} 件')
            for s in plan.skipped:
                self.stdout.write(f'    {s.kind} id={s.row_id} ({s.reason}) {s.detail}')
        for w in plan.warnings:
            self.stdout.write(self.style.WARNING(f'注意: {w}'))
