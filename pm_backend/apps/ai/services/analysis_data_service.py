"""公開済みビューだけを対象に、承認画面用の件数を確認する。明細は取得しない。"""
from datetime import date, datetime

from django.conf import settings
from django.db import connections, DatabaseError

from ai.services.analysis_plan_store import AnalysisError
from ai.services.sql_queries import BASE_SQL_SCHEMA


# 公開列は既存辞書から取得するが、元テーブル・業務固有の実データ注記は公開しない。
ANALYSIS_VIEWS = {
    'v_ai_purchase_receipt': {
        'label': '入荷実績', 'date_field': 'arrival_date', 'quantity_field': 'qty',
        'description': '1行は1回の入荷登録。日別・期間集計は実際の入荷日arrival_dateを使う。',
    },
    'v_ai_shipment': {
        'label': '出荷実績', 'date_field': 'shipment_date', 'quantity_field': 'quantity',
        'description': '1行は1回の出荷実績登録。日別・期間集計はshipment_dateを使う。',
    },
}


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
