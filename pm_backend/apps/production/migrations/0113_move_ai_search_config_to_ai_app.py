from django.db import migrations


class Migration(migrations.Migration):
    """AISearchConfigの管理元を production から ai アプリへ移す。

    実テーブル(ai_search_config)は削除しない。ai アプリの 0001_initial で
    同じテーブルを状態(state)としてそのまま引き継ぐ。
    """

    dependencies = [
        ('production', '0112_add_ai_search_config'),
        ('ai', '0001_initial'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.DeleteModel(name='AISearchConfig'),
            ],
        ),
    ]
