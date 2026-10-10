"""公開済みビューだけを対象に、承認画面用の件数を確認する。明細は取得しない。"""
import re
from datetime import date, datetime

from django.conf import settings
from django.db import connections, DatabaseError

from ai.services.analysis_plan_store import AnalysisError
from ai.services.sql_queries import BASE_SQL_SCHEMA


# 公開列は既存辞書から取得するが、元テーブル・業務固有の実データ注記は公開しない。
ANALYSIS_VIEWS = {
    'v_ai_purchase_receipt': {
        'label': '入荷実績', 'date_field': 'arrival_date', 'quantity_field': 'qty',
        'description': (
            '1行は1回の入荷登録。日別・期間集計は実際の入荷日arrival_dateを使う。'
            '列の意味: arrival_date=入荷日(実際に入荷した日)、registered_at=システムの登録日時、qty=入荷数量、product_code=品番、product_name=製品名、'
            'supplier_id=仕入先(外作先)のID、line_id=ラインのID、product_id=製品のID、'
            'input_source=登録元(PURCHASE_ACTUAL_INPUT=実績入力、PURCHASE_RECEIVING=検収、PURCHASE_RECEIVING_MOBILE=スマホ検収)。'
        ),
    },
    'v_ai_shipment': {
        'label': '出荷実績', 'date_field': 'shipment_date', 'quantity_field': 'quantity',
        'description': (
            '1行は1回の出荷実績登録。日別・期間集計はshipment_dateを使う。'
            '列の意味: shipment_date=出荷日、quantity=出荷数量、product_code=品番、product_name=製品名、product_id=製品のID、'
            'customer_code=得意先(顧客・客先・出荷先)のコード、ship_to_code=納入場(納入地)のコード。'
            '納入場・納入地ごとの集計はship_to_codeを使い、顧客・得意先ごとの集計はcustomer_codeを使う(2つは別の列で、混同しない)。'
            'trip_allocation_id=出荷便割付のID、remark_text=システムが書く便の割付情報(業務メモではない)。'
        ),
    },
    # 品番マスタ。日付の列を持たないため、date_field=None(期間で絞らず全行を取得する)。数量の列もないため、quantity_field=None。
    # 列の意味は、仕様書で確認できたものだけを書く(AI用ビュー作成計画 §4.1-1)。
    'v_ai_product': {
        'label': '品番マスタ', 'date_field': None, 'quantity_field': None,
        'description': (
            '1行は1品番(品番マスタ)。日付の列がなく、期間では絞らず全行が対象。無効な品番も含むため、有効な品番だけを見るときはis_active=1で絞る。'
            '実績ビューのproduct_idは、このビューのidと結べる(出荷・入荷の実績ビューは、品番コードproduct_codeでも結べる)。'
            '列の意味: id=品番のID、product_code=品番コード(一意)、product_name=製品名、'
            'category=品番の区分(値はASSEMBLY・OUTSOURCED・SINGLE・PURCHASED・UNKNOWN・MATERIALと空。各値の業務上の意味は未確認)、'
            'unit_price=単価(空の品番が多い)、line_id=ラインのID(空の品番がある)、process_id=工程のID(空の品番がある)、'
            'order_lot_multiple=発注倍数、order_lot_min=最小発注数(発注量は、不足数を発注倍数の倍数に切り上げ、最小発注数未満なら最小発注数にする)、'
            'transfer_destination=移動先、is_virtual_set=仮想セット品番(連産品)、is_active=有効(1)か無効(0)か、'
            'size_length・size_width・size_thickness=項目名が縦(mm)・横(mm)・厚さ(mm)、management_unit=項目名が管理区分(値はDAY・MINUTE・空)。'
            '上記以外の列(unit・standard_lt_days・stock_location・processing_area・next_process_id・is_final_product・is_line_final_product・'
            'is_special_management_material・specific_gravity・model_name・identification_code・product_group_id・used_container_id・capacity)の業務上の意味は未確認。'
            'size_*・management_unitも、項目名以外の業務上の定義は未確認。'
        ),
    },
    # 工程マスタ。日付・数量の列を持たないため、date_field=None・quantity_field=None(AI用ビュー作成計画 §13)。
    'v_ai_process': {
        'label': '工程マスタ', 'date_field': None, 'quantity_field': None,
        'description': (
            '1行は1工程(工程マスタ)。日付の列がなく、期間では絞らず全行が対象。無効な工程も含むため、有効な工程だけを見るときはis_active=1で絞る。'
            '工程の特定にはprocess_code(工程コード)を使う。'
            '列の意味: id=工程のID、process_code=工程コード(先頭ゼロを含む文字列。例0801。数字として扱わない。GとPURCHASEは実際の工程ではなく、BOM・ルーティングを作るときに、外作(G)・購買(PURCHASE)を示すための工程)、'
            'process_name=工程名、line_id=工程の所属ラインのID(m_lineのidと結べる)、'
            'management_unit=管理単位(DAY=日単位管理、MINUTE=分単位管理)、'
            'equipment_count=設備台数(工程負荷は工程負荷時間を設備台数で按分する)、is_active=有効(1)か無効(0)か、'
            'operating_rate=項目名が稼働率(%)、two_person_only=項目名が2人1設備専用(operating_rate・two_person_onlyは業務上の定義は未確認)。'
        ),
    },
    # ラインマスタ。日付・数量の列を持たないため、date_field=None・quantity_field=None(AI用ビュー作成計画 §15)。
    'v_ai_line': {
        'label': 'ラインマスタ', 'date_field': None, 'quantity_field': None,
        'description': (
            '1行は1ライン(ラインマスタ)。日付の列がなく、期間では絞らず全行が対象。無効なラインも含むため、有効なラインだけを見るときはis_active=1で絞る。'
            '列の意味: id=ラインのID、line_code=ラインコード(先頭ゼロを含む文字列。例000044。数字として扱わない)、line_name=ライン名、'
            'calendar_id=ラインの勤務カレンダ(稼働カレンダのcalendar_idと結べる。空のラインがある)、'
            'line_type=ラインの種別(PROD=社内ライン。社内だけに絞るときに使う。'
            'PURCHASE=仕入先の購買ライン。外作先・購入先のライン、社内ライン以外で、line_codeが仕入先コード、line_nameが仕入先の会社名。'
            '仕入先マスタとは、line_codeと仕入先のsupplier_codeを同じ文字列で結ぶ。'
            'OUTSOURCE=外作ライン。現在は使っていない・削除予定。OTHER=クボタ納期調整。意味の文章は未確認)、'
            'is_active=有効(1)か無効(0)か。工程はm_processのline_id(v_ai_processのline_id)でラインに結べる。'
        ),
    },
    # 仕入先マスタ。日付・数量の列を持たないため、date_field=None・quantity_field=None(AI用ビュー作成計画 §17)。
    'v_ai_supplier': {
        'label': '仕入先マスタ', 'date_field': None, 'quantity_field': None,
        'description': (
            '1行は1仕入先(仕入先マスタ)。日付の列がなく、期間では絞らず全行が対象。is_activeの列はなく、全仕入先が対象。'
            '列の意味: id=仕入先のID(入荷実績ビューv_ai_purchase_receiptのsupplier_idと結べる)、'
            'supplier_code=仕入先コード(先頭ゼロを含む文字列。例000044。英字で始まるものG00001もある。数字として扱わない)、'
            'supplier_name=仕入先名(会社名)、'
            'supplier_type=仕入先の区分(purchase=購入、outsource=外作、both=両方。購入先・外作先を分けるときに使う)、'
            'calendar_id=仕入先専用カレンダー(稼働カレンダのcalendar_idと結べる。空の仕入先が多い)。'
            '購買ライン(v_ai_lineのline_type=PURCHASE)とは、仕入先のsupplier_codeとラインのline_codeを同じ文字列で結ぶ(1対1)。'
        ),
    },
    # 得意先マスタ。日付・数量の列を持たないため、date_field=None・quantity_field=None(AI用ビュー作成計画 §21)。
    'v_ai_customer': {
        'label': '得意先マスタ', 'date_field': None, 'quantity_field': None,
        'description': (
            '1行は1得意先(得意先マスタ)。日付の列がなく、期間では絞らず全行が対象。無効な得意先も含むため、有効な得意先だけを見るときはis_active=1で絞る。'
            '列の意味: id=得意先のID、'
            'customer_code=得意先コード(先頭ゼロを含む文字列。数字として扱わない。出荷実績ビューv_ai_shipmentのcustomer_codeと同じ文字列で結べる)、'
            'customer_name=得意先名(会社名)、short_name=略称、'
            'calendar_id=得意先のカレンダ(稼働カレンダのcalendar_idと結べる)、'
            'is_active=有効(1)か無効(0)か。'
        ),
    },
    # 稼働カレンダ(カレンダの日ごと)。日付の列target_dateがあるため、date_field='target_date'(期間で絞る)。数量の列はないため、quantity_field=None(AI用ビュー作成計画 §24)。
    'v_ai_calendar_day': {
        'label': '稼働カレンダ', 'date_field': 'target_date', 'quantity_field': None,
        'description': (
            '1行は1つのカレンダの1日(カレンダ日)。日別・期間の集計は日付target_dateを使い、指定した期間の行だけが対象。'
            'カレンダのコード・名称・区分は、カレンダマスタから付けた属性(行数は変わらない)。'
            '列の意味: id=カレンダ日のID、calendar_id=カレンダのID(ラインビューv_ai_line・仕入先ビューv_ai_supplier・得意先ビューv_ai_customerのcalendar_idと結べる)、'
            'calendar_code=カレンダコード、calendar_name=カレンダ名、'
            'calendar_type=カレンダの区分(INTERNAL=社内、SUPPLIER=仕入れ、COMPANY=会社、CUSTOMER=顧客、OTHER=その他。各区分の業務上の意味は未確認)、'
            'target_date=対象日、is_working_day=稼働日か(1=稼働日、0=稼働日ではない)、is_delivery_day=納入日か(1か0)、'
            'is_order_day=発注日か(1か0)、is_holiday_work=休日出勤か(1か0)、work_minutes=稼働分(分。空の行がありうる)、'
            'work_pattern_id=勤務パターンのID(空の行がありうる)。'
            'is_delivery_day・is_order_day・is_holiday_work・work_pattern_idの業務上の意味は未確認(項目名のみ)。'
        ),
    },
    # BOM明細。日付の列(bom_valid_from・bom_valid_toはBOMの有効期間で実績の日付ではない)・数量の列(quantityは行をまたいで合計しても意味がない)がないため、
    # date_field=None・quantity_field=None(AI用ビュー作成計画 §25)。
    'v_ai_bom_item': {
        'label': 'BOM明細', 'date_field': None, 'quantity_field': None,
        'description': (
            '1行はBOM明細1行(BOM明細にBOMヘッダと、品番・工程・ライン・仕入先のコード・名称を付けたビュー)。日付の列がなく、期間では絞らず全行が対象。'
            '明細が1行もないBOMはこのビューに出ないため、このビューでBOMの件数(bom_idの種類数)を数えると、実際より少ない。'
            '最新のBOMは、版ではなく有効開始日bom_valid_fromで決める。'
            '列の意味: id=BOM明細のID、bom_id=BOMヘッダのID、'
            'parent_product_id・child_product_id=親品番・子品番のID(品番マスタビューv_ai_productのidと結べる)、'
            'parent_product_code・parent_product_name=親品番のコード・名称、child_product_code・child_product_name=子品番のコード・名称、'
            'bom_version=BOMの版(v1・v2・v_auto_…の3種類。v_auto_…は自動で作ったBOM。数字の大小で最新を決めない)、'
            'bom_valid_from=有効開始日、bom_valid_to=有効終了日(空は期限なし)、bom_is_active=有効(1)か無効(0)か、'
            'bom_is_coproduct=連産品BOMか(1か0。1つの工程で複数の製品が同時に生産されるBOM。親品番は仮想セット品番)、'
            'is_coproduct_driver=連産品代表品か(1か0。連産親品番から代表の子品番を決めるときに使う)、'
            'quantity=親品番1個あたりの子品番の数量(員数。行をまたいで合計しても業務上の意味はない)、'
            'loss_rate=ロス率(比率で%ではない。空でないとき、数量に(1+ロス率)を掛ける)、'
            'sourcing_type=調達区分(MAKE=自社製造、BUY=購買、SUBCON=外注。BUYは仕入先があり、SUBCONは仕入先が必ずある)、'
            'supplier_id・supplier_code・supplier_name=仕入先のID・コード・名称(supplier_idは仕入先マスタビューv_ai_supplierのidと結べる。空の行がありうる)、'
            'process_id・process_code・process_name=工程のID・コード・名称(process_idは工程マスタビューv_ai_processのidと結べる。空の行がありうる。'
            'process_codeのGは外作、PURCHASEは購買を示すための工程で、実際の工程ではない)、'
            'line_id・line_code・line_name=ラインのID・コード・名称(line_idはラインマスタビューv_ai_lineのidと結べる。空の行がありうる)、'
            'time_unit=時間単位(DAY=日、MINUTE=分。どちらの行も、リードタイムlead_time_daysと加工時間duration_minの両方を持つ)、'
            'lead_time_days=リードタイム(日。親→子の需要日をずらすときに使う。0の行はありうる。0は有効な値)、'
            'duration_min=加工時間(サイクル時間。分。空の行がありうる)。'
            'BUY・SUBCONの明細での工程・ラインの業務上の意味、およびサイクル時間の入力ルールは未確認。'
        ),
    },
}


