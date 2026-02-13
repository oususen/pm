"""
本番/開発で同一形式のBOM・ルーティング比較用CSVを出力するコマンド。
出力先: compare_exports/ 配下に複数CSV。
"""

from datetime import datetime
from pathlib import Path
import csv

from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'BOM/ルーティング比較用CSVを一括出力'

    def fetch_all(self, sql):
        with connection.cursor() as cursor:
            cursor.execute(sql)
            cols = [c[0] for c in cursor.description]
            rows = cursor.fetchall()
        return cols, rows

    def write_csv(self, out_dir: Path, filename: str, cols, rows):
        path = out_dir / filename
        with path.open('w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(cols)
            writer.writerows(rows)
        return path

    def handle(self, *args, **options):
        out_dir = Path('compare_exports')
        out_dir.mkdir(parents=True, exist_ok=True)

        tasks = [
            (
                'bom_header.csv',
                """
                SELECT
                  pp.product_code AS parent_code,
                  b.version,
                  b.valid_from,
                  b.valid_to,
                  b.is_active,
                  b.is_coproduct
                FROM m_bom b
                JOIN m_product pp ON b.parent_product_id = pp.id
                ORDER BY pp.product_code, b.version, b.valid_from
                """
            ),
            (
                'bom_item.csv',
                """
                SELECT
                  pp.product_code AS parent_code,
                  b.version,
                  b.valid_from,
                  cp.product_code AS child_code,
                  bi.quantity,
                  bi.loss_rate,
                  bi.sourcing_type,
                  s.supplier_code,
                  pr.process_code,
                  l.line_code,
                  bi.time_unit,
                  bi.lead_time_days,
                  bi.duration_min,
                  bi.is_coproduct_driver,
                  bi.remark
                FROM m_bom_item bi
                JOIN m_bom b ON bi.bom_id = b.id
                JOIN m_product pp ON b.parent_product_id = pp.id
                JOIN m_product cp ON bi.child_product_id = cp.id
                LEFT JOIN m_supplier s ON bi.supplier_id = s.id
                LEFT JOIN m_process pr ON bi.process_id = pr.id
                LEFT JOIN m_line l ON bi.line_id = l.id
                ORDER BY pp.product_code, b.version, b.valid_from, cp.product_code, pr.process_code, l.line_code
                """
            ),
            (
                'routing_header.csv',
                """
                SELECT
                  pp.product_code,
                  r.routing_code,
                  r.description,
                  r.is_default,
                  r.is_active
                FROM m_routing r
                JOIN m_product pp ON r.product_id = pp.id
                ORDER BY pp.product_code, r.routing_code
                """
            ),
            (
                'routing_step.csv',
                """
                SELECT
                  pp.product_code,
                  r.routing_code,
                  rs.step_no,
                  pr.process_code,
                  l.line_code,
                  op.product_code AS output_product_code,
                  rs.hierarchy_path,
                  rs.hierarchy_depth,
                  rs.time_unit,
                  rs.lead_time_days,
                  rs.start_offset_min,
                  rs.duration_min,
                  rs.parallel_count,
                  rs.parallel_group,
                  rs.remark
                FROM m_routing_step rs
                JOIN m_routing r ON rs.routing_id = r.id
                JOIN m_product pp ON r.product_id = pp.id
                JOIN m_process pr ON rs.process_id = pr.id
                LEFT JOIN m_line l ON rs.line_id = l.id
                LEFT JOIN m_product op ON rs.output_product_id = op.id
                ORDER BY pp.product_code, r.routing_code, rs.step_no, rs.parallel_group
                """
            ),
            (
                'routing_step_material.csv',
                """
                SELECT
                  pp.product_code,
                  r.routing_code,
                  rs.step_no,
                  rs.parallel_group,
                  cp.product_code AS component_code,
                  rsm.quantity,
                  rsm.consume_timing,
                  rsm.remark
                FROM m_routing_step_material rsm
                JOIN m_routing_step rs ON rsm.routing_step_id = rs.id
                JOIN m_routing r ON rs.routing_id = r.id
                JOIN m_product pp ON r.product_id = pp.id
                JOIN m_product cp ON rsm.component_id = cp.id
                ORDER BY pp.product_code, r.routing_code, rs.step_no, rs.parallel_group, cp.product_code
                """
            ),
            (
                'process_cycle_time.csv',
                """
                SELECT
                  p.product_code,
                  pr.process_code,
                  l.line_code,
                  pct.cycle_time_min,
                  pct.setup_time_min,
                  pct.lot_size,
                  pct.is_active,
                  pct.valid_from,
                  pct.valid_to
                FROM m_process_cycle_time pct
                JOIN m_product p ON pct.product_id = p.id
                JOIN m_process pr ON pct.process_id = pr.id
                LEFT JOIN m_line l ON pct.line_id = l.id
                ORDER BY p.product_code, pr.process_code, l.line_code, pct.valid_from
                """
            ),
            (
                'cycle_time.csv',
                """
                SELECT
                  p.product_code,
                  pr.process_code,
                  l.line_code,
                  ct.cycle_time_sec,
                  ct.setup_time_min,
                  ct.yield_rate,
                  ct.valid_from,
                  ct.valid_to,
                  ct.is_active
                FROM m_cycle_time ct
                JOIN m_product p ON ct.product_id = p.id
                JOIN m_process pr ON ct.process_id = pr.id
                JOIN m_line l ON ct.line_id = l.id
                ORDER BY p.product_code, pr.process_code, l.line_code, ct.valid_from
                """
            ),
            (
                'routing_step_param.csv',
                """
                SELECT
                  pp.product_code,
                  r.routing_code,
                  rs.step_no,
                  rs.parallel_group,
                  rsp.lot_size,
                  rsp.transfer_batch_qty,
                  rsp.start_trigger,
                  rsp.target_buffer_qty,
                  rsp.max_buffer_qty,
                  rsp.buffer_before_min,
                  rsp.buffer_after_min,
                  rsp.daily_time_window_min
                FROM m_routing_step_param rsp
                JOIN m_routing_step rs ON rsp.routing_step_id = rs.id
                JOIN m_routing r ON rs.routing_id = r.id
                JOIN m_product pp ON r.product_id = pp.id
                ORDER BY pp.product_code, r.routing_code, rs.step_no, rs.parallel_group
                """
            ),
        ]

        self.stdout.write(f'=== Export BOM/Routing compare CSV ===')
        self.stdout.write(f'Output dir: {out_dir}')
        self.stdout.write(f'Generated: {datetime.now()}')

        for filename, sql in tasks:
            cols, rows = self.fetch_all(sql)
            path = self.write_csv(out_dir, filename, cols, rows)
            self.stdout.write(f'{filename}: {len(rows)} rows -> {path}')

        self.stdout.write(self.style.SUCCESS('Export complete'))
