import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('production', '0064_add_stocktake_area'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProductionPlanLineSetting',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tab_key', models.CharField(max_length=30, unique=True, verbose_name='対象タブ')),
                ('target_line_codes', models.JSONField(blank=True, default=list, verbose_name='対象ラインコード一覧')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新日時')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='production_plan_line_settings', to=settings.AUTH_USER_MODEL, verbose_name='更新者')),
            ],
            options={
                'verbose_name': '生産計画ライン設定',
                'verbose_name_plural': '生産計画ライン設定',
                'db_table': 'production_plan_line_setting',
            },
        ),
    ]
