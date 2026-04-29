from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('masters', '0047_routingstep_supplier'),
        ('production', '0050_processworksessionequipment'),
    ]

    operations = [
        migrations.AddField(
            model_name='scheduleconfig',
            name='process',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='schedule_configs', to='masters.process', verbose_name='対象工程'),
        ),
        migrations.AlterField(
            model_name='scheduleconfig',
            name='task_name',
            field=models.CharField(choices=[('INVENTORY_RECALC', '在庫再計算'), ('PICKUP_ONLY', '取り込みのみ'), ('INVENTORY_ONLY', '在庫計算のみ'), ('PROGRESS_ONLY', '進度計算のみ'), ('AUTO_PLAN', '生産計画自動生成'), ('ORDER_EXPANSION', '自動受注展開'), ('AUTO_SAFETY_STOCK_INTERNAL', '自動安全在庫（社内）'), ('AUTO_SAFETY_STOCK_PURCHASE', '自動安全在庫（購入品）'), ('AUTO_PURCHASE_ORDER_CHECK', '発注タイミング日次チェック'), ('PURCHASE_ACTUAL_RECONCILE_CHECK', '納入実績整合チェック'), ('PRODUCTION_ACTUAL_RECONCILE_CHECK', '生産実績整合チェック'), ('PLAN_TO_ACTUAL_COPY', '計画実績自動セット')], max_length=50, verbose_name='タスク名'),
        ),
        migrations.RemoveConstraint(
            model_name='scheduleconfig',
            name='uniq_schedule_task_line',
        ),
        migrations.AddConstraint(
            model_name='scheduleconfig',
            constraint=models.UniqueConstraint(fields=('task_name', 'line', 'process'), name='uniq_schedule_task_line'),
        ),
    ]
