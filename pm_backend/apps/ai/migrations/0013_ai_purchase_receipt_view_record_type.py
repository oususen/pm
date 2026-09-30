from django.db import migrations


# 仕入の入荷実績は t_process_realtime_record に record_type='PURCHASE' で保存するよう変更した。
# ビューの抽出条件を event_data.source から record_type へ置き換える（列定義は 0012 と同じ）。
# MySQL 8.0.21以降の JSON_VALUE を使う(PostgreSQL移行時は ->> 演算子へ書き換えが必要)。
_SELECT_COLUMNS = """
SELECT
    r.id AS id,
    JSON_VALUE(r.event_data, '$.arrival_date' RETURNING DATE) AS arrival_date,
    r.timestamp AS registered_at,
    JSON_VALUE(r.event_data, '$.supplier_id' RETURNING UNSIGNED) AS supplier_id,
    JSON_VALUE(r.event_data, '$.line_id' RETURNING UNSIGNED) AS line_id,
    r.product_id AS product_id,
    r.product_code AS product_code,
    r.product_name AS product_name,
    r.qty AS qty,
    r.process_id AS process_id,
    JSON_VALUE(r.event_data, '$.source') AS input_source
FROM t_process_realtime_record r
"""

CREATE_VIEW = (
    'CREATE OR REPLACE VIEW v_ai_purchase_receipt AS'
    + _SELECT_COLUMNS
    + "WHERE r.record_type = 'PURCHASE'\n"
)

# 0012 の定義へ戻す
RESTORE_0012_VIEW = (
    'CREATE OR REPLACE VIEW v_ai_purchase_receipt AS'
    + _SELECT_COLUMNS
    + "WHERE r.record_type = 'PRODUCTION'\n"
    + "  AND JSON_VALUE(r.event_data, '$.source') IN (\n"
    + "      'PURCHASE_ACTUAL_INPUT', 'PURCHASE_RECEIVING', 'PURCHASE_RECEIVING_MOBILE'\n"
    + '  )\n'
)


class Migration(migrations.Migration):
    dependencies = [('ai', '0012_ai_purchase_receipt_view')]

    operations = [migrations.RunSQL(CREATE_VIEW, RESTORE_0012_VIEW)]
