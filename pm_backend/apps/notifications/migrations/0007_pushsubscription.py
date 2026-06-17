from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0006_callsession_callsignal'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='PushSubscription',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('endpoint', models.TextField(unique=True, verbose_name='エンドポイント')),
                ('p256dh_key', models.TextField(verbose_name='公開鍵')),
                ('auth_key', models.TextField(verbose_name='認証鍵')),
                ('user_agent', models.CharField(blank=True, max_length=255, verbose_name='ユーザーエージェント')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='作成日時')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新日時')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='push_subscriptions', to=settings.AUTH_USER_MODEL, verbose_name='ユーザー')),
            ],
            options={
                'verbose_name': 'Push購読',
                'verbose_name_plural': 'Push購読',
                'db_table': 'push_subscriptions',
                'ordering': ['-updated_at', '-id'],
            },
        ),
    ]
