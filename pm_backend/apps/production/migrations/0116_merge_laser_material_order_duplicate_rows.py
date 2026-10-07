# レーザ材料発注行のキー変更（単位1a）: 重複行の統合
#
# 旧キー (plan_start_date, material, required_date, supplier) で保存されていた計画行を、
# 新キー (material, required_date, supplier) で1行にまとめる。
# 制約の変更は次のマイグレーション（0117）で行う。統合してから一意索引を作るため分けている。

from collections import defaultdict
from datetime import date, datetime, timedelta

from django.db import migrations, transaction


LOCK_STATUSES = ['created', 'reviewing', 'approved', 'sent']


def build_locked_week_map(ApprovalRequest):
    """注文書のロック期間から (supplier, date) -> {週開始日} を作る。

    条件は views_laser_weekly_plan の旧 _build_locked_plan_starts と同じ。
    - route_config.item_key が laser_material_order
    - status が created / reviewing / approved / sent
    - created は context.order_created が True のときだけ対象
    - 日の範囲は context の lock_start_date〜lock_end_date、週は context.start_date
    """
    locked = defaultdict(set)
    approvals = ApprovalRequest.objects.filter(
        route_config__item_key='laser_material_order',
        status__in=LOCK_STATUSES,
    )
    for approval in approvals:
        context = approval.context or {}
        if approval.status == 'created' and context.get('order_created') is not True:
            continue
        supplier = context.get('supplier')
        start = context.get('start_date')
        lock_start = context.get('lock_start_date')
        lock_end = context.get('lock_end_date')
        if not (supplier and start and lock_start and lock_end):
            continue
        try:
            source_start = datetime.strptime(start, '%Y-%m-%d').date()
            locked_start = datetime.strptime(lock_start, '%Y-%m-%d').date()
            locked_end = datetime.strptime(lock_end, '%Y-%m-%d').date()
        except ValueError:
            continue
        cursor = locked_start
        while cursor <= locked_end:
            locked[supplier, cursor].add(source_start)
            cursor += timedelta(days=1)
    return locked


def _latest_sort_key(row):
    """ロックされた週の行がない組で残す行の並び順 (plan_start_date, updated_at, id)。"""
    return (row.plan_start_date or date.min, row.updated_at or datetime.min, row.id)


def merge_duplicate_order_rows(OrderProgress, Receipt, ApprovalRequest):
    """手動追加以外の発注行を (material, supplier, required_date) ごとに1行へ統合する。

    残す行の決め方:
    - plan_start_date がロックされた週に当たる行が1行 → その行を残す
    - ロックされた週の行が2行以上 → 例外で止める
    - ロックされた週の行が0行 → (plan_start_date, updated_at, id) が最大の行を残す
    消す行に入荷実績 (LaserMaterialReceipt) がつながっていたら例外で止める。

    戻り値: {'group_count': 重複した組の数, 'deleted_ids': 削除した行IDのリスト}
    """
    locked_weeks = build_locked_week_map(ApprovalRequest)

    groups = defaultdict(list)
    rows = OrderProgress.objects.filter(is_manual=False, required_date__isnull=False).order_by('id')
    for row in rows:
        groups[(row.material_id, row.supplier, row.required_date)].append(row)

    multi_locked_keys = []
    delete_ids = []
    delete_key_by_id = {}
    group_count = 0
    for key, group_rows in groups.items():
        if len(group_rows) < 2:
            continue
        group_count += 1
        material_id, supplier, required_date = key
        weeks = locked_weeks.get((supplier, required_date), set())
        locked_rows = [row for row in group_rows if row.plan_start_date in weeks]
        if len(locked_rows) >= 2:
            multi_locked_keys.append(
                f'material_id={material_id}, supplier={supplier}, required_date={required_date.isoformat()}, '
                f'row_ids={[row.id for row in locked_rows]}'
            )
            continue
        if len(locked_rows) == 1:
            keep = locked_rows[0]
        else:
            keep = max(group_rows, key=_latest_sort_key)
        for row in group_rows:
            if row.id != keep.id:
                delete_ids.append(row.id)
                delete_key_by_id[row.id] = key

    if multi_locked_keys:
        raise RuntimeError(
            'ロックされた週の行が2行以上ある組があるため、統合を中止しました: '
            + ' / '.join(multi_locked_keys)
        )

    receipt_order_ids = sorted(set(
        Receipt.objects.filter(order_id__in=delete_ids).values_list('order_id', flat=True)
    )) if delete_ids else []
    if receipt_order_ids:
        details = []
        for order_id in receipt_order_ids:
            material_id, supplier, required_date = delete_key_by_id[order_id]
            details.append(
                f'order_id={order_id}, material_id={material_id}, supplier={supplier}, '
                f'required_date={required_date.isoformat()}'
            )
        raise RuntimeError(
            '削除対象の行に入荷実績がつながっているため、統合を中止しました: ' + ' / '.join(details)
        )

    if delete_ids:
        OrderProgress.objects.filter(id__in=delete_ids).delete()
    return {'group_count': group_count, 'deleted_ids': delete_ids}


def forwards(apps, schema_editor):
    OrderProgress = apps.get_model('production', 'LaserWeeklyMaterialOrderProgress')
    Receipt = apps.get_model('production', 'LaserMaterialReceipt')
    ApprovalRequest = apps.get_model('accounts', 'ApprovalRequest')
    with transaction.atomic(using=schema_editor.connection.alias):
        merge_duplicate_order_rows(OrderProgress, Receipt, ApprovalRequest)


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0072_alter_departmentpermission_resource_and_more'),
        ('production', '0115_processrealtimerecord_purchase_source_check'),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
