"""テンプレートの変数(段階2-A、BOSS承認 2026-10-05)。

コードの中の「{{名前}}」を、使うときに、確認した値(引用符つきの文字列)へ置き換える。期間は「period_from」「period_to」(分析案の期間に連動)。
- 変数の種類は、TYPESの1か所にまとめる(追加は、ここへの追加)。種類: 日付(期間)・品番・顧客コード・納入先コード
- 日付の変数は、「名前_from」と「名前_to」の組(2026-10-07、BOSS承認)。全体の期間は period_from・period_to(値は分析案の期間に固定)。
  期間を分けて比べる分析(月ごと・前半と後半など)の「比べる期間」は、組を何組でも。値(初期値)は、AIが目的・手順から読み取り、
  サーバーが、形式・開始日<=終了日・全体の期間の中、を確認する。
- 値は、形式(英数字・アンダースコア・ハイフンのみ)と、実在(品番=v_ai_product、顧客コード=m_customer、納入先コード=v_ai_shipmentの実際の値)を確認する。
  実在した値は、マスタ・ビューに保存されている正規の表記へ直す(小文字の品番 → 大文字、など。DuckDBは大文字小文字を区別するため)。
  大文字小文字だけが違う値が複数あって決められないときは拒否する(parameters_def_ambiguous)
  形式を絞るため、置き換えた値がSQL・Pythonの文字列を壊すことはない
- 保存するコードに、変数の元の値(品番など)や日付が文字のまま残っていたら、保存を断る(直書きの禁止)。
  元の値の検査は、SQL・Pythonの文字列リテラルだけが対象(識別子・コメントは除く。大文字小文字は区別しない)。日付はコード全体を検査する
- 変数の個数の上限は設けない(BOSS承認)。フォールバックはない(値が確認できなければ、拒否する)
"""
import ast
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
PLACEHOLDER_DUMMY = '?PH ?'  # 直書き検査でコードを読むときの {{名前}} の代わり。空白と?を含み、CODE_VALUE_PATTERNの値と一致しない
DATE_LITERAL_PATTERN = re.compile(r'[0-9]{4}-[0-9]{2}-[0-9]{2}')
DATE_NAME_PATTERN = re.compile(r'[a-z][a-z0-9_]*_(?:from|to)')  # 日付の変数の名前(組: 名前_from と 名前_to)
PERIOD_FROM, PERIOD_TO = 'period_from', 'period_to'
DEFINITION_KEYS = {'name', 'type', 'label', 'default'}


class DefinitionError(AnalysisError):
    """変数の定義の不備(BOSS承認 2026-10-07)。画面へ出す固定の理由コード(reasons)と、該当する変数の名前(names: 理由→識別子の一覧)を持つ。AIの自由な文章は持たない。"""

    def __init__(self, detail, reason, names=()):
        super().__init__(detail)
        self.reasons = [reason]
        clean = sorted({name for name in names if type(name) is str and NAME_PATTERN.fullmatch(name)})
        self.names = {reason: clean} if clean else {}


class _Ambiguous(Exception):
    """大文字小文字だけが違う値が複数ある(どれが正規か決められない)。_check_value が、変数の名前をつけて拒否に変える。"""


def _canonical_in_view(view, column, value, label):
    """公開ビューの実際の値のうち、value と(大文字小文字を区別せず)一致する正規の表記を返す。なければ None、2種類以上あれば _Ambiguous。

    DISTINCT は、MySQLの照合順序(ci)だと大文字小文字違いを1つに潰すため、CAST(... AS BINARY) で区別して取得する。ビュー・列の名前は固定(利用者の入力ではない)。
    """
    # 既存の件数確認(count_target_rows)と同じく、分析用の読み取り専用ユーザーでなければ使わない
    if settings.DATABASES.get('ai_reader', {}).get('USER') != 'pm_ai_reader':
        raise AnalysisError('分析用DB接続をpm_ai_readerへ設定してください。', 503)
    try:
        with connections['ai_reader'].cursor() as cursor:
            cursor.execute(f'SELECT DISTINCT CAST(`{column}` AS BINARY) FROM `{view}` WHERE `{column}` = %s', [value])
            found = {bytes(row[0]).decode('utf-8') if isinstance(row[0], (bytes, bytearray)) else row[0] for row in cursor.fetchall()}
    except (DatabaseError, ConnectionDoesNotExist) as exc:
        raise AnalysisError(f'{label}を確認できません。分析用DB接続を管理者へ確認してください。', 503) from exc
    # 照合順序(ci)は全角半角も同じとみなして候補に返すため、入力値と「ASCIIの大文字小文字の違いだけ」で一致する候補に絞る(全角半角は対象外)。
    # 入力値は形式検査(CODE_VALUE_PATTERN)済みでASCII。マスタに全角の値しかなければ、候補は0件(未登録)
    found = {code for code in found if type(code) is str and code.isascii() and code.lower() == value.lower()}
    if len(found) > 1:
        raise _Ambiguous()
    return next(iter(found), None)


