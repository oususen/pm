from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0043_alter_stgorderrawtiera_order_document_no'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='KubotaSakaiImportConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('notify_users', models.ManyToManyField(
                    blank=True,
                    related_name='kubota_sakai_import_notify',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='通知先ユーザー',
                )),
            ],
            options={
                'verbose_name': 'クボタ堺取り込み通知設定',
                'db_table': 'kubota_sakai_import_config',
            },
        ),
    ]
