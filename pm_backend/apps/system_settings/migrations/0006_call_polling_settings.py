from django.db import migrations


def insert_call_polling_settings(apps, schema_editor):
    SystemSetting = apps.get_model('system_settings', 'SystemSetting')
    initial = [
        {
            'key': 'call_polling_sec',
            'value': '3',
            'description': '通話着信監視間隔（秒）',
        },
        {
            'key': 'call_signal_polling_ms',
            'value': '1500',
            'description': '通話シグナル監視間隔（ms）',
        },
    ]
    for item in initial:
        SystemSetting.objects.get_or_create(
            key=item['key'],
            defaults={
                'value': item['value'],
                'description': item['description'],
            },
        )


class Migration(migrations.Migration):

    dependencies = [
        ('system_settings', '0005_due_plan_lock_seed'),
    ]

    operations = [
        migrations.RunPython(insert_call_polling_settings, migrations.RunPython.noop),
    ]
