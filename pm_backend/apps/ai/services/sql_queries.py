"""LLMが作成した読み取り専用SQLを、安全なスキーマ範囲で実行する。"""
import re
from decimal import Decimal

from django.db import connections

from ai.config.service import get_data_policy
from ai.services.query_common import AI_DB_ALIAS


# AI用DB辞書で区分Aと確認済みの、全利用者に公開できる列。
BASE_SQL_SCHEMA = {
    'm_product': ('id', 'product_code', 'product_name', 'category', 'unit', 'line_id', 'process_id', 'is_active'),
    'm_line': ('id', 'line_code', 'line_name', 'line_type', 'lead_time_days', 'is_active'),
    'm_process': ('id', 'process_code', 'process_name', 'line_id', 'management_unit', 'is_active'),
    'm_calendar_day': ('id', 'target_date', 'is_working_day', 'work_minutes'),
    't_process_realtime_record': ('id', 'process_id', 'product_id', 'product_code', 'product_name', 'timestamp', 'record_type', 'qty', 'equipment_state'),
    't_laser_actual': ('id', 'work_date', 'operator_action', 'pattern_no', 'equipment_code', 'equipment_name', 'material_code', 'material_name', 'total_process_time'),
    't_laser_actual_detail': ('id', 'actual_id', 'detail_type', 'product_id', 'product_code', 'product_name', 'total_qty', 'scrap_qty', 'scrap_reason'),
    'brake_line_record': ('id', 'plan_date', 'line_id', 'process_id', 'product_id', 'product_code', 'operator_action', 'operator_action_reason', 'qty'),
    't_scrap_record': ('id', 'line_id', 'process_id', 'occurrence_process_id', 'product_id', 'product_code', 'product_name', 'event_type', 'qty', 'recorded_at', 'plan_date', 'disposition_status', 'return_qty', 'reason'),
    't_overtime_application': ('id', 'work_date', 'application_type', 'hours', 'midnight_hours', 'team_id', 'status'),
    't_order': ('id', 'order_type', 'order_date', 'freeze_from', 'status'),
    't_order_line': ('id', 'order_id', 'product_id', 'product_code', 'order_type', 'quantity', 'actual_shipment_qty', 'due_date', 'is_expanded'),
    'm_routing': ('id', 'product_id', 'is_active'),
    # 仕入先名は外部AIへ送る直前に一時ID(仕入先N)へ伏字化される。連絡先の列は個人情報側だけで扱う。
    'm_supplier': ('id', 'supplier_code', 'supplier_name', 'supplier_type'),
    'v_ai_purchase_receipt': (
        'id', 'arrival_date', 'registered_at', 'supplier_id', 'line_id',
        'product_id', 'product_code', 'product_name', 'qty', 'process_id', 'input_source',
    ),
}

# LLMへ列と一緒に渡すテーブルの業務上の意味。実データで確認した定義だけを書く。
TABLE_NOTES = {
    't_process_realtime_record': (
        '工程実績。record_type=PRODUCTION が生産実績、record_type=PURCHASE が仕入の入荷実績。'
        'SCRAP(仕損)・EQUIPMENT_STATE・OPERATOR_ACTION も同じ表に入るため、record_type を指定せずに qty を合計してはいけない。'
        '生産数は集計ツール、入荷数は v_ai_purchase_receipt を使う。'
    ),
    'v_ai_purchase_receipt': (
        '仕入の入荷実績(仕入れ実績入力・検収・スマホ検収)だけを抜き出したビュー。1行=1回の入荷登録。'
        '入荷数量は qty、入荷日は arrival_date(実際に入荷した日)、registered_at はシステム登録日時。'
        '検収は入荷時に登録するので同じ日だが、実績入力は後から入力できるので異なることがある。'
        '日別・期間の集計は必ず arrival_date を使う。supplier_id は m_supplier.id、line_id は m_line.id、product_id は m_product.id。'
        'input_source は登録元(PURCHASE_ACTUAL_INPUT=実績入力、PURCHASE_RECEIVING=検収、PURCHASE_RECEIVING_MOBILE=スマホ検収)。'
    ),
    'brake_line_record': (
        'ブレーキ・スポットの作業記録。1行=1操作(operator_action)。'
        '生産数は operator_action が END(終了) と PAUSE(中断) の qty 合計(作業区間ごとの加工数で重複しない)。'
        'START・RESUME・TEMP_END は qty=0 で生産数に含めない。中断件数は PAUSE・TEMP_END の件数。'
    ),
    'm_supplier': '仕入先マスタ。supplier_type は仕入先の区分。',
    'm_line': 'ラインマスタ。line_type は PROD=生産、PURCHASE=購買、OUTSOURCE=外作、OTHER=その他。',
}

