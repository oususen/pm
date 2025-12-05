from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('masters', '0004_line_lead_time'),
    ]

    operations = [
        migrations.AlterField(
            model_name='product',
            name='category',
            field=models.CharField(blank=True, choices=[('ASSEMBLY', '組立品'), ('SINGLE', '単品'), ('MATERIAL', '材料'), ('PURCHASED', '購入品')], max_length=20, null=True, verbose_name='カテゴリ'),
        ),
    ]
