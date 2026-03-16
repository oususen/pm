from django.db import migrations


class Migration(migrations.Migration):
    """
    旧ブランチ由来の 0027_alter_capacity_nullable は現行系列に存在しないため、
    実在ノード 0036_merge_0027_0035 のみへ依存させる。
    """

    dependencies = [
        ('masters', '0027_alter_capacity_nullable'),
        ('masters', '0036_merge_0027_0035'),
    ]

    operations = [
    ]
