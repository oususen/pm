from django.db import migrations

# ブレーキ・板金スポットの中断・強制終了(brake_line_record)をAI用に公開するビュー。
# 結合なし。WHERE operator_action IN ('PAUSE','TEMP_END')のみ。
# 公開15列はBOSS判断(AI用ビュー作成計画 次セクション)。
# 非公開(ビューに含めない): operator(個人名。operator_user_id/operator_login_idで代替)のみ。
# sequence_noは含めない(BOSS決定、中断分析には不要)。
# 将来のPostgreSQL移行を考え、MySQL固有の記法(バッククォート・DEFINER・SQL SECURITY・DBの修飾)を
# 使わない標準SQLだけで書く。
CREATE_VIEW = """
CREATE OR REPLACE VIEW v_ai_brake_interruption AS
SELECT
    id,
    plan_date,
    product_code,
    operator_action,
    operator_action_reason,
    qty,
    recorded_at,
    equipment_id,
    line_id,
    process_id,
    product_id,
    operator_user_id,
    operator_login_id,
    interruption_reason_code,
    remarks
FROM brake_line_record
WHERE operator_action IN ('PAUSE', 'TEMP_END')
"""

DROP_VIEW = 'DROP VIEW IF EXISTS v_ai_brake_interruption'


class Migration(migrations.Migration):

    dependencies = [
        ('ai', '0059_ai_brake_production_actual_view_add_columns'),
    ]

    operations = [migrations.RunSQL(CREATE_VIEW, DROP_VIEW)]
