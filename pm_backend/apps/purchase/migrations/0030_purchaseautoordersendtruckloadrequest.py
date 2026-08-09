from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('purchase', '0029_purchaseautoordersendconfig_send_delivery_note_pdf'),
    ]

    operations = [
        migrations.CreateModel(
            name='PurchaseAutoOrderSendTruckLoadRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('request_id', models.CharField(max_length=64, unique=True, verbose_name='リクエストID')),
                ('status', models.CharField(choices=[('RUNNING', '実行中'), ('CANCELED', '中断'), ('COMPLETED', '完了')], default='RUNNING', max_length=20, verbose_name='状態')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='作成日時')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新日時')),
                ('canceled_at', models.DateTimeField(blank=True, null=True, verbose_name='中断要求日時')),
                ('completed_at', models.DateTimeField(blank=True, null=True, verbose_name='完了日時')),
            ],
            options={
                'db_table': 'purchase_auto_order_send_truck_load_request',
                'verbose_name': '注文書自動送信トラック積載判定リクエスト',
                'verbose_name_plural': '注文書自動送信トラック積載判定リクエスト',
            },
        ),
    ]
