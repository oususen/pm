from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("quality", "0031_equipment_item_result_record_type_add_photo"),
    ]

    operations = [
        migrations.AddField(
            model_name="integratedchecksheettemplate",
            name="submitted_items_snapshot",
            field=models.JSONField(blank=True, null=True, verbose_name="提出時点検項目スナップショット"),
        ),
    ]

