from django.db import models
from masters.models import Calendar, Customer, Product


class ShipmentActual(models.Model):
    """出荷実績（受注と独立）"""
    id = models.BigAutoField(primary_key=True)
    shipment_date = models.DateField(verbose_name='出荷日')
    product = models.ForeignKey(
        Product, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='製品'
    )
    product_code = models.CharField(max_length=50, verbose_name='品番コード')
    customer = models.ForeignKey(
        Customer, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='得意先'
    )
    customer_code = models.CharField(max_length=20, null=True, blank=True, verbose_name='得意先コード')
    ship_to_code = models.CharField(max_length=40, null=True, blank=True, verbose_name='納入先コード')
    quantity = models.DecimalField(max_digits=14, decimal_places=3, verbose_name='出荷実績数')
    remark = models.CharField(max_length=200, null=True, blank=True, verbose_name='備考')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        db_table = 't_shipment_actual'
        verbose_name = '出荷実績'
        verbose_name_plural = '出荷実績'
        indexes = [
            models.Index(fields=['shipment_date']),
            models.Index(fields=['product_code']),
            models.Index(fields=['customer_code']),
            models.Index(fields=['ship_to_code']),
        ]

    def __str__(self):
        return f"{self.product_code} {self.shipment_date} {self.quantity}"


class ShipmentActualSplit(models.Model):
    """出荷実績の生産日・注番内訳"""
    id = models.BigAutoField(primary_key=True)
    shipment_actual = models.ForeignKey(
        ShipmentActual, on_delete=models.CASCADE, related_name='splits', verbose_name='出荷実績'
    )
    line_no = models.PositiveIntegerField(default=1, verbose_name='行番号')
    production_date = models.DateField(verbose_name='生産日')
    quantity = models.DecimalField(max_digits=14, decimal_places=3, verbose_name='数量')
    source_order_no = models.CharField(max_length=50, null=True, blank=True, verbose_name='注番')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        db_table = 't_shipment_actual_split'
        verbose_name = '出荷実績内訳'
        verbose_name_plural = '出荷実績内訳'
        ordering = ['shipment_actual_id', 'line_no', 'id']
        indexes = [
            models.Index(fields=['shipment_actual', 'line_no']),
            models.Index(fields=['production_date']),
            models.Index(fields=['source_order_no']),
        ]

    def __str__(self):
        return f"{self.shipment_actual_id} {self.production_date} {self.quantity} {self.source_order_no or ''}".strip()


class ShipmentActualHistory(models.Model):
    """出荷実績の修正履歴"""
    ACTION_CHOICES = [
        ('CREATE', '作成'),
        ('UPDATE', '更新'),
        ('DELETE', '削除'),
    ]

    id = models.BigAutoField(primary_key=True)
    shipment_actual = models.ForeignKey(
        ShipmentActual, on_delete=models.CASCADE, related_name='histories', verbose_name='出荷実績'
    )
    action = models.CharField(max_length=10, choices=ACTION_CHOICES, verbose_name='操作')
    shipment_date = models.DateField(verbose_name='出荷日')
    product_code = models.CharField(max_length=50, verbose_name='品番コード')
    customer_code = models.CharField(max_length=20, null=True, blank=True, verbose_name='得意先コード')
    ship_to_code = models.CharField(max_length=40, null=True, blank=True, verbose_name='納入先コード')
    quantity = models.DecimalField(max_digits=14, decimal_places=3, verbose_name='出荷実績数')
    remark = models.CharField(max_length=200, null=True, blank=True, verbose_name='備考')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='記録日時')

    class Meta:
        db_table = 't_shipment_actual_history'
        verbose_name = '出荷実績履歴'
        verbose_name_plural = '出荷実績履歴'
        indexes = [
            models.Index(fields=['shipment_actual', 'created_at']),
        ]

    def __str__(self):
        return f"{self.shipment_actual_id} {self.action} {self.shipment_date}"


