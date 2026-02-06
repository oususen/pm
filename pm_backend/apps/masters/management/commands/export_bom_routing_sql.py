"""
BOM・ルーティングデータをSQL形式でエクスポート

使用方法:
  python manage.py export_bom_routing_sql

出力ファイル:
  bom_routing_import.sql （本番Adminerで実行）
"""

from datetime import date, datetime
from decimal import Decimal
from django.core.management.base import BaseCommand
from masters.models import (
    BOM, BOMItem, Routing, RoutingStep, RoutingStepMaterial, ProcessCycleTime
)


class Command(BaseCommand):
    help = 'BOM・ルーティングデータをSQL形式でエクスポート'

    def escape_sql(self, value):
        """SQL用にエスケープ"""
        if value is None:
            return 'NULL'
        if isinstance(value, bool):
            return '1' if value else '0'
        if isinstance(value, (int, float, Decimal)):
            return str(value)
        if isinstance(value, (date, datetime)):
            return f"'{value}'"
        # 文字列
        escaped = str(value).replace("'", "''").replace("\\", "\\\\")
        return f"'{escaped}'"

    def generate_bom_sql(self):
        """BOMデータのSQLを生成"""
        lines = []
        lines.append("-- ========================================")
        lines.append("-- BOM data import")
        lines.append("-- ========================================")
        lines.append("")

        for bom in BOM.objects.select_related('parent_product').all():
            parent_code = bom.parent_product.product_code

            lines.append(f"-- BOM: {parent_code} {bom.version}")

            # BOMヘッダ INSERT
            sql = f"""INSERT INTO m_bom (parent_product_id, version, valid_from, valid_to, is_active, is_coproduct, created_at, updated_at)
SELECT p.id, {self.escape_sql(bom.version)}, {self.escape_sql(bom.valid_from)}, {self.escape_sql(bom.valid_to)}, {self.escape_sql(bom.is_active)}, {self.escape_sql(bom.is_coproduct)}, NOW(), NOW()
FROM m_product p
WHERE p.product_code = {self.escape_sql(parent_code)}
AND NOT EXISTS (
    SELECT 1 FROM m_bom b
    JOIN m_product pp ON b.parent_product_id = pp.id
    WHERE pp.product_code = {self.escape_sql(parent_code)}
    AND b.version = {self.escape_sql(bom.version)}
    AND b.valid_from = {self.escape_sql(bom.valid_from)}
);"""
            lines.append(sql)
            lines.append("")

            # BOM明細
            for item in bom.items.select_related('child_product', 'supplier', 'process', 'line').all():
                child_code = item.child_product.product_code
                supplier_code = item.supplier.supplier_code if item.supplier else None
                process_code = item.process.process_code if item.process else None
                line_code = item.line.line_code if item.line else None

                supplier_subq = f"(SELECT id FROM m_supplier WHERE supplier_code = {self.escape_sql(supplier_code)})" if supplier_code else "NULL"
                process_subq = f"(SELECT id FROM m_process WHERE process_code = {self.escape_sql(process_code)})" if process_code else "NULL"
                line_subq = f"(SELECT id FROM m_line WHERE line_code = {self.escape_sql(line_code)})" if line_code else "NULL"

                sql = f"""INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, supplier_id, process_id, line_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, remark, created_at, updated_at)
SELECT
    (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id = pp.id
     WHERE pp.product_code = {self.escape_sql(parent_code)} AND b.version = {self.escape_sql(bom.version)} AND b.valid_from = {self.escape_sql(bom.valid_from)}),
    (SELECT id FROM m_product WHERE product_code = {self.escape_sql(child_code)}),
    {self.escape_sql(item.quantity)}, {self.escape_sql(item.loss_rate)}, {self.escape_sql(item.sourcing_type)},
    {supplier_subq}, {process_subq}, {line_subq},
    {self.escape_sql(item.time_unit)}, {self.escape_sql(item.lead_time_days)}, {self.escape_sql(item.duration_min)},
    {self.escape_sql(item.is_coproduct_driver)}, {self.escape_sql(item.remark)}, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_bom_item bi
    JOIN m_bom b ON bi.bom_id = b.id
    JOIN m_product pp ON b.parent_product_id = pp.id
    JOIN m_product cp ON bi.child_product_id = cp.id
    WHERE pp.product_code = {self.escape_sql(parent_code)}
    AND b.version = {self.escape_sql(bom.version)}
    AND cp.product_code = {self.escape_sql(child_code)}
);"""
                lines.append(sql)
                lines.append("")

        return lines

    def generate_routing_sql(self):
        """ルーティングデータのSQLを生成"""
        lines = []
        lines.append("-- ========================================")
        lines.append("-- Routing data import")
        lines.append("-- ========================================")
        lines.append("")

        for routing in Routing.objects.select_related('product').all():
            product_code = routing.product.product_code

            lines.append(f"-- Routing: {product_code} - {routing.routing_code}")

            sql = f"""INSERT INTO m_routing (product_id, routing_code, description, is_default, is_active, created_at, updated_at)
SELECT p.id, {self.escape_sql(routing.routing_code)}, {self.escape_sql(routing.description)}, {self.escape_sql(routing.is_default)}, {self.escape_sql(routing.is_active)}, NOW(), NOW()
FROM m_product p
WHERE p.product_code = {self.escape_sql(product_code)}
AND NOT EXISTS (
    SELECT 1 FROM m_routing r
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = {self.escape_sql(product_code)}
    AND r.routing_code = {self.escape_sql(routing.routing_code)}
);"""
            lines.append(sql)
            lines.append("")

            # ルーティング工程
            for step in routing.steps.select_related('process', 'line', 'output_product').all():
                process_code = step.process.process_code
                line_code = step.line.line_code if step.line else None
                output_code = step.output_product.product_code if step.output_product else None

                line_subq = f"(SELECT id FROM m_line WHERE line_code = {self.escape_sql(line_code)})" if line_code else "NULL"
                output_subq = f"(SELECT id FROM m_product WHERE product_code = {self.escape_sql(output_code)})" if output_code else "NULL"

                sql = f"""INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = {self.escape_sql(product_code)} AND r.routing_code = {self.escape_sql(routing.routing_code)}),
    {self.escape_sql(step.step_no)},
    (SELECT id FROM m_process WHERE process_code = {self.escape_sql(process_code)}),
    {line_subq}, {output_subq},
    {self.escape_sql(step.hierarchy_path)}, {self.escape_sql(step.hierarchy_depth)}, {self.escape_sql(step.time_unit)},
    {self.escape_sql(step.lead_time_days)}, {self.escape_sql(step.start_offset_min)}, {self.escape_sql(step.duration_min)},
    {self.escape_sql(step.parallel_count)}, {self.escape_sql(step.parallel_group)}, {self.escape_sql(step.remark)}, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = {self.escape_sql(product_code)}
    AND r.routing_code = {self.escape_sql(routing.routing_code)}
    AND rs.step_no = {self.escape_sql(step.step_no)}
    AND rs.parallel_group = {self.escape_sql(step.parallel_group)}
);"""
                lines.append(sql)
                lines.append("")

                # 工程別部品消費
                for material in step.materials.select_related('component').all():
                    component_code = material.component.product_code

                    sql = f"""INSERT INTO m_routing_step_material (routing_step_id, component_id, quantity, consume_timing, remark, created_at, updated_at)
SELECT
    (SELECT rs.id FROM m_routing_step rs
     JOIN m_routing r ON rs.routing_id = r.id
     JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = {self.escape_sql(product_code)}
     AND r.routing_code = {self.escape_sql(routing.routing_code)}
     AND rs.step_no = {self.escape_sql(step.step_no)}
     AND rs.parallel_group = {self.escape_sql(step.parallel_group)}),
    (SELECT id FROM m_product WHERE product_code = {self.escape_sql(component_code)}),
    {self.escape_sql(material.quantity)}, {self.escape_sql(material.consume_timing)}, {self.escape_sql(material.remark)}, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step_material rsm
    JOIN m_routing_step rs ON rsm.routing_step_id = rs.id
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    JOIN m_product cp ON rsm.component_id = cp.id
    WHERE pp.product_code = {self.escape_sql(product_code)}
    AND r.routing_code = {self.escape_sql(routing.routing_code)}
    AND rs.step_no = {self.escape_sql(step.step_no)}
    AND cp.product_code = {self.escape_sql(component_code)}
);"""
                    lines.append(sql)
                    lines.append("")

        return lines

    def generate_process_cycle_time_sql(self):
        """工程別サイクル時間のSQLを生成"""
        lines = []
        lines.append("-- ========================================")
        lines.append("-- Process cycle time import")
        lines.append("-- ========================================")
        lines.append("")

        for ct in ProcessCycleTime.objects.select_related('product', 'process', 'line').all():
            product_code = ct.product.product_code
            process_code = ct.process.process_code
            line_code = ct.line.line_code if ct.line else None

            line_subq = f"(SELECT id FROM m_line WHERE line_code = {self.escape_sql(line_code)})" if line_code else "NULL"
            valid_from_cond = f"= {self.escape_sql(ct.valid_from)}" if ct.valid_from else "IS NULL"

            sql = f"""INSERT INTO m_process_cycle_time (product_id, process_id, line_id, cycle_time_min, setup_time_min, lot_size, is_active, valid_from, valid_to, created_at, updated_at)
SELECT
    (SELECT id FROM m_product WHERE product_code = {self.escape_sql(product_code)}),
    (SELECT id FROM m_process WHERE process_code = {self.escape_sql(process_code)}),
    {line_subq},
    {self.escape_sql(ct.cycle_time_min)}, {self.escape_sql(ct.setup_time_min)}, {self.escape_sql(ct.lot_size)},
    {self.escape_sql(ct.is_active)}, {self.escape_sql(ct.valid_from)}, {self.escape_sql(ct.valid_to)}, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_process_cycle_time pct
    JOIN m_product pp ON pct.product_id = pp.id
    JOIN m_process pr ON pct.process_id = pr.id
    WHERE pp.product_code = {self.escape_sql(product_code)}
    AND pr.process_code = {self.escape_sql(process_code)}
    AND pct.valid_from {valid_from_cond}
);"""
            lines.append(sql)
            lines.append("")

        return lines

    def handle(self, *args, **options):
        self.stdout.write("=== BOM/Routing SQL Export ===")

        all_lines = []
        all_lines.append("-- Auto-generated SQL: BOM/Routing Import")
        all_lines.append(f"-- Generated: {datetime.now()}")
        all_lines.append("-- Note: Product/Process/Line/Supplier masters must be imported first")
        all_lines.append("")
        all_lines.append("SET NAMES utf8mb4;")
        all_lines.append("")

        # BOM
        bom_count = BOM.objects.count()
        item_count = BOMItem.objects.count()
        self.stdout.write(f"BOM: {bom_count}, Items: {item_count}")
        all_lines.extend(self.generate_bom_sql())

        # Routing
        routing_count = Routing.objects.count()
        step_count = RoutingStep.objects.count()
        material_count = RoutingStepMaterial.objects.count()
        self.stdout.write(f"Routing: {routing_count}, Steps: {step_count}, Materials: {material_count}")
        all_lines.extend(self.generate_routing_sql())

        # ProcessCycleTime
        ct_count = ProcessCycleTime.objects.count()
        self.stdout.write(f"ProcessCycleTime: {ct_count}")
        all_lines.extend(self.generate_process_cycle_time_sql())

        # ファイル出力
        output_file = 'bom_routing_import.sql'
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(all_lines))

        self.stdout.write(self.style.SUCCESS(f"\nExport complete: {output_file}"))
        self.stdout.write("Run this SQL in production Adminer")
