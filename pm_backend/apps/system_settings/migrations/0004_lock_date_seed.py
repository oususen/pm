from django.db import migrations


LOCK_DATE_KEYS = [
    ('lock_date.kubota_sakai_due', '', 'クボタ堺納期調整 締め日'),
    ('lock_date.inventory', '', '在庫計算 締め日'),
    ('lock_date.progress', '', '進度計算 締め日'),
]


def seed_lock_dates(apps, schema_editor):
    SystemSetting = apps.get_model('system_settings', 'SystemSetting')
    for key, value, description in LOCK_DATE_KEYS:
        SystemSetting.objects.get_or_create(
            key=key,
            defaults={'value': value, 'description': description},
        )


def delete_lock_dates(apps, schema_editor):
    SystemSetting = apps.get_model('system_settings', 'SystemSetting')
    keys = [k for k, _, _ in LOCK_DATE_KEYS]
    SystemSetting.objects.filter(key__in=keys).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('system_settings', '0003_kubota_sakai_config'),
    ]

    operations = [
        migrations.RunPython(seed_lock_dates, delete_lock_dates),
    ]
