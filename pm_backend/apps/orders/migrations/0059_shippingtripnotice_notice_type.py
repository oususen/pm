from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0058_shippingtripnotice'),
    ]

    operations = [
        migrations.AddField(
            model_name='shippingtripnotice',
            name='notice_type',
            field=models.CharField(choices=[('NORMAL', '普通'), ('URGENT', '緊急')], default='NORMAL', max_length=20, verbose_name='連絡種別'),
        ),
    ]
