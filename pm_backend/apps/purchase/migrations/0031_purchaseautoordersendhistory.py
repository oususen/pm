from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('masters', '0080_add_container_gap_to_trucks'),
        ('purchase', '0030_purchaseautoordersendtruckloadrequest'),
    ]

    operations = [
        migrations.CreateModel(
            name='PurchaseAutoOrderSendHistory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('supplier_code', models.CharField(blank=True, default='', max_length=50, verbose_name='仕入先コード')),
                ('supplier_name', models.CharField(blank=True, default='', max_length=255, verbose_name='仕入先名')),
                ('trigger_type', models.CharField(choices=[('SCHEDULED', '自動実行'), ('MANUAL', '手動実行'), ('HOLIDAY_TRIAL', '休日トライ')], default='SCHEDULED', max_length=20, verbose_name='実行種別')),
                ('status', models.CharField(choices=[('SUCCESS', '成功'), ('FAILED', '失敗'), ('RUNNING', '実行中'), ('SKIPPED', 'スキップ')], default='RUNNING', max_length=20, verbose_name='実行結果')),
                ('started_at', models.DateTimeField(auto_now_add=True, verbose_name='開始日時')),
                ('finished_at', models.DateTimeField(blank=True, null=True, verbose_name='終了日時')),
                ('duration_seconds', models.FloatField(blank=True, null=True, verbose_name='実行時間（秒）')),
                ('to_email', models.CharField(blank=True, default='', max_length=255, verbose_name='宛先メール')),
                ('cc_emails', models.TextField(blank=True, default='', verbose_name='CCメール')),
                ('subject', models.CharField(blank=True, default='', max_length=255, verbose_name='件名')),
                ('message', models.TextField(blank=True, default='', verbose_name='結果メッセージ')),
                ('first_delivery_date', models.DateField(blank=True, null=True, verbose_name='先頭納入日')),
                ('order_item_count', models.PositiveIntegerField(default=0, verbose_name='注文書品目数')),
                ('order_excel_file', models.FileField(blank=True, upload_to='purchase_auto_order_send/order_excel/', verbose_name='注文書Excel')),
                ('config', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='histories', to='purchase.purchaseautoordersendconfig', verbose_name='注文書自動送信設定')),
                ('supplier', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='auto_order_send_histories', to='masters.supplier', verbose_name='仕入先')),
            ],
            options={
                'verbose_name': '注文書自動送信履歴',
                'verbose_name_plural': '注文書自動送信履歴',
                'db_table': 'purchase_auto_order_send_history',
                'ordering': ['-started_at', '-id'],
            },
        ),
    ]
