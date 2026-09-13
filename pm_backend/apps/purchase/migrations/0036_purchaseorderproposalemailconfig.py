from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('masters', '0034_equipment'),
        ('purchase', '0035_rename_holiday_manual_display'),
    ]

    operations = [
        migrations.CreateModel(
            name='PurchaseOrderProposalEmailConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('body', models.TextField(blank=True, default='', verbose_name='本文テンプレート')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='作成日時')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新日時')),
                ('cc_users', models.ManyToManyField(blank=True, related_name='purchase_order_proposal_email_configs', to=settings.AUTH_USER_MODEL, verbose_name='CCユーザー')),
                ('supplier', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='purchase_order_proposal_email_config', to='masters.supplier', verbose_name='仕入先')),
            ],
            options={
                'verbose_name': '発注提案メール設定',
                'verbose_name_plural': '発注提案メール設定',
                'db_table': 'purchase_order_proposal_email_config',
                'ordering': ['supplier__supplier_code'],
            },
        ),
    ]
