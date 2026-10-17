from django.db import migrations

# レーザーの中断(t_laser_actual単独。結合なし)のうち、
# operator_action IN ('PAUSE', 'TEMP_END')(中断・強制終了の行)だけをAI用に公開するビュー。
# t_laser_actual_detail(構成部品明細)へは結合しない。結合すると中断1件が明細の行数分重複するため、
# BOSSが結合なし設計を決定済み(AI用ビュー作成計画 §36)。
# 公開15列はBOSS判断。非公開(本ビューでは参照しない。detail側の列のため構造的に出現しない):
# t_laser_actual_detailのdetail_type・display_order・product_*・units_per_shot・total_qty・scrap_qty・scrap_reason等。
# operator_user_id は t_laser_actual.created_by_id の別名(v_ai_laser_production_actualと同じ理由で付け替え)。
# created_at はこのビューでは衝突する列がないため、接尾辞(_h等)は不要(無印のまま)。
# line_id・process_id は2026-10-14にライン・工程の保存機能を追加したため、それより前の実績行はNULL(欠損ではなく仕様)。
# 将来のPostgreSQL移行を考え、MySQL固有の記法(バッククォート・DEFINER・SQL SECURITY・DBの修飾)を
# 使わない標準SQLだけで書く。
CREATE_VIEW = """
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

DROP_VIEW = 'DROP VIEW IF EXISTS v_ai_laser_interruption'


class Migration(migrations.Migration):

    dependencies = [
        ('ai', '0057_ai_brake_production_actual_view'),
        ('production', '0118_laser_actual_line_process'),
    ]

    operations = [migrations.RunSQL(CREATE_VIEW, DROP_VIEW)]
