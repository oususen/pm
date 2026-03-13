from django.conf import settings
from django.db import models

from masters.models import Equipment, Product

from .models_laser_pattern import LaserPattern


class LaserActual(models.Model):
    """レーザー実績ヘッダ（保存時スナップショット保持）"""

    OPERATOR_ACTION_START = 'START'
    OPERATOR_ACTION_END = 'END'
    OPERATOR_ACTION_PAUSE = 'PAUSE'
    OPERATOR_ACTION_TEMP_END = 'TEMP_END'
    OPERATOR_ACTION_RESUME = 'RESUME'
    OPERATOR_ACTION_CHOICES = [
        (OPERATOR_ACTION_START, '開始'),
        (OPERATOR_ACTION_END, '終了'),
        (OPERATOR_ACTION_PAUSE, '中断'),
        (OPERATOR_ACTION_TEMP_END, '一時終了'),
        (OPERATOR_ACTION_RESUME, '再開'),
    ]

    id = models.BigAutoField(primary_key=True)
    work_date = models.DateField(verbose_name='作業日')
    equipment = models.ForeignKey(
        Equipment,
        on_delete=models.PROTECT,
        related_name='laser_actuals',
        verbose_name='設備',
    )
    pattern = models.ForeignKey(
        LaserPattern,
        on_delete=models.PROTECT,
        related_name='laser_actuals',
        verbose_name='パターン',
    )
    shot_count = models.PositiveIntegerField(verbose_name='回数')
    operator_action = models.CharField(
        max_length=20,
        choices=OPERATOR_ACTION_CHOICES,
        default=OPERATOR_ACTION_END,
        verbose_name='作業時刻',
    )
    operator_action_reason = models.CharField(
        max_length=200,
        blank=True,
        default='',
        verbose_name='作業時刻理由',
    )
    remarks = models.TextField(blank=True, default='', verbose_name='備考')

    # スナップショット（登録時点の値を保持）
    pattern_no = models.CharField(max_length=50, verbose_name='パターン番号')
    equipment_code = models.CharField(max_length=50, blank=True, default='', verbose_name='設備コード')
    equipment_name = models.CharField(max_length=100, blank=True, default='', verbose_name='設備名')
    material = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='laser_actual_materials',
        verbose_name='使用材料',
    )
    material_code = models.CharField(max_length=50, blank=True, default='', verbose_name='使用材料コード')
    material_name = models.CharField(max_length=100, blank=True, default='', verbose_name='使用材料名')
    process_time_per_shot = models.DecimalField(
        max_digits=10,
        decimal_places=1,
        default=0,
        verbose_name='加工時間(分/回)',
    )
    total_process_time = models.DecimalField(
        max_digits=12,
        decimal_places=1,
        default=0,
        verbose_name='総加工時間(分)',
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_laser_actuals',
        verbose_name='作成者',
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='updated_laser_actuals',
        verbose_name='更新者',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        db_table = 't_laser_actual'
        verbose_name = 'レーザー実績'
        verbose_name_plural = 'レーザー実績'
        ordering = ['-work_date', '-created_at', '-id']
        indexes = [
            models.Index(fields=['work_date']),
            models.Index(fields=['equipment']),
            models.Index(fields=['pattern_no']),
        ]

    def __str__(self):
        return f'{self.work_date} {self.pattern_no} x{self.shot_count}'


class LaserActualDetail(models.Model):
    """レーザー実績明細（構成部品/完成品換算）"""

    DETAIL_TYPE_COMPONENT = 'COMPONENT'
    DETAIL_TYPE_FINISHED = 'FINISHED'
    DETAIL_TYPE_CHOICES = [
        (DETAIL_TYPE_COMPONENT, '構成部品'),
        (DETAIL_TYPE_FINISHED, '完成品'),
    ]

    id = models.BigAutoField(primary_key=True)
    actual = models.ForeignKey(
        LaserActual,
        on_delete=models.CASCADE,
        related_name='details',
        verbose_name='レーザー実績',
    )
    detail_type = models.CharField(
        max_length=20,
        choices=DETAIL_TYPE_CHOICES,
        verbose_name='明細種別',
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='laser_actual_details',
        verbose_name='製品',
    )
    product_code = models.CharField(max_length=50, blank=True, default='', verbose_name='製品コード')
    product_name = models.CharField(max_length=100, blank=True, default='', verbose_name='製品名')
    units_per_shot = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        default=0,
        verbose_name='1回あたり数量',
    )
    total_qty = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        default=0,
        verbose_name='換算数量',
    )
    scrap_qty = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        default=0,
        verbose_name='仕損数量',
    )
    scrap_reason = models.CharField(
        max_length=200,
        blank=True,
        default='',
        verbose_name='仕損理由',
    )
    display_order = models.PositiveIntegerField(default=0, verbose_name='表示順')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        db_table = 't_laser_actual_detail'
        verbose_name = 'レーザー実績明細'
        verbose_name_plural = 'レーザー実績明細'
        ordering = ['detail_type', 'display_order', 'id']
        indexes = [
            models.Index(fields=['actual', 'detail_type']),
        ]

    def __str__(self):
        return f'{self.actual_id}:{self.detail_type}:{self.product_code}'
