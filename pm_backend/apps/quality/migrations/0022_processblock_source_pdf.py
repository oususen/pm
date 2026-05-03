from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("quality", "0021_integrated_template_metadata"),
    ]

    operations = [
        migrations.AddField(
            model_name="integratedchecksheetprocessblock",
            name="source_pdf",
            field=models.FileField(blank=True, upload_to="integrated_checksheets/source_pdf/", verbose_name="台紙PDF"),
        ),
    ]
