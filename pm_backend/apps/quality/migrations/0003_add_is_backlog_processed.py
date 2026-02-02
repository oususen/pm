# Generated manually - add is_backlog_processed field to t_scrap_record_detail

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('quality', '0002_add_is_production_recorded'),
    ]

    operations = [
        migrations.RunSQL(
            sql="ALTER TABLE t_scrap_record_detail ADD COLUMN is_backlog_processed TINYINT(1) NOT NULL DEFAULT 0;",
            reverse_sql="ALTER TABLE t_scrap_record_detail DROP COLUMN is_backlog_processed;",
        ),
        # 既存データを処理済みとしてマーク
        migrations.RunSQL(
            sql="UPDATE t_scrap_record_detail SET is_backlog_processed = 1;",
            reverse_sql="UPDATE t_scrap_record_detail SET is_backlog_processed = 0;",
        ),
    ]
