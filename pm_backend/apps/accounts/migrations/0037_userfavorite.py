from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0036_add_batch_delete_permission'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserFavorite',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('screen_key', models.CharField(max_length=100, verbose_name='画面キー')),
                ('name', models.CharField(max_length=100, verbose_name='お気に入り名')),
                ('payload', models.JSONField(default=dict, verbose_name='保存内容')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='作成日時')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新日時')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='favorites', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'ユーザーお気に入り',
                'verbose_name_plural': 'ユーザーお気に入り',
                'db_table': 'accounts_user_favorite',
                'ordering': ['screen_key', 'name', 'id'],
                'unique_together': {('user', 'screen_key', 'name')},
            },
        ),
    ]
