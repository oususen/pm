from django.db import migrations


# 公開列・順序を維持し、親品コードの取得元だけ正規FK参照へ変更する。
STEP_VIEW = """
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
    pp.product_code AS parent_product_code,
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
LEFT JOIN m_product pp ON pp.id = s.parent_product_id
"""

MATERIAL_VIEW = """
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
    pp.product_code AS step_parent_product_code,
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
LEFT JOIN m_product pp ON pp.id = s.parent_product_id
"""

class Migration(migrations.Migration):
    dependencies = [('ai', '0050_ai_leader_unit_view'), ('masters', '0087_routingstep_parent_product')]
    operations = [
        migrations.RunSQL(STEP_VIEW, '\nCREATE OR REPLACE VIEW v_ai_routing_step AS\nSELECT\n    s.id,\n    s.routing_id,\n    r.routing_code,\n    r.product_id AS routing_product_id,\n    rp.product_code AS routing_product_code,\n    rp.product_name AS routing_product_name,\n    r.is_default AS routing_is_default,\n    r.is_active AS routing_is_active,\n    r.valid_from_datetime AS routing_valid_from_datetime,\n    r.valid_to_datetime AS routing_valid_to_datetime,\n    s.step_no,\n    s.parallel_group,\n    s.parallel_count,\n    s.hierarchy_depth,\n    s.hierarchy_path,\n    s.process_id,\n    pr.process_code,\n    pr.process_name,\n    s.line_id,\n    l.line_code,\n    l.line_name,\n    s.supplier_id,\n    sp.supplier_code,\n    sp.supplier_name,\n    s.output_product_id,\n    op.product_code AS output_product_code,\n    op.product_name AS output_product_name,\n    s.remark AS parent_product_code,\n    s.source_bom_item_id,\n    s.time_unit,\n    s.lead_time_days,\n    s.start_offset_min,\n    s.duration_min\nFROM m_routing_step s\nLEFT JOIN m_routing r ON r.id = s.routing_id\nLEFT JOIN m_product rp ON rp.id = r.product_id\nLEFT JOIN m_process pr ON pr.id = s.process_id\nLEFT JOIN m_line l ON l.id = s.line_id\nLEFT JOIN m_supplier sp ON sp.id = s.supplier_id\nLEFT JOIN m_product op ON op.id = s.output_product_id\n'),
        migrations.RunSQL(MATERIAL_VIEW, '\nCREATE OR REPLACE VIEW v_ai_routing_step_material AS\nSELECT\n    m.id,\n    m.routing_step_id,\n    s.routing_id,\n    r.routing_code,\n    r.product_id AS routing_product_id,\n    rp.product_code AS routing_product_code,\n    rp.product_name AS routing_product_name,\n    s.step_no,\n    s.process_id AS step_process_id,\n    pr.process_code AS step_process_code,\n    pr.process_name AS step_process_name,\n    s.output_product_id AS step_output_product_id,\n    op.product_code AS step_output_product_code,\n    op.product_name AS step_output_product_name,\n    s.remark AS step_parent_product_code,\n    m.component_id,\n    cp.product_code AS component_code,\n    cp.product_name AS component_name,\n    m.quantity,\n    m.consume_timing\nFROM m_routing_step_material m\nLEFT JOIN m_routing_step s ON s.id = m.routing_step_id\nLEFT JOIN m_routing r ON r.id = s.routing_id\nLEFT JOIN m_product rp ON rp.id = r.product_id\nLEFT JOIN m_process pr ON pr.id = s.process_id\nLEFT JOIN m_product op ON op.id = s.output_product_id\nLEFT JOIN m_product cp ON cp.id = m.component_id\n'),
    ]