class ShipToLeadTime(models.Model):
    """納入地別出荷加算日数"""
    id = models.BigAutoField(primary_key=True)
    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE, verbose_name='顧客'
    )
    ship_to_code = models.CharField(max_length=40, verbose_name='納入先コード')
    ship_to_name = models.CharField(max_length=100, blank=True, default='', verbose_name='納入地名')
    additional_days = models.PositiveIntegerField(default=0, verbose_name='出荷加算日数')
    calendar = models.ForeignKey(
        Calendar, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name='カレンダ',
    )
    is_active = models.BooleanField(default=True, verbose_name='有効')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        db_table = 'm_ship_to_lead_time'
        verbose_name = '納入地別出荷加算日数'
        verbose_name_plural = '納入地別出荷加算日数'
        unique_together = [('customer', 'ship_to_code')]
        ordering = ['customer__customer_code', 'ship_to_code']

    def __str__(self):
        return f"{self.customer.customer_code} {self.ship_to_code}({self.ship_to_name}) +{self.additional_days}日"


class DeliveryProgress(models.Model):
    """出荷進捗（出荷指示書用）"""
    id = models.BigAutoField(primary_key=True)
    order = models.ForeignKey('orders.Order', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='受注')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='製品')
    order_date = models.DateTimeField(verbose_name='出荷日')
    order_quantity = models.IntegerField(verbose_name='受注数量')
    shipped_quantity = models.IntegerField(default=0, verbose_name='出荷済数量')
    remark = models.CharField(max_length=200, null=True, blank=True, verbose_name='備考')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        db_table = 't_delivery_progress'
        verbose_name = '出荷進捗'
        verbose_name_plural = '出荷進捗'
        indexes = [
            models.Index(fields=['order_date']),
            models.Index(fields=['product']),
        ]

    def __str__(self):
        product_code = self.product.product_code if self.product else '?'
        return f"{product_code} {self.order_date.date()} {self.order_quantity}個"


class KubotaSakaiDeliveryProgress(models.Model):
    """クボタ堺配送進捗（品番×納入地×日付）

    進捗 = 前日進捗 - 需要 + 便振分 + 調整
    需要: KubotaSakaiDueAdjustment.delivery_qty を品番×納入地×日付で合算
    便振分: KubotaSakaiTripAssignment.qty を品番×納入地×日付で合算
    """
    id = models.BigAutoField(primary_key=True)
    plan_date = models.DateField(verbose_name='日付')
    product_code = models.CharField(max_length=50, verbose_name='製品コード')
    ship_to_code = models.CharField(max_length=40, verbose_name='納入地コード')
    demand_qty = models.IntegerField(default=0, verbose_name='需要数')
    assigned_qty = models.IntegerField(default=0, verbose_name='便振分数')
    adjust_qty = models.IntegerField(default=0, verbose_name='調整数')
    progress_qty = models.IntegerField(default=0, verbose_name='進捗')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        db_table = 't_kubota_sakai_delivery_progress'
        verbose_name = 'クボタ堺配送進捗'
        verbose_name_plural = 'クボタ堺配送進捗'
        unique_together = [('plan_date', 'product_code', 'ship_to_code')]
        indexes = [
            models.Index(fields=['product_code', 'ship_to_code', 'plan_date']),
        ]

    def __str__(self):
        return f"{self.product_code} {self.ship_to_code} {self.plan_date} 進捗:{self.progress_qty}"


class KubotaSakaiTripDisplaySetting(models.Model):
    """クボタ堺便計画の表示順・色設定（品番×納入地）。"""

    id = models.BigAutoField(primary_key=True)
    product_code = models.CharField(max_length=50, verbose_name='製品コード')
    ship_to_code = models.CharField(max_length=40, blank=True, default='', verbose_name='納入地コード')
    display_order = models.IntegerField(default=0, verbose_name='表示順')
    bg_color = models.CharField(max_length=10, blank=True, default='', verbose_name='行背景色')
    text_color = models.CharField(max_length=10, blank=True, default='', verbose_name='行文字色')
    plus_bg_color = models.CharField(max_length=10, blank=True, default='', verbose_name='追加ボタン背景色')
    plus_text_color = models.CharField(max_length=10, blank=True, default='', verbose_name='追加ボタン文字色')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        db_table = 't_kubota_sakai_trip_display_setting'
        verbose_name = 'クボタ堺便計画表示設定'
        verbose_name_plural = 'クボタ堺便計画表示設定'
        unique_together = [('product_code', 'ship_to_code')]
        ordering = ['display_order', 'product_code', 'ship_to_code']
        indexes = [
            models.Index(fields=['display_order', 'product_code']),
            models.Index(fields=['product_code', 'ship_to_code']),
        ]

    def __str__(self):
        return f"{self.product_code} {self.ship_to_code} ({self.display_order})"
