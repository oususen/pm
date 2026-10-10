from django.db import migrations


# 工程マスタ(m_process)をAI用に公開するビュー。結合なし・全行(WHEREなし)。列は別名なし。
# 公開9列はBOSS判断(AI用ビュー作成計画 §13)。
# 非公開(ビューに含めない): is_outsource, created_at, updated_at
# 将来のPostgreSQL移行を考え、MySQL固有の記法(バッククォート・DEFINER・SQL SECURITY・DBの修飾)を使わない標準SQLだけで書く。
# (定義者・権限の付与は、DBごとに異なるため、マイグレーションに含めず、別の手順SQLで行う。AI用ビュー作成計画 §9.3)
CREATE_VIEW = """
CREATE OR REPLACE VIEW v_ai_process AS
SELECT
    id,
    process_code,
    process_name,
    line_id,
    management_unit,
    operating_rate,
    equipment_count,
    two_person_only,
    is_active
FROM m_process
"""

DROP_VIEW = 'DROP VIEW IF EXISTS v_ai_process'


class Migration(migrations.Migration):
    # ビューの元になる m_process の9列は masters 0084(two_person_only の追加)までで揃う
    # (line_id=0003、management_unit=0011、equipment_count・operating_rate=0073、two_person_only=0084)
    dependencies = [
        ('ai', '0034_ai_product_view'),
        ('masters', '0084_add_two_person_only_to_process'),
    ]

    operations = [migrations.RunSQL(CREATE_VIEW, DROP_VIEW)]
