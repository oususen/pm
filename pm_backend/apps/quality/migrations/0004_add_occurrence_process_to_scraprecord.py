from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('quality', '0003_add_is_backlog_processed'),
    ]

    operations = [
        migrations.RunSQL(
            sql="ALTER TABLE t_scrap_record ADD COLUMN occurrence_process_id BIGINT NULL",
            reverse_sql="ALTER TABLE t_scrap_record DROP COLUMN occurrence_process_id",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE t_scrap_record ADD CONSTRAINT fk_scrap_occurrence_process FOREIGN KEY (occurrence_process_id) REFERENCES m_process(id) ON DELETE SET NULL",
            reverse_sql="ALTER TABLE t_scrap_record DROP FOREIGN KEY fk_scrap_occurrence_process",
        ),
    ]
