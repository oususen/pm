from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('ai', '0003_add_readonly_sql_tool')]

    operations = [
        migrations.AlterField(
            model_name='aitoolpolicy',
            name='tool_code',
            field=models.CharField(
                choices=[
                    ('search_product', '品番マスタ検索'),
                    ('count_products', '品番マスタ件数集計'),
                    ('get_business_data', '生産・品質・残業の集計'),
                    ('get_missing_routing_orders', 'ルーティング未設定品の確認'),
                    ('search_employee', '社員候補検索'),
                    ('get_individual_overtime', '個人別残業集計'),
                    ('get_personal_overtime_threshold', '残業しきい値超過者集計'),
                    ('execute_readonly_sql', 'AI用DB辞書の読み取りSQL'),
                ],
                max_length=80,
                verbose_name='ツール',
            ),
        ),
    ]
