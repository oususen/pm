from django.db import migrations, models


class Migration(migrations.Migration):
    """工程実時間記録の記録タイプに仕入実績(PURCHASE)を追加する。

    choices の変更のみでDDLは発生しない（max_length=20 は変更なし）。
    既存の仕入実績レコードの PRODUCTION → PURCHASE 更新は、コードデプロイ直後にSQLで行う。
    """

    dependencies = [
        ('production', '0113_move_ai_search_config_to_ai_app'),
    ]

    operations = [
        migrations.AlterField(
            model_name='processrealtimerecord',
            name='record_type',
            field=models.CharField(
                choices=[
                    ('PRODUCTION', '生産完成'),
                    ('PURCHASE', '仕入実績'),
                    ('SCRAP', '仕損'),
                    ('EQUIPMENT_STATE', '設備状態変更'),
                    ('OPERATOR_ACTION', '作業者アクション'),
                ],
                max_length=20,
                verbose_name='記録タイプ',
            ),
        ),
    ]
