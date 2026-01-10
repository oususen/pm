from django.db import models
from masters.models import Customer, Product


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
