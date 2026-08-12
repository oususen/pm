"""製品チェックシート(A案)のテーブルを削除。工程一体チェックシート(B案)に完全移行済み。"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("quality", "0038_seed_training_prototype"),
    ]

    operations = [
        migrations.RunSQL(
            sql=[
                "DROP TABLE IF EXISTS quality_product_checksheet_workflow_log;",
                "DROP TABLE IF EXISTS quality_product_checksheet_task;",
                "DROP TABLE IF EXISTS quality_product_checksheet_photo;",
                "DROP TABLE IF EXISTS quality_product_checksheet_record;",
                "DROP TABLE IF EXISTS quality_product_checksheet_field;",
                "DROP TABLE IF EXISTS quality_product_checksheet_batch;",
                "DROP TABLE IF EXISTS quality_product_checksheet_template;",
            ],
            reverse_sql=[
                # 復元はバックアップから行う
                migrations.RunSQL.noop,
            ],
        ),
    ]
