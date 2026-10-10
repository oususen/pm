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
    'm_bom': ('id', 'parent_product_id', 'version', 'valid_from', 'valid_to', 'is_active', 'is_coproduct'),
    'm_bom_item': (
        'id', 'bom_id', 'child_product_id', 'quantity', 'loss_rate', 'sourcing_type',
        'supplier_id', 'process_id', 'line_id', 'time_unit', 'lead_time_days',
        'duration_min', 'is_coproduct_driver', 'remark',
    ),
    'm_calendar_day': ('id', 'target_date', 'is_working_day', 'work_minutes'),
    't_process_realtime_record': ('id', 'process_id', 'product_id', 'product_code', 'product_name', 'timestamp', 'record_type', 'qty', 'equipment_state'),
    't_laser_actual': ('id', 'work_date', 'operator_action', 'pattern_no', 'equipment_code', 'equipment_name', 'material_code', 'material_name', 'total_process_time'),
    't_laser_actual_detail': ('id', 'actual_id', 'detail_type', 'product_id', 'product_code', 'product_name', 'total_qty', 'scrap_qty', 'scrap_reason'),
    'brake_line_record': ('id', 'plan_date', 'line_id', 'process_id', 'product_id', 'product_code', 'operator_action', 'operator_action_reason', 'qty'),
    't_scrap_record': ('id', 'line_id', 'process_id', 'occurrence_process_id', 'product_id', 'product_code', 'product_name', 'event_type', 'qty', 'recorded_at', 'plan_date', 'disposition_status', 'return_qty', 'reason'),
    't_overtime_application': ('id', 'work_date', 'application_type', 'hours', 'midnight_hours', 'team_id', 'status'),
    't_order': ('id', 'order_type', 'order_date', 'freeze_from', 'status'),
    't_order_line': ('id', 'order_id', 'product_id', 'product_code', 'order_type', 'quantity', 'actual_shipment_qty', 'due_date', 'is_expanded', 'ship_to_code'),
    'm_routing': ('id', 'product_id', 'is_active'),
    # 仕入先名は外部AIへ送る直前に一時ID(仕入先N)へ伏字化される。連絡先の列は個人情報側だけで扱う。
    # 得意先コード・納入場コードはコードであり個人情報ではないため全利用者に公開する(得意先名は個人情報側)。
    'm_customer': ('id', 'customer_code'),
    'm_supplier': ('id', 'supplier_code', 'supplier_name', 'supplier_type'),
    'v_ai_purchase_receipt': (
        'id', 'arrival_date', 'registered_at', 'supplier_id', 'line_id',
        'product_id', 'product_code', 'product_name', 'qty', 'process_id', 'input_source',
    ),
    'v_ai_shipment': (
        'id', 'shipment_date', 'product_code', 'product_id', 'product_name',
        'customer_code', 'ship_to_code', 'quantity', 'trip_allocation_id', 'remark_text',
    ),
    # 品番マスタのビュー(AI用ビュー作成計画 §9。image_url・product_name_halfwidth・is_phantom・self_lt_days・created_at・updated_at は非公開)
    'v_ai_product': (
        'id', 'product_code', 'product_name', 'category', 'unit', 'unit_price', 'standard_lt_days',
        'stock_location', 'processing_area', 'line_id', 'process_id', 'next_process_id', 'management_unit',
        'is_final_product', 'is_line_final_product', 'is_virtual_set', 'order_lot_min', 'order_lot_multiple',
        'is_special_management_material', 'specific_gravity', 'size_length', 'size_width', 'size_thickness',
        'transfer_destination', 'model_name', 'identification_code', 'product_group_id', 'used_container_id',
        'capacity', 'is_active',
    ),
    # 工程マスタのビュー(AI用ビュー作成計画 §13。is_outsource・created_at・updated_at は非公開)
    'v_ai_process': (
        'id', 'process_code', 'process_name', 'line_id', 'management_unit', 'operating_rate',
        'equipment_count', 'two_person_only', 'is_active',
    ),
    # ラインマスタのビュー(AI用ビュー作成計画 §15。lead_time_days・use_direct_process・created_at・updated_at は非公開)
    'v_ai_line': ('id', 'line_code', 'line_name', 'calendar_id', 'line_type', 'is_active'),
    # 仕入先マスタのビュー(AI用ビュー作成計画 §17。contact_person・phone_number・order_email は個人名・連絡先のため非公開)
    'v_ai_supplier': ('id', 'supplier_code', 'supplier_name', 'supplier_type', 'calendar_id'),
    # 得意先マスタのビュー(AI用ビュー作成計画 §21。created_at・updated_at は非公開)
    'v_ai_customer': ('id', 'customer_code', 'customer_name', 'short_name', 'calendar_id', 'is_active'),
    # 稼働カレンダのビュー(AI用ビュー作成計画 §24。m_calendar_day に m_calendar を LEFT JOIN。note・created_at・updated_at と、m_calendar の他の列は非公開)
    'v_ai_calendar_day': (
        'id', 'calendar_id', 'calendar_code', 'calendar_name', 'calendar_type', 'target_date',
        'is_working_day', 'is_delivery_day', 'is_order_day', 'is_holiday_work', 'work_minutes', 'work_pattern_id',
    ),
    # BOM明細のビュー(AI用ビュー作成計画 §25。m_bom_item に m_bom・m_product・m_process・m_line・m_supplier を LEFT JOIN。
    # remark・created_at・updated_at と、結合先のコード・名称以外の列は非公開)
    'v_ai_bom_item': (
        'id', 'bom_id', 'parent_product_id', 'parent_product_code', 'parent_product_name',
        'bom_version', 'bom_valid_from', 'bom_valid_to', 'bom_is_active', 'bom_is_coproduct',
        'child_product_id', 'child_product_code', 'child_product_name', 'quantity', 'loss_rate', 'sourcing_type',
        'supplier_id', 'supplier_code', 'supplier_name', 'process_id', 'process_code', 'process_name',
        'line_id', 'line_code', 'line_name', 'time_unit', 'lead_time_days', 'duration_min', 'is_coproduct_driver',
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
    'v_ai_shipment': (
        '出荷実績(t_shipment_actual)のビュー。1行=1回の出荷実績登録。出荷数は quantity、出荷日は shipment_date。'
        '日別・期間の集計は shipment_date を使う。customer_code は得意先コード、ship_to_code は納入場コード。'
        'trip_allocation_id は出荷便割付のID(なければNULL)、remark_text はシステムが書く便の割付情報(例: [TRIP_ACTUAL]54:576|PD=2026-07-22:42)で業務メモではない。'
        '現在はクボタ(得意先コード000196)向けの出荷だけが登録されている。'
    ),
    'v_ai_product': (
        '品番マスタ(m_product)のビュー。1行=1品番(全行。無効な品番も含むため、有効な品番だけを見るときは is_active=1 で絞る)。'
        'product_code は品番コード(一意)、product_name は製品名。実績ビューの product_id は、このビューの id と結べる。'
        'category は品番の区分(値: ASSEMBLY・OUTSOURCED・SINGLE・PURCHASED・UNKNOWN・MATERIAL と空。各値の業務上の意味は未確認)。'
        'unit_price は単価で、空(NULL)の品番が多い。line_id・process_id も空の品番がある(line_id は m_line.id、process_id は m_process.id)。'
        'management_unit は項目名が管理区分で、値は DAY・MINUTE・空(業務上の意味は未確認)。'
        '発注量は、不足数を order_lot_multiple(発注倍数)の倍数に切り上げ、order_lot_min(最小発注数)未満なら最小発注数にする(自動発注提案仕様書)。'
        'size_length・size_width・size_thickness は項目名が縦(mm)・横(mm)・厚さ(mm)(業務上の定義は未確認)。'
    ),
    'v_ai_process': (
        '工程マスタ(m_process)のビュー。1行=1工程(全行。無効な工程も含むため、有効な工程だけを見るときは is_active=1 で絞る)。'
        'process_code は工程の特定に使うコード(先頭ゼロを含む文字列。例 0801。数字として扱わない)。工程の特定にはコードを使う。'
        'process_code の G と PURCHASE は実際の工程ではなく、BOM・ルーティングを作るときに、外作(G)・購買(PURCHASE)を示すための工程。'
        'line_id は工程の所属ライン(m_line.id と結べる)。'
        'management_unit は DAY=日単位管理、MINUTE=分単位管理。'
        'equipment_count は設備台数(工程負荷は、工程負荷時間を設備台数で按分する)。'
        'operating_rate は項目名が稼働率(%)、two_person_only は項目名が2人1設備専用(どちらも業務上の定義は未確認)。'
    ),
    'v_ai_line': (
        'ラインマスタ(m_line)のビュー。1行=1ライン(全行。無効なラインも含むため、有効なラインだけを見るときは is_active=1 で絞る)。'
        'line_code はラインのコード(先頭ゼロを含む文字列。例 000044。数字として扱わない)。'
        'line_type は PROD=社内ライン(社内だけに絞るときに使う)、'
        'PURCHASE=仕入先の購買ライン(外作先・購入先のライン。社内ライン以外。line_code が仕入先コード、line_name が仕入先の会社名。'
        '仕入先マスタとは、line_code と仕入先の supplier_code を同じ文字列で結ぶ)、'
        'OUTSOURCE=外作ライン(現在は使っていない。削除予定)、OTHER=クボタ納期調整(意味の文章は未確認)。'
        'calendar_id はラインの勤務カレンダ(稼働カレンダの calendar_id と結べる。空のラインがある)。'
        'is_active は有効(1)・無効(0)。工程は m_process の line_id(v_ai_process の line_id)でラインに結べる。'
    ),
    'v_ai_supplier': (
        '仕入先マスタ(m_supplier)のビュー。1行=1仕入先(全行。is_active の列はない)。'
        'supplier_code は仕入先コード(先頭ゼロを含む文字列。例 000044。英字で始まるもの G00001 もある。数字として扱わない)、supplier_name は仕入先名(会社名)。'
        'supplier_type は purchase=購入、outsource=外作、both=両方(購入先・外作先を分けるときに使う)。'
        'calendar_id は仕入先専用カレンダー(稼働カレンダの calendar_id と結べる。空の仕入先が多い)。'
        'id は仕入先のID(入荷実績ビュー v_ai_purchase_receipt の supplier_id と結べる)。'
        '購買ライン(v_ai_line の line_type=PURCHASE)とは、仕入先の supplier_code とラインの line_code を同じ文字列で結ぶ(1対1)。'
    ),
    'v_ai_customer': (
        '得意先マスタ(m_customer)のビュー。1行=1得意先(全行。無効な得意先も含むため、有効な得意先だけを見るときは is_active=1 で絞る)。'
        'customer_code は得意先コード(先頭ゼロを含む文字列。数字として扱わない。出荷実績ビュー v_ai_shipment の customer_code と同じ文字列で結べる)、'
        'customer_name は得意先名(会社名)、short_name は略称。'
        'calendar_id は得意先のカレンダ(稼働カレンダの calendar_id と結べる)。'
        'is_active は有効(1)・無効(0)。'
    ),
    'v_ai_calendar_day': (
        '稼働カレンダ(m_calendar_day にカレンダマスタ m_calendar の属性を付けたビュー)。1行=1つのカレンダの1日。日別・期間の集計は target_date を使う。'
        'calendar_id はカレンダのID(ラインビュー v_ai_line・仕入先ビュー v_ai_supplier・得意先ビュー v_ai_customer の calendar_id と結べる)、'
        'calendar_code はカレンダコード、calendar_name はカレンダ名。'
        'calendar_type は INTERNAL=社内、SUPPLIER=仕入れ、COMPANY=会社、CUSTOMER=顧客、OTHER=その他(各区分の業務上の意味は未確認)。'
        'is_working_day は稼働日(1)か否(0)か。is_delivery_day は納入日、is_order_day は発注日、is_holiday_work は休日出勤で、いずれも 1 か 0。'
        'work_minutes は稼働分(分。空の行がありうる)、work_pattern_id は勤務パターンのID(空の行がありうる)。'
        'is_delivery_day・is_order_day・is_holiday_work・work_pattern_id の業務上の意味は未確認(項目名のみ)。'
    ),
    'v_ai_bom_item': (
        'BOM明細(m_bom_item にBOMヘッダ m_bom と、品番・工程・ライン・仕入先のコード・名称を付けたビュー)。1行=BOM明細1行(全行。日付の列はなく、期間では絞らない)。'
        '明細が1行もないBOMはこのビューに出ないので、このビューでBOMの件数(bom_idの種類数)を数えると、実際より少ない。'
        'bom_id はBOMヘッダのID。parent_product_id は親品番のID、child_product_id は子品番のIDで、どちらも品番マスタビュー v_ai_product の id と結べる'
        '(コードと名称は parent_product_code・parent_product_name、child_product_code・child_product_name)。'
        'bom_version は版(v1・v2・v_auto_… の3種類。v_auto_… は自動で作ったBOM)。数字の大小で最新を決めない。最新のBOMは、版ではなく有効開始日 bom_valid_from で決める。'
        'bom_valid_to は有効終了日(空は期限なし)、bom_is_active は有効(1)か無効(0)か。'
        'bom_is_coproduct は連産品BOM(1つの工程で複数の製品が同時に生産されるBOM。親品番は仮想セット品番)で、1か0。'
        'is_coproduct_driver は連産品代表品(連産親品番から代表の子品番を決めるときに使う)で、1か0。'
        'quantity は親品番1個あたりの子品番の数量(員数)。行をまたいで合計しても業務上の意味はない。'
        'loss_rate はロス率(比率で、%ではない)。空でないとき、数量に (1+ロス率) を掛ける。'
        'sourcing_type は調達区分で、MAKE=自社製造、BUY=購買、SUBCON=外注。BUY(購買)は仕入先があり、SUBCON(外注)は仕入先が必ずある。'
        'supplier_id は仕入先マスタビュー v_ai_supplier の id、process_id は工程マスタビュー v_ai_process の id、'
        'line_id はラインマスタビュー v_ai_line の id と結べる(supplier_id・process_id・line_id は空の行がありうる)。'
        'process_code の G は外作、PURCHASE は購買を示すための工程で、実際の工程ではない。'
        'time_unit は時間単位(DAY=日、MINUTE=分)。どちらの行も、リードタイム lead_time_days(日)と加工時間(サイクル時間)duration_min(分)の両方を持つ(duration_min は空の行がありうる)。'
        'lead_time_days が0の行はありうる(0は有効な値)。lead_time_days は親→子の需要日をずらすときに使う。'
        'BUY・SUBCON の明細での工程・ラインの業務上の意味、およびサイクル時間の入力ルールは未確認。'
    ),
    'brake_line_record': (
        'ブレーキ・スポットの作業記録。1行=1操作(operator_action)。'
        '生産数は operator_action が END(終了) と PAUSE(中断) の qty 合計(作業区間ごとの加工数で重複しない)。'
        'START・RESUME・TEMP_END は qty=0 で生産数に含めない。中断件数は PAUSE・TEMP_END の件数。'
    ),
    'm_supplier': '仕入先マスタ。supplier_type は仕入先の区分。',
    'm_line': 'ラインマスタ。line_type は PROD=生産、PURCHASE=購買、OUTSOURCE=外作、OTHER=その他。',
    'm_bom': (
        'BOMヘッダ。parent_product_id は m_product.id。BOMの有効期間は valid_from から valid_to までで、'
        'valid_to がNULLの場合は終了日なし。'
    ),
    'm_bom_item': (
        'BOM明細。bom_id は m_bom.id、child_product_id は m_product.id。quantity は親製品1個当たりの必要数。'
        'sourcing_type は MAKE=自社製造、BUY=購買、SUBCON=外注。'
        'supplier_id、process_id、line_id はそれぞれ対応するマスタのID。remark は明細備考。'
    ),
}

