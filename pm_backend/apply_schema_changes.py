import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pm_backend.settings')
django.setup()

from django.db import connection

sql_statements = [
    "ALTER TABLE m_routing_step ADD COLUMN step_type ENUM('FLOW','PARALLEL_POOL') NOT NULL DEFAULT 'FLOW' AFTER line_id;",
    "ALTER TABLE m_cycle_time ADD COLUMN yield_rate DECIMAL(5,3) NULL AFTER setup_time_min;",
    "ALTER TABLE m_routing_step_param ADD COLUMN buffer_before_min INT NULL AFTER max_buffer_qty, ADD COLUMN buffer_after_min INT NULL AFTER buffer_before_min;"
]

with connection.cursor() as cursor:
    for sql in sql_statements:
        try:
            print(f"Executing: {sql}")
            cursor.execute(sql)
            print("✓ Success")
        except Exception as e:
            print(f"✗ Error: {e}")

print("\nAll schema changes applied!")
