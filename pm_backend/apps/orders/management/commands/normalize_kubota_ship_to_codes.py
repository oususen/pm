"""クボタ納入先コードの一回限りのデータ移行。既定は読取専用の事前確認。"""
import json
import os
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.core.serializers.json import DjangoJSONEncoder
from django.db import connection, transaction
from django.db.models import Min, Max

from masters.models import Customer
from orders.core.services.ship_to_utils import normalize_kubota_ship_to_code
from production.services.order_expansion import OrderExpansionService
from shipping.models import KubotaSakaiDeliveryProgress, ShippingProgress
from shipping.services.kubota_sakai_delivery_progress import recalculate_delivery_progress
from shipping.services.shipping_progress import recalculate_shipping_progress


def merge_settings(rows):
    """未設定項目のみ補完する。異なる設定値は自動選択せず中止する。"""
    fields = ('ship_to_name', 'additional_days', 'bg_color', 'text_color', 'calendar_id', 'is_active')
    merged = {}
    for field in fields:
        values = {r[field] for r in rows if r[field] not in (None, '')}
        if len(values) > 1:
            raise CommandError(f'納入地設定が競合しています: {rows[0]["ship_to_code"]} / {field}')
        merged[field] = next(iter(values)) if values else rows[0][field]
    return merged


