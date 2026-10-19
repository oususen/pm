from django.db import migrations

# v_ai_laser_production_actual と v_ai_laser_interruption に interruption_reason_code 列(中断理由コード、
# t_laser_actual.interruption_reason_code。production/migrations/0125(単位C-6)で追加された列。
# masters.InterruptionReason(line_category='1')のコードを指す)を追加公開する。
# 2026-10-20、BOSS承認済み(Codexレビュー指摘の修正2)。
# 0056・0058は既にDBへ適用済み(列追加前の列数)のため、ここで CREATE OR REPLACE VIEW を再発行して追加する。
# 0056・0058のファイル自体は適用済み内容のまま変更しない(適用済みマイグレーションの中身を後から
# 書き換えても、Djangoは再実行しないため)。
# 将来のPostgreSQL移行を考え、MySQL固有の記法(バッククォート・DEFINER・SQL SECURITY・DBの修飾)を
# 使わない標準SQLだけで書く。
CREATE_LASER_PRODUCTION_ACTUAL_VIEW = """
CREATE OR REPLACE VIEW v_ai_laser_production_actual AS
SELECT
    d.id,
    d.actual_id,
    a.created_by_id AS operator_user_id,
    a.equipment_id,
    a.equipment_code,
    a.equipment_name,
    a.line_id,
    a.process_id,
    a.pattern_id,
    a.pattern_no,
    a.material_id,
    a.material_code,
    a.material_name,
    d.product_id,
    d.product_code,
    d.product_name,
    a.work_date,
    a.shot_count,
    a.process_time_per_shot,
    a.total_process_time,
    a.operator_action,
    a.operator_action_reason,
    d.units_per_shot,
    d.total_qty,
    d.scrap_qty,
    d.scrap_reason,
    a.updated_by_id AS end_operator_user_id,
    a.created_at AS created_at_h,
    a.updated_at AS updated_at_h,
    d.created_at,
    d.updated_at,
    a.interruption_reason_code
FROM t_laser_actual_detail d
JOIN t_laser_actual a ON a.id = d.actual_id
WHERE a.operator_action IN ('END', 'PAUSE') AND d.detail_type = 'COMPONENT'
"""

# ロールバックは0056が作成した31列版に戻す
REVERT_LASER_PRODUCTION_ACTUAL_VIEW = """
CREATE OR REPLACE VIEW v_ai_laser_production_actual AS
SELECT
    d.id,
    d.actual_id,
    a.created_by_id AS operator_user_id,
    a.equipment_id,
    a.equipment_code,
    a.equipment_name,
    a.line_id,
    a.process_id,
    a.pattern_id,
    a.pattern_no,
    a.material_id,
    a.material_code,
    a.material_name,
    d.product_id,
    d.product_code,
    d.product_name,
    a.work_date,
    a.shot_count,
    a.process_time_per_shot,
    a.total_process_time,
    a.operator_action,
    a.operator_action_reason,
    d.units_per_shot,
    d.total_qty,
    d.scrap_qty,
    d.scrap_reason,
    a.updated_by_id AS end_operator_user_id,
    a.created_at AS created_at_h,
    a.updated_at AS updated_at_h,
    d.created_at,
    d.updated_at
FROM t_laser_actual_detail d
JOIN t_laser_actual a ON a.id = d.actual_id
WHERE a.operator_action IN ('END', 'PAUSE') AND d.detail_type = 'COMPONENT'
"""

CREATE_LASER_INTERRUPTION_VIEW = """
CREATE OR REPLACE VIEW v_ai_laser_interruption AS
SELECT
    id,
    work_date,
    equipment_id,
    equipment_code,
    equipment_name,
    line_id,
    process_id,
    pattern_no,
    material_id,
    material_code,
    material_name,
    operator_action,
    operator_action_reason,
    created_by_id AS operator_user_id,
    created_at,
    interruption_reason_code
FROM t_laser_actual
WHERE operator_action IN ('PAUSE', 'TEMP_END')
"""

# ロールバックは0058が作成した15列版に戻す
REVERT_LASER_INTERRUPTION_VIEW = """
CREATE OR REPLACE VIEW v_ai_laser_interruption AS
SELECT
    id,
    work_date,
    equipment_id,
    equipment_code,
    equipment_name,
    line_id,
    process_id,
    pattern_no,
    material_id,
    material_code,
    material_name,
    operator_action,
    operator_action_reason,
    created_by_id AS operator_user_id,
    created_at
FROM t_laser_actual
WHERE operator_action IN ('PAUSE', 'TEMP_END')
"""


class Migration(migrations.Migration):

    dependencies = [
        ('ai', '0061_ai_process_interruption_view'),
        ('production', '0125_laseractual_interruption_reason_code'),
    ]

    operations = [
        migrations.RunSQL(CREATE_LASER_PRODUCTION_ACTUAL_VIEW, REVERT_LASER_PRODUCTION_ACTUAL_VIEW),
        migrations.RunSQL(CREATE_LASER_INTERRUPTION_VIEW, REVERT_LASER_INTERRUPTION_VIEW),
    ]
