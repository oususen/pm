"""
KubotaSakaiDueAdjustment を BACKLOG 型に再構築。
既存データを全削除し、旧カラムを削除、新カラムを追加する。
"""
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('orders', '0049_kubotasakaidueadjustment_source_fields'),
    ]

    operations = [
        # 1. 既存データを全削除（BACKLOG型に構造変更するため）
        migrations.RunSQL(
            sql="DELETE FROM t_kubota_sakai_due_adjustment;",
            reverse_sql=migrations.RunSQL.noop,
        ),

        # 2. 旧インデックス・制約を削除
        migrations.AlterUniqueTogether(
            name='kubotasakaidueadjustment',
            unique_together=set(),
        ),
        migrations.RemoveIndex(
            model_name='kubotasakaidueadjustment',
            name='t_kubota_sa_adjuste_c2f9fa_idx',
        ),
        migrations.RemoveIndex(
            model_name='kubotasakaidueadjustment',
            name='t_kubota_sa_order_l_ebeab6_idx',
        ),
        migrations.RemoveIndex(
            model_name='kubotasakaidueadjustment',
            name='kbt_saki_due_shipto_ord_idx',
        ),

        # 3. 旧カラム削除
        migrations.RemoveField(model_name='kubotasakaidueadjustment', name='split_no'),
        migrations.RemoveField(model_name='kubotasakaidueadjustment', name='adjusted_due_date'),
        migrations.RemoveField(model_name='kubotasakaidueadjustment', name='adjusted_qty'),
        migrations.RemoveField(model_name='kubotasakaidueadjustment', name='adjustment_type'),
        migrations.RemoveField(model_name='kubotasakaidueadjustment', name='customer_approved'),
        migrations.RemoveField(model_name='kubotasakaidueadjustment', name='adjusted_by'),
        migrations.RemoveField(model_name='kubotasakaidueadjustment', name='adjusted_at'),
        migrations.RemoveField(model_name='kubotasakaidueadjustment', name='note'),
        migrations.RemoveField(model_name='kubotasakaidueadjustment', name='source_due_date'),
        migrations.RemoveField(model_name='kubotasakaidueadjustment', name='source_qty'),
        migrations.RemoveField(model_name='kubotasakaidueadjustment', name='ship_to_name'),

        # 4. order_line を nullable に変更
        migrations.AlterField(
            model_name='kubotasakaidueadjustment',
            name='order_line',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='kubota_sakai_due_adjustments',
                to='orders.orderline',
                verbose_name='受注明細',
            ),
        ),

        # 5. 既存カラムの用途変更（source_order_no, ship_to_code, remaining_qty はそのまま）

        # 6. 新カラム追加
        migrations.AddField(
            model_name='kubotasakaidueadjustment',
            name='product_code',
            field=models.CharField(default='', max_length=50, verbose_name='品番'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='kubotasakaidueadjustment',
            name='order_type',
            field=models.CharField(
                choices=[('FIRM', '確定'), ('FORECAST', '内示')],
                default='FORECAST',
                max_length=20,
                verbose_name='受注タイプ',
            ),
        ),
        migrations.AddField(
            model_name='kubotasakaidueadjustment',
            name='due_date',
            field=models.DateField(default='2026-01-01', verbose_name='日付'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='kubotasakaidueadjustment',
            name='demand_qty',
            field=models.DecimalField(decimal_places=3, default=0, max_digits=14, verbose_name='受注数'),
        ),
        migrations.AddField(
            model_name='kubotasakaidueadjustment',
            name='delivery_qty',
            field=models.DecimalField(decimal_places=3, default=0, max_digits=14, verbose_name='納入数'),
        ),
        migrations.AddField(
            model_name='kubotasakaidueadjustment',
            name='updated_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='kubota_sakai_due_adj_updated',
                to=settings.AUTH_USER_MODEL,
                verbose_name='更新者',
            ),
        ),
        migrations.AddField(
            model_name='kubotasakaidueadjustment',
            name='updated_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='更新日時'),
        ),
        migrations.AddField(
            model_name='kubotasakaidueadjustment',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default='2026-01-01 00:00:00', verbose_name='作成日時'),
            preserve_default=False,
        ),

        # 7. 新しいユニーク制約・インデックス
        migrations.AlterUniqueTogether(
            name='kubotasakaidueadjustment',
            unique_together={('product_code', 'ship_to_code', 'source_order_no', 'due_date')},
        ),
        migrations.AddIndex(
            model_name='kubotasakaidueadjustment',
            index=models.Index(fields=['due_date'], name='orders_kubo_due_dat_idx'),
        ),
        migrations.AddIndex(
            model_name='kubotasakaidueadjustment',
            index=models.Index(fields=['product_code', 'ship_to_code'], name='kbt_saki_due_prod_ship_idx'),
        ),

        # 8. ordering 変更
        migrations.AlterModelOptions(
            name='kubotasakaidueadjustment',
            options={
                'ordering': ['product_code', 'ship_to_code', 'source_order_no', 'due_date'],
                'verbose_name': 'クボタ堺納期調整',
                'verbose_name_plural': 'クボタ堺納期調整',
            },
        ),
    ]
