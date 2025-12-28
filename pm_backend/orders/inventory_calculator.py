"""
在庫計算ロジック
LineBacklogの在庫・計画在庫を再計算するためのユーティリティ
"""
from datetime import datetime, timedelta
from decimal import Decimal
from django.db.models import F, Sum
from .models_line_backlog import LineBacklog
from .models_scrap import ScrapRecord, ScrapRecordDetail
from masters.models import BOM


def aggregate_scrap_to_backlog(line_id=None, start_date=None, end_date=None):
    """
    ScrapRecordとScrapRecordDetailから仕損数を集計し、
    LineBacklog.scrap_qtyに反映

    Args:
        line_id: 対象ラインID（Noneの場合は全ライン）
        start_date: 開始日
        end_date: 終了日
    """
    # まず既存のscrap_qtyをゼロリセット
    reset_filter = {}
    if line_id:
        reset_filter['line_id'] = line_id
    if start_date and end_date:
        reset_filter['plan_date__range'] = [start_date, end_date]

    LineBacklog.objects.filter(**reset_filter).update(scrap_qty=0)

    # 自工程仕損の集計
    scrap_filter = {
        'disposition_status': 'REJECTED',  # 仕損確定のみ
        'plan_date__isnull': False,
    }
    if line_id:
        scrap_filter['line_id'] = line_id
    if start_date and end_date:
        scrap_filter['plan_date__range'] = [start_date, end_date]

    scrap_records = ScrapRecord.objects.filter(**scrap_filter).select_related('product', 'line', 'process')

    for scrap in scrap_records:
        if not scrap.product or not scrap.line or not scrap.process:
            continue

        LineBacklog.objects.filter(
            plan_date=scrap.plan_date,
            product=scrap.product,
            line=scrap.line,
            process=scrap.process,
        ).update(scrap_qty=F('scrap_qty') + int(scrap.qty))

    # 後工程仕損の展開分
    detail_filter = {
        'scrap_record__disposition_status': 'REJECTED',
        'scrap_record__plan_date__isnull': False,
    }
    if line_id:
        detail_filter['line_id'] = line_id
    if start_date and end_date:
        detail_filter['scrap_record__plan_date__range'] = [start_date, end_date]

    details = ScrapRecordDetail.objects.filter(**detail_filter).select_related('scrap_record', 'product')

    for detail in details:
        if not detail.product or not detail.line_id or not detail.process_id:
            continue

        LineBacklog.objects.filter(
            plan_date=detail.scrap_record.plan_date,
            product=detail.product,
            line_id=detail.line_id,
            process_id=detail.process_id,
        ).update(scrap_qty=F('scrap_qty') + int(detail.deduct_qty))


def calculate_actual_shipment(backlog):
    """
    実績出庫数を後工程の実績から計算

    Args:
        backlog: LineBacklogインスタンス

    Returns:
        int: 実績出庫数（計算できない場合はNone）
    """
    from masters.models import BOMItem

    # この製品を子製品として使用しているBOMItemを検索
    parent_bom_items = BOMItem.objects.filter(
        child_product=backlog.product,
        bom__is_active=True
    ).select_related('bom__parent_product')

    if not parent_bom_items.exists():
        return None

    total_shipment = 0
    found_actual = False

    for bom_item in parent_bom_items:
        # 後工程の実績を取得
        # ※ リードタイムを考慮する場合は plan_date を調整
        downstream_backlogs = LineBacklog.objects.filter(
            product=bom_item.bom.parent_product,
            plan_date=backlog.plan_date,  # 同日（またはLT調整）
        )

        for downstream in downstream_backlogs:
            if downstream.actual_qty and downstream.actual_qty > 0:
                # 実績 × BOM数量 = 出庫数
                quantity = bom_item.quantity or Decimal('1')
                shipment = int(downstream.actual_qty * quantity)
                total_shipment += shipment
                found_actual = True

    return total_shipment if found_actual else None


def has_downstream_actual(backlog):
    """
    後工程に実績が入力されているかチェック

    Args:
        backlog: LineBacklogインスタンス

    Returns:
        bool: 後工程に実績があればTrue
    """
    from masters.models import BOMItem

    parent_bom_items = BOMItem.objects.filter(
        child_product=backlog.product,
        bom__is_active=True
    )

    for bom_item in parent_bom_items:
        downstream_backlogs = LineBacklog.objects.filter(
            product=bom_item.bom.parent_product,
            plan_date=backlog.plan_date,
            actual_qty__gt=0
        )
        if downstream_backlogs.exists():
            return True

    return False


