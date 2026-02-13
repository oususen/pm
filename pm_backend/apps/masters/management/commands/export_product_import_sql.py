"""
開発DBから BOM/ルーティング関連で参照される製品を抽出し、
product_import.sql を生成するコマンド。
既存品番は NOT EXISTS でスキップする。
line_id/process_id は NULL で出力する。
"""

from datetime import date, datetime
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import connection

from masters.models import Product


class Command(BaseCommand):
    help = 'BOM/ルーティング参照の製品を product_import.sql に出力'

    def escape_sql(self, value):
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

    def fetch_product_codes(self):
        sql = """
            SELECT DISTINCT product_code
            FROM (
                SELECT p.product_code
                FROM m_bom b
                JOIN m_product p ON b.parent_product_id = p.id
                UNION
                SELECT p.product_code
                FROM m_bom_item bi
                JOIN m_product p ON bi.child_product_id = p.id
                UNION
                SELECT p.product_code
                FROM m_routing r
                JOIN m_product p ON r.product_id = p.id
                UNION
                SELECT p.product_code
                FROM m_routing_step rs
                JOIN m_product p ON rs.output_product_id = p.id
                WHERE rs.output_product_id IS NOT NULL
                UNION
                SELECT p.product_code
                FROM m_routing_step_material rsm
                JOIN m_product p ON rsm.component_id = p.id
                UNION
                SELECT p.product_code
                FROM m_process_cycle_time pct
                JOIN m_product p ON pct.product_id = p.id
                UNION
                SELECT p.product_code
                FROM m_cycle_time ct
                JOIN m_product p ON ct.product_id = p.id
                UNION
                SELECT p.product_code
                FROM m_line_product_lt lp
                JOIN m_product p ON lp.product_id = p.id
                UNION
                SELECT p.product_code
                FROM m_supplier_item si
                JOIN m_product p ON si.product_id = p.id
            ) t
            WHERE product_code IS NOT NULL
            ORDER BY product_code
        """
        with connection.cursor() as cursor:
            cursor.execute(sql)
            return [row[0] for row in cursor.fetchall()]

    def generate_product_sql(self, product_codes):
        if not product_codes:
            return []

        products = Product.objects.filter(product_code__in=product_codes)
        product_map = {p.product_code: p for p in products}

        lines = []
        for code in product_codes:
            product = product_map.get(code)
            if not product:
                continue

            sql = (
                "INSERT INTO m_product ("
                "product_code, product_name, product_name_halfwidth, category, unit, "
                "standard_lt_days, image_url, line_id, process_id, management_unit, "
                "self_lt_days, is_final_product, is_line_final_product, is_phantom, "
                "is_virtual_set, is_active, created_at, updated_at"
                ") "
                "SELECT "
                f"{self.escape_sql(product.product_code)}, "
                f"{self.escape_sql(product.product_name)}, "
                f"{self.escape_sql(product.product_name_halfwidth)}, "
                f"{self.escape_sql(product.category)}, "
                f"{self.escape_sql(product.unit)}, "
                f"{self.escape_sql(product.standard_lt_days)}, "
                f"{self.escape_sql(product.image_url)}, "
                "NULL, NULL, "
                f"{self.escape_sql(product.management_unit)}, "
                f"{self.escape_sql(product.self_lt_days)}, "
                f"{self.escape_sql(product.is_final_product)}, "
                f"{self.escape_sql(product.is_line_final_product)}, "
                f"{self.escape_sql(product.is_phantom)}, "
                f"{self.escape_sql(product.is_virtual_set)}, "
                f"{self.escape_sql(product.is_active)}, "
                "NOW(), NOW() "
                "FROM DUAL "
                "WHERE NOT EXISTS ("
                f"SELECT 1 FROM m_product p WHERE p.product_code = {self.escape_sql(product.product_code)}"
                ");"
            )
            lines.append(sql)

        return lines

    def handle(self, *args, **options):
        self.stdout.write('=== Export product_import.sql ===')

        product_codes = self.fetch_product_codes()
        self.stdout.write(f'Products to export: {len(product_codes)}')

        all_lines = []
        all_lines.append('-- Auto-generated SQL: product_import.sql')
        all_lines.append(f'-- Generated: {datetime.now()}')
        all_lines.append('SET NAMES utf8mb4;')
        all_lines.append('')

        all_lines.extend(self.generate_product_sql(product_codes))
        all_lines.append('')

        output_file = 'product_import.sql'
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(all_lines))

        self.stdout.write(self.style.SUCCESS(f'Export complete: {output_file}'))
