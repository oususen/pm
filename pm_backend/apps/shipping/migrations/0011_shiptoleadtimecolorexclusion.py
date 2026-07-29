from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('shipping', '0010_shiptoleadtime_colors'),
    ]

    operations = [
        migrations.CreateModel(
            name='ShipToLeadTimeColorExclusion',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('product_code', models.CharField(max_length=50, verbose_name='品番コード')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='作成日時')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新日時')),
                ('ship_to_lead_time', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='color_exclusions', to='shipping.shiptoleadtime', verbose_name='納入地別出荷加算日数')),
            ],
            options={
                'db_table': 'm_ship_to_lead_time_color_exclusion',
                'verbose_name': '納入地色設定除外品番',
                'verbose_name_plural': '納入地色設定除外品番',
                'ordering': ['ship_to_lead_time_id', 'product_code'],
            },
        ),
        migrations.AlterUniqueTogether(
            name='shiptoleadtimecolorexclusion',
            unique_together={('ship_to_lead_time', 'product_code')},
        ),
        migrations.AddIndex(
            model_name='shiptoleadtimecolorexclusion',
            index=models.Index(fields=['ship_to_lead_time', 'product_code'], name='m_ship_to_l_ship_to_035557_idx'),
        ),
        migrations.AddIndex(
            model_name='shiptoleadtimecolorexclusion',
            index=models.Index(fields=['product_code'], name='m_ship_to_l_product_b2594d_idx'),
        ),
    ]
