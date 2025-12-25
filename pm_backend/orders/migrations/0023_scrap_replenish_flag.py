from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0022_scrap_reason_detail'),
    ]

    operations = [
        migrations.AddField(
            model_name='scraprecord',
            name='is_replenished',
            field=models.BooleanField(default=False, verbose_name='補充完了'),
        ),
        migrations.AddField(
            model_name='scraprecord',
            name='process_record',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='scrap_detail', to='orders.processrealtimerecord', verbose_name='工程実時間記録'),
        ),
        migrations.AddField(
            model_name='scraprecord',
            name='replenished_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='補充完了日時'),
        ),
        migrations.AddField(
            model_name='scraprecord',
            name='replenished_by',
            field=models.CharField(blank=True, max_length=50, null=True, verbose_name='補充完了者'),
        ),
    ]
