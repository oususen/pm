from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('masters', '0017_remove_workpattern_break_minutes_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='image_url',
            field=models.CharField(max_length=255, null=True, blank=True, verbose_name='画像URL'),
        ),
    ]
