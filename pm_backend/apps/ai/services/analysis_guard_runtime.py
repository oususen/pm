"""分析用の固定外枠。コンテナ内で、AIのSQL・Pythonを検査してから実行する。Django側でも、Pythonの静的検査に使う。

このファイルのテキストを、そのまま(先頭に設定値の代入だけを加えて)コンテナへ送るコードの外枠とする。
コンテナ側(runtimeが`__name__ == 'user_code'`で実行する)でだけ、末尾の`_main()`が動く。Djangoが読み込んだ場合は、何も実行しない。

方針(AI分析基盤仕様書§4.8):
- AIのSQLは、「中間テーブル名」と「SELECT/WITHの問い合わせ」だけを受け取る。INSERT・UPDATE・DELETE・DROP・CREATEは、AIには許可しない。
  外枠が、検査に合格した問い合わせだけを、`CREATE TABLE <名前> AS (<問い合わせ>)`に組み立てて実行する。
- 問い合わせは、DuckDB本体の構文木(`json_serialize_sql`)で検査する。解析できない文・複数の文・SELECT以外は拒否し、
  文字列の検査だけで続行しない。参照できるテーブルは、承認ビューと、作成済みの`w_`の中間テーブル(と、その問い合わせ内のCTE)だけ。
  システムビュー・メタデータ関数・外部ファイルの読み取りは、構文木で参照先と関数を調べて拒否する。
- AIのPythonは、`con`を、検査つきの窓口に置き換えて実行する。窓口は、実行のたびに、同じ検査を適用する(単一の読み取り文だけ)。
- 承認ビューのテーブルの値は、実行の前後で、行ごとのハッシュの合計で比較する(件数だけの比較にしない)。
安全の境界は、隔離コンテナである。この外枠は、その手前の防御である。
"""
import ast
import builtins
import json
import re
import types

ALLOWED_IMPORTS = ('json', 'math', 'datetime', 'decimal', 'statistics', 'collections', 'itertools', 're')
TABLE_FUNCTIONS = ('range', 'generate_series', 'unnest')  # FROMで使える関数。メタデータ・外部ファイルの関数は含めない
STEP_NAME = re.compile(r'^w_[a-z0-9_]{1,40}$')
INTERMEDIATE_PREFIX = 'w_'
# 環境・設定・外部ファイル・拡張・メタデータに触れる関数。すべてを許可リストにするのは現実的でないため、拒否リストで拒否し、
# コンテナ側の外部アクセス遮断(enable_external_access=False)と合わせて守る。
DENIED_FUNCTION = re.compile(
    r'^(read_|.*_scan$|duckdb_|pragma_|sniff_|glob$|getenv$|current_setting$|query$|query_table$|install_|load_extension|'
    r'parquet_|iceberg_|delta_|http_|httpfs|checkpoint|force_checkpoint|which_secret|create_secret|getvariable$)', re.IGNORECASE)
FORBIDDEN_NAMES = frozenset({
    'open', 'eval', 'exec', 'compile', '__import__', 'input', 'breakpoint', 'getattr', 'setattr', 'delattr',
    'globals', 'locals', 'vars', 'memoryview', 'help', 'exit', 'quit',
})
CON_METHODS = ('sql', 'execute', 'table')
OUTPUT_FUNCTIONS = ('emit_table', 'emit_chart', 'emit_report')
SELECT_NODE_TYPES = ('SELECT_NODE', 'SET_OPERATION_NODE', 'RECURSIVE_CTE_NODE', 'CTE_NODE')
# 実行中のフレーム・コード・トレースバックへ届く属性。元の接続や外枠の変数へ到達できてしまうため、`_`で始まらなくても拒否する。
FRAME_ATTRIBUTE = re.compile(r'^(gi_|cr_|ag_|f_|tb_|co_)')
# 構文木の許可リスト(未知の種類は、拒否する)。式は`class`、それ以外(問い合わせ・テーブル参照・修飾子・並び順)は`type`で判定する。
EXPRESSION_CLASSES = frozenset({
    'BETWEEN', 'CASE', 'CAST', 'COLLATE', 'COLUMN_REF', 'COMPARISON', 'CONJUNCTION', 'CONSTANT', 'FUNCTION', 'LAMBDA',
    'OPERATOR', 'POSITIONAL_REFERENCE', 'STAR', 'SUBQUERY', 'WINDOW',
})
STRUCTURE_TYPES = frozenset({
    'SELECT_NODE', 'SET_OPERATION_NODE', 'RECURSIVE_CTE_NODE', 'CTE_NODE',
    'BASE_TABLE', 'TABLE_FUNCTION', 'SUBQUERY', 'JOIN', 'EMPTY', 'EXPRESSION_LIST', 'PIVOT',
    'ORDER_MODIFIER', 'LIMIT_MODIFIER', 'LIMIT_PERCENT_MODIFIER', 'DISTINCT_MODIFIER',
    'ASCENDING', 'DESCENDING', 'ORDER_DEFAULT',
})
MAX_TREE_DEPTH = 150


