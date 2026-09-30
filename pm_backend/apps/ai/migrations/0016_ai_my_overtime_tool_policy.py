from django.db import migrations


# 本人の残業集計ツール(get_my_overtime)の管理設定を、本社横断(ai_home)と勤務(overtime)へ追加する。
# 既存の設定は変更しない(get_or_create)。管理設定画面で画面ごとに無効にできる。
SCREENS = ('ai_home', 'overtime')
TOOL_CODE = 'get_my_overtime'


def add_policy(apps, schema_editor):
    policy_model = apps.get_model('ai', 'AIToolPolicy')
    for screen_id in SCREENS:
        policy_model.objects.get_or_create(
            screen_id=screen_id, tool_code=TOOL_CODE,
            defaults={'is_enabled': True, 'allow_external_transfer': True},
        )


def remove_policy(apps, schema_editor):
    apps.get_model('ai', 'AIToolPolicy').objects.filter(tool_code=TOOL_CODE, screen_id__in=SCREENS).delete()


class Migration(migrations.Migration):
    dependencies = [('ai', '0015_alter_aitoolpolicy_tool_code')]

    operations = [migrations.RunPython(add_policy, remove_policy)]
