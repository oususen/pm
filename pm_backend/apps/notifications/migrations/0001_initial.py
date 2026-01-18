from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200, verbose_name='タイトル')),
                ('category', models.CharField(max_length=50, verbose_name='カテゴリ')),
                ('domain', models.CharField(max_length=50, verbose_name='種別')),
                ('valid_from', models.DateField(blank=True, null=True, verbose_name='有効開始日')),
                ('valid_to', models.DateField(blank=True, null=True, verbose_name='有効終了日')),
                ('display_order', models.IntegerField(default=0, verbose_name='表示順')),
                ('description', models.TextField(blank=True, verbose_name='説明')),
                ('operator_name', models.CharField(blank=True, max_length=100, verbose_name='入力者')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='作成日時')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新日時')),
            ],
            options={
                'verbose_name': '通知',
                'verbose_name_plural': '通知',
                'db_table': 'notifications',
                'ordering': ['display_order', 'id'],
            },
        ),
    ]
