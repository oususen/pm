from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('production', '0043_processworksession_operator_name'),
    ]

    operations = [
        migrations.AlterField(
            model_name='productionrecordinquirysetting',
            name='tab_key',
            field=models.CharField(
                choices=[
                    ('tank', 'タンク'),
                    ('floor', 'フロア'),
                    ('floor-shipping', 'フロア出荷'),
                    ('blade', 'ブレード'),
                    ('laser', 'レーザ'),
                    ('brake', 'ブレーキ'),
                    ('spot', 'スポット'),
                ],
                max_length=20,
                unique=True,
                verbose_name='対象タブ',
            ),
        ),
    ]
