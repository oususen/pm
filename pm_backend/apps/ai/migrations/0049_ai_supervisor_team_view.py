from django.db import migrations


# 班長の担当班(accounts_userprofile_supervisor_teams。UserProfile.supervisor_teams の中間テーブル)をAI用に公開するビュー。
# 中間テーブルを主とし、ユーザーの識別情報(auth_user のログインID・姓・名、accounts_userprofile の社員コード)と、
# 班(accounts_department)の名称を LEFT JOIN で付ける。
# 結合はすべて相手の主キー(a.id・p.user_id・d.id)との1対1のため、行数は accounts_userprofile_supervisor_teams と同じ。WHEREなし(全行)。
# admin アカウントの除外は行わない(v_ai_user は admin を除くため、v_ai_user と結べない行がありうる)。
# 公開8列はBOSS承認(AI用ビュー作成計画 §29。2026-10-11。氏名・社員コードの付与もBOSS承認)。ログインID(username)は login_id の別名で公開する。
# 非公開(ビューに含めない): auth_user の password・email 等、accounts_userprofile の employee_code 以外の列
# 将来のPostgreSQL移行を考え、MySQL固有の記法(バッククォート・DEFINER・SQL SECURITY・DBの修飾)を使わない標準SQLだけで書く。
# (定義者・権限の付与は、DBごとに異なるため、マイグレーションに含めず、別の手順SQLで行う。AI用ビュー作成計画 §29)
CREATE_VIEW = """
CREATE OR REPLACE VIEW v_ai_supervisor_team AS
SELECT
    m.id,
    m.userprofile_id AS user_id,
    a.username AS login_id,
    a.last_name,
    a.first_name,
    p.employee_code,
    m.department_id AS team_id,
    d.name AS team_name
FROM accounts_userprofile_supervisor_teams m
LEFT JOIN auth_user a ON a.id = m.userprofile_id
LEFT JOIN accounts_userprofile p ON p.user_id = m.userprofile_id
LEFT JOIN accounts_department d ON d.id = m.department_id
"""

DROP_VIEW = 'DROP VIEW IF EXISTS v_ai_supervisor_team'


class Migration(migrations.Migration):
    # 中間テーブル accounts_userprofile_supervisor_teams は accounts 0072(現行の最新)までで揃う。auth_user・accounts_userprofile・accounts_department は既存。
    dependencies = [
        ('ai', '0048_ai_unit_line_view'),
    ]

    operations = [migrations.RunSQL(CREATE_VIEW, DROP_VIEW)]
