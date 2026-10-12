from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('masters', '0086_add_is_order_day_to_calendar_day')]

    # データ移行は承認済み対応表を直前照合する専用コマンドで全件一括実行する。
    operations = [
        migrations.AddField(
            model_name='routingstep', name='parent_product',
            field=models.ForeignKey(
                to='masters.product', on_delete=django.db.models.deletion.PROTECT,
                null=True, blank=True, related_name='parent_routing_steps', verbose_name='親製品',
            ),
        ),
    ]
