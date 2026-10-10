from django.db import migrations


# ラインマスタ(m_line)をAI用に公開するビュー。結合なし・全行(WHEREなし)。列は別名なし。
# 公開6列はBOSS判断(AI用ビュー作成計画 §15)。
# 非公開(ビューに含めない): lead_time_days, use_direct_process, created_at, updated_at
# 将来のPostgreSQL移行を考え、MySQL固有の記法(バッククォート・DEFINER・SQL SECURITY・DBの修飾)を使わない標準SQLだけで書く。
# (定義者・権限の付与は、DBごとに異なるため、マイグレーションに含めず、別の手順SQLで行う。AI用ビュー作成計画 §9.3)
CREATE_VIEW = """
CREATE OR REPLACE VIEW v_ai_line AS
SELECT
    id,
    line_code,
    line_name,
    calendar_id,
    line_type,
    is_active
FROM m_line
"""

DROP_VIEW = 'DROP VIEW IF EXISTS v_ai_line'


class Migration(migrations.Migration):
    # ビューの元になる m_line の6列は masters 0023(line_type の追加)までで揃う
    # (id・line_code・line_name・is_active=0001、calendar_id=0015、line_type=0023)
    dependencies = [
        ('ai', '0035_ai_process_view'),
        ('masters', '0023_line_line_type'),
    ]

    operations = [migrations.RunSQL(CREATE_VIEW, DROP_VIEW)]
