from django.db import migrations


def insert_initial_settings(apps, schema_editor):
    SystemSetting = apps.get_model('system_settings', 'SystemSetting')
    initial = [
        {
            'key': 'notification_polling_sec',
            'value': '60',
            'description': '通知ポーリング間隔（秒）',
        },
        {
            'key': 'task_polling_sec',
            'value': '120',
            'description': 'タスクポーリング間隔（秒）',
        },
    ]
    for item in initial:
        SystemSetting.objects.get_or_create(key=item['key'], defaults={
            'value': item['value'],
            'description': item['description'],
        })


class Migration(migrations.Migration):

    dependencies = [
        ('system_settings', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(insert_initial_settings, migrations.RunPython.noop),
    ]
