"""実績サイクル時間モデル"""
from django.db import models
from masters.models import Process, Product, Line


class ActualCycleTime(models.Model):
    """工程別・製品別の実績平均サイクル時間"""

    id = models.BigAutoField(primary_key=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name='製品')
    process = models.ForeignKey(Process, on_delete=models.CASCADE, verbose_name='工程')
    line = models.ForeignKey(Line, on_delete=models.CASCADE, verbose_name='ライン')
    calc_from_date = models.DateField(verbose_name='計算期間FROM')
    calc_to_date = models.DateField(verbose_name='計算期間TO')
    total_qty = models.DecimalField(max_digits=12, decimal_places=3, verbose_name='出来高合計')
    total_seconds = models.IntegerField(verbose_name='有効稼働時間合計(秒)')
    cycle_time_sec = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='平均サイクル時間(秒/個)')
    adjusted_cycle_time_sec = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        verbose_name='補正サイクル時間(秒/個)',
        help_text='実績CT ÷ (稼働率/100)'
    )
    operating_rate_applied = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        verbose_name='適用稼働率(%)',
    )
    calculated_at = models.DateTimeField(auto_now=True, verbose_name='計算日時')

    class Meta:
        db_table = 't_actual_cycle_time'
        verbose_name = '実績サイクル時間'
        verbose_name_plural = '実績サイクル時間'
        unique_together = [('product', 'process', 'line', 'calc_from_date', 'calc_to_date')]

    def __str__(self):
        return f"{self.process} {self.product} {self.cycle_time_sec}秒/個"


class FinishedProductCycleTime(models.Model):
    """完成品の工程別サイクル時間（BOM展開後）"""

    id = models.BigAutoField(primary_key=True)
    finished_product = models.ForeignKey(
        Product, on_delete=models.CASCADE,
        related_name='finished_cycle_times',
        verbose_name='完成品',
    )
    process = models.ForeignKey(Process, on_delete=models.CASCADE, verbose_name='工程')
    line = models.ForeignKey(Line, on_delete=models.CASCADE, verbose_name='ライン')
    cycle_time_sec = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='サイクル時間(秒/個)')
    use_adjusted = models.BooleanField(default=False, verbose_name='補正CT使用')
    calc_from_date = models.DateField(verbose_name='計算期間FROM')
    calc_to_date = models.DateField(verbose_name='計算期間TO')
    calculated_at = models.DateTimeField(auto_now=True, verbose_name='計算日時')

    class Meta:
        db_table = 't_finished_product_cycle_time'
        verbose_name = '完成品サイクル時間'
        verbose_name_plural = '完成品サイクル時間'
        unique_together = [('finished_product', 'process', 'line', 'calc_from_date', 'calc_to_date')]

    def __str__(self):
        return f"{self.finished_product} @{self.process} {self.cycle_time_sec}秒/個"
