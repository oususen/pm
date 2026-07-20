import logging
import time
from datetime import datetime, timedelta

from django.core.files.storage import default_storage

from production.models_schedule_config import ScheduleConfig

logger = logging.getLogger('masters')

TASK_NAME = 'CONTAINER_IMPORT_TMP_CLEANUP'
TMP_DIR = 'tmp/container_import'
RETENTION_HOURS = 24


def run_container_import_tmp_cleanup(*, created_by=None):
    """荷姿設定Excel取込のプレビューで一時保存したxlsxのうち、RETENTION_HOURSより古いものを削除する。
    プレビュー後にキャンセルされたファイルは import_excel_commit で削除されずに残るため、定期的に掃除する。
    """
    config, _ = ScheduleConfig.objects.get_or_create(
        task_name=TASK_NAME,
        line=None,
        defaults={'scheduled_hour': 3, 'scheduled_minute': 0, 'is_enabled': False},
    )

    config.last_run_at = datetime.now()
    config.last_run_status = 'RUNNING'
    config.last_run_message = '削除処理を実行中...'
    config.save(update_fields=['last_run_at', 'last_run_status', 'last_run_message'])

    started = time.perf_counter()
    try:
        deleted = 0
        cutoff = datetime.now() - timedelta(hours=RETENTION_HOURS)
        try:
            _dirs, files = default_storage.listdir(TMP_DIR)
        except FileNotFoundError:
            files = []

        for name in files:
            path = f'{TMP_DIR}/{name}'
            try:
                modified = default_storage.get_modified_time(path)
            except (FileNotFoundError, NotImplementedError, OSError):
                continue
            if modified.replace(tzinfo=None) < cutoff:
                default_storage.delete(path)
                deleted += 1

        duration = round(time.perf_counter() - started, 2)
        config.last_run_status = 'SUCCESS'
        config.last_run_duration_seconds = duration
        config.last_run_message = f'{deleted}件の一時ファイルを削除しました'
        config.save(update_fields=['last_run_status', 'last_run_duration_seconds', 'last_run_message'])
        from production.models_schedule_config import record_schedule_run_log
        record_schedule_run_log(
            config,
            status=config.last_run_status,
            message=config.last_run_message,
            duration_seconds=config.last_run_duration_seconds,
        )
        return {'status': 'SUCCESS', 'deleted': deleted}
    except Exception as exc:
        duration = round(time.perf_counter() - started, 2)
        logger.exception('荷姿設定Excel取込 一時ファイル削除中にエラー')
        config.last_run_status = 'FAILED'
        config.last_run_duration_seconds = duration
        config.last_run_message = f'実行中にエラーが発生しました: {exc}'
        config.save(update_fields=['last_run_status', 'last_run_duration_seconds', 'last_run_message'])
        from production.models_schedule_config import record_schedule_run_log
        record_schedule_run_log(
            config,
            status=config.last_run_status,
            message=config.last_run_message,
            duration_seconds=config.last_run_duration_seconds,
        )
        raise
