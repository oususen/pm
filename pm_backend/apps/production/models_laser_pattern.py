from django.db import models

from masters.models import Equipment, Product


class LaserPattern(models.Model):
    """レーザ加工パターン（ヘッダ）"""

    id = models.BigAutoField(primary_key=True)
    pattern_no = models.CharField(max_length=50, unique=True, verbose_name='パターン番号')
    material = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name='laser_patterns_as_material',
        verbose_name='使用材料',
    )
    equipment = models.ForeignKey(
        Equipment,
        on_delete=models.PROTECT,
        related_name='laser_patterns',
        verbose_name='使用設備',
    )
    process_time_min = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='加工時間(分/回)',
    )
    processing_freq_pattern = models.ForeignKey(
        'production.LaserProcessingFreqPattern',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='laser_patterns',
        verbose_name='加工頻度パターン',
    )
    processing_start_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='加工頻度適用開始日',
    )
    is_budget_target = models.BooleanField(default=False, verbose_name='材料予算用')
    is_active = models.BooleanField(default=True, verbose_name='有効')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        db_table = 't_laser_pattern'
        verbose_name = 'レーザパターン'
        verbose_name_plural = 'レーザパターン'
        ordering = ['pattern_no']

    def __str__(self):
        return self.pattern_no


class LaserPatternComponent(models.Model):
    """レーザ加工パターン構成部品"""

    id = models.BigAutoField(primary_key=True)
    pattern = models.ForeignKey(
        LaserPattern,
        on_delete=models.CASCADE,
        related_name='component_items',
        verbose_name='レーザパターン',
    )
    component_product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name='laser_pattern_component_items',
        verbose_name='構成部品',
    )
    take_qty = models.DecimalField(max_digits=14, decimal_places=3, default=0, verbose_name='取り数')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        db_table = 't_laser_pattern_component'
        verbose_name = 'レーザパターン構成部品'
        verbose_name_plural = 'レーザパターン構成部品'
        unique_together = [['pattern', 'component_product']]
        ordering = ['id']

    def __str__(self):
        return f'{self.pattern.pattern_no} - {self.component_product.product_code}'


class LaserPatternFinishedProduct(models.Model):
    """レーザ加工パターン完成品紐づけ"""

    id = models.BigAutoField(primary_key=True)
    pattern = models.ForeignKey(
        LaserPattern,
        on_delete=models.CASCADE,
        related_name='finished_items',
        verbose_name='レーザパターン',
    )
    finished_product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name='laser_pattern_finished_items',
        verbose_name='完成品',
    )
    units_per_shot = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        default=0,
        verbose_name='完成品取り数',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        db_table = 't_laser_pattern_finished'
        verbose_name = 'レーザパターン完成品'
        verbose_name_plural = 'レーザパターン完成品'
        unique_together = [['pattern', 'finished_product']]
        ordering = ['id']

    def __str__(self):
        return f'{self.pattern.pattern_no} - {self.finished_product.product_code}'