# 個人情報を扱う権限を持つ利用者だけに追加公開する列。DeepSeekへは一時IDへ伏字化して渡す。
PERSONAL_SQL_COLUMNS = {
    'm_customer': ('id', 'customer_code', 'customer_name', 'short_name', 'is_active'),
    'm_supplier': ('id', 'supplier_code', 'supplier_name', 'supplier_type', 'contact_person', 'phone_number', 'order_email'),
    't_process_realtime_record': ('operator_name', 'batch_no', 'remarks'),
    'brake_line_record': ('operator',),
    't_scrap_record': ('decided_by', 'reason_detail', 'batch_no', 'operator_name', 'remarks'),
    't_order': ('customer_id', 'order_no'),
    't_order_line': ('customer_order_no', 'ship_to_code', 'remark'),
}

SCREEN_SQL_TABLES = {
    'ai_home': frozenset(set(BASE_SQL_SCHEMA) | set(PERSONAL_SQL_COLUMNS)),
    'orders': frozenset({'m_customer', 'm_product', 'm_routing', 't_order', 't_order_line'}),
    'production': frozenset({'m_product', 'm_line', 'm_process', 'm_calendar_day', 't_process_realtime_record', 't_laser_actual', 't_laser_actual_detail', 'brake_line_record'}),
    'quality': frozenset({'m_product', 'm_line', 'm_process', 't_scrap_record'}),
    'overtime': frozenset({'t_overtime_application'}),
    'purchase': frozenset({'m_supplier', 'm_product', 'm_line', 'm_calendar_day', 'v_ai_purchase_receipt'}),
    'shipping': frozenset(),
    'inventory': frozenset(),
}

FORBIDDEN_SQL = re.compile(
    r'\b(?:INSERT|UPDATE|DELETE|REPLACE|MERGE|CREATE|ALTER|DROP|TRUNCATE|GRANT|REVOKE|'
    r'CALL|EXEC(?:UTE)?|SET|USE|SHOW|DESCRIBE|EXPLAIN|HANDLER|LOAD|INTO|OUTFILE|DUMPFILE|'
    r'LOCK|UNLOCK|FOR\s+UPDATE|SLEEP)\b',
    re.IGNORECASE,
)
SENSITIVE_IDENTIFIER = re.compile(
    r'\b(?:password|email|phone|contact|address|username|user_name|order_no|customer_order_no|'
    r'operator|operator_name|applicant|approver|created_by|updated_by|remarks|comment|signature|'
    r'batch_no|reason_detail|rejection_reason)\b',
    re.IGNORECASE,
)
SQL_KEYWORDS = {
    'select', 'distinct', 'from', 'join', 'inner', 'left', 'right', 'outer', 'cross', 'on', 'where',
    'and', 'or', 'not', 'is', 'null', 'in', 'between', 'like', 'as', 'group', 'by', 'order', 'asc', 'desc',
    'limit', 'having', 'with', 'case', 'when', 'then', 'else', 'end', 'true', 'false', 'interval', 'day',
    'count', 'sum', 'avg', 'min', 'max', 'coalesce', 'date', 'cast', 'decimal', 'signed',
}


def _schema_for_table(table, allow_personal_data=False):
    columns = list(BASE_SQL_SCHEMA.get(table, ()))
    if allow_personal_data:
        columns.extend(PERSONAL_SQL_COLUMNS.get(table, ()))
    return tuple(dict.fromkeys(columns))


def schema_text(screen_id, allow_personal_data=False):
    """LLMへ渡す、画面領域に限定したSQL辞書。列に加えてテーブルの業務上の意味も渡す。"""
    tables = SCREEN_SQL_TABLES.get(screen_id, frozenset())
    lines = []
    for table in sorted(tables):
        columns = _schema_for_table(table, allow_personal_data)
        if not columns:
            continue
        line = f"- {table}: {', '.join(columns)}"
        if TABLE_NOTES.get(table):
            line += f"\n  意味: {TABLE_NOTES[table]}"
        lines.append(line)
    return '\n'.join(lines) or 'この画面ではSQL照会を公開していません。'


def _without_literals(sql):
    return re.sub(r"'(?:''|[^'])*'|\"(?:\"\"|[^\"])*\"", "''", sql)


