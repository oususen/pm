from django.db import migrations

# レーザーの生産実績(t_laser_actual_detail に t_laser_actual を結合)のうち、
# operator_action IN ('END', 'PAUSE')(終了・中断の確定済み行) かつ detail_type='COMPONENT'(構成部品の明細行)
# だけをAI用に公開するビュー。公開31列はBOSS判断(AI用ビュー作成計画 §34)。
# 非公開(ビューに含めない): detail_type(常にCOMPONENT固定で業務上の意味がない)、
# display_order(画面の並び順で分析に使わない)、ヘッダの remarks(DB確認済み: 全件空。t_laser_actual 4,997件中4,997件が空文字)。
# operator_user_id は t_laser_actual.created_by_id の別名(この記録を登録した作業者)、
# end_operator_user_id は t_laser_actual.updated_by_id の別名(ヘッダの最終更新者)。
# どちらも元の列名(created_by_id・updated_by_id)だけでは意味が分かりにくいため、業務上の役割が分かる名前に付け替えた。
# 将来のPostgreSQL移行を考え、MySQL固有の記法(バッククォート・DEFINER・SQL SECURITY・DBの修飾)を
# 使わない標準SQLだけで書く。
CREATE_VIEW = """
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

DROP_VIEW = 'DROP VIEW IF EXISTS v_ai_laser_production_actual'


class Migration(migrations.Migration):

    dependencies = [
        ('ai', '0055_ai_process_production_actual_view'),
        ('production', '0118_laser_actual_line_process'),
    ]

    operations = [migrations.RunSQL(CREATE_VIEW, DROP_VIEW)]