class Command(BaseCommand):
    help = 'クボタ納入先を5桁へ統一。--apply 時のみ更新し、需要を全件再展開する。'
    requires_system_checks = []

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true')
        parser.add_argument('--backup', help='更新前データのJSONL退避先（既存ファイルは上書きしない）')

    def query(self, sql, params=()):
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            columns = [c[0] for c in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def execute_sql(self, sql, params=()):
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.rowcount

    def scopes(self, customer_id):
        # 顧客IDを持たないクボタ専用テーブルは全行を対象にする。
        return {
            'm_ship_to_lead_time': f'customer_id={customer_id}',
            'stg_order_daily': f'customer_id={customer_id}',
            't_order_line': f'order_id IN (SELECT id FROM t_order WHERE customer_id={customer_id})',
            't_shipment_actual': f"customer_id={customer_id} OR customer_code='000196'",
            't_shipment_actual_history': "customer_code='000196'",
            't_shipping_run': "customer_code='000196'",
            't_shipping_trip': "customer_code='000196'",
            't_shipping_trip_allocation': "trip_id IN (SELECT id FROM t_shipping_trip WHERE customer_code='000196')",
            'm_kubota_sakai_pseudo_truck_product': '1=1',
            't_kubota_sakai_due_adjustment': '1=1',
            't_kubota_sakai_due_allocation_override': '1=1',
            't_kubota_sakai_trip_display_setting': '1=1',
            't_kubota_sakai_delivery_progress': '1=1',
        }

    def plan(self, scopes):
        mappings = {}
        for table, scope in scopes.items():
            codes = self.query(f'SELECT DISTINCT ship_to_code FROM `{table}` WHERE ({scope})')
            mapping = {}
            for row in codes:
                code = row['ship_to_code']
                normalized = normalize_kubota_ship_to_code(code)
                # この移行では空白だけの補正や英数字コードの変更は行わない。
                if code and normalized.isascii() and normalized.isdecimal() and code != normalized:
                    mapping[code] = normalized
            mappings[table] = mapping
            if mapping:
                placeholders = ','.join(['%s'] * len(mapping))
                count = self.query(
                    f'SELECT COUNT(*) n FROM `{table}` WHERE ({scope}) AND ship_to_code IN ({placeholders})',
                    tuple(mapping),
                )[0]['n']
                self.stdout.write(f'{table}: {count}行 / {mapping}')
                self.check_unique_keys(table, scope, mapping)
        return mappings

    def check_unique_keys(self, table, scope, mapping):
        if table == 'm_ship_to_lead_time':
            groups = defaultdict(list)
            for row in self.query(f'SELECT * FROM `{table}` WHERE ({scope})'):
                groups[mapping.get(row['ship_to_code'], row['ship_to_code'])].append(row)
            for rows in groups.values():
                if len(rows) > 1:
                    merge_settings(rows)
            return
        if table == 't_kubota_sakai_delivery_progress':
            # 新旧コードが同日に併存していても rebuild_delivery_progress() で統合するため検査不要。
            return
        indexes = defaultdict(list)
        for row in self.query(f'SHOW INDEX FROM `{table}`'):
            if not row['Non_unique']:
                indexes[row['Key_name']].append((row['Seq_in_index'], row['Column_name']))
        for index, fields in indexes.items():
            fields = [name for _, name in sorted(fields)]
            if 'ship_to_code' not in fields:
                continue
            seen = {}
            selected = ','.join(f'`{field}`' for field in fields)
            for row in self.query(f'SELECT id,{selected} FROM `{table}` WHERE ({scope})'):
                key = tuple(mapping.get(row[f], row[f]) if f == 'ship_to_code' else row[f] for f in fields)
                # NULLを含む業務キーも保守的に競合として検査する。
                if key in seen and seen[key]['ship_to_code'] != row['ship_to_code']:
                    raise CommandError(f'更新後のキーが競合します: {table}/{index}: {key}')
                seen[key] = row

    def backup(self, path, scopes):
        snapshots = dict(scopes)
        snapshots.update({
            'stg_order_raw_kubota': "customer_code='000196'",
            'm_ship_to_lead_time_color_exclusion':
                'ship_to_lead_time_id IN (SELECT id FROM m_ship_to_lead_time WHERE ' + scopes['m_ship_to_lead_time'] + ')',
            # 全件再展開で変更する需要と確定展開フラグも退避する。
            't_line_demand': '1=1',
            't_order_line': '(' + scopes['t_order_line'] + ") OR order_id IN (SELECT id FROM t_order WHERE status='OPEN' AND order_type='FIRM')",
            't_shipping_progress': "customer_code='000196'",
        })
        path = Path(path).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('x', encoding='utf-8') as backup:
            backup.write(json.dumps({'format': 1, 'created_at': datetime.now().isoformat()}, ensure_ascii=False) + '\n')
            for table, scope in snapshots.items():
                # 大量の需要を辞書のリストとして一括保持しない。
                with connection.cursor() as cursor:
                    cursor.execute(f'SELECT * FROM `{table}` WHERE ({scope}) FOR UPDATE')
                    columns = [column[0] for column in cursor.description]
                    while True:
                        rows = cursor.fetchmany(1000)
                        if not rows:
                            break
                        for values in rows:
                            row = dict(zip(columns, values))
                            backup.write(json.dumps({'table': table, 'row': row}, cls=DjangoJSONEncoder, ensure_ascii=False) + '\n')
            backup.flush()
            os.fsync(backup.fileno())
        self.stdout.write(f'更新前データ退避: {path}')

    def update_settings(self, scope, mapping):
        groups = defaultdict(list)
        for row in self.query(f'SELECT * FROM m_ship_to_lead_time WHERE ({scope})'):
            groups[mapping.get(row['ship_to_code'], row['ship_to_code'])].append(row)
        for code, rows in groups.items():
            if len(rows) == 1 and rows[0]['ship_to_code'] == code:
                continue
            # 正式コードのIDを残して、旧コード側の設定・適用品番を引き継ぐ。
            keeper = next((r for r in rows if r['ship_to_code'] == code), rows[0])
            merged = merge_settings(rows)
            for row in rows:
                if row['id'] == keeper['id']:
                    continue
                products = self.query('SELECT product_code FROM m_ship_to_lead_time_color_exclusion WHERE ship_to_lead_time_id=%s', (row['id'],))
                for product in products:
                    self.execute_sql(
                        'INSERT INTO m_ship_to_lead_time_color_exclusion (ship_to_lead_time_id,product_code,created_at,updated_at) '
                        'SELECT %s,%s,%s,%s WHERE NOT EXISTS (SELECT 1 FROM m_ship_to_lead_time_color_exclusion WHERE ship_to_lead_time_id=%s AND product_code=%s)',
                        (keeper['id'], product['product_code'], datetime.now(), datetime.now(), keeper['id'], product['product_code']),
                    )
                self.execute_sql('DELETE FROM m_ship_to_lead_time_color_exclusion WHERE ship_to_lead_time_id=%s', (row['id'],))
                self.execute_sql('DELETE FROM m_ship_to_lead_time WHERE id=%s', (row['id'],))
            assignments = ','.join(f'`{field}`=%s' for field in merged)
            self.execute_sql(f'UPDATE m_ship_to_lead_time SET ship_to_code=%s,{assignments} WHERE id=%s', (code, *merged.values(), keeper['id']))

    def rebuild_shipping_progress(self):
        qs = ShippingProgress.objects.filter(customer_code='000196')
        codes = {r['ship_to_code'] for r in self.query("SELECT DISTINCT ship_to_code FROM t_shipping_progress WHERE customer_code='000196'")}
        changed = {code: normalize_kubota_ship_to_code(code) for code in codes
                   if code and normalize_kubota_ship_to_code(code).isascii()
                   and normalize_kubota_ship_to_code(code).isdecimal() and code != normalize_kubota_ship_to_code(code)}
        if not changed:
            return
        affected = qs.filter(ship_to_code__in=set(changed) | set(changed.values()))
        dates = affected.aggregate(start=Min('plan_date'), end=Max('plan_date'))
        groups = defaultdict(list)
        for row in affected.order_by('id'):
            groups[(row.product_code, changed.get(row.ship_to_code, row.ship_to_code), row.plan_date)].append(row)
        for (_, code, _), rows in groups.items():
            keeper = next((row for row in rows if row.ship_to_code == code), rows[0])
            # 手動調整は同一納入地の寄与として保持し、累積進度は再計算する。
            keeper.adjust_qty = sum(row.adjust_qty for row in rows)
            for row in rows:
                if row.pk != keeper.pk:
                    row.delete()
            keeper.ship_to_code = code
            keeper.save(update_fields=['ship_to_code', 'adjust_qty'])
        recalculate_shipping_progress(dates['start'], dates['end'], customer_code='000196', ship_to_codes=set(changed.values()))

    def rebuild_delivery_progress(self):
        codes = {r['ship_to_code'] for r in self.query('SELECT DISTINCT ship_to_code FROM t_kubota_sakai_delivery_progress')}
        changed = {code: normalize_kubota_ship_to_code(code) for code in codes
                   if code and normalize_kubota_ship_to_code(code).isascii()
                   and normalize_kubota_ship_to_code(code).isdecimal() and code != normalize_kubota_ship_to_code(code)}
        if not changed:
            return
        affected = KubotaSakaiDeliveryProgress.objects.filter(ship_to_code__in=set(changed) | set(changed.values()))
        dates = affected.aggregate(start=Min('plan_date'), end=Max('plan_date'))
        groups = defaultdict(list)
        for row in affected.order_by('id'):
            groups[(row.product_code, changed.get(row.ship_to_code, row.ship_to_code), row.plan_date)].append(row)
        for (_, code, _), rows in groups.items():
            keeper = next((row for row in rows if row.ship_to_code == code), rows[0])
            # 手動調整は同一納入地の寄与として保持し、需要・便振分・累積進度は再計算する。
            keeper.adjust_qty = sum(row.adjust_qty for row in rows)
            for row in rows:
                if row.pk != keeper.pk:
                    row.delete()
            keeper.ship_to_code = code
            keeper.save(update_fields=['ship_to_code', 'adjust_qty'])
        recalculate_delivery_progress(dates['start'], dates['end'])

    def handle(self, *args, **options):
        if connection.vendor != 'mysql':
            raise CommandError('この移行はMySQL専用です。')
        if options['apply'] and not options['backup']:
            raise CommandError('--apply には --backup が必要です。')
        customer = Customer.objects.get(customer_code='000196')
        scopes = self.scopes(customer.pk)
        with transaction.atomic():
            if options['apply']:
                self.backup(options['backup'], scopes)
            mappings = self.plan(scopes)
            raw_rows = self.query("SELECT id,raw_payload FROM stg_order_raw_kubota WHERE customer_code='000196'")
            raw_updates = []
            for row in raw_rows:
                payload = json.loads(row['raw_payload']) if isinstance(row['raw_payload'], str) else row['raw_payload']
                code = payload.get('ship_to')
                normalized = normalize_kubota_ship_to_code(code)
                if code and normalized.isascii() and normalized.isdecimal() and code != normalized:
                    raw_updates.append((normalized, row['id']))
            self.stdout.write(f'stg_order_raw_kubota.raw_payload.ship_to: {len(raw_updates)}行')
            if not options['apply']:
                self.stdout.write('事前確認のみ。DBは変更していません。適用時は需要を全件再展開し、対象納入地の出荷進度を再計算します。')
                return
            if not any(mappings.values()) and not raw_updates:
                self.stdout.write('変更対象なし。再展開は行いません。')
                return
            # コード変更で実績の対応先を失わないことを確認してから全件再展開する。
            actuals = self.query("SELECT id FROM t_line_demand WHERE ship_to_code REGEXP '^[0-9]{1,4}$' AND actual_qty<>0 LIMIT 1")
            if actuals:
                raise CommandError('旧コードの需要に実績値があります。実績の引継ぎ方法を確認してください。')
            self.update_settings(scopes['m_ship_to_lead_time'], mappings.pop('m_ship_to_lead_time'))
            mappings.pop('t_kubota_sakai_delivery_progress')
            for table, mapping in mappings.items():
                for old, new in mapping.items():
                    self.execute_sql(f'UPDATE `{table}` SET ship_to_code=%s WHERE ({scopes[table]}) AND ship_to_code=%s', (new, old))
            for new, row_id in raw_updates:
                # 原票のrow配列は保持し、業務処理が参照する抽出済みコードだけを変更する。
                self.execute_sql("UPDATE stg_order_raw_kubota SET raw_payload=JSON_SET(raw_payload,'$.ship_to',%s) WHERE id=%s", (new, row_id))
            self.stdout.write('需要を全件再展開しています。')
            result = OrderExpansionService().expand_open_orders(clear_existing=True)
            if result.get('errors'):
                raise CommandError(str(result['errors']))
            self.stdout.write(json.dumps(result, cls=DjangoJSONEncoder, ensure_ascii=False))
            self.rebuild_shipping_progress()
            self.rebuild_delivery_progress()
            self.stdout.write(self.style.SUCCESS('5桁統一・需要再展開・出荷進度再計算・配送進捗再計算が完了しました。'))
