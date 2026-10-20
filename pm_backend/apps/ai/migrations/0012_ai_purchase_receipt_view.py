from django.db import migrations


# 仕入の入荷実績は t_process_realtime_record に生産実績と同じ record_type='PRODUCTION' で保存され、
# 仕入分かどうか・仕入先・入荷日は event_data(JSON) にしかない。
# AIがSQLで生産と仕入を取り違えないよう、仕入分だけを平らな列にしたビューを用意する。
# PostgreSQL の ->> 演算子を使用(event_dataはJSONField)。
CREATE_VIEW = """
CREATE OR REPLACE VIEW v_ai_purchase_receipt AS
SELECT
    r.id AS id,
    (r.event_data->>'arrival_date')::date AS arrival_date,
    r.timestamp AS registered_at,
    (r.event_data->>'supplier_id')::bigint AS supplier_id,
    (r.event_data->>'line_id')::bigint AS line_id,
    r.product_id AS product_id,
    r.product_code AS product_code,
    r.product_name AS product_name,
    r.qty AS qty,
    r.process_id AS process_id,
    r.event_data->>'source' AS input_source
FROM t_process_realtime_record r
WHERE r.record_type = 'PRODUCTION'
  AND (r.event_data->>'source') IN (
      'PURCHASE_ACTUAL_INPUT', 'PURCHASE_RECEIVING', 'PURCHASE_RECEIVING_MOBILE'
  )
"""

DROP_VIEW = 'DROP VIEW IF EXISTS v_ai_purchase_receipt'


class Migration(migrations.Migration):
    # ビューの元になる t_process_realtime_record を作る production 0001 より後に実行する(新しいDBでの migrate 順序)
    dependencies = [
        ('ai', '0011_aidatapolicy_conversation_retention_days'),
        ('production', '0001_initial'),
    ]

    operations = [migrations.RunSQL(CREATE_VIEW, DROP_VIEW)]