# 個人情報を扱う権限を持つ利用者だけに追加公開する列。DeepSeekへは一時IDへ伏字化して渡す。
PERSONAL_SQL_COLUMNS = {
    'm_customer': ('id', 'customer_name', 'short_name', 'is_active'),
    'm_supplier': ('id', 'supplier_code', 'supplier_name', 'supplier_type', 'contact_person', 'phone_number', 'order_email'),
    't_process_realtime_record': ('operator_name', 'batch_no', 'remarks'),
    'brake_line_record': ('operator',),
    't_scrap_record': ('decided_by', 'reason_detail', 'batch_no', 'operator_name', 'remarks'),
    't_order': ('customer_id', 'order_no'),
    't_order_line': ('customer_order_no', 'remark'),
}

SCREEN_SQL_TABLES = {
    'ai_home': frozenset(set(BASE_SQL_SCHEMA) | set(PERSONAL_SQL_COLUMNS)),
    'orders': frozenset({'m_customer', 'm_product', 'm_routing', 't_order', 't_order_line'}),
    'production': frozenset({'m_product', 'm_line', 'm_process', 'm_calendar_day', 't_process_realtime_record', 't_laser_actual', 't_laser_actual_detail', 'brake_line_record'}),
    'quality': frozenset({'m_product', 'm_line', 'm_process', 't_scrap_record'}),
    'overtime': frozenset({'t_overtime_application'}),
    'purchase': frozenset({'m_supplier', 'm_product', 'm_line', 'm_calendar_day', 'v_ai_purchase_receipt'}),
    'shipping': frozenset({'m_product', 'm_calendar_day', 'v_ai_shipment'}),
    'inventory': frozenset(),
    'masters': frozenset({'m_product', 'm_bom', 'm_bom_item', 'm_process', 'm_line', 'm_supplier'}),
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


def allowed_tables_for_screen(screen_id, cross_screen_ids=()):
    """起点画面と、その質問で承認された横断領域のテーブルだけを返す。"""
    tables = set(SCREEN_SQL_TABLES.get(screen_id, frozenset()))
    for cross_screen_id in cross_screen_ids or ():
        tables.update(SCREEN_SQL_TABLES.get(cross_screen_id, frozenset()))
    return frozenset(tables)


def schema_text(screen_id, allow_personal_data=False, cross_screen_ids=()):
    """LLMへ渡す、画面領域に限定したSQL辞書。列に加えてテーブルの業務上の意味も渡す。"""
    tables = allowed_tables_for_screen(screen_id, cross_screen_ids)
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
    allowed_tables = allowed_tables_for_screen(
        screen_context['id'], screen_context.get('cross_screen_ids', ()),
    )
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
