from django.db import migrations, models


# position → employment_type へのマッピング
POSITION_TO_EMPLOYMENT = {
    '人材派遣': 'dispatch',
    '実習生': 'intern',
    '特定技能実習生': 'skilled',
    'パート、時給者': 'part',
    '正（準）社員': 'regular',
}

# department_position_permission の position_name → role キー へのマッピング
POSITION_NAME_TO_ROLE = {
    'リーダー': 'leader',
    '事業部長': 'manager',
    '係長': 'chief',
    '班長': 'supervisor',
    '正（準）社員': 'staff',
}

# 雇用形態扱いで権限不要なもの（削除対象）
POSITION_NAME_DELETE = {'人材派遣', '実習生', '特定技能実習生', 'パート、時給者'}


def migrate_data(apps, schema_editor):
    UserProfile = apps.get_model('accounts', 'UserProfile')
    DepartmentPositionPermission = apps.get_model('accounts', 'DepartmentPositionPermission')
    PositionPermission = apps.get_model('accounts', 'PositionPermission')

    # 1. userprofile: position → employment_type に移行、正（準）社員+leaderはstaffに
    for profile in UserProfile.objects.all():
        pos = (profile.position or '').strip()

        # 正（準）社員 で role=leader の人はstaffに
        if pos == '正（準）社員' and profile.role == 'leader':
            profile.role = 'staff'

        # employment_type を position から設定
        if pos in POSITION_TO_EMPLOYMENT:
            profile.employment_type = POSITION_TO_EMPLOYMENT[pos]

        profile.save()

    # 2. department_position_permission: position_name を role キーに変換
    for perm in DepartmentPositionPermission.objects.all():
        name = (perm.position_name or '').strip()
        if name in POSITION_NAME_DELETE:
            perm.delete()
        elif name in POSITION_NAME_TO_ROLE:
            perm.position_name = POSITION_NAME_TO_ROLE[name]
            perm.save()

    # 3. position_permission も同様に変換（現在は空だが念のため）
    for perm in PositionPermission.objects.all():
        name = (perm.position_name or '').strip()
        if name in POSITION_NAME_DELETE:
            perm.delete()
        elif name in POSITION_NAME_TO_ROLE:
            perm.position_name = POSITION_NAME_TO_ROLE[name]
            perm.save()


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0014_add_unit_group_level'),
    ]

    operations = [
        # データ移行を先に実行
        migrations.RunPython(migrate_data, migrations.RunPython.noop),

        # employment_type の選択肢更新
        migrations.AlterField(
            model_name='userprofile',
            name='employment_type',
            field=models.CharField(
                max_length=20,
                choices=[
                    ('regular', '正準社員'),
                    ('dispatch', '人材派遣'),
                    ('intern', '実習生'),
                    ('skilled', '特定技能実習生'),
                    ('contract', '嘱託社員'),
                    ('part', 'パート'),
                ],
                default='regular',
                verbose_name='雇用形態',
            ),
        ),

        # role の選択肢更新
        migrations.AlterField(
            model_name='userprofile',
            name='role',
            field=models.CharField(
                max_length=20,
                choices=[
                    ('manager', '事業部長・課長'),
                    ('chief', '係長'),
                    ('supervisor', '班長'),
                    ('leader', 'リーダー'),
                    ('staff', '一般'),
                ],
                default='staff',
                verbose_name='役割',
            ),
        ),

        # position フィールド削除
        migrations.RemoveField(
            model_name='userprofile',
            name='position',
        ),
    ]
