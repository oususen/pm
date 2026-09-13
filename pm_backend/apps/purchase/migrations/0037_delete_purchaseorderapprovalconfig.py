from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('purchase', '0036_purchaseorderproposalemailconfig'),
    ]

    operations = [
        migrations.DeleteModel(
            name='PurchaseOrderApprovalConfig',
        ),
    ]
