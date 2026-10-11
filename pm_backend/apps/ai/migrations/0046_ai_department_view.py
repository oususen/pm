from django.db import migrations


# 部署(accounts_department)をAI用に公開するビュー。組織(部署)の階層を表す。
# 親の部署の名称を付けるため、自分自身を主キー(pd.id = d.parent_id)で LEFT JOIN する。結合先は主キーの1対1のため、行数は accounts_department と同じ。
# WHEREなし(全行)。公開6列はBOSS承認(AI用ビュー作成計画 §27。2026-10-11)。親の部署の名称は parent_name の別名で公開する。
# 将来のPostgreSQL移行を考え、MySQL固有の記法(バッククォート・DEFINER・SQL SECURITY・DBの修飾)を使わない標準SQLだけで書く。
# (定義者・権限の付与は、DBごとに異なるため、マイグレーションに含めず、別の手順SQLで行う。AI用ビュー作成計画 §27)
CREATE_VIEW = """
CREATE OR REPLACE VIEW v_ai_department AS
SELECT
    d.id,
    d.name,
    d.level,
    d.display_id,
    d.parent_id,
    pd.name AS parent_name
FROM accounts_department d
LEFT JOIN accounts_department pd ON pd.id = d.parent_id
"""

DROP_VIEW = 'DROP VIEW IF EXISTS v_ai_department'


class Migration(migrations.Migration):
    # ビューの元になる列は accounts 0072(現行の最新)までで揃う(accounts_department: id・name・level・parent_id・display_id=0002)
    dependencies = [
        ('ai', '0045_ai_user_view'),
    ]

    operations = [migrations.RunSQL(CREATE_VIEW, DROP_VIEW)]