def recalculate_stock_qty(line_id, product_id, start_date, end_date):
    """
    実在庫を日次で再計算

    Args:
        line_id: ラインID
        product_id: 製品ID
        start_date: 開始日
        end_date: 終了日
    """
    backlogs = LineBacklog.objects.filter(
        line_id=line_id,
        product_id=product_id,
        plan_date__range=[start_date, end_date]
    ).order_by('plan_date')

    prev_stock = 0

    for backlog in backlogs:
        # 前日在庫を取得
        if backlog.plan_date > start_date:
            prev_day = backlog.plan_date - timedelta(days=1)
            prev = LineBacklog.objects.filter(
                line_id=line_id,
                product_id=product_id,
                plan_date=prev_day
            ).first()
            prev_stock = prev.stock_qty if prev else 0

        # 実在庫計算
        actual_production = backlog.actual_qty or 0

        # 実績出庫数を計算
        actual_shipment = backlog.actual_shipment_qty or 0
        if actual_shipment == 0:
            # actual_shipment_qtyが未設定の場合、後工程から計算
            calculated_shipment = calculate_actual_shipment(backlog)
            if calculated_shipment is not None:
                actual_shipment = calculated_shipment
                # 計算結果を保存
                backlog.actual_shipment_qty = actual_shipment

        backlog.stock_qty = (
            prev_stock
            + actual_production
            - actual_shipment
            + (backlog.adjust_qty or 0)
            - (backlog.scrap_qty or 0)
        )
        backlog.save(update_fields=['stock_qty', 'actual_shipment_qty'])

        prev_stock = backlog.stock_qty


def recalculate_planned_stock_qty(line_id, product_id, start_date, end_date):
    """
    計画在庫を日次で再計算（時制考慮版）
    - 過去（plan_date < today）:
        - 実績あり → 実績ベース計算
        - 実績なし → 生産・出庫ゼロとして計算
    - 今日以降（plan_date >= today）: 計画ベース計算

    Args:
        line_id: ラインID
        product_id: 製品ID
        start_date: 開始日
        end_date: 終了日
    """
    backlogs = LineBacklog.objects.filter(
        line_id=line_id,
        product_id=product_id,
        plan_date__range=[start_date, end_date]
    ).order_by('plan_date')

    today = datetime.now().date()
    prev_planned = 0

    for backlog in backlogs:
        # 前日の計画在庫を取得
        if backlog.plan_date > start_date:
            prev_day = backlog.plan_date - timedelta(days=1)
            prev = LineBacklog.objects.filter(
                line_id=line_id,
                product_id=product_id,
                plan_date=prev_day
            ).first()
            prev_planned = prev.planned_stock_qty if prev else 0

        # 時制による計算分岐
        if backlog.plan_date < today:
            # ===== 過去：実績ベース =====
            if backlog.actual_qty and backlog.actual_qty > 0:
                # 実績あり：実績ベースで計算
                actual_production = backlog.actual_qty

                # 実績出庫数を取得
                actual_shipment = backlog.actual_shipment_qty or 0
                if actual_shipment == 0:
                    calculated_shipment = calculate_actual_shipment(backlog)
                    if calculated_shipment is not None:
                        actual_shipment = calculated_shipment
                    elif has_downstream_actual(backlog):
                        # 後工程に実績があるなら、計画値で代用
                        actual_shipment = backlog.demand_qty_plan or backlog.order_qty or 0
                    else:
                        # 後工程も実績なし = 出庫ゼロ
                        actual_shipment = 0

                backlog.planned_stock_qty = (
                    prev_planned
                    + actual_production
                    - actual_shipment
                    + (backlog.adjust_qty or 0)
                    - (backlog.scrap_qty or 0)
                )
            else:
                # 実績なし：生産しなかった
                # しかし、計画出庫（後工程の需要）は考慮する
                planned_shipment = backlog.demand_qty_plan or backlog.order_qty or 0
                backlog.planned_stock_qty = (
                    prev_planned
                    + 0  # 生産ゼロ
                    - planned_shipment  # 計画出庫（後工程の需要）
                    + (backlog.adjust_qty or 0)
                    - (backlog.scrap_qty or 0)
                )
        else:
            # ===== 今日以降：計画ベース =====
            backlog.planned_stock_qty = (
                prev_planned
                + (backlog.plan_qty or 0)
                - (backlog.demand_qty_plan or backlog.order_qty or 0)
                + (backlog.adjust_qty or 0)
                # 仕損は含めない（未来の仕損は予測不可）
            )

        backlog.save(update_fields=['planned_stock_qty'])
        prev_planned = backlog.planned_stock_qty


def recalculate_inventory_for_line(line_id, start_date, end_date):
    """
    指定ラインの全製品について在庫を再計算

    Args:
        line_id: ラインID
        start_date: 開始日
        end_date: 終了日
    """
    import logging
    logger = logging.getLogger(__name__)

    logger.info(f"在庫再計算開始: line_id={line_id}, {start_date} ~ {end_date}")

    # まず仕損数を集計
    aggregate_scrap_to_backlog(line_id, start_date, end_date)

    # 製品ごとに在庫計算
    product_ids = LineBacklog.objects.filter(
        line_id=line_id,
        plan_date__range=[start_date, end_date]
    ).values_list('product_id', flat=True).distinct()

    logger.info(f"対象製品数: {len(product_ids)}")

    for product_id in product_ids:
        logger.info(f"製品ID {product_id} の在庫計算中...")

        # 実在庫を計算
        recalculate_stock_qty(line_id, product_id, start_date, end_date)

        # 計画在庫を計算
        recalculate_planned_stock_qty(line_id, product_id, start_date, end_date)

    logger.info("在庫再計算完了")
