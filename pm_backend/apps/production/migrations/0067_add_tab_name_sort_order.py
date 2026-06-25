from django.db import migrations, models


DEFAULT_TAB_NAMES = {
    'tank': 'タンク',
    'floor': '２班',
    'kubota': 'クボタ',
    'floor-shipping': 'フロア出荷',
    'blade': 'ブレード',
    'laser': 'レーザ',
    'brake': 'ブレーキ',
    'spot': 'スポット',
}

DEFAULT_SORT_ORDERS = {
    'tank': 0,
    'floor': 1,
    'kubota': 2,
    'floor-shipping': 3,
    'blade': 4,
    'laser': 5,
    'brake': 6,
    'spot': 7,
}


def set_tab_names(apps, schema_editor):
    Setting = apps.get_model('production', 'ProductionPlanLineSetting')
    for row in Setting.objects.all():
        row.tab_name = DEFAULT_TAB_NAMES.get(row.tab_key, row.tab_key)
        row.sort_order = DEFAULT_SORT_ORDERS.get(row.tab_key, 99)
        row.save(update_fields=['tab_name', 'sort_order'])


class Migration(migrations.Migration):
    dependencies = [
        ('production', '0066_migrate_plan_line_settings_data'),
    ]

    operations = [
        migrations.AddField(
            model_name='productionplanlinesetting',
            name='tab_name',
            field=models.CharField(blank=True, default='', max_length=50, verbose_name='タブ表示名'),
        ),
        migrations.AddField(
            model_name='productionplanlinesetting',
            name='sort_order',
            field=models.IntegerField(default=0, verbose_name='表示順'),
        ),
        migrations.AlterModelOptions(
            name='productionplanlinesetting',
            options={'ordering': ['sort_order', 'id'], 'verbose_name': '生産計画ライン設定', 'verbose_name_plural': '生産計画ライン設定'},
        ),
        migrations.RunPython(set_tab_names, migrations.RunPython.noop),
    ]