class GuardError(Exception):
    """検査に失敗した。codeは固定の理由コード。"""

    def __init__(self, code, detail=''):
        super().__init__(code)
        self.code = code
        self.detail = detail


# ---- Pythonの静的検査(Django側でも使う。duckdbに依存しない) ----

def validate_python(source):
    """AIのPythonの静的検査。問題があれば、固定の理由コードのリストを返す(空なら合格)。"""
    problems = []

    def add(code):
        if code not in problems:
            problems.append(code)

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return ['syntax_error']
    has_output = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split('.')[0] not in ALLOWED_IMPORTS:
                    add('import_not_allowed')
        elif isinstance(node, ast.ImportFrom):
            if node.level or (node.module or '').split('.')[0] not in ALLOWED_IMPORTS:
                add('import_not_allowed')
        elif isinstance(node, ast.Name):
            if node.id in FORBIDDEN_NAMES or node.id.startswith('__'):
                add('forbidden_name')
        elif isinstance(node, ast.Attribute):
            if node.attr.startswith('_') or FRAME_ATTRIBUTE.match(node.attr):
                add('private_attribute')
            if isinstance(node.value, ast.Name) and node.value.id == 'con' and node.attr not in CON_METHODS:
                add('con_method_not_allowed')
        elif isinstance(node, (ast.Global, ast.Nonlocal, ast.AsyncFunctionDef, ast.AsyncFor, ast.AsyncWith, ast.Await)):
            add('construct_not_allowed')
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in OUTPUT_FUNCTIONS:
            has_output = True
    if not has_output:
        add('no_output')
    return problems


# ---- 問い合わせの検査(コンテナ内。DuckDBの構文木を使う) ----

def _check_dict(node, visible, allowed):
    """辞書1つ分の検査。未知の式・構造は拒否する(許可リストにないものは、通さない)。"""
    kind = node.get('type')
    expression_class = node.get('class')
    if expression_class is not None:
        if expression_class not in EXPRESSION_CLASSES:
            raise GuardError('syntax_not_supported', str(expression_class)[:60])
    elif isinstance(kind, str) and kind not in STRUCTURE_TYPES:
        raise GuardError('syntax_not_supported', kind[:60])  # SHOW・DESCRIBEなど、未知のテーブル参照・ノードを含む
    if kind == 'BASE_TABLE' and expression_class is None:
        table = str(node.get('table_name', '')).lower()
        if node.get('catalog_name') or node.get('schema_name') not in ('', 'main'):
            raise GuardError('reference_not_allowed', f'{node.get("schema_name")}.{table}'[:100])
        if table not in allowed and table not in visible:
            raise GuardError('reference_not_allowed', table[:100])
    elif kind == 'TABLE_FUNCTION' and expression_class is None:
        name = str((node.get('function') or {}).get('function_name', '')).lower()
        if name not in TABLE_FUNCTIONS:
            raise GuardError('table_function_not_allowed', name[:100])
    if 'function_name' in node and DENIED_FUNCTION.match(str(node['function_name'])):
        raise GuardError('function_not_allowed', str(node['function_name'])[:100])


