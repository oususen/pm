from django.db import migrations


# 得意先マスタ(m_customer)をAI用に公開するビュー。結合なし・全行(WHEREなし)。列は別名なし。
# 公開6列はBOSS承認(AI用ビュー作成計画 §21)。
# 非公開(ビューに含めない): created_at(作成日時), updated_at(更新日時)
# 将来のPostgreSQL移行を考え、MySQL固有の記法(バッククォート・DEFINER・SQL SECURITY・DBの修飾)を使わない標準SQLだけで書く。
# (定義者・権限の付与は、DBごとに異なるため、マイグレーションに含めず、管理コマンド setup_ai_views で行う。AI用ビュー作成計画 §20)
CREATE_VIEW = """
CREATE OR REPLACE VIEW v_ai_customer AS
SELECT
    id,
    customer_code,
    customer_name,
    short_name,
    calendar_id,
    is_active
FROM m_customer
"""

DROP_VIEW = 'DROP VIEW IF EXISTS v_ai_customer'


class Migration(migrations.Migration):
    # ビューの元になる m_customer の6列は masters 0001_initial で揃う
    # (id・customer_code・customer_name・short_name・is_active・calendar_id は、すべて CreateModel Customer で作成)
    dependencies = [
        ('ai', '0038_ai_supplier_view'),
        ('masters', '0001_initial'),
    ]

    operations = [migrations.RunSQL(CREATE_VIEW, DROP_VIEW)]
