from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('ai', '0018_alter_aitoolpolicy_screen_id')]

    operations = [
        migrations.CreateModel(
            name='AICrossScreenAccessPolicy',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('source_screen_id', models.CharField(choices=[('ai_home', '本社横断'), ('orders', '受注'), ('production', '生産'), ('quality', '品質'), ('overtime', '勤務'), ('purchase', '仕入'), ('shipping', '出荷'), ('inventory', '在庫'), ('masters', 'マスタ')], max_length=40, verbose_name='起点画面')),
                ('target_screen_id', models.CharField(choices=[('ai_home', '本社横断'), ('orders', '受注'), ('production', '生産'), ('quality', '品質'), ('overtime', '勤務'), ('purchase', '仕入'), ('shipping', '出荷'), ('inventory', '在庫'), ('masters', 'マスタ')], max_length=40, verbose_name='追加参照領域')),
                ('purpose', models.CharField(max_length=200, verbose_name='利用目的')),
                ('is_enabled', models.BooleanField(default=True, verbose_name='有効')),
                ('allow_external_transfer', models.BooleanField(default=True, verbose_name='外部AIへの集計結果送信を許可')),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={'db_table': 'ai_cross_screen_access_policy', 'ordering': ['source_screen_id', 'target_screen_id']},
        ),
        migrations.AddConstraint(model_name='aicrossscreenaccesspolicy', constraint=models.UniqueConstraint(fields=('source_screen_id', 'target_screen_id'), name='ai_cross_screen_access_unique')),
    ]
