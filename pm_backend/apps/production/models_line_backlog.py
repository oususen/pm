from django.db import models
from masters.models import Process, Product, Line, RoutingStep


class LineBacklog(models.Model):
    """
    ライン別生産計画テーブル
    需要、計画、実績、在庫、計画在庫を管理する
    """
    plan_date = models.DateField()
    process = models.ForeignKey(Process, on_delete=models.CASCADE, related_name='backlogs')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='line_backlogs')
    line = models.ForeignKey(Line, on_delete=models.CASCADE, related_name='backlogs')

    # 需要（後ラインからの需要、または受注展開からの需要）
    demand_qty_plan = models.IntegerField(default=0)

    # 発注数/受注数（取り込み時に計算される需要数）
    # 最終ライン：LineDemandからの受注数
    # 他ライン：後ラインのplan_qtyを集計 × BOM個数
    order_qty = models.IntegerField(default=0)

    # 計画（ユーザーが入力する生産計画数量）
    plan_qty = models.IntegerField(default=0)

    # 実績（実際の生産数量）
    actual_qty = models.IntegerField(default=0)

    # 在庫
    stock_qty = models.IntegerField(default=0)

    # 計画在庫
    planned_stock_qty = models.IntegerField(default=0)

    # 調整数（手動調整、棚卸差異など）
    adjust_qty = models.IntegerField(default=0, verbose_name="調整数")

    # 仕損数（自工程仕損 + 後工程仕損の展開分）
    scrap_qty = models.IntegerField(default=0, verbose_name="仕損数")

    # 実績出庫数（後工程への実績出庫）
    actual_shipment_qty = models.IntegerField(default=0, verbose_name="実績出庫数")

    # 進度（後工程実績をLT遡りで計算、計画に対する進み/遅れを表す）
    progress_qty = models.IntegerField(default=0, verbose_name="進度")

    # 生産順序番号（日をまたいだ通し番号）
    sequence_no = models.IntegerField(null=True, blank=True)

    # ライン計画との紐付けID（ライン_製品_日付_順番で一意）
    plan_id = models.CharField(max_length=255, null=True, blank=True, db_index=True)

    source_line = models.ForeignKey(Line, on_delete=models.SET_NULL, null=True, blank=True, related_name='backlog_sources')
    source_routing_step = models.ForeignKey(RoutingStep, on_delete=models.SET_NULL, null=True, blank=True, related_name='backlog_sources')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'line_backlog'
        unique_together = [('plan_date', 'process', 'product', 'line', 'sequence_no')]
        indexes = [
            models.Index(fields=['plan_date', 'line']),
        ]

    def __str__(self):
        return f"{self.plan_date} {self.process} {self.product} {self.line} {self.demand_qty_plan}"
