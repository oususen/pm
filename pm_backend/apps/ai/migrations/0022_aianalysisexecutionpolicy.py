from django.db import migrations, models


def create_initial_policy(apps, schema_editor):
    """新規テーブルへ分析実行設定の初期値1行を登録する。"""
    Policy = apps.get_model('ai', 'AIAnalysisExecutionPolicy')
    Policy.objects.using(schema_editor.connection.alias).create(
        plan_cache_ttl_minutes=60,
        max_execution_seconds=300,
        max_memory_mb=2048,
        max_cpu_cores='1.0',
        max_fetch_rows=100000,
    )


class Migration(migrations.Migration):
    dependencies = [('ai', '0021_add_default_cross_screen_access_policies')]

    operations = [
        migrations.CreateModel(
            name='AIAnalysisExecutionPolicy',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('plan_cache_ttl_minutes', models.PositiveIntegerField(default=60, verbose_name='分析案キャッシュ有効期限（分）')),
                ('max_execution_seconds', models.PositiveIntegerField(default=300, verbose_name='Python最大実行時間（秒）')),
                ('max_memory_mb', models.PositiveIntegerField(default=2048, verbose_name='Python最大メモリ（MB）')),
                ('max_cpu_cores', models.DecimalField(decimal_places=1, default='1.0', max_digits=2, verbose_name='Python CPU上限（コア数）')),
                ('max_fetch_rows', models.PositiveIntegerField(default=100000, verbose_name='取得行数の上限（行）')),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'ai_analysis_execution_policy',
                'verbose_name': 'AI分析実行設定',
                'verbose_name_plural': 'AI分析実行設定',
            },
        ),
        # 巻戻しではCreateModelの逆操作で新規テーブルごと削除される。
        migrations.RunPython(create_initial_policy, migrations.RunPython.noop),
    ]
