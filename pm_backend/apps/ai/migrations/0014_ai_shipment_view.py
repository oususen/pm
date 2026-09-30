from django.db import migrations


# 出荷実績(t_shipment_actual)をAI用に平らにしたビュー。
# t_shipment_actual.product_id は全行NULLのため、製品は品番コードで m_product と結ぶ（品番コードは m_product で一意）。
# 備考は社内AIの伏字化が列名 remark を個人情報とみなすため、別名 remark_text にする(中身はシステムが書く便の割付情報)。
CREATE_VIEW = """
CREATE OR REPLACE VIEW v_ai_shipment AS
SELECT
    s.id AS id,
    s.shipment_date AS shipment_date,
    s.product_code AS product_code,
    p.id AS product_id,
    p.product_name AS product_name,
    s.customer_code AS customer_code,
    s.ship_to_code AS ship_to_code,
    s.quantity AS quantity,
    s.shipping_trip_allocation_id AS trip_allocation_id,
    s.remark AS remark_text
FROM t_shipment_actual s
LEFT JOIN m_product p ON p.product_code = s.product_code
"""

DROP_VIEW = 'DROP VIEW IF EXISTS v_ai_shipment'


class Migration(migrations.Migration):
    # ビューの元になる t_shipment_actual(shipping 0006 で shipping_trip_allocation を追加)と m_product(masters 0001)より後に実行する
    dependencies = [
        ('ai', '0013_ai_purchase_receipt_view_record_type'),
        ('shipping', '0006_shipmentactual_shipping_trip_allocation_and_more'),
        ('masters', '0001_initial'),
    ]

    operations = [migrations.RunSQL(CREATE_VIEW, DROP_VIEW)]
