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
}


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
    return warnings


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
        if ANALYSIS_VIEWS[view]['date_field'] not in fields:
            raise AnalysisError('対象期間の根拠となる日付フィールドが必要です。')
    return datasets


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
                date_field = ANALYSIS_VIEWS[view]['date_field']
                cursor.execute(
                    f'SELECT COUNT(*) FROM `{view}` WHERE `{date_field}` >= %s AND `{date_field}` <= %s',
                    [proposal['date_from'], proposal['date_to']],
                )
                counts.append({'view': view, 'rows': cursor.fetchone()[0]})
    except DatabaseError as exc:
        raise AnalysisError('対象件数を確認できません。分析用DB接続・ビュー定義者・SELECT権限を管理者へ確認してください。', 503) from exc
    return {'datasets': counts, 'total_rows': sum(item['rows'] for item in counts), 'counted_at': datetime.now().isoformat()}
