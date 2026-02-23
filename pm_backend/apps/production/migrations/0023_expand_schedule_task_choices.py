from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('production', '0022_alter_scheduleconfig_task_name'),
    ]

    operations = [
        migrations.AlterField(
            model_name='scheduleconfig',
            name='task_name',
            field=models.CharField(
                choices=[
                    ('INVENTORY_RECALC', '在庫再計算'),
                    ('PICKUP_ONLY', '取り込みのみ'),
                    ('INVENTORY_ONLY', '在庫計算のみ'),
                    ('PROGRESS_ONLY', '進度計算のみ'),
                    ('AUTO_PLAN', '生産計画自動生成'),
                    ('ORDER_EXPANSION', '自動受注展開'),
                ],
                max_length=50,
                verbose_name='タスク名',
            ),
        ),
    ]