def _validate_sql(sql, allowed_tables, max_rows, allow_personal_data=False):
    statement = str(sql or '').strip()
    if not statement:
        return None, 'SQLを指定してください。'
    if ';' in statement or '--' in statement or '/*' in statement or '*/' in statement or '#' in statement:
        return None, '複数文・コメントを含むSQLは実行できません。'
    if not re.match(r'^SELECT\b', statement, re.IGNORECASE):
        return None, 'SELECTで始まる読み取り専用SQLだけ実行できます。'
    if FORBIDDEN_SQL.search(_without_literals(statement)):
        return None, '更新・削除・DDL・管理SQLは実行できません。'
    if not allow_personal_data and SENSITIVE_IDENTIFIER.search(_without_literals(statement)):
        return None, '個人情報・連絡先・受注番号・備考などの列はSQLで参照できません。'
    if re.search(r'\bSELECT\s+(?:DISTINCT\s+)?(?:[A-Za-z_]\w*\.)?\*|,\s*(?:[A-Za-z_]\w*\.)?\*', statement, re.IGNORECASE):
        return None, 'ワイルドカード（*）は使えません。AI用DB辞書の列を明示してください。'

    tables = [match.group(1).strip('`') for match in re.finditer(r'\b(?:FROM|JOIN)\s+`?([A-Za-z_]\w*)`?', statement, re.IGNORECASE)]
    if not tables:
        return None, 'FROM句を含むSQLを指定してください。'
    unknown_tables = sorted(set(tables) - set(allowed_tables))
    if unknown_tables:
        return None, f"この画面で参照できないテーブルです: {', '.join(unknown_tables)}"

    aliases = set(re.findall(r'\b(?:FROM|JOIN)\s+`?[A-Za-z_]\w*`?\s+(?:AS\s+)?([A-Za-z_]\w*)', statement, re.IGNORECASE))
    allowed_identifiers = set(SQL_KEYWORDS) | set(allowed_tables) | aliases
    for table in allowed_tables:
        allowed_identifiers.update(_schema_for_table(table, allow_personal_data))
    scrubbed = _without_literals(statement).replace('`', '')
    scrubbed = re.sub(r'\bAS\s+[A-Za-z_]\w*', 'AS', scrubbed, flags=re.IGNORECASE)
    unknown_identifiers = {
        token.lower()
        for token in re.findall(r'\b([A-Za-z_]\w*)\b', scrubbed)
        if token.lower() not in {item.lower() for item in allowed_identifiers}
    }
    if unknown_identifiers:
        return None, f"AI用DB辞書にない列・識別子が含まれます: {', '.join(sorted(unknown_identifiers))}"

    limit_match = re.search(r'\bLIMIT\s+(\d+)\b', statement, re.IGNORECASE)
    if limit_match and int(limit_match.group(1)) > max_rows:
        return None, f'LIMITは{max_rows}件以下にしてください。'
    if not limit_match:
        statement = f'{statement} LIMIT {max_rows}'
    return statement, None


def _serialize_value(value):
    if isinstance(value, Decimal):
        return float(value)
    if hasattr(value, 'isoformat'):
        return value.isoformat()
    return value


def execute_readonly_sql(arguments, screen_context, allow_personal_data=False, redactor=None):
    """SQLを検査してAI専用読み取り接続で実行し、最大行数の集計・参照結果だけを返す。"""
    policy = get_data_policy()
    allowed_tables = SCREEN_SQL_TABLES.get(screen_context['id'], frozenset())
    statement, error = _validate_sql(
        arguments.get('sql'), allowed_tables, policy.max_external_result_rows, allow_personal_data,
    )
    if error:
        return {'status': 'invalid_request', 'detail': error}, None, None
    try:
        with connections[AI_DB_ALIAS].cursor() as cursor:
            cursor.execute(statement)
            columns = [column[0] for column in cursor.description]
            rows = [
                {column: _serialize_value(value) for column, value in zip(columns, row)}
                for row in cursor.fetchmany(policy.max_external_result_rows)
            ]
    except Exception as exc:
        return {'status': 'invalid_request', 'detail': f'読み取りSQLを実行できませんでした: {str(exc)[:160]}'}, None, None
    if redactor and allow_personal_data:
        personal_columns = {column for columns in PERSONAL_SQL_COLUMNS.values() for column in columns}
        replacement_index = 1 + sum(
            1 for _, replacement in redactor.replacements if str(replacement).startswith('照会情報')
        )
        for row in rows:
            for column, value in row.items():
                if column not in personal_columns or not isinstance(value, str) or not value.strip():
                    continue
                redactor.add(value, f'照会情報{replacement_index}')
                row[column] = redactor.redact_text(value)
                replacement_index += 1
    return {
        'status': 'ok',
        'source': 'AI用DB辞書の読み取り専用SQL',
        'tables': sorted(set(re.findall(r'\b(?:FROM|JOIN)\s+`?([A-Za-z_]\w*)`?', statement, re.IGNORECASE))),
        'row_count': len(rows),
        'rows': rows,
        'executed_sql': statement,
    }, None, None