def ai_view_definition(view):
    """AI(分析案・相談・コード生成)へ渡すビューの定義。値がNoneのキー(date_field・quantity_field)は出さない。

    日付ありのビューは、従来と同じ内容(キーの順序も同じ)になる。
    """
    return {key: value for key, value in ANALYSIS_VIEWS[view].items() if value is not None}


# 業務の言葉と列の対応表(BOSS承認 2026-10-07)。(対象ビュー, 言葉, 列)。「納入先」は、顧客を指すことも納入場を指すこともあるため、載せない。
TERM_COLUMNS = (
    ('v_ai_shipment', ('納入地', '納入場', '納入場所'), 'ship_to_code'),
    ('v_ai_shipment', ('顧客', '得意先', '客先', '出荷先'), 'customer_code'),
    (None, ('品番', '部番'), 'product_code'),
    (None, ('製品名', '品名'), 'product_name'),
    ('v_ai_shipment', ('出荷日',), 'shipment_date'),
    ('v_ai_shipment', ('出荷数量', '出荷数'), 'quantity'),
    ('v_ai_purchase_receipt', ('入荷日',), 'arrival_date'),
    ('v_ai_purchase_receipt', ('入荷数量', '入荷数'), 'qty'),
    ('v_ai_purchase_receipt', ('仕入先', '外作先'), 'supplier_id'),
)
SHIP_TO_TERMS, CUSTOMER_TERMS = TERM_COLUMNS[0][1], TERM_COLUMNS[1][1]


