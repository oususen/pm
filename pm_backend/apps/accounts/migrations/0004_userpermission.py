from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_alter_usersmtpconfig_table'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserPermission',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('resource', models.CharField(choices=[('dashboard', 'ダッシュボード'), ('orders', '受注'), ('production', '生産'), ('purchase', '仕入'), ('shipping', '出荷'), ('inventory', '在庫'), ('quality', '品質'), ('masters', 'マスタ'), ('settings', '設定'), ('users', 'ユーザー管理'), ('manual', 'マニュアル')], max_length=50)),
                ('can_view', models.BooleanField(default=False)),
                ('can_edit', models.BooleanField(default=False)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='permissions', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'accounts_userpermission',
                'unique_together': {('user', 'resource')},
            },
        ),
    ]
