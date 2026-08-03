from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('purchase', '0024_purchaseautoordersendconfig'),
    ]

    operations = [
        migrations.RenameField(
            model_name='purchaseautoordersendconfig',
            old_name='planning_days_forward',
            new_name='progress_days_forward',
        ),
        migrations.AddField(
            model_name='purchaseautoordersendconfig',
            name='progress_days_back',
            field=models.PositiveSmallIntegerField(default=7, verbose_name='進度表（何営業日前から）'),
        ),
        migrations.AlterField(
            model_name='purchaseautoordersendconfig',
            name='lead_time_days',
            field=models.PositiveSmallIntegerField(default=2, verbose_name='納入日（何営業日後）'),
        ),
        migrations.AlterField(
            model_name='purchaseautoordersendconfig',
            name='progress_days_forward',
            field=models.PositiveSmallIntegerField(default=30, verbose_name='進度表（何日後まで）'),
        ),
    ]
