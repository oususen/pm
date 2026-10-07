"""テンプレートの変数(段階2-A、BOSS承認 2026-10-05)。

コードの中の「{{名前}}」を、使うときに、確認した値(引用符つきの文字列)へ置き換える。期間は「period_from」「period_to」(分析案の期間に連動)。
- 変数の種類は、TYPESの1か所にまとめる(追加は、ここへの追加)。種類: 日付(期間)・品番・顧客コード・納入先コード
- 日付の変数は、「名前_from」と「名前_to」の組(2026-10-07、BOSS承認)。全体の期間は period_from・period_to(値は分析案の期間に固定)。
  期間を分けて比べる分析(月ごと・前半と後半など)の「比べる期間」は、組を何組でも。値(初期値)は、AIが目的・手順から読み取り、
  サーバーが、形式・開始日<=終了日・全体の期間の中、を確認する。
- 値は、形式(英数字・アンダースコア・ハイフンのみ)と、実在(品番=m_product、顧客コード=m_customer、納入先コード=ビューの実際の値)を確認する。
  形式を絞るため、置き換えた値がSQL・Pythonの文字列を壊すことはない
- 保存するコードに、変数の元の値(品番など)や日付が文字のまま残っていたら、保存を断る(直書きの禁止)
- 変数の個数の上限は設けない(BOSS承認)。フォールバックはない(値が確認できなければ、拒否する)
"""
import re
from datetime import date

from django.conf import settings
from django.db import DatabaseError, connections
from django.db.utils import ConnectionDoesNotExist

from ai.services.analysis_data_service import validate_period
from ai.services.analysis_plan_store import AnalysisError

NAME_PATTERN = re.compile(r'[a-z][a-z0-9_]*')
PLACEHOLDER_PATTERN = re.compile(r'\{\{([a-z][a-z0-9_]*)\}\}')
CODE_VALUE_PATTERN = re.compile(r'[A-Za-z0-9_-]{1,40}')  # fullmatchで使う(末尾の改行を通さない)
DATE_LITERAL_PATTERN = re.compile(r'[0-9]{4}-[0-9]{2}-[0-9]{2}')
DATE_NAME_PATTERN = re.compile(r'[a-z][a-z0-9_]*_(?:from|to)')  # 日付の変数の名前(組: 名前_from と 名前_to)
PERIOD_FROM, PERIOD_TO = 'period_from', 'period_to'
DEFINITION_KEYS = {'name', 'type', 'label', 'default'}


def _exists_product(value):
    from masters.models import Product
    try:
        return Product.objects.filter(product_code=value).exists()
    except DatabaseError as exc:
        raise AnalysisError('品番を確認できません。しばらくしてから、もう一度お試しください。', 503) from exc


def _exists_customer(value):
    from masters.models import Customer
    try:
        return Customer.objects.filter(customer_code=value).exists()
    except DatabaseError as exc:
        raise AnalysisError('顧客コードを確認できません。しばらくしてから、もう一度お試しください。', 503) from exc


def _exists_ship_to(value):
    """納入先コードの正本の表がないため、出荷実績ビューの実際の値で確認する(読み取り専用の分析用接続)。"""
    # 既存の件数確認(count_target_rows)と同じく、分析用の読み取り専用ユーザーでなければ使わない
    if settings.DATABASES.get('ai_reader', {}).get('USER') != 'pm_ai_reader':
        raise AnalysisError('分析用DB接続をpm_ai_readerへ設定してください。', 503)
    try:
        with connections['ai_reader'].cursor() as cursor:
            cursor.execute('SELECT 1 FROM `v_ai_shipment` WHERE `ship_to_code` = %s LIMIT 1', [value])
            return cursor.fetchone() is not None
    except (DatabaseError, ConnectionDoesNotExist) as exc:
        raise AnalysisError('納入先コードを確認できません。分析用DB接続を管理者へ確認してください。', 503) from exc


# 種類: 画面の表示名と、値の実在の確認。追加はここへ
TYPES = {
    'date': {'label': '日付', 'exists': None},
    'product_code': {'label': '品番', 'exists': _exists_product},
    'customer_code': {'label': '顧客コード', 'exists': _exists_customer},
    'ship_to_code': {'label': '納入先コード', 'exists': _exists_ship_to},
}


def _check_value(type_name, value):
    """1つの値の形式と実在。日付は、形式の確認だけ(期間は、組で別に確認する)。"""
    if type_name == 'date':
        try:
            if type(value) is not str or date.fromisoformat(value).isoformat() != value:
                raise ValueError()
        except ValueError:
            raise AnalysisError('日付はYYYY-MM-DDで指定してください。') from None
        return value
    if type(value) is not str or not CODE_VALUE_PATTERN.fullmatch(value):
        raise AnalysisError('コードは英数字・アンダースコア・ハイフンだけで指定してください。')
    if not TYPES[type_name]['exists'](value):
        raise AnalysisError(f"{TYPES[type_name]['label']}が登録されていません。")
    return value


