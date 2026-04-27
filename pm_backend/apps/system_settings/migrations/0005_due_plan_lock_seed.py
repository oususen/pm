from django.db import migrations


PLAN_LOCK_KEYS = [
    ('lock_days.kubota_sakai_due_plan', '0', 'クボタ堺納期調整 計画入力ロック日数'),
]


def seed_plan_lock(apps, schema_editor):
    SystemSetting = apps.get_model('system_settings', 'SystemSetting')
    for key, value, description in PLAN_LOCK_KEYS:
        SystemSetting.objects.get_or_create(
            key=key,
            defaults={'value': value, 'description': description},
        )


def delete_plan_lock(apps, schema_editor):
    SystemSetting = apps.get_model('system_settings', 'SystemSetting')
    keys = [k for k, _, _ in PLAN_LOCK_KEYS]
    SystemSetting.objects.filter(key__in=keys).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('system_settings', '0004_lock_date_seed'),
    ]

    operations = [
        migrations.RunPython(seed_plan_lock, delete_plan_lock),
    ]