def _exists_product(value):
    """品番マスタの公開ビュー(v_ai_product)にある、正規の表記を返す。なければ None。"""
    return _canonical_in_view('v_ai_product', 'product_code', value, '品番')


def _exists_customer(value):
    """顧客マスタ(m_customer)に保存されている、正規の表記を返す。なければ None(顧客マスタのビューは未作成)。"""
    from masters.models import Customer
    try:
        return Customer.objects.filter(customer_code=value).values_list('customer_code', flat=True).first()
    except DatabaseError as exc:
        raise AnalysisError('顧客コードを確認できません。しばらくしてから、もう一度お試しください。', 503) from exc


def _exists_ship_to(value):
    """納入先コードの正本の表がないため、出荷実績ビューの実際の値で確認し、正規の表記を返す(読み取り専用の分析用接続)。"""
    return _canonical_in_view('v_ai_shipment', 'ship_to_code', value, '納入先コード')


# 種類: 画面の表示名と、値の実在の確認(正規の表記、なければ None を返す)。追加はここへ
TYPES = {
    'date': {'label': '日付', 'exists': None},
    'product_code': {'label': '品番', 'exists': _exists_product},
    'customer_code': {'label': '顧客コード', 'exists': _exists_customer},
    'ship_to_code': {'label': '納入先コード', 'exists': _exists_ship_to},
}


def _check_value(type_name, value, name=None):
    """1つの値の形式と実在。日付は、形式の確認だけ(期間は、組で別に確認する)。コード系は、マスタ・ビューの正規の表記を返す。"""
    if type_name == 'date':
        try:
            if type(value) is not str or date.fromisoformat(value).isoformat() != value:
                raise ValueError()
        except ValueError:
            raise DefinitionError('日付はYYYY-MM-DDで指定してください。', 'parameters_def_date', [name]) from None
        return value
    if type(value) is not str or not CODE_VALUE_PATTERN.fullmatch(value):
        raise DefinitionError('コードは英数字・アンダースコア・ハイフンだけで指定してください。', 'parameters_def_value', [name])
    try:
        canonical = TYPES[type_name]['exists'](value)
    except _Ambiguous:
        raise DefinitionError(f"{TYPES[type_name]['label']}に、大文字小文字だけが違う値が複数あり、決められません。", 'parameters_def_ambiguous', [name]) from None
    if not canonical:
        raise DefinitionError(f"{TYPES[type_name]['label']}が登録されていません。", 'parameters_def_unregistered', [name])
    if type(canonical) is not str or not CODE_VALUE_PATTERN.fullmatch(canonical):  # 置き換えで文字列を壊し得る表記は使わない
        raise DefinitionError('コードは英数字・アンダースコア・ハイフンだけで指定してください。', 'parameters_def_value', [name])
    return canonical


