from django.db import migrations


# 品番マスタ(m_product)をAI用に公開するビュー。結合なし・全行(WHEREなし)。列は別名なし。
# 公開32列はBOSS判断(AI用ビュー作成計画 §9)。
# 非公開(ビューに含めない): image_url, product_name_halfwidth, is_phantom, self_lt_days
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
    is_active,
    created_at,
    updated_at
FROM m_product
"""

DROP_VIEW = 'DROP VIEW IF EXISTS v_ai_product'


class Migration(migrations.Migration):
    # ビューの元になる m_product の列は masters 0085(is_special_management_material の追加)までで揃う
    dependencies = [
        ('ai', '0033_aiproviderconfig_analysis_temperature'),
        ('masters', '0085_add_special_management_material'),
    ]

    operations = [migrations.RunSQL(CREATE_VIEW, DROP_VIEW)]
