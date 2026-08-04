from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0060_rename_t_shipping_t_busines_258278_idx_t_shipping__busines_f5923b_idx_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='kubotasakaidueadjustment',
            name='coordination_note',
            field=models.CharField(blank=True, default='', max_length=200, verbose_name='業務連絡メモ'),
        ),
    ]
