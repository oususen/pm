from django.db import migrations


# ユーザー(auth_user)をAI用に公開するビュー。auth_user を主とし、プロフィール(accounts_userprofile)と、
# プロフィールの5つの所属(部署・事業部・係・班・グループ)の部署(accounts_department)の名称を LEFT JOIN で付ける。
# 結合はすべて相手の主キーとの1対1(プロフィールは主キー user_id、部署は主キー id)のため、行数は WHERE 後の auth_user と同じ。
# WHERE は auth_user の1条件だけ: u.username <> 'admin'(admin アカウントを含めない。BOSS承認 2026-10-11)。
# 公開21列はBOSS承認(AI用ビュー作成計画 §27。2026-10-11)。ログインID(username)は login_id の別名で公開する。
# 非公開(ビューに含めない): auth_user の password・last_login・is_superuser・email・date_joined、
# accounts_userprofile の created_at・updated_at、結合先の部署の名称以外の列
# 将来のPostgreSQL移行を考え、MySQL固有の記法(バッククォート・DEFINER・SQL SECURITY・DBの修飾)を使わない標準SQLだけで書く。
# (定義者・権限の付与は、DBごとに異なるため、マイグレーションに含めず、別の手順SQLで行う。AI用ビュー作成計画 §27)
CREATE_VIEW = """
CREATE OR REPLACE VIEW v_ai_user AS
SELECT
    u.id,
    u.username AS login_id,
    u.first_name,
    u.last_name,
    u.is_active,
    u.is_staff,
    p.employee_code,
    p.employment_type,
    p.role,
    p.is_system_admin,
    p.joined_on,
    p.department_id,
    d1.name AS department_name,
    p.division_id,
    d2.name AS division_name,
    p.group_id,
    d3.name AS group_name,
    p.team_id,
    d4.name AS team_name,
    p.unit_id,
    d5.name AS unit_name
FROM auth_user u
LEFT JOIN accounts_userprofile p ON p.user_id = u.id
LEFT JOIN accounts_department d1 ON d1.id = p.department_id
LEFT JOIN accounts_department d2 ON d2.id = p.division_id
LEFT JOIN accounts_department d3 ON d3.id = p.group_id
LEFT JOIN accounts_department d4 ON d4.id = p.team_id
LEFT JOIN accounts_department d5 ON d5.id = p.unit_id
WHERE u.username <> 'admin'
"""

DROP_VIEW = 'DROP VIEW IF EXISTS v_ai_user'


class Migration(migrations.Migration):
    # ビューの元になる列は accounts 0072(現行の最新)までで揃う
    # (auth_user の列=auth 0012 まで。accounts_userprofile: user_id・employee_code・role・employment_type・department_id・division_id・
    #  group_id・team_id・joined_on=0002、unit_id=0017、is_system_admin=0071。accounts_department: id・name・level・parent_id・display_id=0002)
    dependencies = [
        ('ai', '0044_alter_aianalysistemplate_category'),
        ('accounts', '0072_alter_departmentpermission_resource_and_more'),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [migrations.RunSQL(CREATE_VIEW, DROP_VIEW)]
