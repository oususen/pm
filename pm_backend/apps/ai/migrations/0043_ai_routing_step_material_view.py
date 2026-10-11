from django.db import migrations


# 工程別部品消費(m_routing_step_material)をAI用に公開するビュー。m_routing_step_material を主とし、
# 工程(m_routing_step)・ルーティング(m_routing)・ルーティングの品番/加工後品/部品(m_product)・工程(m_process)を LEFT JOIN で付ける。
# 結合はすべて相手の主キー(id)との1対1のため、行数は m_routing_step_material と同じ。WHEREなし(全行)。
# 公開20列はBOSS承認(AI用ビュー作成計画 §26。2026-10-11)。工程由来の列には step_ を付けた。
# s.remark は工程の親品の品番コード(文字列)として step_parent_product_code の別名で公開する。材料側の remark は公開しない。
# 材料のない工程は、このビューに行がない。
# 非公開(ビューに含めない): m_routing_step_material の remark・created_at・updated_at、m_routing_step の step_type・created_at・updated_at 等、
# 結合先のコード・名称以外の列
# 将来のPostgreSQL移行を考え、MySQL固有の記法(バッククォート・DEFINER・SQL SECURITY・DBの修飾)を使わない標準SQLだけで書く。
# (定義者・権限の付与は、DBごとに異なるため、マイグレーションに含めず、別の手順SQLで行う。AI用ビュー作成計画 §26.7)
CREATE_VIEW = """
CREATE OR REPLACE VIEW v_ai_routing_step_material AS
SELECT
    m.id,
    m.routing_step_id,
    s.routing_id,
    r.routing_code,
    r.product_id AS routing_product_id,
    rp.product_code AS routing_product_code,
    rp.product_name AS routing_product_name,
    s.step_no,
    s.process_id AS step_process_id,
    pr.process_code AS step_process_code,
    pr.process_name AS step_process_name,
    s.output_product_id AS step_output_product_id,
    op.product_code AS step_output_product_code,
    op.product_name AS step_output_product_name,
    s.remark AS step_parent_product_code,
    m.component_id,
    cp.product_code AS component_code,
    cp.product_name AS component_name,
    m.quantity,
    m.consume_timing
FROM m_routing_step_material m
LEFT JOIN m_routing_step s ON s.id = m.routing_step_id
LEFT JOIN m_routing r ON r.id = s.routing_id
LEFT JOIN m_product rp ON rp.id = r.product_id
LEFT JOIN m_process pr ON pr.id = s.process_id
LEFT JOIN m_product op ON op.id = s.output_product_id
LEFT JOIN m_product cp ON cp.id = m.component_id
"""

DROP_VIEW = 'DROP VIEW IF EXISTS v_ai_routing_step_material'


class Migration(migrations.Migration):
    # ビューの元になる列は masters 0086(現行の最新)までで揃う
    # (m_routing_step_material: id・routing_step_id・component_id・quantity・consume_timing=0008。
    #  m_routing_step・m_routing・m_product・m_process は 0042 と同じ)
    dependencies = [
        ('ai', '0042_ai_routing_step_view'),
        ('masters', '0086_add_is_order_day_to_calendar_day'),
    ]

    operations = [migrations.RunSQL(CREATE_VIEW, DROP_VIEW)]