def validate_definitions(parameters):
    """変数の定義(保存時)。[{name, type, label, default}]。期間は period_from・period_to を組で、種類は日付。"""
    if not isinstance(parameters, list):
        raise DefinitionError('変数の定義の形式が不正です。', 'parameters_def_format')
    seen = set()
    cleaned = []
    for item in parameters:
        if not isinstance(item, dict) or set(item) != DEFINITION_KEYS:
            raise DefinitionError('変数の定義の形式が不正です。', 'parameters_def_format', [item.get('name') if isinstance(item, dict) else None])
        name, type_name, label = item['name'], item['type'], item['label']
        if type(name) is not str or not NAME_PATTERN.fullmatch(name) or name in seen:
            raise DefinitionError('変数の名前が不正、または重複しています(英小文字・数字・アンダースコア)。', 'parameters_def_name', [name])
        seen.add(name)
        if type(type_name) is not str or type_name not in TYPES:
            raise DefinitionError('変数の種類が不正です。', 'parameters_def_type', [name])
        if type(label) is not str or not label.strip():
            raise DefinitionError('変数のラベルを指定してください。', 'parameters_def_label', [name])
        if name in (PERIOD_FROM, PERIOD_TO) and type_name != 'date':
            raise DefinitionError('period_from・period_toは、種類を日付にしてください。', 'parameters_def_type', [name])
        if type_name == 'date' and not DATE_NAME_PATTERN.fullmatch(name):
            raise DefinitionError('日付の変数の名前は、「名前_from」と「名前_to」の組にしてください。', 'parameters_def_name', [name])
        cleaned.append({'name': name, 'type': type_name, 'label': label.strip(), 'default': item['default']})
    for item in cleaned:  # 日付の変数は、開始(_from)と終了(_to)を組で
        if item['type'] == 'date':
            base, partner = _date_partner(item['name'])
            if partner not in seen or next(c for c in cleaned if c['name'] == partner)['type'] != 'date':
                raise DefinitionError('日付の変数は、「名前_from」と「名前_to」を組で指定してください。', 'parameters_def_pair', [item['name']])
    # 元の値(既定値)の形式・実在の確認。コード系は、正規の表記を保存する定義の default にする(直書き検査・ハッシュを揃えるため)
    for item, value in zip(cleaned, resolve_values(cleaned, {}).values()):
        item['default'] = value
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
        values[item['name']] = _check_value(item['type'], supplied.get(item['name'], item['default']), item['name'])
    if PERIOD_FROM in values:
        _check_order(values[PERIOD_FROM], values[PERIOD_TO], [PERIOD_FROM, PERIOD_TO])
        outer = (values[PERIOD_FROM], values[PERIOD_TO])
    for item in definitions:
        if item['type'] != 'date' or not item['name'].endswith('_from') or item['name'] == PERIOD_FROM:
            continue
        partner = _date_partner(item['name'])[1]
        start, end = values[item['name']], values[partner]
        _check_order(start, end, [item['name'], partner])  # 開始日が終了日以前
        if outer is not None and not (outer[0] <= start and end <= outer[1]):
            raise DefinitionError('比べる期間は、全体の期間の中に収めてください。', 'parameters_def_outside', [item['name'], partner])
    return values


def _check_order(start, end, names):
    """開始日が終了日以前であること(形式は、確認済みの値)。"""
    try:
        validate_period(start, end)
    except AnalysisError:
        raise DefinitionError('開始日は、終了日以前にしてください。', 'parameters_def_order', names) from None


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


# 目的・手順に書かれた値(品番・顧客コードなど)が、コードの文字列として直接書かれていないかの確認用(2026-10-08、BOSS承認。警告のみ)
COPY_TOKEN_PATTERN = re.compile(r'[A-Za-z0-9_-]{4,40}')
STRING_LITERAL_PATTERN = re.compile(r"'([^'\n]*)'|\"([^\"\n]*)\"")


def copied_literals(plan_texts, steps, python):
    """目的・手順・出力案に書かれた値のうち、コード(変数の形のコード)の文字列として直接書かれているものを、昇順で返す。

    対象の値は、数字を1つ以上含む4〜40文字の英数字・_・-(品番・顧客コードの形)で、日付(YYYY-MM-DD)は除く(日付は、別の検査)。
    変数にすれば、コードには{{名前}}と書かれ、文字列としては現れない。DBは参照しない(機械的な文字列の確認だけ)。
    """
    tokens = {token for token in COPY_TOKEN_PATTERN.findall(' '.join(str(text) for text in plan_texts))
              if any(char.isdigit() for char in token) and not DATE_LITERAL_PATTERN.fullmatch(token)}
    literals = [first or second for text in _texts(steps, python) for first, second in STRING_LITERAL_PATTERN.findall(text)]
    return sorted(token for token in tokens if any(token in literal for literal in literals))


def has_date_literal(steps, python):
    """コード(変数の形でない、実行する形)に、日付(YYYY-MM-DD)が直接書かれているか。"""
    return any(DATE_LITERAL_PATTERN.search(text) for text in _texts(steps, python))


def normalize_definitions(raw, date_from, date_to):
    """AIが返した変数の一覧(コード生成)を、保存する定義にする。期間(period_from・period_to)の元の値は、AIの値ではなく、分析案の期間にする。

    各項目は name・type・label(品番などは default も)だけ。形式・種類・値の実在は、validate_definitions が確認する。
    """
    if not isinstance(raw, list) or not raw:
        raise DefinitionError('変数の一覧の形式が不正です。', 'parameters_def_format')
    periods = {PERIOD_FROM: date_from, PERIOD_TO: date_to}
    definitions = []
    for item in raw:
        if not isinstance(item, dict) or not {'name', 'type', 'label'} <= set(item) <= DEFINITION_KEYS:
            raise DefinitionError('変数の定義の形式が不正です。', 'parameters_def_format', [item.get('name') if isinstance(item, dict) else None])
        name = item['name']
        if type(name) is not str:
            raise DefinitionError('変数の名前の形式が不正です。', 'parameters_def_name')
        if name in periods:
            definitions.append({**item, 'default': periods[name]})
        elif 'default' not in item:
            raise DefinitionError('変数の元の値(default)がありません。', 'parameters_def_default', [name])
        else:
            definitions.append(dict(item))
    cleaned = validate_definitions(definitions)
    resolve_values(cleaned, {}, outer=(date_from, date_to))  # 比べる期間が、分析案の期間の中に収まること(AIの日付を、サーバーが確認する)
    return cleaned


