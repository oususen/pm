from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('masters', '0053_seed_manual_documents'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProductCodeMapping',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('source_product_code', models.CharField(max_length=30, unique=True, verbose_name='変換元品番')),
                ('target_product_code', models.CharField(max_length=30, verbose_name='変換先品番')),
                ('is_active', models.BooleanField(default=True, verbose_name='有効')),
                ('note', models.CharField(blank=True, default='', max_length=200, verbose_name='備考')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='作成日時')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新日時')),
            ],
            options={
                'verbose_name': '品番変換',
                'verbose_name_plural': '品番変換',
                'db_table': 'm_product_code_mapping',
                'ordering': ['source_product_code'],
            },
        ),
    ]

