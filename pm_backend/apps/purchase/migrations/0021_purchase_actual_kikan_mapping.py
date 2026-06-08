from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('purchase', '0020_auto_delivery_list_progress_forward'),
        ('masters', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='PurchaseActualKikanMapping',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('mappings', models.JSONField(blank=True, default=list, verbose_name='品番マッピング一覧')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新日時')),
                ('supplier', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='kikan_mapping',
                    to='masters.supplier',
                    verbose_name='仕入先',
                )),
                ('updated_by', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='purchase_actual_kikan_mappings',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='更新者',
                )),
            ],
            options={
                'verbose_name': '仕入先納入基幹マッピング',
                'verbose_name_plural': '仕入先納入基幹マッピング',
                'db_table': 'purchase_actual_kikan_mapping',
            },
        ),
    ]
