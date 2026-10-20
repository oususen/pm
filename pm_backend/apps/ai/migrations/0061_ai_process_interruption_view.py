from django.db import migrations

# 一般工程の中断・強制終了(t_process_work_session)をAI用に公開するビュー。
# WHERE end_action IN ('PAUSE','TEMP_END')のみ。
# interruption_reasonは新規の計算列。t_process_work_sessionには理由の列が無いため、
# end_record_idでt_process_realtime_recordにLEFT JOINし、interruption_reason_code(新・コード)を
# 優先、空ならevent_data(JSON)のpause_reason/temp_end_reason/operator_action_reason(旧・自由記述)を
# 使う。2026-10-18、BOSS承認済み。過去データのinterruption_reason_code補完が進めば、
# JSON抽出への依存は将来減る見込み(暫定措置)。
# 公開16列はBOSS判断(AI用ビュー作成計画 次セクション)。
# 非公開(ビューに含めない): status・production_qty・issue_count・issue_flags・defect_qty・
# equipment_via_session(t_process_work_session_equipmentとの結合案。開発DB確認: 対象120件中8件(6.7%)しか
# 設備が紐づいておらずカバレッジが低いため、BOSS判断により非公開。設備の詳細分析は別途検討)。
# 将来のPostgreSQL移行を考え、バッククォート・DEFINER・SQL SECURITY・DB修飾は使わない。
# PostgreSQL の ->> 演算子を使用(event_dataはJSONField)。
CREATE_VIEW = """
CREATE OR REPLACE VIEW v_ai_process_interruption AS
SELECT
    s.id,
    s.product_code,
    s.product_name,
    s.plan_date,
    s.session_no,
    s.session_type,
    s.start_action,
    s.end_action,
    s.started_at,
    s.ended_at,
    s.duration_seconds,
    s.process_id,
    s.product_id,
    s.operator_name,
    s.operator_login_id,
    COALESCE(
        NULLIF(r.interruption_reason_code, ''),
        NULLIF(r.event_data->>'pause_reason', ''),
        NULLIF(r.event_data->>'temp_end_reason', ''),
        NULLIF(r.event_data->>'operator_action_reason', '')
    ) AS interruption_reason
FROM t_process_work_session s
LEFT JOIN t_process_realtime_record r ON r.id = s.end_record_id
WHERE s.end_action IN ('PAUSE', 'TEMP_END')
"""

DROP_VIEW = 'DROP VIEW IF EXISTS v_ai_process_interruption'


class Migration(migrations.Migration):

    dependencies = [
        ('ai', '0060_ai_brake_interruption_view'),
    ]

    operations = [migrations.RunSQL(CREATE_VIEW, DROP_VIEW)]
