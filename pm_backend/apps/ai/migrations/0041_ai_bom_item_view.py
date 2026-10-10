from django.db import migrations


# BOM明細(m_bom_item)をAI用に公開するビュー。m_bom_item を主とし、BOMヘッダ(m_bom)と、
# 親品番・子品番(m_product)・工程(m_process)・ライン(m_line)・仕入先(m_supplier)のコード・名称を LEFT JOIN で付ける。
# 結合はすべて相手の主キー(id)との1対1のため、行数は m_bom_item と同じ。WHEREなし(全行)。
# 明細が1行もないBOMは、このビューに出ない。
# 公開29列はBOSS承認(AI用ビュー作成計画 §25。2026-10-10)。ヘッダ由来の列には bom_ を付けた。
# 非公開(ビューに含めない): m_bom_item の remark・created_at・updated_at、m_bom の created_at・updated_at、
# 結合先のコード・名称以外の列(仕入先の担当者・電話・メールを含む)
# 将来のPostgreSQL移行を考え、MySQL固有の記法(バッククォート・DEFINER・SQL SECURITY・DBの修飾)を使わない標準SQLだけで書く。
# (定義者・権限の付与は、DBごとに異なるため、マイグレーションに含めず、別の手順SQLで行う。AI用ビュー作成計画 §25.6)
CREATE_VIEW = """
CREATE OR REPLACE VIEW v_ai_bom_item AS
SELECT
    i.id,
    i.bom_id,
    b.parent_product_id,
    pp.product_code AS parent_product_code,
    pp.product_name AS parent_product_name,
    b.version AS bom_version,
    b.valid_from AS bom_valid_from,
    b.valid_to AS bom_valid_to,
    b.is_active AS bom_is_active,
    b.is_coproduct AS bom_is_coproduct,
    i.child_product_id,
    cp.product_code AS child_product_code,
    cp.product_name AS child_product_name,
    i.quantity,
    i.loss_rate,
    i.sourcing_type,
    i.supplier_id,
    s.supplier_code,
    s.supplier_name,
    i.process_id,
    pr.process_code,
    pr.process_name,
    i.line_id,
    l.line_code,
    l.line_name,
    i.time_unit,
    i.lead_time_days,
    i.duration_min,
    i.is_coproduct_driver
FROM m_bom_item i
LEFT JOIN m_bom b ON b.id = i.bom_id
LEFT JOIN m_product pp ON pp.id = b.parent_product_id
LEFT JOIN m_product cp ON cp.id = i.child_product_id
LEFT JOIN m_process pr ON pr.id = i.process_id
LEFT JOIN m_line l ON l.id = i.line_id
LEFT JOIN m_supplier s ON s.id = i.supplier_id
"""

DROP_VIEW = 'DROP VIEW IF EXISTS v_ai_bom_item'


class Migration(migrations.Migration):
    # ビューの元になる列は masters 0086(現行の最新)までで揃う
    # (m_bom_item: id・bom_id・child_product_id・quantity・loss_rate・sourcing_type・supplier_id・process_id・line_id=0001、
    #  time_unit・lead_time_days・duration_min=0001(0006で変更)、is_coproduct_driver=0029。
    #  m_bom: id・parent_product_id・version・valid_from・valid_to・is_active=0001、is_coproduct=0013。
    #  m_product・m_process・m_line・m_supplier のコード・名称=0001)
    dependencies = [
        ('ai', '0040_ai_calendar_day_view'),
        ('masters', '0086_add_is_order_day_to_calendar_day'),
    ]

    operations = [migrations.RunSQL(CREATE_VIEW, DROP_VIEW)]
