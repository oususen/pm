from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0039_add_purchase_auto_delivery_list_permission'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userprofile',
            name='role',
            field=models.CharField(
                choices=[
                    ('manager', '事業部長・課長'),
                    ('chief', '係長'),
                    ('supervisor', '班長'),
                    ('leader', 'リーダー'),
                    ('office_staff', '事務員'),
                    ('staff', '一般'),
                ],
                default='staff',
                max_length=20,
                verbose_name='役割',
            ),
        ),
    ]
