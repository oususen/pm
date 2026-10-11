from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('ai', '0046_ai_department_view')]

    # 既存履歴の目的は補完せずNULLを維持する。
    operations = [
        migrations.AddField(
            model_name='aianalysisrun', name='purpose',
            field=models.TextField(blank=True, null=True, verbose_name='分析目的'),
        ),
    ]