def validate_definitions(parameters):
    """変数の定義(保存時)。[{name, type, label, default}]。期間は period_from・period_to を組で、種類は日付。"""
    if not isinstance(parameters, list):
        raise AnalysisError('変数の定義の形式が不正です。')
    seen = set()
    cleaned = []
    for item in parameters:
        if not isinstance(item, dict) or set(item) != DEFINITION_KEYS:
            raise AnalysisError('変数の定義の形式が不正です。')
        name, type_name, label = item['name'], item['type'], item['label']
        if type(name) is not str or not NAME_PATTERN.fullmatch(name) or name in seen:
            raise AnalysisError('変数の名前が不正、または重複しています(英小文字・数字・アンダースコア)。')
        seen.add(name)
        if type(type_name) is not str or type_name not in TYPES:
            raise AnalysisError('変数の種類が不正です。')
        if type(label) is not str or not label.strip():
            raise AnalysisError('変数のラベルを指定してください。')
        if name in (PERIOD_FROM, PERIOD_TO) and type_name != 'date':
            raise AnalysisError('period_from・period_toは、種類を日付にしてください。')
        if type_name == 'date' and not DATE_NAME_PATTERN.fullmatch(name):
            raise AnalysisError('日付の変数の名前は、「名前_from」と「名前_to」の組にしてください。')
        cleaned.append({'name': name, 'type': type_name, 'label': label.strip(), 'default': item['default']})
    for item in cleaned:  # 日付の変数は、開始(_from)と終了(_to)を組で
        if item['type'] == 'date':
            base, partner = _date_partner(item['name'])
            if partner not in seen or next(c for c in cleaned if c['name'] == partner)['type'] != 'date':
                raise AnalysisError('日付の変数は、「名前_from」と「名前_to」を組で指定してください。')
    resolve_values(cleaned, {})  # 元の値(既定値)の形式・実在の確認
    return cleaned


def _date_partner(name):
    """日付の変数の名前から、(組の名前, 相手の変数名)を返す。例: aug_from → ('aug', 'aug_to')。"""
    if name.endswith('_from'):
        return name[:-5], name[:-5] + '_to'
    return name[:-3], name[:-3] + '_from'


def resolve_values(definitions, supplied, outer=None):
    """変数の値を決める。指定がなければ既定値。未知の名前・不正な値・存在しない値・期間の逆順は拒否する。

    比べる期間(period_from・period_to以外の日付の組)は、全体の期間の中に収まること。全体の期間は、変数(period_from・period_to)があればその値、
    なければ outer=(開始日, 終了日)(分析案・テンプレートの期間)。どちらもなければ、中に収まることは、呼出し側で確認する。
    """
    if not isinstance(supplied, dict):
        raise AnalysisError('変数の値の形式が不正です。')
    names = {item['name'] for item in definitions}
    if set(supplied) - names:
        raise AnalysisError('定義にない変数は指定できません。')
    values = {}
    for item in definitions:
        values[item['name']] = _check_value(item['type'], supplied.get(item['name'], item['default']))
    if PERIOD_FROM in values:
        validate_period(values[PERIOD_FROM], values[PERIOD_TO])
        outer = (values[PERIOD_FROM], values[PERIOD_TO])
    for item in definitions:
        if item['type'] != 'date' or not item['name'].endswith('_from') or item['name'] == PERIOD_FROM:
            continue
        start, end = values[item['name']], values[_date_partner(item['name'])[1]]
        validate_period(start, end)  # 開始日が終了日以前
        if outer is not None and not (outer[0] <= start and end <= outer[1]):
            raise AnalysisError('比べる期間は、全体の期間の中に収めてください。')
    return values


def placeholder_names(steps, python):
    """コードに書かれた、読める形の{{名前}}の名前(重複なし・昇順)。失敗の画面に出す、変数名の一覧用。"""
    found = set()
    for text in _texts(steps, python):
        found.update(PLACEHOLDER_PATTERN.findall(text))
    return sorted(found)


def _texts(steps, python):
    return [str(step.get('query', '')) for step in steps] + [str(step.get('name', '')) for step in steps] + [python]


QUOTED_PLACEHOLDER_PATTERN = re.compile(r'''['"]\{\{|\}\}['"]''')


LOOSE_PLACEHOLDER_PATTERN = re.compile(r'\{\{[^{}\n]*\}\}')


def has_placeholder_like(steps, python):
    """コードに、変数らしい表記({{...}})が残っているか。変数を宣言(parameters)せずに書かれたものを見つけるため。形の不正な入力でも、例外にしない。"""
    texts = [step.get('query') for step in steps if isinstance(step, dict)] if isinstance(steps, list) else []
    texts.append(python)
    return any(isinstance(text, str) and LOOSE_PLACEHOLDER_PATTERN.search(text) for text in texts)


def has_date_literal(steps, python):
    """コード(変数の形でない、実行する形)に、日付(YYYY-MM-DD)が直接書かれているか。"""
    return any(DATE_LITERAL_PATTERN.search(text) for text in _texts(steps, python))


