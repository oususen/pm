# Generated merge migration to resolve conflicting leaf nodes.
# NOTE:
# 旧ブランチの 0027_alter_capacity_nullable が削除済みのため、
# 現行系列の最新ノード 0035_equipment_process に合わせる。

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('masters', '0035_equipment_process'),
    ]

    operations = [
    ]