def term_guide_text(ask_user=False):
    """AI(分析案・相談)へ渡す、言葉と列の対応表の文面。ask_user=True(相談)は、文脈で決められない「納入先」を、利用者に確認させる。"""
    items = ' / '.join(f"{'・'.join(terms)}={column}" for _view, terms, column in TERM_COLUMNS)
    return (
        f'言葉と列の対応: {items}。'
        '「納入先」は対応表にない。'
        + ('文脈から、顧客(customer_code)か納入場(ship_to_code)かが決められないときは、利用者に確認する。' if ask_user
           else '目的や文脈から、顧客(customer_code)か納入場(ship_to_code)かを判断する。')
    )


COLUMN_NEXT_ACTION = '次の操作: 手順を読み、列が合っていれば、そのまま承認します。違っていれば、画面右下の「目的・期間を変更して作り直す」を押し、目的を書き直して、分析案を作り直してください。'


def column_warnings(purpose, proposal):
    """分析案の、目的の言葉と取得する列・手順の食い違いを、警告の文で返す(機械的な検査。AIの出力を直さず、承認前に利用者へ見せる)。"""
    datasets = proposal['datasets']
    warnings = []
    for view, terms, column in TERM_COLUMNS:
        term = next((item for item in terms if item in purpose), None)
        if term is None:
            continue
        related = [d for d in datasets if column in BASE_SQL_SCHEMA[d['view']] and (view is None or d['view'] == view)]
        if related and not any(column in d['fields'] for d in related):
            warnings.append(f'目的の「{term}」に対応する列 {column} が、取得する列に含まれていません。手順が別の列を使っていないか確認してください。')
    text = ' '.join([*proposal['steps'], *proposal['outputs']])
    ship_to, customer = any(t in purpose for t in SHIP_TO_TERMS), any(t in purpose for t in CUSTOMER_TERMS)
    if ship_to and not customer and 'customer_code' in text and 'ship_to_code' not in text:
        warnings.append('目的は納入場(納入地)ですが、手順・出力に customer_code(得意先・顧客のコード)が使われています。集計の列が違う可能性があります(納入場はship_to_code)。')
    if customer and not ship_to and 'ship_to_code' in text and 'customer_code' not in text:
        warnings.append('目的は顧客(得意先)ですが、手順・出力に ship_to_code(納入場のコード)が使われています。集計の列が違う可能性があります(顧客はcustomer_code)。')
    # 次の操作を、文の最後に付ける(BOSS指示 2026-10-08)
    return [warning + COLUMN_NEXT_ACTION for warning in warnings]


