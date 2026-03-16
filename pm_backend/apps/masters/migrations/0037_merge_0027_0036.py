from django.db import migrations


class Migration(migrations.Migration):
    """
    0026から分岐した 0027_alter_capacity_nullable と
    0036_merge_0027_0035 を統合するマージマイグレーション。
    本番: 0027は適用済みのためスキップ、0037のみ適用される。
    開発PC: 0027(nullable化)を適用後、0037が適用される。
    """

    dependencies = [
        ('masters', '0027_alter_capacity_nullable'),
        ('masters', '0036_merge_0027_0035'),
    ]

    operations = [
    ]