def _scan(obj, visible, allowed, depth=0):
    """構文木をたどる。WITHの名前は、その問い合わせ(と、後に続くWITHの定義)の中でだけ有効とし、外側・別の枝では使えない。"""
    if depth > MAX_TREE_DEPTH:
        raise GuardError('query_too_deep')
    if isinstance(obj, list):
        for item in obj:
            _scan(item, visible, allowed, depth + 1)
        return
    if not isinstance(obj, dict):
        return
    inner = visible
    cte_map = obj.get('cte_map')
    if isinstance(cte_map, dict) and cte_map.get('map'):
        defined = []
        for entry in cte_map['map']:
            name = str(entry.get('key', '')).lower()
            value = entry.get('value')
            node = ((value or {}).get('query') or {}).get('node') or {}
            # 先に定義したWITHの名前は見える。自分自身の名前は、再帰WITH(RECURSIVE_CTE_NODE)の中だけ見える
            scope = visible | frozenset(defined) | (frozenset({name}) if node.get('type') == 'RECURSIVE_CTE_NODE' else frozenset())
            _scan(value, scope, allowed, depth + 1)
            defined.append(name)
        inner = visible | frozenset(defined)
    _check_dict(obj, inner, allowed)
    for key, value in obj.items():
        if key != 'cte_map':
            _scan(value, inner, allowed, depth + 1)


def validate_tree(tree, allowed_tables):
    """DuckDBの構文木(json_serialize_sqlの結果)が、単一の読み取り文で、許可の範囲内であることを確認する(duckdb不要)。"""
    if not isinstance(tree, dict):
        raise GuardError('query_unparseable')
    statements = tree.get('statements') or []
    if tree.get('error') or len(statements) != 1:
        raise GuardError('query_not_single_select', str(tree.get('error_message', ''))[:200])
    if (statements[0].get('node') or {}).get('type') not in SELECT_NODE_TYPES:
        raise GuardError('query_not_select')
    try:
        _scan(statements, frozenset(), {name.lower() for name in allowed_tables})
    except RecursionError as exc:
        raise GuardError('query_too_deep') from exc
    return tree


def check_query(raw, sql, allowed_tables):
    """問い合わせが、単一の読み取り文で、参照先・関数が許可の範囲内であることを確認する。違反は、GuardErrorにする。"""
    if not isinstance(sql, str) or not sql.strip():
        raise GuardError('query_empty')
    try:
        tree = json.loads(raw.execute('SELECT json_serialize_sql(?::VARCHAR)', [sql]).fetchone()[0])
    except Exception as exc:
        raise GuardError('query_unparseable', str(exc)[:200]) from exc
    return validate_tree(tree, allowed_tables)


class _Result:
    """窓口が返す結果。取得済みの行だけを持ち、元の接続・SQLを実行する手段を持たない。"""

    def __init__(self, columns, rows):
        self.columns = list(columns)
        self.description = [(name,) for name in self.columns]
        self._rows = list(rows)
        self._position = 0

    def fetchall(self):
        rows, self._position = self._rows[self._position:], len(self._rows)
        return rows

    def fetchone(self):
        if self._position >= len(self._rows):
            return None
        self._position += 1
        return self._rows[self._position - 1]

    def fetchmany(self, size=1):
        rows = self._rows[self._position:self._position + size]
        self._position += len(rows)
        return rows


class _GuardedConnection:
    def __init__(self, raw, allowed_tables):
        self._raw = raw
        self._allowed = allowed_tables

    def _run(self, sql, params=None):
        check_query(self._raw, sql, self._allowed)
        cursor = self._raw.execute(sql, params) if params is not None else self._raw.execute(sql)
        columns = [item[0] for item in (self._raw.description or [])]
        return _Result(columns, cursor.fetchall() if columns else [])

    def sql(self, query, params=None):
        return self._run(query, params)

    def execute(self, query, params=None):
        return self._run(query, params)

    def table(self, name):
        if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9_]+', name):
            raise GuardError('reference_not_allowed', 'table')
        return self._run(f'SELECT * FROM "{name}"')


def _fingerprint(raw, names):
    """承認ビューのテーブルごとに、件数と、行ごとのハッシュの合計を返す。値が変わると、件数が同じでも変わる。"""
    return {name: raw.execute(f'SELECT count(*), coalesce(sum(hash(t)::HUGEINT), 0) FROM "{name}" t').fetchone() for name in names}


