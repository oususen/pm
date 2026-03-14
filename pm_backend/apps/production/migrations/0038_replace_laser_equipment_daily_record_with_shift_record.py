"""
migration 0037 で作成した LaserEquipmentDailyRecord (t_laser_equipment_daily_record) を削除し、
LaserShiftRecord (t_laser_shift_record) を作成する。
"""
from django.conf import settings
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('production', '0037_laser_equipment_daily_record'),
        ('masters', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # 旧テーブル削除
        migrations.DeleteModel(
            name='LaserEquipmentDailyRecord',
        ),

        # 新テーブル作成
        migrations.CreateModel(
            name='LaserShiftRecord',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('work_date', models.DateField(verbose_name='作業日')),
                ('shift_no', models.PositiveSmallIntegerField(
                    choices=[(1, '1勤'), (2, '2勤')],
                    verbose_name='シフト',
                )),
                ('start_totalizer_hour', models.PositiveIntegerField(verbose_name='開始積算カウンター(H)')),
                ('start_totalizer_min', models.PositiveIntegerField(
                    validators=[django.core.validators.MaxValueValidator(59)],
                    verbose_name='開始積算カウンター(M)',
                )),
                ('end_totalizer_hour', models.PositiveIntegerField(
                    blank=True, null=True, verbose_name='終了積算カウンター(H)'
                )),
                ('end_totalizer_min', models.PositiveIntegerField(
                    blank=True, null=True,
                    validators=[django.core.validators.MaxValueValidator(59)],
                    verbose_name='終了積算カウンター(M)',
                )),
                ('work_hours', models.DecimalField(
                    blank=True, decimal_places=1, max_digits=5, null=True,
                    verbose_name='仕事時間(H)',
                )),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='作成日時')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新日時')),
                ('equipment', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='laser_shift_records',
                    to='masters.equipment',
                    verbose_name='設備',
                )),
                ('created_by', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='created_laser_shift_records',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='作成者',
                )),
                ('updated_by', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='updated_laser_shift_records',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='更新者',
                )),
            ],
            options={
                'verbose_name': 'レーザーシフト稼働記録',
                'verbose_name_plural': 'レーザーシフト稼働記録',
                'db_table': 't_laser_shift_record',
                'ordering': ['-work_date', 'equipment', 'shift_no'],
                'unique_together': {('work_date', 'equipment', 'shift_no')},
            },
        ),
        migrations.AddIndex(
            model_name='lasershiftrecord',
            index=models.Index(fields=['work_date'], name='t_laser_shi_work_da_3db0fb_idx'),
        ),
        migrations.AddIndex(
            model_name='lasershiftrecord',
            index=models.Index(fields=['equipment', 'work_date'], name='t_laser_shi_equipme_913bd7_idx'),
        ),
    ]
