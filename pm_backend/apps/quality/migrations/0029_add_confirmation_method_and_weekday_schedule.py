from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("quality", "0028_equipmentinspectionresult_photo_url_and_record_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="equipmentinspectionitem",
            name="confirmation_method",
            field=models.TextField(blank=True, default="", verbose_name="確認方法"),
        ),
        migrations.AddField(
            model_name="equipmentinspectionresult",
            name="confirmation_method",
            field=models.TextField(blank=True, default="", verbose_name="確認方法"),
        ),
        migrations.AddField(
            model_name="equipmentinspectiontemplate",
            name="measurement_schedule_type",
            field=models.CharField(
                choices=[("MONTHLY", "月"), ("WEEKDAY", "曜日")],
                default="MONTHLY",
                max_length=10,
                verbose_name="定期実測スケジュール種別",
            ),
        ),
        migrations.AddField(
            model_name="equipmentinspectiontemplate",
            name="measurement_weekdays",
            field=models.JSONField(blank=True, default=list, verbose_name="定期実測対象曜日"),
        ),
    ]
