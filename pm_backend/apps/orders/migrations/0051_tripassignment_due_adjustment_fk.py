"""KubotaSakaiTripAssignment: order_line FK → due_adjustment FK に変更。

既存の割付データは納期調整BACKLOGテーブルに紐付かないため全削除してから
カラムを差し替える。運用開始前の段階なので既存データの変換は不要。
"""

from django.db import migrations, models
import django.db.models.deletion


def clear_old_assignments(apps, schema_editor):
    """旧スキーマの割付データを全削除"""
    KubotaSakaiTripAssignment = apps.get_model('orders', 'KubotaSakaiTripAssignment')
    KubotaSakaiTripAssignment.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0050_rebuild_kubota_sakai_due_adjustment'),
    ]

    operations = [
        # 1. 既存データを全削除（旧FK構造のデータは変換不能）
        migrations.RunPython(clear_old_assignments, migrations.RunPython.noop),

        # 2. 旧インデックス削除
        migrations.RemoveIndex(
            model_name='kubotasakaitripassignment',
            name='t_kubota_sa_order_l_00289c_idx',
        ),

        # 3. order_line カラム削除
        migrations.RemoveField(
            model_name='kubotasakaitripassignment',
            name='order_line',
        ),

        # 4. due_adjustment FK 追加
        migrations.AddField(
            model_name='kubotasakaitripassignment',
            name='due_adjustment',
            field=models.ForeignKey(
                default=1,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='trip_assignments',
                to='orders.kubotasakaidueadjustment',
                verbose_name='納期調整',
            ),
            preserve_default=False,
        ),

        # 5. 新インデックス追加
        migrations.AddIndex(
            model_name='kubotasakaitripassignment',
            index=models.Index(fields=['due_adjustment'], name='orders_kubo_due_adj_idx'),
        ),

        # 6. ordering 更新（Meta変更は自動検出）
    ]