# 目的文の「N月」(例: 8月・8月〜9月・8月から9月)。「2か月」「12ヶ月」(月の前が、数字でない)は、含めない
MONTH_RANGE_PATTERN = re.compile(r'(?<![0-9])(1[0-2]|[1-9])月\s*(?:〜|～|~|から|-|ー)\s*(1[0-2]|[1-9])月')
MONTH_PATTERN = re.compile(r'(?<![0-9])(1[0-2]|[1-9])月')


def _mentioned_months(purpose):
    """目的文に書かれた月(1〜12)の集合。「8月〜9月」は、8月と9月(範囲の途中の月も含む。年をまたぐ範囲は、扱わない)。"""
    months = set()
    for start, end in MONTH_RANGE_PATTERN.findall(purpose):
        if int(start) <= int(end):
            months.update(range(int(start), int(end) + 1))
    months.update(int(m) for m in MONTH_PATTERN.findall(purpose))
    return months


# 期間の一部を除く指示(「7月31日までを除く」「7月24日からを除く」)の、片側だけの書き方。区切り(、。改行)までの文で判定する
EXCLUDE_UNTIL_PATTERN = re.compile(r'([^、。,.\n]*?)まで(?:を|は|の分を?)?(?:除|除外)')
EXCLUDE_FROM_PATTERN = re.compile(r'([^、。,.\n]*?)から(?:を|は|の分を?)?(?:除|除外)')
RANGE_MARK_PATTERN = re.compile(r'から|〜|～|~|-|ー')


