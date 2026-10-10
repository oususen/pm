from django.db import migrations


# 0034 で作成した32列の v_ai_product から、BOSS判断(判断画面で作成日・更新日を非公開に変更。2026-10-10)に合わせて、
# created_at・updated_at を外す(公開30列)。結合なし・全行(WHEREなし)。列は別名なし。
# 非公開(ビューに含めない): image_url, product_name_halfwidth, is_phantom, self_lt_days, created_at, updated_at
# 将来のPostgreSQL移行を考え、MySQL固有の記法(バッククォート・DEFINER・SQL SECURITY・DBの修飾)を使わない標準SQLだけで書く。
# (定義者・権限の付与は、DBごとに異なるため、マイグレーションに含めず、別の手順SQLで行う。AI用ビュー作成計画 §9.3)
CREATE_VIEW = """
CREATE OR REPLACE VIEW v_ai_product AS
SELECT
    id,
    product_code,
    product_name,
    category,
    unit,
    unit_price,
    standard_lt_days,
    stock_location,
    processing_area,
    line_id,
    process_id,
    next_process_id,
    management_unit,
    is_final_product,
    is_line_final_product,
    is_virtual_set,
    order_lot_min,
    order_lot_multiple,
    is_special_management_material,
    specific_gravity,
    size_length,
    size_width,
    size_thickness,
    transfer_destination,
    model_name,
    identification_code,
    product_group_id,
    used_container_id,
    capacity,
    is_active
FROM m_product
"""

# 元に戻す場合は、0034 の32列のビュー定義(created_at・updated_at を含む)に戻す
RESTORE_VIEW_32 = """
CREATE OR REPLACE VIEW v_ai_product AS
SELECT
    id,
    product_code,
    product_name,
    category,
    unit,
    unit_price,
    standard_lt_days,
    stock_location,
    processing_area,
    line_id,
    process_id,
    next_process_id,
    management_unit,
    is_final_product,
    is_line_final_product,
    is_virtual_set,
    order_lot_min,
    order_lot_multiple,
    is_special_management_material,
    specific_gravity,
    size_length,
    size_width,
    size_thickness,
    transfer_destination,
    model_name,
    identification_code,
    product_group_id,
    used_container_id,
    capacity,
    is_active,
    created_at,
    updated_at
FROM m_product
"""


class Migration(migrations.Migration):
    # ビューの元になる m_product の列は masters 0085(is_special_management_material の追加)までで揃う(0034 と同じ)
    dependencies = [
        ('ai', '0036_ai_line_view'),
        ('masters', '0085_add_special_management_material'),
    ]

    operations = [migrations.RunSQL(CREATE_VIEW, RESTORE_VIEW_32)]
