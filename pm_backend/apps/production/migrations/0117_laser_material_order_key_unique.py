# レーザ材料発注行のキー変更（単位1a）: 一意制約の変更
#
# 0116 で重複行を統合した後に、旧制約（条件付き。MySQL では作成されていなかった）を外し、
# 条件なしの (material, required_date, supplier) の一意制約を追加する。

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('production', '0116_merge_laser_material_order_duplicate_rows'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='laserweeklymaterialorderprogress',
            name='laser_weekly_material_order_progress_unique',
        ),
        migrations.AddConstraint(
            model_name='laserweeklymaterialorderprogress',
            constraint=models.UniqueConstraint(
                fields=('material', 'required_date', 'supplier'),
                name='laser_weekly_material_order_key_unique',
            ),
        ),
    ]
