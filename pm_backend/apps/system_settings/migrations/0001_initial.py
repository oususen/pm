from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='SystemSetting',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key', models.CharField(max_length=100, unique=True, verbose_name='キー')),
                ('value', models.CharField(max_length=500, verbose_name='値')),
                ('description', models.CharField(blank=True, max_length=200, verbose_name='説明')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新日時')),
                ('updated_by', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='更新者',
                )),
            ],
            options={
                'verbose_name': 'システム設定',
                'verbose_name_plural': 'システム設定',
                'db_table': 'system_settings',
                'ordering': ['key'],
            },
        ),
    ]
