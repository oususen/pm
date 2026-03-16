from django.db import migrations


class Migration(migrations.Migration):
    """
    0027_alter_capacity_nullable (0026から分岐した葉ノード) と
    0036_merge_0027_0035 を統合するマージマイグレーション
    """

    dependencies = [
        ('masters', '0027_alter_capacity_nullable'),
        ('masters', '0036_merge_0027_0035'),
    ]

    operations = [
    ]