def exclusion_warnings(purpose):
    """除く期間の、開始日・終了日の片方だけが書かれているとき、警告の文を返す(機械的な検査。AIには補わせない。BOSS承認 2026-10-08)。"""
    warnings = []
    if any(not RANGE_MARK_PATTERN.search(found.group(1)) for found in EXCLUDE_UNTIL_PATTERN.finditer(purpose)):
        warnings.append('除く期間の開始日が書かれていません。「6月30日から7月31日までを除く」のように、開始日も書いてください。次の操作: 画面右下の「目的・期間を変更して作り直す」を押し、目的を書き直して、分析案を作り直してください。')
    if any('まで' not in found.group(1) and not RANGE_MARK_PATTERN.search(found.group(1).replace('から', '', 1)) for found in EXCLUDE_FROM_PATTERN.finditer(purpose)):
        warnings.append('除く期間の終了日が書かれていません。「7月24日から7月31日までを除く」のように、終了日も書いてください。次の操作: 画面右下の「目的・期間を変更して作り直す」を押し、目的を書き直して、分析案を作り直してください。')
    return warnings


def period_warnings(purpose, date_from, date_to):
    """目的文の月と、期間(画面の開始日・終了日)の食い違いを、警告の文で返す(機械的な検査。AIの出力は直さない。BOSS承認 2026-10-08)。

    目的に月が書かれているとき、期間が、その月より広い(別の月も含む)、または、目的の月が期間に含まれない場合に、警告する。月が書かれていなければ、検査しない。
    """
    mentioned = _mentioned_months(purpose)
    if not mentioned:
        return []
    start, end = date.fromisoformat(date_from), date.fromisoformat(date_to)
    period_months, year, month = set(), start.year, start.month
    while (year, month) <= (end.year, end.month):
        period_months.add(month)
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    label = lambda values: '・'.join(f'{m}月' for m in sorted(values))
    warnings = []
    extra = period_months - mentioned
    if extra:
        warnings.append(f'目的に書かれた月（{label(mentioned)}）より、期間（{date_from}〜{date_to}）が広く、{label(extra)}の分も含まれます。期間の欄を、目的に合わせて直してください。次の操作: 画面右下の「目的・期間を変更して作り直す」を押し、期間を直して、分析案を作り直してください。')
    missing = mentioned - period_months
    if missing:
        warnings.append(f'目的に書かれた{label(missing)}が、期間（{date_from}〜{date_to}）に含まれていません。期間の欄を、目的に合わせて直してください。次の操作: 画面右下の「目的・期間を変更して作り直す」を押し、期間を直して、分析案を作り直してください。')
    return warnings