def normalize_definitions(raw, date_from, date_to):
    """AIが返した変数の一覧(コード生成)を、保存する定義にする。期間(period_from・period_to)の元の値は、AIの値ではなく、分析案の期間にする。

    各項目は name・type・label(品番などは default も)だけ。形式・種類・値の実在は、validate_definitions が確認する。
    """
    if not isinstance(raw, list) or not raw:
        raise AnalysisError('変数の一覧の形式が不正です。')
    periods = {PERIOD_FROM: date_from, PERIOD_TO: date_to}
    definitions = []
    for item in raw:
        if not isinstance(item, dict) or not {'name', 'type', 'label'} <= set(item) <= DEFINITION_KEYS:
            raise AnalysisError('変数の定義の形式が不正です。')
        name = item['name']
        if type(name) is not str:
            raise AnalysisError('変数の名前の形式が不正です。')
        if name in periods:
            definitions.append({**item, 'default': periods[name]})
        elif 'default' not in item:
            raise AnalysisError('変数の元の値(default)がありません。')
        else:
            definitions.append(dict(item))
    cleaned = validate_definitions(definitions)
    resolve_values(cleaned, {}, outer=(date_from, date_to))  # 比べる期間が、分析案の期間の中に収まること(AIの日付を、サーバーが確認する)
    return cleaned


class SourceCheckError(AnalysisError):
    """コードと変数の不一致。画面へ出す固定の理由コード(reason)を持つ(AIの文章は持たない)。"""

    def __init__(self, detail, reason, extra=(), names=None):
        super().__init__(detail)
        self.reason = reason
        self.names = names or {}  # 理由コード→変数の名前(英小文字・数字・アンダースコアだけの識別子)。AIの自由な文章は持たない
        self.reasons = [reason, *extra]  # 主な理由のあとに、場所・種類の固定コードを続ける(直書きのとき)


def check_source(steps, python, definitions):
    """保存するコード(変数の形)の確認: 使った変数がすべて定義にあり、定義した変数がすべて使われ、元の値・日付が文字のまま残っていない。"""
    texts = _texts(steps, python)
    if any(PLACEHOLDER_PATTERN.search(name) for name in [str(step.get('name', '')) for step in steps]):
        raise SourceCheckError('中間テーブル名に変数は使えません。', 'parameters_source_invalid')
    used = set()
    for text in texts:
        used.update(PLACEHOLDER_PATTERN.findall(text))
    names = {item['name'] for item in definitions}
    if used - names:
        raise SourceCheckError('コードに、定義されていない変数があります。', 'parameters_undeclared', names={'parameters_undeclared': sorted(used - names)})
    if names - used:
        raise SourceCheckError('定義した変数が、コードで使われていません。', 'parameters_unused', names={'parameters_unused': sorted(names - used)})
    # 置き換えで引用符が付くため、変数の前後に引用符があると、文字列が壊れる
    if any(QUOTED_PLACEHOLDER_PATTERN.search(text) for text in texts):
        raise SourceCheckError('変数の前後に引用符を付けないでください({{名前}} だけを書くと、値が引用符つきで入ります)。', 'parameters_quoted')
    # 変数の置き換えの対象外の文字(変数の形の外)で判定する
    stripped = [PLACEHOLDER_PATTERN.sub('', text) for text in texts]
    # 正しい変数の形を除いた残りに「{{」「}}」があれば、不正な変数の表記(名前の形式違い・空白・波括弧の不一致など)として断る
    if any('{{' in text or '}}' in text for text in stripped):
        raise SourceCheckError('コードに、変数として読めない {{...}} の表記があります。名前は英小文字・数字・アンダースコアで、{{名前}} の形にしてください。', 'parameters_source_invalid')
    # 固定の値の直書き: 場所(SQL=steps、Python)と種類(変数の元の値・日付)を、すべて集めて、固定のコードで返す(AIの文章は返さない)
    count = len(steps)
    kinds, places = set(), set()
    for index, text in enumerate(stripped):
        place = 'parameters_literal_sql' if index < count else 'parameters_literal_python' if index == 2 * count else None  # 中間テーブル名(count〜2count-1)は対象外
        if place is None:
            continue
        if any(item['type'] != 'date' and item['default'] in text for item in definitions):
            kinds.add('parameters_literal_value'); places.add(place)
        if DATE_LITERAL_PATTERN.search(text):
            kinds.add('parameters_literal_date'); places.add(place)
    if kinds:
        raise SourceCheckError('固定の値(日付・変数の元の値)がコードに直接書かれています。変数だけを使ってください。', 'parameters_literal',
                               [*sorted(places), *sorted(kinds)])


def _substitute(text, values):
    result = PLACEHOLDER_PATTERN.sub(lambda match: "'" + values[match.group(1)] + "'", text)
    if '{{' in result or '}}' in result:
        raise AnalysisError('置き換えられなかった変数の表記が残っています。コードを作り直してください。', 409)
    return result


def concrete_code(steps, python, values):
    """変数を、確認済みの値(引用符つきの文字列)へ置き換えた、実行する形のコード。元の手順・Pythonは変えない。"""
    new_steps = [{**step, 'query': _substitute(step['query'], values)} for step in steps]
    return new_steps, _substitute(python, values)
