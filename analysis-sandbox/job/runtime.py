"""生成コードの実行環境(子プロセス)。監督プロセス(job_main.py)から起動される。

生成コードは、取得済みのビューのスナップショット(一時DuckDB)だけを読める。MySQLへの接続・外部通信の手段は持たない。
結果は emit_table / emit_chart / emit_report で出力し、最後にまとめて /tmp/result.json へ書く。
結果の検証・上限の判定は、信頼する監督プロセス側が行う(ここでの出力は信頼しない)。
"""
import datetime
import decimal
import json
import os
import sys
import traceback

DB_PATH = '/tmp/job.duckdb'
META_PATH = '/tmp/job_meta.json'
CODE_PATH = '/tmp/user_code.py'
RESULT_PATH = '/tmp/result.json'


def _scalar(value):
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, decimal.Decimal):
        return str(value)
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.isoformat()
    raise TypeError(f'表に出力できない型です: {type(value).__name__}')


def main():
    import duckdb

    with open(META_PATH, encoding='utf-8') as handle:
        meta = json.load(handle)
    views = set(meta['views'])
    connection = duckdb.connect(DB_PATH, config={
        'memory_limit': f"{meta['duckdb_memory_limit_mb']}MB",
        'threads': meta['threads'],
        'enable_external_access': False,
    })
    tables, charts, reports = [], [], []

    def load_view(name):
        """承認済みビューのスナップショットを返す。MySQLへは接続しない。"""
        if name not in views:
            raise ValueError(f'取得していないビューです: {name}')
        return connection.table(name)

    def emit_table(name, columns, rows):
        tables.append({'name': str(name), 'columns': [str(c) for c in columns],
                       'rows': [[_scalar(v) for v in row] for row in rows]})

    def emit_chart(kind, title, x, series):
        charts.append({'kind': str(kind), 'title': str(title), 'x': [_scalar(v) for v in x],
                       'series': [{'name': str(s['name']), 'values': [_scalar(v) for v in s['values']]} for s in series]})

    def emit_report(text):
        reports.append(str(text))

    namespace = {
        '__name__': 'user_code', 'con': connection, 'load_view': load_view,
        'emit_table': emit_table, 'emit_chart': emit_chart, 'emit_report': emit_report,
    }
    with open(CODE_PATH, encoding='utf-8') as handle:
        source = handle.read()
    exec(compile(source, 'user_code', 'exec'), namespace)
    result = {'tables': tables, 'charts': charts, 'report': '\n\n'.join(reports) if reports else None}
    temporary = RESULT_PATH + '.tmp'
    with open(temporary, 'w', encoding='utf-8') as handle:
        json.dump(result, handle, ensure_ascii=False)
    os.replace(temporary, RESULT_PATH)
    connection.close()


if __name__ == '__main__':
    try:
        main()
    except BaseException:
        traceback.print_exc()
        sys.exit(1)
