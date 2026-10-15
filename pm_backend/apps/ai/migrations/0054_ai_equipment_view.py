from django.db import migrations

# 設備マスタ(m_equipment)をAI用に公開するビュー。結合なし・全行(WHEREなし)。
# 公開6列はBOSS判断(AI用ビュー作成計画 §32)。
# 非公開(ビューに含めない): display_order, notes, created_at, updated_at
# 将来のPostgreSQL移行を考え、MySQL固有の記法(バッククォート・DEFINER・SQL SECURITY・DBの修飾)を使わない標準SQLだけで書く。
# (定義者・権限の付与は、DBごとに異なるため、マイグレーションに含めず、setup_ai_views コマンドで行う)
CREATE_VIEW = """
CREATE OR REPLACE VIEW v_ai_equipment AS
SELECT
    id,
    equipment_code,
    equipment_name,
    is_active,
    line_id,
    process_id
FROM m_equipment
"""

DROP_VIEW = 'DROP VIEW IF EXISTS v_ai_equipment'


class Migration(migrations.Migration):

    dependencies = [
        ('ai', '0053_add_anthropic_provider'),
        ('masters', '0035_equipment_process'),
    ]

    operations = [migrations.RunSQL(CREATE_VIEW, DROP_VIEW)]
