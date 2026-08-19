from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('masters', '0081_kubotasakaitruck_auto_assign_target'),
    ]

    operations = [
        migrations.CreateModel(
            name='MobileDeviceHistory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('location', models.CharField(max_length=200, verbose_name='配置場所')),
                ('manager_name', models.CharField(max_length=100, verbose_name='管理責任者')),
                ('status', models.CharField(choices=[('ACTIVE', '使用中'), ('IDLE', '遊休'), ('DISPOSED', '廃却')], max_length=10, verbose_name='状態')),
                ('note', models.TextField(blank=True, default='', verbose_name='備考')),
                ('started_at', models.DateField(verbose_name='開始日')),
                ('ended_at', models.DateField(verbose_name='終了日')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='登録日時')),
                ('changed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL, verbose_name='変更者')),
                ('device', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='histories', to='masters.mobiledevice', verbose_name='端末')),
            ],
            options={
                'verbose_name': '端末使用履歴',
                'verbose_name_plural': '端末使用履歴',
                'ordering': ['-ended_at', '-started_at'],
            },
        ),
    ]
