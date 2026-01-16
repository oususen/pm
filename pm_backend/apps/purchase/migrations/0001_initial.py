from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ('masters', '0028_contact'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='PurchasePlanLockSetting',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('lock_days', models.PositiveIntegerField(default=0, verbose_name='ロック日数')),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='purchase_plan_lock_settings', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'purchase_plan_lock_setting',
            },
        ),
        migrations.CreateModel(
            name='PurchasePlanChangeLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('changed_at', models.DateTimeField(auto_now_add=True)),
                ('plan_date', models.DateField()),
                ('sequence_no', models.IntegerField(blank=True, null=True)),
                ('plan_id', models.CharField(blank=True, max_length=255, null=True)),
                ('before_qty', models.IntegerField(default=0)),
                ('after_qty', models.IntegerField(default=0)),
                ('reason', models.TextField()),
                ('changed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='purchase_plan_change_logs', to=settings.AUTH_USER_MODEL)),
                ('line', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='masters.line')),
                ('process', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='masters.process')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='masters.product')),
            ],
            options={
                'db_table': 'purchase_plan_change_log',
            },
        ),
        migrations.AddIndex(
            model_name='purchaseplanchangelog',
            index=models.Index(fields=['plan_date', 'line'], name='purchase_pl_plan_da_8a5c9e_idx'),
        ),
    ]
