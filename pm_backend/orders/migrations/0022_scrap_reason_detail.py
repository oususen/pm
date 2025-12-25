from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0021_scraprecord'),
    ]

    operations = [
        migrations.AddField(
            model_name='scraprecord',
            name='reason_detail',
            field=models.CharField(blank=True, max_length=200, null=True, verbose_name='理由詳細'),
        ),
    ]