_PUBLIC_MODULES = {}


def _public_module(name):
    """許可したモジュールの、公開名だけの複製。モジュールの属性(`statistics.sys`など)から、sys・os・実際のモジュールへ届かないよう、
    モジュール型の属性と`_`で始まる名前を除く。"""
    if name not in _PUBLIC_MODULES:
        module = builtins.__import__(name)
        _PUBLIC_MODULES[name] = types.SimpleNamespace(**{
            key: value for key, value in vars(module).items() if not key.startswith('_') and not isinstance(value, types.ModuleType)})
    return _PUBLIC_MODULES[name]


def _safe_builtins():
    safe = {name: value for name, value in vars(builtins).items() if name not in FORBIDDEN_NAMES}

    def restricted_import(name, globals=None, locals=None, fromlist=(), level=0):
        if level or name not in ALLOWED_IMPORTS:  # 許可したモジュールの最上位だけ。`json.decoder`のような下位モジュールは使えない
            raise GuardError('import_not_allowed', name[:50])
        return _public_module(name)

    safe['__import__'] = restricted_import
    return safe


def validate_steps(steps, approved_views):
    """中間テーブルの手順の形式を確認する(Djangoでも、コンテナでも使う)。問題があれば、GuardError。"""
    if not isinstance(steps, list):
        raise GuardError('steps_invalid')
    approved = {name.lower() for name in approved_views}
    names = set()
    for step in steps:
        if not isinstance(step, dict) or set(step) != {'name', 'query'}:
            raise GuardError('steps_invalid')
        name = step['name']
        if not isinstance(name, str) or not STEP_NAME.match(name) or name in names or name in approved:
            raise GuardError('step_name_invalid', str(name)[:50])
        names.add(name)
        if not isinstance(step['query'], str) or not step['query'].strip():
            raise GuardError('query_empty')


def _run_steps(raw, steps, approved):
    """手順を順に実行する。1手順ごとに、検査してから、`CREATE TABLE ... AS`を外枠が組み立てる。"""
    allowed = list(approved)
    for step in steps:
        try:
            check_query(raw, step['query'], allowed)
            raw.execute(f'CREATE TABLE "{step["name"]}" AS (\n{step["query"]}\n)')
        except GuardError as exc:
            exc.step = step['name']
            raise
        except Exception as exc:
            error = GuardError('query_failed', str(exc)[:300])
            error.step = step['name']
            raise error from exc
        allowed.append(step['name'])
    return allowed


def _main():
    namespace = globals()
    raw = namespace['con']
    config = json.loads(namespace['_CONFIG_JSON'])
    source = namespace['_PYTHON_SOURCE']
    approved, steps, trial = config['approved'], config['steps'], config['mode'] == 'trial'
    before = _fingerprint(raw, approved)
    try:
        validate_steps(steps, approved)
        problems = validate_python(source)
        if problems:
            raise GuardError('python_rejected', ','.join(problems))
        allowed = _run_steps(raw, steps, approved)
        if _fingerprint(raw, approved) != before:
            raise GuardError('source_modified')
    except GuardError as exc:
        if not trial:
            raise
        namespace['emit_report'](json.dumps({'trial': 'failed', 'step': getattr(exc, 'step', None), 'reason': exc.code,
                                              'message': exc.detail}, ensure_ascii=False))
        return
    if trial:  # 試行は、空のテーブルでのSQLの確認だけ。Pythonは実行しない
        namespace['emit_report'](json.dumps({'trial': 'passed', 'steps': len(steps)}))
        return
    guarded = _GuardedConnection(raw, allowed)
    scope = {
        '__builtins__': _safe_builtins(), '__name__': 'ai_python', 'con': guarded,
        'load_view': lambda name: guarded.table(name),
        'emit_table': namespace['emit_table'], 'emit_chart': namespace['emit_chart'], 'emit_report': namespace['emit_report'],
    }
    exec(compile(source, 'ai_python', 'exec'), scope)
    if _fingerprint(raw, approved) != before:
        raise GuardError('source_modified')


if __name__ == 'user_code':
    _main()
