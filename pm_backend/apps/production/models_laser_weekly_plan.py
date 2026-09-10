from django.conf import settings
from django.db import models
from masters.models import Line, Product
from .models_laser_pattern import LaserPattern


class LaserWeeklyPlanTarget(models.Model):
    SOURCE_ORDER_QTY = 'ORDER_QTY'
    SOURCE_PLAN_QTY = 'PLAN_QTY'
    SOURCE_CHOICES = [(SOURCE_ORDER_QTY, '需要（order_qty）'), (SOURCE_PLAN_QTY, '後工程計画（plan_qty）')]
    downstream_line = models.ForeignKey(Line, on_delete=models.PROTECT, related_name='laser_weekly_targets')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='laser_weekly_targets')
    laser_pattern = models.ForeignKey(LaserPattern, on_delete=models.PROTECT, related_name='weekly_plan_targets')
    finished_product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='laser_weekly_finished_targets')
    lead_time_days = models.PositiveIntegerField(default=0, verbose_name='LT(日)')
    quantity_source = models.CharField(max_length=10, choices=SOURCE_CHOICES, default=SOURCE_ORDER_QTY, verbose_name='数量取得元')
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 't_laser_weekly_plan_target'
        ordering = ['sort_order', 'downstream_line_id', 'product_id']
        constraints = [models.UniqueConstraint(fields=['downstream_line', 'product', 'laser_pattern', 'finished_product'], name='laser_weekly_target_unique')]


class LaserWeeklyPlanManualQuantity(models.Model):
    target = models.ForeignKey(LaserWeeklyPlanTarget, on_delete=models.CASCADE, related_name='manual_quantities')
    plan_date = models.DateField(verbose_name='レーザ計画日')
    sheets = models.PositiveIntegerField(verbose_name='手動回数')

    class Meta:
        db_table = 't_laser_weekly_plan_manual_quantity'
        constraints = [models.UniqueConstraint(fields=['target', 'plan_date'], name='laser_weekly_manual_quantity_unique')]


class LaserWeeklyPatternManualQuantity(models.Model):
    laser_pattern = models.ForeignKey(LaserPattern, on_delete=models.CASCADE, related_name='weekly_manual_quantities')
    plan_date = models.DateField(verbose_name='レーザ計画日')
    sheets = models.PositiveIntegerField(verbose_name='手動回数')

    class Meta:
        db_table = 't_laser_weekly_pattern_manual_quantity'
        constraints = [models.UniqueConstraint(fields=['laser_pattern', 'plan_date'], name='laser_weekly_pattern_manual_quantity_unique')]


class LaserWeeklyPatternInitialProgress(models.Model):
    laser_pattern = models.ForeignKey(LaserPattern, on_delete=models.CASCADE, related_name='weekly_initial_progress')
    week_start_date = models.DateField(verbose_name='週開始日')
    initial_progress = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='期首進度')
    is_locked = models.BooleanField(default=False, verbose_name='ロック')

    class Meta:
        db_table = 't_laser_weekly_pattern_initial_progress'
        constraints = [models.UniqueConstraint(fields=['laser_pattern', 'week_start_date'], name='laser_weekly_initial_progress_unique')]


class LaserWeeklyPatternDailyProgress(models.Model):
    laser_pattern = models.ForeignKey(LaserPattern, on_delete=models.CASCADE, related_name='weekly_daily_progress')
    progress_date = models.DateField(verbose_name='日付')
    progress = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='進度')

    class Meta:
        db_table = 't_laser_weekly_pattern_daily_progress'
        constraints = [models.UniqueConstraint(fields=['laser_pattern', 'progress_date'], name='laser_weekly_daily_progress_unique')]


class LaserWeeklyMaterialGroup(models.Model):
    group_name = models.CharField(max_length=120, unique=True)
    material_type = models.CharField(max_length=20, blank=True, default='')
    sheets_per_material = models.DecimalField(max_digits=14, decimal_places=3, default=1)
    patterns = models.ManyToManyField(LaserPattern, related_name='weekly_material_groups', blank=True)
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 't_laser_weekly_material_group'
        ordering = ['sort_order', 'group_name']


class LaserWeeklyMaterialOrderProgress(models.Model):
    SUPPLIER_SATO = 'SATO'
    SUPPLIER_MEISEI = 'MEISEI'
    SUPPLIER_CHOICES = [(SUPPLIER_SATO, '佐藤商事'), (SUPPLIER_MEISEI, '名成鋼機')]

    plan_start_date = models.DateField(verbose_name='計画開始日', null=True, blank=True)
    material = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='laser_weekly_order_progresses')
    required_date = models.DateField(verbose_name='必要日', null=True, blank=True)
    delivery_date = models.DateField(verbose_name='納期')
    supplier = models.CharField(max_length=10, choices=SUPPLIER_CHOICES, verbose_name='仕入先')
    required_sheets = models.PositiveIntegerField(default=0, verbose_name='必要枚数')
    lot_multiple = models.PositiveIntegerField(default=0, verbose_name='発注倍数')
    required_lots = models.PositiveIntegerField(default=0, verbose_name='必要ロット数')
    order_lots = models.PositiveIntegerField(default=0, verbose_name='発注ロット数')
    order_sheets = models.PositiveIntegerField(default=0, verbose_name='端数枚数')
    is_manual = models.BooleanField(default=False, verbose_name='手動追加')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 't_laser_weekly_material_order_progress'
        constraints = [
            models.UniqueConstraint(
                fields=['plan_start_date', 'material', 'required_date', 'supplier'],
                condition=models.Q(is_manual=False),
                name='laser_weekly_material_order_progress_unique',
            ),
            models.UniqueConstraint(
                fields=['material', 'delivery_date', 'supplier'],
                condition=models.Q(is_manual=True),
                name='laser_weekly_material_order_manual_unique',
            ),
        ]


class LaserWeeklyMaterialInitialProgress(models.Model):
    plan_start_date = models.DateField(verbose_name='計画開始日')
    material = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='laser_weekly_initial_progresses')
    initial_progress = models.IntegerField(default=0, verbose_name='期首進度')
    is_locked = models.BooleanField(default=False, verbose_name='ロック')

    class Meta:
        db_table = 't_laser_weekly_material_initial_progress'
        constraints = [models.UniqueConstraint(fields=['plan_start_date', 'material'], name='laser_weekly_material_initial_progress_unique')]


class LaserMaterialOrderEmailConfig(models.Model):
    supplier = models.CharField(
        max_length=10,
        choices=LaserWeeklyMaterialOrderProgress.SUPPLIER_CHOICES,
        unique=True,
        verbose_name='仕入先',
    )
    body = models.TextField(blank=True, default='', verbose_name='本文')
    cc_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='laser_material_order_email_configs',
        verbose_name='CCユーザー',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 't_laser_material_order_email_config'
        ordering = ['supplier']
