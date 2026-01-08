# Generated manually on 2026-01-08
# テーブル名をm_container_capacityに変更（命名規則の統一）

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('masters', '0025_update_container_capacity_table'),
    ]

    operations = [
        migrations.AlterModelTable(
            name='containercapacity',
            table='m_container_capacity',
        ),
    ]
