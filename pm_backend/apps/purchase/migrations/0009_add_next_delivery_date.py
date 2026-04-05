# Generated manually for adding next_delivery_date fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('purchase', '0008_purchaseorderapprovalconfig_proxy_approver_users_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='purchaseorderproposal',
            name='next_delivery_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='purchaseorderproposalline',
            name='next_delivery_date',
            field=models.DateField(blank=True, null=True),
        ),
    ]
