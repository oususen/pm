"""常駐ワーカーの起動版を照合する。生存キー以外には版情報を保存しない。"""
import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path


SOURCE_ROOT = Path(__file__).resolve().parents[1]
# 実行・取得・履歴・外枠と、それらの設定／承認処理を版に含める。
WORKER_FILES = (
    'models.py', 'config/service.py', 'management/commands/analysis_worker.py',
    'services/analysis_worker_identity.py', 'services/analysis_job_service.py',
    'services/analysis_execution_service.py', 'services/analysis_run_service.py',
    'services/analysis_codegen_service.py', 'services/analysis_guard_runtime.py',
    'services/analysis_plan_store.py', 'services/analysis_data_service.py',
    'services/analysis_planning_service.py', 'services/analysis_llm.py',
    'services/analysis_redaction.py',
)


def current_code_version():
    digest = hashlib.sha256()
    for name in WORKER_FILES:
        for value in (name.encode('utf-8'), (SOURCE_ROOT / name).read_bytes()):
            digest.update(len(value).to_bytes(8, 'big'))
            digest.update(value)
    return digest.hexdigest()


def worker_registration(worker_id, code_version):
    return json.dumps({'id': worker_id, 'code_version': code_version}, sort_keys=True)


def worker_version_matches(raw, current_version):
    try:
        state = json.loads(raw)
        return (type(state) is dict and set(state) == {'id', 'code_version'}
                and isinstance(state['id'], str) and bool(state['id'])
                and state['code_version'] == current_version)
    except (TypeError, ValueError):
        # UUIDだけの旧生存キーも版を証明できないため拒否する。
        return False


def ensure_jst_clock():
    """OSの時刻帯を勝手に変えず、JSTのnaive datetime.now()だけを許す。"""
    now = datetime.now()
    if now.tzinfo is not None or now.astimezone().utcoffset() != timedelta(hours=9):
        raise ValueError('専用ワーカーの時刻帯をJSTに設定してください。')
