# 本番環境で適用済みのマイグレーション（ファイルのみ欠落していたため復元）
# ContainerCapacityのcapacityフィールドをnullable対応

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('masters', '0026_rename_container_capacity_table'),
    ]

    operations = [
        migrations.AlterField(
            model_name='containercapacity',
            name='capacity',
            field=models.IntegerField(blank=True, null=True, verbose_name='入り数', help_text='容器に入る製品の個数'),
        ),
    ]
