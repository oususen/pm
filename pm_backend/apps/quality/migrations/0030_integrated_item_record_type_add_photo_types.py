from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("quality", "0029_add_confirmation_method_and_weekday_schedule"),
    ]

    operations = [
        migrations.AlterField(
            model_name="integratedchecksheetitem",
            name="record_type",
            field=models.CharField(
                choices=[
                    ("CHECK", "チェック"),
                    ("NUMERIC", "数値"),
                    ("PHOTO_NUMERIC", "写真＋数値"),
                    ("PHOTO", "写真のみ"),
                    ("TEXT", "文字"),
                ],
                default="CHECK",
                max_length=20,
                verbose_name="記録種別",
            ),
        ),
    ]
