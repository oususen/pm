from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('purchase', '0032_purchaseautoordersendconfig_progress_file_toggles'),
    ]

    operations = [
        migrations.AddField(
            model_name='purchaseautoordersendhistory',
            name='attachment_labels',
            field=models.TextField(blank=True, default='', verbose_name='添付内容（改行区切り）'),
        ),
    ]