# 重複・欠落の確認に必要な管理列。分析用コンテナへ必ず送る(BOSS承認 2026-10-03)。社外AIには、値を送らない。
MANAGEMENT_COLUMN = 'id'
MANAGEMENT_COLUMN_PURPOSE = '重複・欠落の確認用'


def with_management_columns(datasets):
    """各ビューの取得列へ、管理列(id)を先頭に加える。AIの回答の検証後に、サーバーが加える(AIには、idを指定させない)。"""
    return [{**dataset, 'fields': [MANAGEMENT_COLUMN, *[f for f in dataset['fields'] if f != MANAGEMENT_COLUMN]]} for dataset in datasets]


def validate_period(date_from, date_to):
    try:
        start, end = date.fromisoformat(date_from), date.fromisoformat(date_to)
        if start.isoformat() != date_from or end.isoformat() != date_to or start > end:
            raise ValueError()
    except (TypeError, ValueError):
        raise AnalysisError('対象期間をYYYY-MM-DDで指定し、開始日を終了日以前にしてください。')
    return date_from, date_to


def validate_datasets(datasets, date_from, date_to):
    validate_period(date_from, date_to)
    if not isinstance(datasets, list) or not datasets:
        raise AnalysisError('利用ビューが指定されていません。')
    seen = set()
    for dataset in datasets:
        if not isinstance(dataset, dict) or set(dataset) != {'view', 'fields'}:
            raise AnalysisError('利用ビュー・フィールドの指定が不正です。')
        view = dataset['view']
        if not isinstance(view, str) or view not in ANALYSIS_VIEWS or view in seen:
            raise AnalysisError('未公開または重複したビューは分析できません。')
        seen.add(view)
        fields = dataset['fields']
        if (not isinstance(fields, list) or not fields
                or any(not isinstance(field, str) or field not in BASE_SQL_SCHEMA[view] for field in fields)
                or len(set(fields)) != len(fields)):
            raise AnalysisError('未公開または重複したフィールドは分析できません。')
        date_field = ANALYSIS_VIEWS[view]['date_field']  # 必須キー(日付なしのビューは、明示的にNoneと宣言する。.get()で補わない)
        if date_field is not None and date_field not in fields:
            raise AnalysisError('対象期間の根拠となる日付フィールドが必要です。')
    return datasets


def build_where(view, date_from, date_to, last_id=None):
    """COUNT・取得で共通に使うWHERE句と束縛パラメータを返す。(句, パラメータ)

    日付ありのビューは、期間で絞る(従来と同じ文字列・パラメータ)。日付なしのビュー(date_field=None)は、期間では絞らない。
    last_id を渡すと、idを基準にしたページ送りの条件を加える。条件が無ければ、WHERE自体を付けない。
    """
    date_field = ANALYSIS_VIEWS[view]['date_field']
    conditions, params = [], []
    if date_field is not None:
        conditions.append(f'`{date_field}` >= %s AND `{date_field}` <= %s')
        params += [date_from, date_to]
    if last_id is not None:
        conditions.append('`id` > %s')
        params.append(last_id)
    return (' WHERE ' + ' AND '.join(conditions) if conditions else ''), params


def count_target_rows(proposal):
    """LLMのSQLは実行せず、固定COUNTと束縛パラメータだけを使用する。"""
    datasets = validate_datasets(proposal['datasets'], proposal['date_from'], proposal['date_to'])
    if settings.DATABASES['ai_reader']['USER'] != 'pm_ai_reader':
        raise AnalysisError('分析用DB接続をpm_ai_readerへ設定してください。', 503)
    counts = []
    try:
        with connections['ai_reader'].cursor() as cursor:
            for dataset in datasets:
                view = dataset['view']
                where, params = build_where(view, proposal['date_from'], proposal['date_to'])
                cursor.execute(f'SELECT COUNT(*) FROM `{view}`{where}', params)
                # period_applied: 期間で絞った件数か(日付ありはtrue、日付なし=全行はfalse)。画面の表示用
                counts.append({'view': view, 'rows': cursor.fetchone()[0], 'period_applied': ANALYSIS_VIEWS[view]['date_field'] is not None})
    except DatabaseError as exc:
        raise AnalysisError('対象件数を確認できません。分析用DB接続・ビュー定義者・SELECT権限を管理者へ確認してください。', 503) from exc
    return {'datasets': counts, 'total_rows': sum(item['rows'] for item in counts), 'counted_at': datetime.now().isoformat()}
