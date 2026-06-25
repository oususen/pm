from django.db import migrations


def copy_line_settings(apps, schema_editor):
    """production_record_inquiry_settingから生産計画用タブのデータを新テーブルへコピー"""
    OldSetting = apps.get_model('production', 'ProductionRecordInquirySetting')
    NewSetting = apps.get_model('production', 'ProductionPlanLineSetting')
    plan_tabs = ['tank', 'floor', 'kubota', 'floor-shipping', 'blade', 'laser', 'brake', 'spot']
    for row in OldSetting.objects.filter(tab_key__in=plan_tabs):
        NewSetting.objects.update_or_create(
            tab_key=row.tab_key,
            defaults={
                'target_line_codes': row.target_line_codes or [],
                'updated_by': row.updated_by,
            },
        )


class Migration(migrations.Migration):
    dependencies = [
        ('production', '0065_productionplanlinesetting'),
    ]

    operations = [
        migrations.RunPython(copy_line_settings, migrations.RunPython.noop),
    ]
