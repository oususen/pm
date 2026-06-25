from django.db import migrations, models


DEFAULT_TAB_NAMES = {
    'tank': 'タンク',
    'floor': 'フロア',
    'team2': '2班',
    'floor-shipping': 'フロア出荷',
    'blade': 'ブレード',
    'laser': '板金',
    'brake': 'ブレーキ',
    'spot': 'スポット',
}

DEFAULT_SORT_ORDERS = {
    'tank': 0,
    'floor': 1,
    'team2': 2,
    'blade': 3,
    'laser': 4,
    'floor-shipping': 5,
    'brake': 6,
    'spot': 7,
}


def set_tab_names(apps, schema_editor):
    Setting = apps.get_model('production', 'ProductionRecordInquirySetting')
    for row in Setting.objects.all():
        row.tab_name = DEFAULT_TAB_NAMES.get(row.tab_key, row.tab_key)
        row.sort_order = DEFAULT_SORT_ORDERS.get(row.tab_key, 99)
        row.save(update_fields=['tab_name', 'sort_order'])


class Migration(migrations.Migration):
    dependencies = [
        ('production', '0067_add_tab_name_sort_order'),
    ]

    operations = [
        migrations.AddField(
            model_name='productionrecordinquirysetting',
            name='tab_name',
            field=models.CharField(blank=True, default='', max_length=50, verbose_name='タブ表示名'),
        ),
        migrations.AddField(
            model_name='productionrecordinquirysetting',
            name='sort_order',
            field=models.IntegerField(default=0, verbose_name='表示順'),
        ),
        migrations.AlterField(
            model_name='productionrecordinquirysetting',
            name='tab_key',
            field=models.CharField(max_length=30, unique=True, verbose_name='タブキー'),
        ),
        migrations.AlterModelOptions(
            name='productionrecordinquirysetting',
            options={'ordering': ['sort_order', 'id'], 'verbose_name': '生産実績照会設定', 'verbose_name_plural': '生産実績照会設定'},
        ),
        migrations.RunPython(set_tab_names, migrations.RunPython.noop),
    ]
