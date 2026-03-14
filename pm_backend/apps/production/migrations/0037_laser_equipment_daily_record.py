from django.conf import settings
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('production', '0036_laseractualdetail_scrap_fields'),
        ('masters', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='LaserEquipmentDailyRecord',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('work_date', models.DateField(verbose_name='作業日')),
                ('totalizer_hour', models.PositiveIntegerField(verbose_name='積算カウンター(H)')),
                ('totalizer_min', models.PositiveIntegerField(
                    validators=[django.core.validators.MaxValueValidator(59)],
                    verbose_name='積算カウンター(M)',
                )),
                ('work_hours', models.DecimalField(decimal_places=1, max_digits=5, verbose_name='仕事時間(H)')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='作成日時')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新日時')),
                ('equipment', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='laser_daily_records',
                    to='masters.equipment',
                    verbose_name='設備',
                )),
                ('created_by', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='created_laser_daily_records',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='作成者',
                )),
                ('updated_by', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='updated_laser_daily_records',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='更新者',
                )),
            ],
            options={
                'verbose_name': 'レーザー設備稼働日次記録',
                'verbose_name_plural': 'レーザー設備稼働日次記録',
                'db_table': 't_laser_equipment_daily_record',
                'ordering': ['-work_date', 'equipment'],
                'unique_together': {('work_date', 'equipment')},
            },
        ),
        migrations.AddIndex(
            model_name='laserequipmentdailyrecord',
            index=models.Index(fields=['work_date'], name='t_laser_equ_work_da_2bb519_idx'),
        ),
        migrations.AddIndex(
            model_name='laserequipmentdailyrecord',
            index=models.Index(fields=['equipment', 'work_date'], name='t_laser_equ_equipme_5eee98_idx'),
        ),
    ]
