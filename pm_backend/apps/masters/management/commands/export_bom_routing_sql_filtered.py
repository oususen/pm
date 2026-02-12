"""
品番を指定してBOM・ルーティング・関連製品のSQLを出力するコマンド。
本番への移行用にIDではなくコードで参照するINSERT文を生成する。
使用例:
  python manage.py export_bom_routing_sql_filtered --product-codes YD60011305 YD60009874 --include-products --output bom_routing_YD600.sql
"""

from datetime import date, datetime
from decimal import Decimal
from django.core.management.base import BaseCommand
from masters.models import (
    BOM,
    BOMItem,
    Routing,
    RoutingStep,
    RoutingStepMaterial,
    ProcessCycleTime,
    Product,
)


class Command(BaseCommand):
    help = '指定品番のBOM・ルーティングをSQL形式でエクスポート（NOT EXISTS 付き）'

    def add_arguments(self, parser):
        parser.add_argument(
            '--product-codes',
            nargs='+',
            help='親品番コードをスペース区切りで指定（未指定は全件）',
        )
        parser.add_argument(
            '--include-products',
            action='store_true',
            help='関連品番のm_product INSERT文を含める（既存はNOT EXISTSでスキップ）',
        )
        parser.add_argument(
            '--output',
            default='bom_routing_import.sql',
            help='出力先ファイル名（既定: bom_routing_import.sql）',
        )

    # --------------- 共通ヘルパ ---------------
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
        escaped = str(value).replace("'", "''").replace('\\', '\\\\')
        return f"'{escaped}'"

    def _filter_boms(self, product_codes):
        if not product_codes:
            return BOM.objects.select_related('parent_product').all()
        return BOM.objects.select_related('parent_product').filter(
            parent_product__product_code__in=product_codes
        )

    def _filter_routings(self, product_codes):
        if not product_codes:
            return Routing.objects.select_related('product').all()
        return Routing.objects.select_related('product').filter(
            product__product_code__in=product_codes
        )

    def _collect_related_product_codes(self, parent_codes):
        """親品番に紐づく子部品・工程出力・工程別部品を集約"""
        if not parent_codes:
            return set()

        codes = set(parent_codes)

        child_codes = BOMItem.objects.filter(
            bom__parent_product__product_code__in=parent_codes
        ).values_list('child_product__product_code', flat=True)
        codes.update([c for c in child_codes if c])

        output_codes = RoutingStep.objects.filter(
            routing__product__product_code__in=parent_codes,
            output_product__isnull=False,
        ).values_list('output_product__product_code', flat=True)
        codes.update([c for c in output_codes if c])

        material_codes = RoutingStepMaterial.objects.filter(
            routing_step__routing__product__product_code__in=parent_codes
        ).values_list('component__product_code', flat=True)
        codes.update([c for c in material_codes if c])

        return codes

    # --------------- SQL生成 ---------------
    def generate_product_sql(self, target_product_codes: set):
        if not target_product_codes:
            return []

        lines = []
        lines.append('-- ========================================')
        lines.append('-- Product data import (upsert by product_code)')
        lines.append('-- ========================================')
        lines.append('')

        products = Product.objects.filter(product_code__in=target_product_codes)
        for product in products:
            # NOT NULL でデフォルトが無い環境に備えて明示的に0を入れる
            sql = f"""INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT {self.escape_sql(product.product_code)}, {self.escape_sql(product.product_name)}, {self.escape_sql(product.category)}, {self.escape_sql(product.unit)}, 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = {self.escape_sql(product.product_code)}
);"""
            lines.append(sql)
            lines.append('')

        return lines

    def generate_bom_sql(self, product_codes=None):
        lines = []
        lines.append('-- ========================================')
        lines.append('-- BOM data import')
        lines.append('-- ========================================')
        lines.append('')

        for bom in self._filter_boms(product_codes):
            parent_code = bom.parent_product.product_code

            lines.append(f"-- BOM: {parent_code} {bom.version}")

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
            lines.append('')

            for item in bom.items.select_related('child_product', 'supplier', 'process', 'line').all():
                child_code = item.child_product.product_code
                supplier_code = item.supplier.supplier_code if item.supplier else None
                process_code = item.process.process_code if item.process else None
                line_code = item.line.line_code if item.line else None

                supplier_subq = f"(SELECT id FROM m_supplier WHERE supplier_code = {self.escape_sql(supplier_code)})" if supplier_code else 'NULL'
                process_subq = f"(SELECT id FROM m_process WHERE process_code = {self.escape_sql(process_code)})" if process_code else 'NULL'
                line_subq = f"(SELECT id FROM m_line WHERE line_code = {self.escape_sql(line_code)})" if line_code else 'NULL'

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
                lines.append('')

        return lines

    def generate_routing_sql(self, product_codes=None):
        lines = []
        lines.append('-- ========================================')
        lines.append('-- Routing data import')
        lines.append('-- ========================================')
        lines.append('')

        for routing in self._filter_routings(product_codes):
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
            lines.append('')

            for step in routing.steps.select_related('process', 'line', 'output_product').all():
                process_code = step.process.process_code
                line_code = step.line.line_code if step.line else None
                output_code = step.output_product.product_code if step.output_product else None

                line_subq = f"(SELECT id FROM m_line WHERE line_code = {self.escape_sql(line_code)})" if line_code else 'NULL'
                output_subq = f"(SELECT id FROM m_product WHERE product_code = {self.escape_sql(output_code)})" if output_code else 'NULL'

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
                lines.append('')

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
                    lines.append('')

        return lines

    def generate_process_cycle_time_sql(self, product_codes=None):
        lines = []
        lines.append('-- ========================================')
        lines.append('-- Process cycle time import')
        lines.append('-- ========================================')
        lines.append('')

        qs = ProcessCycleTime.objects.select_related('product', 'process', 'line')
        if product_codes:
            qs = qs.filter(product__product_code__in=product_codes)

        for ct in qs:
            product_code = ct.product.product_code
            process_code = ct.process.process_code
            line_code = ct.line.line_code if ct.line else None

            line_subq = f"(SELECT id FROM m_line WHERE line_code = {self.escape_sql(line_code)})" if line_code else 'NULL'
            valid_from_cond = f"= {self.escape_sql(ct.valid_from)}" if ct.valid_from else 'IS NULL'

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
            lines.append('')

        return lines

    # --------------- メイン処理 ---------------
    def handle(self, *args, **options):
        product_codes = options.get('product_codes')
        include_products = options.get('include_products', False)
        output_file = options.get('output') or 'bom_routing_import.sql'

        self.stdout.write('=== BOM/Routing SQL Export (filtered) ===')

        all_lines = []
        all_lines.append('-- Auto-generated SQL: BOM/Routing Import')
        all_lines.append(f"-- Generated: {datetime.now()}")
        if include_products:
            all_lines.append('-- Includes m_product inserts (NOT EXISTS skip)')
        else:
            all_lines.append('-- Note: Product/Process/Line/Supplier masters must be imported first')
        all_lines.append('')
        all_lines.append('SET NAMES utf8mb4;')
        all_lines.append('')

        # 対象品番（関連品も含めて製品マスタを補完）
        related_product_codes = self._collect_related_product_codes(product_codes) if product_codes else set()

        if include_products:
            target_codes = related_product_codes or set(product_codes or [])
            prod_count = Product.objects.filter(product_code__in=target_codes).count()
            self.stdout.write(f'Products: {prod_count}')
            all_lines.extend(self.generate_product_sql(target_codes))

        # BOM
        bom_qs = self._filter_boms(product_codes)
        bom_count = bom_qs.count()
        item_count = BOMItem.objects.filter(bom__in=bom_qs).count()
        self.stdout.write(f'BOM: {bom_count}, Items: {item_count}')
        all_lines.extend(self.generate_bom_sql(product_codes))

        # Routing
        routing_qs = self._filter_routings(product_codes)
        routing_count = routing_qs.count()
        step_count = RoutingStep.objects.filter(routing__in=routing_qs).count()
        material_count = RoutingStepMaterial.objects.filter(routing_step__routing__in=routing_qs).count()
        self.stdout.write(f'Routing: {routing_count}, Steps: {step_count}, Materials: {material_count}')
        all_lines.extend(self.generate_routing_sql(product_codes))

        # ProcessCycleTime
        ct_qs = ProcessCycleTime.objects.filter(product__product_code__in=product_codes) if product_codes else ProcessCycleTime.objects.all()
        ct_count = ct_qs.count()
        self.stdout.write(f'ProcessCycleTime: {ct_count}')
        all_lines.extend(self.generate_process_cycle_time_sql(product_codes))

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(all_lines))

        self.stdout.write(self.style.SUCCESS(f'\nExport complete: {output_file}'))
        self.stdout.write('Run this SQL in production Adminer')
