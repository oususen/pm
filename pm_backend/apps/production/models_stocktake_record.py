from django.conf import settings
from django.db import models


class StocktakeRecord(models.Model):
    """棚卸現物入力の記録"""

    stocktake_date = models.DateField(verbose_name='棚卸日')
    product = models.ForeignKey('masters.Product', on_delete=models.CASCADE, related_name='stocktake_records')
    line = models.ForeignKey('masters.Line', on_delete=models.SET_NULL, null=True, blank=True, related_name='stocktake_records')
    process = models.ForeignKey('masters.Process', on_delete=models.SET_NULL, null=True, blank=True, related_name='stocktake_records')
    system_stock_qty = models.IntegerField(default=0, verbose_name='机上在庫')
    system_progress_qty = models.IntegerField(default=0, verbose_name='机上進度')
    actual_stock_qty = models.IntegerField(default=0, verbose_name='現物数')
    note = models.CharField(max_length=255, blank=True, default='', verbose_name='備考')
    recorder_name = models.CharField(max_length=50, blank=True, default='', verbose_name='記入者名')
    counter_name = models.CharField(max_length=50, blank=True, default='', verbose_name='カウンター名')
    area_name = models.CharField(max_length=50, blank=True, default='', verbose_name='入力エリア')
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='stocktake_record_updates',
        verbose_name='更新者',
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')

    class Meta:
        db_table = 'production_stocktake_record'
        verbose_name = '棚卸現物入力'
        verbose_name_plural = '棚卸現物入力'
        constraints = []
        indexes = [
            models.Index(fields=['stocktake_date', 'updated_at']),
            models.Index(fields=['product', 'stocktake_date']),
        ]

    def __str__(self):
        product_code = getattr(self.product, 'product_code', '')
        return f'{self.stocktake_date} {product_code}'


class StocktakeRecorder(models.Model):
    """棚卸記入者（日ごと）"""

    stocktake_date = models.DateField(verbose_name='棚卸日')
    name = models.CharField(max_length=50, verbose_name='記入者名')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'production_stocktake_recorder'
        constraints = [
            models.UniqueConstraint(
                fields=['stocktake_date', 'name'],
                name='uniq_stocktake_recorder',
            )
        ]
        ordering = ['name']

    def __str__(self):
        return f'{self.stocktake_date} {self.name}'


class StocktakeCounter(models.Model):
    """棚卸カウンター（日ごと）"""

    stocktake_date = models.DateField(verbose_name='棚卸日')
    name = models.CharField(max_length=50, verbose_name='カウンター名')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'production_stocktake_counter'
        constraints = [
            models.UniqueConstraint(
                fields=['stocktake_date', 'name'],
                name='uniq_stocktake_counter',
            )
        ]
        ordering = ['name']

    def __str__(self):
        return f'{self.stocktake_date} {self.name}'


class StocktakeArea(models.Model):
    """棚卸エリア（置き場のグルーピング）"""
    name = models.CharField(max_length=50, unique=True, verbose_name='エリア名')
    locations = models.JSONField(default=list, verbose_name='所属置き場リスト')
    sort_order = models.IntegerField(default=0, verbose_name='表示順')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        db_table = 'production_stocktake_area'
        verbose_name = '棚卸エリア'
        verbose_name_plural = '棚卸エリア'
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name


class StocktakeLayoutConfig(models.Model):
    """棚卸レイアウト配置設定"""

    name = models.CharField(max_length=50, default='default', unique=True, verbose_name='設定名')
    cols = models.IntegerField(default=8, verbose_name='列数')
    row_count = models.IntegerField(default=6, verbose_name='行数')
    cells = models.JSONField(default=dict, verbose_name='セル配置')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'production_stocktake_layout_config'

    def __str__(self):
        return self.name