def normalized_values(raw, definitions):
    """AIが返した変数の元の値(default)と、保存する定義の default(正規の表記)を名前で比べ、異なった項目を [{name, from, to}] で返す(画面の警告用)。

    コード系(日付以外)だけ。from は形式(CODE_VALUE_PATTERN)に合う文字列だけで、AIの自由な文章は入れない。例外は出さない。
    """
    given = {item.get('name'): item.get('default') for item in raw if isinstance(item, dict)} if isinstance(raw, list) else {}
    result = []
    for item in definitions:
        before = given.get(item['name'])
        if item['type'] != 'date' and type(before) is str and CODE_VALUE_PATTERN.fullmatch(before) and before != item['default']:
            result.append({'name': item['name'], 'from': before, 'to': item['default']})
    return sorted(result, key=lambda entry: entry['name'])


class SourceCheckError(AnalysisError):
    """コードと変数の不一致。画面へ出す固定の理由コード(reason)を持つ(AIの文章は持たない)。"""

    def __init__(self, detail, reason, extra=(), names=None):
        super().__init__(detail)
        self.reason = reason
        self.names = names or {}  # 理由コード→変数の名前(英小文字・数字・アンダースコアだけの識別子)。AIの自由な文章は持たない
        self.reasons = [reason, *extra]  # 主な理由のあとに、場所・種類の固定コードを続ける(直書きのとき)


def _sql_string_literals(text):
    """SQLの文字列リテラル(シングルクォート。'' はエスケープ)の中身の一覧。コメント(-- 行、/* */)・ダブルクォート・バッククォートの識別子は除く。閉じていない引用符は、末尾までを中身とみなす。"""
    literals = []
    i, n = 0, len(text)
    while i < n:
        char = text[i]
        if text.startswith('--', i):
            end = text.find('\n', i)
            i = n if end < 0 else end + 1
        elif text.startswith('/*', i):
            end = text.find('*/', i + 2)
            i = n if end < 0 else end + 2
        elif char in '"`':  # 識別子
            end = i + 1
            while end < n:
                if text[end] == char:
                    if text.startswith(char, end + 1):
                        end += 2
                        continue
                    break
                end += 1
            i = end + 1
        elif char == "'":
            buffer, end = [], i + 1
            while end < n:
                if text[end] == "'":
                    if text.startswith("'", end + 1):
                        buffer.append("'")
                        end += 2
                        continue
                    break
                buffer.append(text[end])
                end += 1
            literals.append(''.join(buffer))
            i = end + 1
        else:
            i += 1
    return literals


def _python_string_literals(text):
    """Pythonの文字列定数(f-stringの文字列部分を含む)の一覧。コメント・識別子は含まない。{{名前}} は、実行時の置き換え(_substitute)と同じく引用符つきの文字列のダミーに置き換えて読む。
    ダミーは空白と記号(?)を含むため、変数の値(英数字・アンダースコア・ハイフンだけ)とは一致しない。
    置き換えても構文が読めないコードは、ここでは何も返さない(例外にもしない)。その構文の不正の検査は、続く validate_generated(置き換え後の実行する形の検査)に任される。"""
    try:
        tree = ast.parse(PLACEHOLDER_PATTERN.sub(lambda match: "'" + PLACEHOLDER_DUMMY + "'", text))
    except (SyntaxError, ValueError, RecursionError, MemoryError):
        return []
    return [node.value for node in ast.walk(tree) if isinstance(node, ast.Constant) and isinstance(node.value, str)]


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
        # コード系は、SQL・Pythonの「文字列リテラル」だけを、大文字小文字を区別せず比較する(識別子・コメントは対象外。小文字で直書きされても見逃さない)
        literals = _python_string_literals(texts[index]) if place == 'parameters_literal_python' else _sql_string_literals(stripped[index])
        if any(item['type'] != 'date' and item['default'].lower() in literal.lower() for item in definitions for literal in literals):
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
