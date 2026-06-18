from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0007_pushsubscription'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='NativePushToken',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('platform', models.CharField(choices=[('android', 'Android'), ('ios', 'iOS')], max_length=20, verbose_name='プラットフォーム')),
                ('token', models.CharField(max_length=512, unique=True, verbose_name='トークン')),
                ('device_id', models.CharField(blank=True, max_length=255, verbose_name='端末ID')),
                ('device_name', models.CharField(blank=True, max_length=255, verbose_name='端末名')),
                ('app_version', models.CharField(blank=True, max_length=100, verbose_name='アプリバージョン')),
                ('is_active', models.BooleanField(default=True, verbose_name='有効')),
                ('last_seen_at', models.DateTimeField(auto_now=True, verbose_name='最終確認日時')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='作成日時')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新日時')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='native_push_tokens', to=settings.AUTH_USER_MODEL, verbose_name='ユーザー')),
            ],
            options={
                'db_table': 'native_push_tokens',
                'ordering': ['-updated_at', '-id'],
                'verbose_name': 'ネイティブ Push トークン',
                'verbose_name_plural': 'ネイティブ Push トークン',
            },
        ),
    ]
