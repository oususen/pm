from django.db import migrations


def seed_kubota_sakai_config(apps, schema_editor):
    SystemSetting = apps.get_model('system_settings', 'SystemSetting')
    SystemSetting.objects.get_or_create(
        key='kubota_sakai.assignment_deadline_days',
        defaults={
            'value': '3',
            'description': 'クボタ堺: 調整後納期の何営業日前までに便割付必須か',
        },
    )


def delete_kubota_sakai_config(apps, schema_editor):
    SystemSetting = apps.get_model('system_settings', 'SystemSetting')
    SystemSetting.objects.filter(
        key='kubota_sakai.assignment_deadline_days'
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('system_settings', '0002_initial_data'),
    ]

    operations = [
        migrations.RunPython(seed_kubota_sakai_config, delete_kubota_sakai_config),
    ]
