"""
開発DBから master_rel_import.sql を生成するコマンド。
対象テーブル:
- m_line_default
- m_line_product_lt
- m_supplier_item
- m_cycle_time

生成SQLは code ベースで参照し、本番のID差異に依存しない。
使用方法:
  python manage.py export_master_rel_sql

出力ファイル:
  master_rel_import.sql
"""

from datetime import date, datetime
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'm_line_default/m_line_product_lt/m_supplier_item/m_cycle_time を code ベースでSQL出力'

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

    def fetch_all(self, sql):
        with connection.cursor() as cursor:
            cursor.execute(sql)
            return cursor.fetchall()

    def generate_line_default(self):
        lines = []
        rows = self.fetch_all(
            """
            SELECT ld.default_lt_days, l.line_code
            FROM m_line_default ld
            JOIN m_line l ON ld.line_id = l.id
            ORDER BY l.line_code
            """
        )
        for default_lt_days, line_code in rows:
            sql = (
                "INSERT INTO m_line_default (line_id, default_lt_days) VALUES ("
                f"(SELECT id FROM m_line WHERE line_code = {self.escape_sql(line_code)}),"
                f"{self.escape_sql(default_lt_days)}"
                ");"
            )
            lines.append(sql)
        return lines

    def generate_line_product_lt(self):
        lines = []
        rows = self.fetch_all(
            """
            SELECT lp.lt_days, l.line_code, p.product_code
            FROM m_line_product_lt lp
            JOIN m_line l ON lp.line_id = l.id
            JOIN m_product p ON lp.product_id = p.id
            ORDER BY l.line_code, p.product_code
            """
        )
        for lt_days, line_code, product_code in rows:
            sql = (
                "INSERT INTO m_line_product_lt (line_id, product_id, lt_days) VALUES ("
                f"(SELECT id FROM m_line WHERE line_code = {self.escape_sql(line_code)}),"
                f"(SELECT id FROM m_product WHERE product_code = {self.escape_sql(product_code)}),"
                f"{self.escape_sql(lt_days)}"
                ");"
            )
            lines.append(sql)
        return lines

    def generate_supplier_item(self):
        lines = []
        rows = self.fetch_all(
            """
            SELECT si.purchase_lt_days, si.min_lot, si.order_cycle_days,
                   s.supplier_code, p.product_code
            FROM m_supplier_item si
            JOIN m_supplier s ON si.supplier_id = s.id
            JOIN m_product p ON si.product_id = p.id
            ORDER BY s.supplier_code, p.product_code
            """
        )
        for purchase_lt_days, min_lot, order_cycle_days, supplier_code, product_code in rows:
            sql = (
                "INSERT INTO m_supplier_item (supplier_id, product_id, purchase_lt_days, min_lot, order_cycle_days) VALUES ("
                f"(SELECT id FROM m_supplier WHERE supplier_code = {self.escape_sql(supplier_code)}),"
                f"(SELECT id FROM m_product WHERE product_code = {self.escape_sql(product_code)}),"
                f"{self.escape_sql(purchase_lt_days)},"
                f"{self.escape_sql(min_lot)},"
                f"{self.escape_sql(order_cycle_days)}"
                ");"
            )
            lines.append(sql)
        return lines

    def generate_cycle_time(self):
        lines = []
        rows = self.fetch_all(
            """
            SELECT ct.cycle_time_sec, ct.setup_time_min, ct.yield_rate,
                   ct.valid_from, ct.valid_to, ct.is_active,
                   p.product_code, pr.process_code, l.line_code
            FROM m_cycle_time ct
            JOIN m_product p ON ct.product_id = p.id
            JOIN m_process pr ON ct.process_id = pr.id
            JOIN m_line l ON ct.line_id = l.id
            ORDER BY p.product_code, pr.process_code, l.line_code, ct.valid_from
            """
        )
        for cycle_time_sec, setup_time_min, yield_rate, valid_from, valid_to, is_active, product_code, process_code, line_code in rows:
            sql = (
                "INSERT INTO m_cycle_time (product_id, process_id, line_id, cycle_time_sec, setup_time_min, yield_rate, valid_from, valid_to, is_active, created_at, updated_at) VALUES ("
                f"(SELECT id FROM m_product WHERE product_code = {self.escape_sql(product_code)}),"
                f"(SELECT id FROM m_process WHERE process_code = {self.escape_sql(process_code)}),"
                f"(SELECT id FROM m_line WHERE line_code = {self.escape_sql(line_code)}),"
                f"{self.escape_sql(cycle_time_sec)},"
                f"{self.escape_sql(setup_time_min)},"
                f"{self.escape_sql(yield_rate)},"
                f"{self.escape_sql(valid_from)},"
                f"{self.escape_sql(valid_to)},"
                f"{self.escape_sql(is_active)},"
                "NOW(), NOW()"
                ");"
            )
            lines.append(sql)
        return lines

    def handle(self, *args, **options):
        self.stdout.write('=== Export master_rel_import.sql ===')

        all_lines = []
        all_lines.append('-- Auto-generated SQL: master_rel_import.sql')
        all_lines.append(f'-- Generated: {datetime.now()}')
        all_lines.append('SET NAMES utf8mb4;')
        all_lines.append('')

        all_lines.append('-- m_line_default')
        all_lines.extend(self.generate_line_default())
        all_lines.append('')

        all_lines.append('-- m_line_product_lt')
        all_lines.extend(self.generate_line_product_lt())
        all_lines.append('')

        all_lines.append('-- m_supplier_item')
        all_lines.extend(self.generate_supplier_item())
        all_lines.append('')

        all_lines.append('-- m_cycle_time')
        all_lines.extend(self.generate_cycle_time())
        all_lines.append('')

        output_file = 'master_rel_import.sql'
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(all_lines))

        self.stdout.write(self.style.SUCCESS(f'Export complete: {output_file}'))
