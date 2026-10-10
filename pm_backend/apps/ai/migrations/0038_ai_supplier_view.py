from django.db import migrations


# 仕入先マスタ(m_supplier)をAI用に公開するビュー。結合なし・全行(WHEREなし)。列は別名なし。
# 公開5列はBOSS判断(AI用ビュー作成計画 §17)。
# 非公開(ビューに含めない): contact_person(担当者名), phone_number(電話番号), order_email(メールアドレス)。個人名・連絡先のため
# 将来のPostgreSQL移行を考え、MySQL固有の記法(バッククォート・DEFINER・SQL SECURITY・DBの修飾)を使わない標準SQLだけで書く。
# (定義者・権限の付与は、DBごとに異なるため、マイグレーションに含めず、別の手順SQLで行う。AI用ビュー作成計画 §19.1)
CREATE_VIEW = """
CREATE OR REPLACE VIEW v_ai_supplier AS
SELECT
    id,
    supplier_code,
    supplier_name,
    supplier_type,
    calendar_id
FROM m_supplier
"""

DROP_VIEW = 'DROP VIEW IF EXISTS v_ai_supplier'


class Migration(migrations.Migration):
    # ビューの元になる m_supplier の5列は masters 0059(supplier_type の追加)までで揃う
    # (id・supplier_code・supplier_name=0001、calendar_id=0032、supplier_type=0059)
    dependencies = [
        ('ai', '0037_ai_product_view_remove_dates'),
        ('masters', '0059_supplier_supplier_type'),
    ]

    operations = [migrations.RunSQL(CREATE_VIEW, DROP_VIEW)]
