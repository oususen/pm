from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('ai', '0017_add_masters_tool_policy')]

    operations = [
        migrations.AlterField(
            model_name='aitoolpolicy',
            name='screen_id',
            field=models.CharField(
                choices=[
                    ('ai_home', '本社横断'), ('orders', '受注'), ('production', '生産'),
                    ('quality', '品質'), ('overtime', '勤務'), ('purchase', '仕入'),
                    ('shipping', '出荷'), ('inventory', '在庫'), ('masters', 'マスタ'),
                ],
                max_length=40,
                verbose_name='画面領域',
            ),
        ),
    ]
