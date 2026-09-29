from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('ai', '0007_fix_openrouter_default_model')]

    operations = [
        migrations.CreateModel(
            name='AIKnowledgeDocument',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('category', models.CharField(choices=[('pm_structure', 'PMアプリ構造'), ('manual', 'マニュアル'), ('procedure', '手順書'), ('security', '安全・運用規約')], max_length=30, verbose_name='区分')),
                ('name', models.CharField(max_length=150, verbose_name='資料名')),
                ('file', models.FileField(upload_to='ai_knowledge/', verbose_name='資料ファイル')),
                ('description', models.CharField(blank=True, default='', max_length=300, verbose_name='説明')),
                ('is_enabled', models.BooleanField(default=True, verbose_name='有効')),
                ('uploaded_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={'verbose_name': 'AIナレッジ資料', 'verbose_name_plural': 'AIナレッジ資料', 'db_table': 'ai_knowledge_document', 'ordering': ['category', 'name', 'id']},
        ),
    ]
