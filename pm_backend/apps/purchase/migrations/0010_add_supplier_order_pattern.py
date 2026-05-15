import django.db.models.deletion
from django.db import migrations, models


PATTERN_TYPE_MAP = {
    'EVERY_WEEK': ('WEEKLY', '毎週曜日'),
    'MONTHLY_DATE': ('MONTHLY_DATE', '毎月日付'),
    'WEEKLY_NTH_DAY': ('MONTHLY_NTH_DOW', '月の第N週の曜日'),
}

DAY_LABELS = {0: '月', 1: '火', 2: '水', 3: '木', 4: '金', 5: '土', 6: '日'}


def migrate_data(apps, schema_editor):
    SupplierOrderPattern = apps.get_model('purchase', 'SupplierOrderPattern')
    SupplierOrderSchedule = apps.get_model('purchase', 'SupplierOrderSchedule')

    for schedule in SupplierOrderSchedule.objects.all():
        old_type = schedule.pattern_type
        recurrence_type, recurrence_label = PATTERN_TYPE_MAP.get(old_type, ('WEEKLY', '毎週曜日'))

        if old_type == 'EVERY_WEEK':
            code = f'W-{DAY_LABELS.get(schedule.day_of_week, "?")}'
            name = f'毎週{DAY_LABELS.get(schedule.day_of_week, "?")}'
        elif old_type == 'MONTHLY_DATE':
            code = f'M-{schedule.day_of_month}'
            name = f'毎月{schedule.day_of_month}日'
        elif old_type == 'WEEKLY_NTH_DAY':
            code = f'N{schedule.nth_week}-{DAY_LABELS.get(schedule.day_of_week, "?")}'
            name = f'第{schedule.nth_week}{DAY_LABELS.get(schedule.day_of_week, "?")}曜'
        else:
            code = f'UNKNOWN-{schedule.id}'
            name = f'不明パターン({old_type})'

        pattern, _created = SupplierOrderPattern.objects.get_or_create(
            pattern_code=code,
            defaults={
                'pattern_name': name,
                'recurrence_type': recurrence_type,
                'day_of_week': schedule.day_of_week,
                'nth_week': schedule.nth_week,
                'day_of_month': schedule.day_of_month,
                'is_active': True,
            },
        )
        schedule.pattern = pattern
        schedule.save(update_fields=['pattern'])


class Migration(migrations.Migration):

    dependencies = [
        ('purchase', '0009_add_next_delivery_date'),
    ]

    operations = [
        migrations.CreateModel(
            name='SupplierOrderPattern',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('pattern_code', models.CharField(max_length=30, unique=True, verbose_name='パターンコード')),
                ('pattern_name', models.CharField(max_length=100, verbose_name='パターン名')),
                ('recurrence_type', models.CharField(choices=[('WEEKLY', '毎週曜日'), ('MONTHLY_DATE', '毎月日付'), ('MONTHLY_NTH_DOW', '月の第N週の曜日'), ('EVERY_BUSINESS_DAY', '毎営業日')], max_length=30, verbose_name='繰返し種別')),
                ('day_of_week', models.SmallIntegerField(blank=True, null=True, verbose_name='曜日(0=月〜6=日)')),
                ('nth_week', models.SmallIntegerField(blank=True, null=True, verbose_name='第N週')),
                ('day_of_month', models.SmallIntegerField(blank=True, null=True, verbose_name='日付')),
                ('is_active', models.BooleanField(default=True, verbose_name='有効')),
                ('note', models.CharField(blank=True, default='', max_length=200, verbose_name='備考')),
            ],
            options={
                'db_table': 'supplier_order_pattern',
                'ordering': ['pattern_code'],
            },
        ),
        migrations.AddField(
            model_name='supplierorderschedule',
            name='pattern',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='schedules', to='purchase.supplierorderpattern', verbose_name='発注パターン'),
        ),
        migrations.RunPython(migrate_data, migrations.RunPython.noop),
        migrations.RemoveIndex(
            model_name='supplierorderschedule',
            name='supplier_or_pattern_f98395_idx',
        ),
        migrations.RemoveField(
            model_name='supplierorderschedule',
            name='day_of_month',
        ),
        migrations.RemoveField(
            model_name='supplierorderschedule',
            name='day_of_week',
        ),
        migrations.RemoveField(
            model_name='supplierorderschedule',
            name='nth_week',
        ),
        migrations.RemoveField(
            model_name='supplierorderschedule',
            name='pattern_type',
        ),
    ]
