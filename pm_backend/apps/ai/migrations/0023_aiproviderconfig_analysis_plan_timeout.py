from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('ai', '0022_aianalysisexecutionpolicy')]

    operations = [
        # 既存のモデル・有効状態は変更しない。社外プロバイダの新規列は使用しない。
        migrations.AddField(
            model_name='aiproviderconfig',
            name='analysis_plan_timeout_seconds',
            field=models.PositiveIntegerField(
                default=180, validators=[MinValueValidator(30), MaxValueValidator(600)],
                verbose_name='分析案作成タイムアウト（秒）',
            ),
        ),
    ]
