from django.db import migrations

# ブレーキ・板金スポットの実績(brake_line_record)をAI用に公開するビュー。結合なし・全行(WHEREなし)。
# brake_line_recordは1行=1操作イベント(START/END/PAUSE/TEMP_END/RESUME)。
# ブレーキ(line_id=9、L0010)とスポット(line_id=10、L0013)が混在する。区別するときはline_idで絞る。
# 公開13列はBOSS判断(AI用ビュー作成計画 §35)。
# 非公開(ビューに含めない): operator(個人名。operator_user_idで代替)、
# operator_login_id・interruption_reason_code・remarks(2026-10-16追加されたばかりの新列で、実データがほぼ空のため今回は非公開)。
# 将来のPostgreSQL移行を考え、MySQL固有の記法(バッククォート・DEFINER・SQL SECURITY・DBの修飾)を
# 使わない標準SQLだけで書く。
CREATE_VIEW = """
CREATE OR REPLACE VIEW v_ai_brake_production_actual AS
SELECT
    id,
    plan_date,
    product_code,
    operator_action,
    operator_action_reason,
    qty,
    sequence_no,
    recorded_at,
    equipment_id,
    line_id,
    process_id,
    product_id,
    operator_user_id
FROM brake_line_record
"""

DROP_VIEW = 'DROP VIEW IF EXISTS v_ai_brake_production_actual'


class Migration(migrations.Migration):

    dependencies = [
        ('ai', '0056_ai_laser_production_actual_view'),
        ('production', '0121_brakelinerecord_interruption_reason_code_and_more'),
    ]

    operations = [migrations.RunSQL(CREATE_VIEW, DROP_VIEW)]
