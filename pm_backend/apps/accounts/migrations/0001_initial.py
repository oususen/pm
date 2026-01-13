from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='UserSmtpConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('smtp_host', models.CharField(max_length=255)),
                ('smtp_port', models.PositiveIntegerField(blank=True, null=True)),
                ('smtp_user', models.CharField(max_length=255)),
                ('smtp_password', models.CharField(max_length=255)),
                ('is_active', models.BooleanField(default=True)),
                ('is_admin', models.BooleanField(default=False)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='smtp_config', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'user_smtp_configs',
            },
        ),
    ]
