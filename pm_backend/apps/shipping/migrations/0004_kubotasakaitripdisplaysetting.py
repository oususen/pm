from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shipping', '0003_kubota_sakai_delivery_progress'),
    ]

    operations = [
        migrations.CreateModel(
            name='KubotaSakaiTripDisplaySetting',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('product_code', models.CharField(max_length=50, verbose_name='製品コード')),
                ('ship_to_code', models.CharField(blank=True, default='', max_length=40, verbose_name='納入地コード')),
                ('display_order', models.IntegerField(default=0, verbose_name='表示順')),
                ('bg_color', models.CharField(blank=True, default='', max_length=10, verbose_name='行背景色')),
                ('text_color', models.CharField(blank=True, default='', max_length=10, verbose_name='行文字色')),
                ('plus_bg_color', models.CharField(blank=True, default='', max_length=10, verbose_name='追加ボタン背景色')),
                ('plus_text_color', models.CharField(blank=True, default='', max_length=10, verbose_name='追加ボタン文字色')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='作成日時')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新日時')),
            ],
            options={
                'db_table': 't_kubota_sakai_trip_display_setting',
                'verbose_name': 'クボタ堺便計画表示設定',
                'verbose_name_plural': 'クボタ堺便計画表示設定',
                'ordering': ['display_order', 'product_code', 'ship_to_code'],
                'unique_together': {('product_code', 'ship_to_code')},
            },
        ),
        migrations.AddIndex(
            model_name='kubotasakaitripdisplaysetting',
            index=models.Index(fields=['display_order', 'product_code'], name='t_kubota_sa_display_94f6f9_idx'),
        ),
        migrations.AddIndex(
            model_name='kubotasakaitripdisplaysetting',
            index=models.Index(fields=['product_code', 'ship_to_code'], name='t_kubota_sa_product_0f37cb_idx'),
        ),
    ]
