from datetime import timedelta
from decimal import Decimal

from outsource.models import OutsourceOrder, OutsourceSplit, OutsourceBOM, MaterialRequirement
from masters.models import Calendar
from orders.utils.calendar_utils import subtract_working_days


def explode_materials_for_order(order_id):
    """
    案件の分割計画に対してBOM展開を行い、材料所要量を生成する。

    分割計画の各加工日に対して:
      必要数量 = 分割数量 × 員数
      支給予定日 = 加工日 - 支給運送LT

    戻り値: { 'created_count': int, 'errors': [...] }
    """
    results = {'created_count': 0, 'errors': []}

    try:
        order = OutsourceOrder.objects.select_related('item', 'item__subcontractor').get(id=order_id)
    except OutsourceOrder.DoesNotExist:
        results['errors'].append('案件が見つかりません')
        return results

    if not order.item:
        results['errors'].append('品目マスタが未紐付けです')
        return results

    bom_lines = OutsourceBOM.objects.filter(item=order.item)
    if not bom_lines.exists():
        results['errors'].append('BOMが未登録です')
        return results

    splits = order.splits.all()
    if not splits.exists():
        results['errors'].append('分割計画が未登録です')
        return results

    supply_transport_lt = order.item.subcontractor.transport_lt_supply
    daiso_calendar = Calendar.objects.filter(calendar_code__iexact='daiso').first()

    # 既存の材料所要量を削除（再生成）
    MaterialRequirement.objects.filter(split__order=order).delete()

    for split in splits:
        for bom in bom_lines:
            required_qty = Decimal(str(split.qty)) * bom.quantity_per
            supply_date = split.process_date - timedelta(days=supply_transport_lt)
            supplier_calendar = getattr(getattr(bom, 'supplier', None), 'calendar', None)
            calc_calendar = supplier_calendar or daiso_calendar
            material_due_date = subtract_working_days(supply_date, 1, calc_calendar)

            MaterialRequirement.objects.create(
                split=split,
                material_code=bom.material_code,
                material_name=bom.material_name,
                supplier_name=bom.supplier_name,
                required_qty=required_qty,
                material_due_date=material_due_date,
                supply_date=supply_date,
            )
            results['created_count'] += 1

    return results


def explode_materials_for_orders(order_ids):
    """複数案件のBOM展開を一括実行"""
    total_results = {'created_count': 0, 'errors': [], 'order_results': []}

    for order_id in order_ids:
        result = explode_materials_for_order(order_id)
        total_results['created_count'] += result['created_count']
        total_results['order_results'].append({
            'order_id': order_id,
            **result,
        })
        if result['errors']:
            total_results['errors'].extend(
                [f"案件ID {order_id}: {e}" for e in result['errors']]
            )

    return total_results
