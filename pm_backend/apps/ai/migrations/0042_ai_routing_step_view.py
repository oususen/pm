from django.db import migrations


# ルーティング工程(m_routing_step)をAI用に公開するビュー。m_routing_step を主とし、ルーティングヘッダ(m_routing)と、
# ルーティングの品番・加工後品(m_product)・工程(m_process)・ライン(m_line)・外作先(m_supplier)のコード・名称を LEFT JOIN で付ける。
# 結合はすべて相手の主キー(id)との1対1のため、行数は m_routing_step と同じ。WHEREなし(全行)。
# 公開33列はBOSS承認(AI用ビュー作成計画 §26。2026-10-11)。ヘッダ由来の列には routing_ を付けた。
# s.remark は工程の親品の品番コード(文字列)として parent_product_code の別名で公開する。
# 非公開(ビューに含めない): m_routing_step の step_type・created_at・updated_at、m_routing の description・created_at・updated_at、
# 結合先のコード・名称以外の列(仕入先の担当者・電話・メールを含む)
# 将来のPostgreSQL移行を考え、MySQL固有の記法(バッククォート・DEFINER・SQL SECURITY・DBの修飾)を使わない標準SQLだけで書く。
# (定義者・権限の付与は、DBごとに異なるため、マイグレーションに含めず、別の手順SQLで行う。AI用ビュー作成計画 §26.7)
CREATE_VIEW = """
CREATE OR REPLACE VIEW v_ai_routing_step AS
SELECT
    s.id,
    s.routing_id,
    r.routing_code,
    r.product_id AS routing_product_id,
    rp.product_code AS routing_product_code,
    rp.product_name AS routing_product_name,
    r.is_default AS routing_is_default,
    r.is_active AS routing_is_active,
    r.valid_from_datetime AS routing_valid_from_datetime,
    r.valid_to_datetime AS routing_valid_to_datetime,
    s.step_no,
    s.parallel_group,
    s.parallel_count,
    s.hierarchy_depth,
    s.hierarchy_path,
    s.process_id,
    pr.process_code,
    pr.process_name,
    s.line_id,
    l.line_code,
    l.line_name,
    s.supplier_id,
    sp.supplier_code,
    sp.supplier_name,
    s.output_product_id,
    op.product_code AS output_product_code,
    op.product_name AS output_product_name,
    s.remark AS parent_product_code,
    s.source_bom_item_id,
    s.time_unit,
    s.lead_time_days,
    s.start_offset_min,
    s.duration_min
FROM m_routing_step s
LEFT JOIN m_routing r ON r.id = s.routing_id
LEFT JOIN m_product rp ON rp.id = r.product_id
LEFT JOIN m_process pr ON pr.id = s.process_id
LEFT JOIN m_line l ON l.id = s.line_id
LEFT JOIN m_supplier sp ON sp.id = s.supplier_id
LEFT JOIN m_product op ON op.id = s.output_product_id
"""

DROP_VIEW = 'DROP VIEW IF EXISTS v_ai_routing_step'


class Migration(migrations.Migration):
    # ビューの元になる列は masters 0086(現行の最新)までで揃う
    # (m_routing_step: id・routing_id・step_no・process_id・line_id=0001、output_product_id=0007、
    #  hierarchy_path・hierarchy_depth=0010、parallel_count=0020、parallel_group=0021、source_bom_item_id=0043、
    #  supplier_id=0047、time_unit・lead_time_days・start_offset_min・duration_min・remark=0001。
    #  m_routing: id・product_id・routing_code・is_default・is_active=0001、valid_from_datetime・valid_to_datetime=0041。
    #  m_product・m_process・m_line・m_supplier のコード・名称=0001)
    dependencies = [
        ('ai', '0041_ai_bom_item_view'),
        ('masters', '0086_add_is_order_day_to_calendar_day'),
    ]

    operations = [migrations.RunSQL(CREATE_VIEW, DROP_VIEW)]
