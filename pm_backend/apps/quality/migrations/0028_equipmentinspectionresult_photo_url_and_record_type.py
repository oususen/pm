from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("quality", "0027_add_workflow_log_and_dates_to_integrated_checksheet"),
    ]

    operations = [
        migrations.AlterField(
            model_name="equipmentinspectionitem",
            name="record_type",
            field=models.CharField(
                choices=[
                    ("CHECK", "チェック"),
                    ("NUMERIC", "数値"),
                    ("PHOTO_NUMERIC", "写真＋数値"),
                    ("TEXT", "文字"),
                ],
                default="CHECK",
                max_length=20,
                verbose_name="記録種別",
            ),
        ),
        migrations.AddField(
            model_name="equipmentinspectionresult",
            name="photo_url",
            field=models.CharField(blank=True, default="", max_length=255, verbose_name="写真記録URL"),
        ),
        migrations.AlterField(
            model_name="equipmentinspectionresult",
            name="record_type",
            field=models.CharField(
                choices=[
                    ("CHECK", "チェック"),
                    ("NUMERIC", "数値"),
                    ("PHOTO_NUMERIC", "写真＋数値"),
                    ("TEXT", "文字"),
                ],
                default="CHECK",
                max_length=20,
                verbose_name="記録種別",
            ),
        ),
    ]
