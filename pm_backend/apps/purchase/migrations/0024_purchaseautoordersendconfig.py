from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('purchase', '0023_purchaseautodeliverylistconfig_email_body_custom'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='PurchaseAutoOrderSendConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_enabled', models.BooleanField(default=True, verbose_name='有効')),
                ('scheduled_hour', models.PositiveSmallIntegerField(default=7, verbose_name='実行時（時）')),
                ('scheduled_minute', models.PositiveSmallIntegerField(default=0, verbose_name='実行時（分）')),
                ('lead_time_days', models.PositiveSmallIntegerField(default=2, verbose_name='起点納入日（何営業日後）')),
                ('planning_days_forward', models.PositiveSmallIntegerField(default=7, verbose_name='計画対象期間（日）')),
                ('calc_mode', models.CharField(choices=[('DEMAND', '需要そのまま'), ('LOT_ROUNDED', 'ロット丸め')], default='DEMAND', max_length=20, verbose_name='数量算出方式')),
                ('send_order_excel', models.BooleanField(default=True, verbose_name='注文書Excel送信')),
                ('email_body_custom', models.TextField(blank=True, default='', verbose_name='メール本文（カスタム）')),
                ('reply_to_email', models.EmailField(blank=True, default='', max_length=254, verbose_name='返信先メールアドレス')),
                ('cc_emails', models.TextField(blank=True, default='', verbose_name='業務員CC送信先メール（改行区切り）')),
                ('last_run_at', models.DateTimeField(blank=True, null=True, verbose_name='最終実行日時')),
                ('last_run_status', models.CharField(blank=True, choices=[('SUCCESS', '成功'), ('FAILED', '失敗'), ('RUNNING', '実行中'), ('SKIPPED', 'スキップ')], max_length=20, null=True, verbose_name='最終実行結果')),
                ('last_run_message', models.TextField(blank=True, default='', verbose_name='最終実行メッセージ')),
                ('last_run_duration_seconds', models.FloatField(blank=True, null=True, verbose_name='最終実行時間（秒）')),
                ('notify_on_failure', models.ManyToManyField(blank=True, related_name='auto_order_send_failure_notifications', to=settings.AUTH_USER_MODEL, verbose_name='失敗時の通知先')),
                ('notify_on_non_delivery', models.ManyToManyField(blank=True, related_name='auto_order_send_non_delivery_notifications', to=settings.AUTH_USER_MODEL, verbose_name='納入日でないときの通知先')),
                ('supplier', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='auto_order_send_config', to='masters.supplier', verbose_name='対象仕入先')),
            ],
            options={
                'verbose_name': '注文書自動送信設定',
                'verbose_name_plural': '注文書自動送信設定',
                'db_table': 'purchase_auto_order_send_config',
            },
        ),
    ]
