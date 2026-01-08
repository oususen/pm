# Generated manually on 2026-01-08
# ContainerCapacityモデルを既存のテーブル構造に合わせて更新

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('masters', '0024_containercapacity_productgroup_product_capacity_and_more'),
    ]

    operations = [
        # m_container_capacityテーブルの名前をcontainer_capacityに変更
        migrations.AlterModelTable(
            name='containercapacity',
            table='container_capacity',
        ),

        migrations.AlterModelOptions(
            name='containercapacity',
            options={'ordering': ['name'], 'verbose_name': '容器仕様', 'verbose_name_plural': '容器仕様'},
        ),

        # created_at, updated_at, description, is_activeフィールドを削除
        migrations.RemoveField(
            model_name='containercapacity',
            name='created_at',
        ),
        migrations.RemoveField(
            model_name='containercapacity',
            name='updated_at',
        ),
        migrations.RemoveField(
            model_name='containercapacity',
            name='description',
        ),
        migrations.RemoveField(
            model_name='containercapacity',
            name='is_active',
        ),

        # 新しいフィールドを追加
        migrations.AddField(
            model_name='containercapacity',
            name='container_code',
            field=models.CharField(blank=True, max_length=20, null=True, verbose_name='容器コード'),
        ),
        migrations.AddField(
            model_name='containercapacity',
            name='width',
            field=models.IntegerField(blank=True, null=True, verbose_name='幅'),
        ),
        migrations.AddField(
            model_name='containercapacity',
            name='depth',
            field=models.IntegerField(blank=True, null=True, verbose_name='奥行'),
        ),
        migrations.AddField(
            model_name='containercapacity',
            name='height',
            field=models.IntegerField(blank=True, null=True, verbose_name='高さ'),
        ),
        migrations.AddField(
            model_name='containercapacity',
            name='max_weight',
            field=models.IntegerField(blank=True, default=0, null=True, verbose_name='最大重量'),
        ),
        migrations.AddField(
            model_name='containercapacity',
            name='can_mix',
            field=models.BooleanField(blank=True, default=True, null=True, verbose_name='混載可能'),
        ),
        migrations.AddField(
            model_name='containercapacity',
            name='stackable',
            field=models.BooleanField(blank=True, default=True, null=True, verbose_name='積み重ね可能'),
        ),
        migrations.AddField(
            model_name='containercapacity',
            name='max_stack',
            field=models.IntegerField(blank=True, default=1, null=True, verbose_name='最大積み重ね段数'),
        ),

        # 既存フィールドの変更
        migrations.AlterField(
            model_name='containercapacity',
            name='id',
            field=models.AutoField(primary_key=True, serialize=False),
        ),
        migrations.AlterField(
            model_name='containercapacity',
            name='name',
            field=models.CharField(max_length=50, verbose_name='容器名'),
        ),
        migrations.AlterField(
            model_name='containercapacity',
            name='capacity',
            field=models.IntegerField(blank=True, help_text='容器に入る製品の個数', null=True, verbose_name='入り数'),
        ),
    ]
