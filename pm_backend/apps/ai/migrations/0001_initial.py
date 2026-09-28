from django.db import migrations, models


class Migration(migrations.Migration):
    """AISearchConfigをproductionアプリからai アプリへ移設する。

    実テーブル(ai_search_config)は production の 0112 マイグレーションで
    既に作成済み・本番運用中のため、ここではDBへは触れず、Djangoの
    アプリ状態(state)だけにモデルを追加する。
    """

    initial = True

    dependencies = []

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.CreateModel(
                    name='AISearchConfig',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('model_path', models.CharField(max_length=100, verbose_name='モデルパス')),
                        ('label', models.CharField(max_length=50, verbose_name='表示ラベル')),
                        ('search_fields', models.JSONField(verbose_name='検索フィールド')),
                        ('display_fields', models.JSONField(verbose_name='表示フィールド')),
                        ('display_template', models.CharField(max_length=300, verbose_name='表示テンプレート')),
                        ('filter_json', models.JSONField(blank=True, default=dict, verbose_name='フィルタ条件')),
                        ('is_active', models.BooleanField(default=True, verbose_name='有効')),
                        ('display_order', models.IntegerField(default=0, verbose_name='表示順')),
                        ('created_at', models.DateTimeField(auto_now_add=True)),
                        ('updated_at', models.DateTimeField(auto_now=True)),
                    ],
                    options={
                        'verbose_name': 'AI検索設定',
                        'verbose_name_plural': 'AI検索設定',
                        'db_table': 'ai_search_config',
                        'ordering': ['display_order', 'label'],
                    },
                ),
            ],
        ),
    ]
