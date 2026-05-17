from django.db import models
from masters.models import Supplier, Calendar
from orders.utils.calendar_utils import add_working_days, subtract_working_days, get_business_today


class Subcontractor(models.Model):
    """外作先マスタ"""
    name = models.CharField('外作先名', max_length=100)
    daily_capacity = models.IntegerField('日キャパ（参考値）', null=True, blank=True)
    transport_lt_supply = models.IntegerField('支給運送LT（日数）', default=1)
    transport_lt_delivery = models.IntegerField('完成品運送LT（日数）', default=1)
    notes = models.TextField('備考', blank=True, default='')
    is_active = models.BooleanField('有効', default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'outsource_subcontractor'
        verbose_name = '外作先'
        verbose_name_plural = '外作先'

    def __str__(self):
        return self.name

class OutsourceItem(models.Model):
    """外作品目マスタ"""
    item_code = models.CharField('品目コード', max_length=50, unique=True)
    product_number = models.CharField('品番', max_length=20, blank=True, default='')
    item_name = models.CharField('品目名称', max_length=200)
    subcontractor = models.ForeignKey(
        Subcontractor, on_delete=models.PROTECT,
        verbose_name='外作先', related_name='items'
    )
    customer_delivery_lt = models.IntegerField('顧客納入LT（日数）', default=2)
    is_active = models.BooleanField('有効', default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'outsource_item'
        verbose_name = '外作品目'
        verbose_name_plural = '外作品目'

    def save(self, *args, **kwargs):
        if self.item_code and not self.product_number:
            code = self.item_code.lstrip('B')
            if len(code) >= 10:
                self.product_number = f'{code[:6]}-{code[6:10]}'
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.item_code} {self.item_name}'


class OutsourceMaterial(models.Model):
    """構成品マスタ"""
    material_code = models.CharField('材料コード', max_length=50, unique=True)
    material_name = models.CharField('材料名称', max_length=200)
    supplier = models.ForeignKey(
        Supplier, on_delete=models.SET_NULL,
        verbose_name='調達先', null=True, blank=True
    )
    supplier_name = models.CharField('調達先名（自動）', max_length=100, blank=True, default='')
    procurement_lt = models.IntegerField('調達LT（日数）', default=7)
    is_active = models.BooleanField('有効', default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'outsource_material'
        verbose_name = '構成品'
        verbose_name_plural = '構成品'
        ordering = ['material_code']

    def save(self, *args, **kwargs):
        if self.supplier:
            self.supplier_name = self.supplier.supplier_name
        super().save(*args, **kwargs)
        self.bom_usages.update(
            material_code=self.material_code,
            material_name=self.material_name,
            supplier=self.supplier,
            supplier_name=self.supplier_name,
            procurement_lt=self.procurement_lt,
        )
        # 既存の材料所要量にも調達先変更を反映（未出庫分のみ）
        MaterialRequirement.objects.filter(
            material_code=self.material_code,
            supplied=False,
        ).update(
            supplier_name=self.supplier_name,
        )

    def __str__(self):
        return f'{self.material_code} {self.material_name}'


class OutsourceBOM(models.Model):
    """外作BOM（品目→材料）"""
    item = models.ForeignKey(
        OutsourceItem, on_delete=models.CASCADE,
        verbose_name='親品目', related_name='bom_lines'
    )
    material = models.ForeignKey(
        OutsourceMaterial, on_delete=models.PROTECT,
        verbose_name='構成品', related_name='bom_usages',
        null=True, blank=True
    )
    material_code = models.CharField('材料コード', max_length=50)
    material_name = models.CharField('材料名称', max_length=200)
    quantity_per = models.DecimalField('員数（親1個あたり）', max_digits=10, decimal_places=4, default=1)
    unit = models.CharField('単位', max_length=20, default='個')
    supplier = models.ForeignKey(
        Supplier, on_delete=models.SET_NULL,
        verbose_name='調達先', null=True, blank=True
    )
    supplier_name = models.CharField('調達先名（自動）', max_length=100, blank=True, default='')
    procurement_lt = models.IntegerField('材料調達LT（日数）', default=7)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'outsource_bom'
        verbose_name = '外作BOM'
        verbose_name_plural = '外作BOM'
        unique_together = ['item', 'material_code']

    def save(self, *args, **kwargs):
        if self.material:
            self.material_code = self.material.material_code
            self.material_name = self.material.material_name
            if not self.supplier and self.material.supplier:
                self.supplier = self.material.supplier
            if self.procurement_lt == 7 and self.material.procurement_lt:
                self.procurement_lt = self.material.procurement_lt
        if self.supplier:
            self.supplier_name = self.supplier.supplier_name
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.item.item_code} → {self.material_code}'


class OutsourceOrder(models.Model):
    """外作受注（案件）"""
    STATUS_CHOICES = [
        ('IMPORTED', '取込済'),
        ('SENT_TO_SUB', '展開送付済'),
        ('SPLIT_REGISTERED', '分割計画登録済'),
        ('IN_PROGRESS', '加工中'),
        ('COMPLETED', '完了'),
    ]

    case_no = models.CharField('案件番号', max_length=100, unique=True)
    item = models.ForeignKey(
        OutsourceItem, on_delete=models.PROTECT,
        verbose_name='品目', related_name='orders',
        null=True, blank=True
    )
    item_code = models.CharField('品目コード', max_length=50)
    item_name = models.CharField('品目名称', max_length=200)
    order_qty = models.IntegerField('受注数量')
    painting_name = models.CharField('塗装名', max_length=100)
    painting_date = models.DateField('塗装日')
    earliest_start = models.DateField('最早着手日', null=True, blank=True)
    latest_finish = models.DateField('最遅完了日', null=True, blank=True)
    status = models.CharField('ステータス', max_length=20, choices=STATUS_CHOICES, default='IMPORTED')
    imported_at = models.DateTimeField('取込日時', auto_now_add=True)
    notes = models.TextField('備考', blank=True, default='')

    class Meta:
        db_table = 'outsource_order'
        verbose_name = '外作受注'
        verbose_name_plural = '外作受注'
        ordering = ['-painting_date', 'item_code']

    def __str__(self):
        return f'{self.case_no} ({self.item_name})'

    def calculate_constraints(self, extra_order_lt=0):
        """制約条件を計算: 最早着手日・最遅完了日"""
        if not self.item:
            return

        # 既定カレンダ（未設定時フォールバック）
        daiso_calendar = Calendar.objects.filter(calendar_code__iexact='daiso').first()

        # 最遅完了日 = 塗装日 - 運送LT（顧客納入）※DAISOカレンダで営業日逆算
        self.latest_finish = subtract_working_days(
            self.painting_date,
            int(self.item.customer_delivery_lt or 0),
            daiso_calendar,
        )

        # 最早着手日 = 今日 + 材料調達LT + 支給運送LT
        # 調達先カレンダがあれば優先、なければDAISOカレンダを使用
        bom_lines = self.item.bom_lines.select_related('supplier').all()
        supply_transport_lt = self.item.subcontractor.transport_lt_supply
        business_today = get_business_today()
        candidates = []
        for bom in bom_lines:
            supplier_calendar = getattr(getattr(bom, 'supplier', None), 'calendar', None)
            calc_calendar = supplier_calendar or daiso_calendar
            total_days = int(bom.procurement_lt or 0) + int(supply_transport_lt or 0) + int(extra_order_lt or 0)
            candidates.append(add_working_days(business_today, total_days, calc_calendar))

        if candidates:
            self.earliest_start = max(candidates)
        else:
            self.earliest_start = add_working_days(
                business_today,
                int(supply_transport_lt or 0) + int(extra_order_lt or 0),
                daiso_calendar,
            )


class OutsourceSplit(models.Model):
    """分割計画"""
    order = models.ForeignKey(
        OutsourceOrder, on_delete=models.CASCADE,
        verbose_name='案件', related_name='splits'
    )
    sequence = models.IntegerField('分割連番')
    process_date = models.DateField('加工予定日')
    qty = models.IntegerField('分割数量')
    material_supplied = models.BooleanField('材料支給済', default=False)
    process_completed = models.BooleanField('加工完了', default=False)
    shipped = models.BooleanField('出荷済', default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'outsource_split'
        verbose_name = '分割計画'
        verbose_name_plural = '分割計画'
        ordering = ['order', 'sequence']
        unique_together = ['order', 'sequence']

    def __str__(self):
        return f'{self.order.case_no} #{self.sequence} ({self.process_date})'


class MaterialRequirement(models.Model):
    """材料所要量"""
    split = models.ForeignKey(
        OutsourceSplit, on_delete=models.CASCADE,
        verbose_name='分割計画', related_name='material_requirements'
    )
    material_code = models.CharField('材料コード', max_length=50)
    material_name = models.CharField('材料名称', max_length=200)
    supplier_name = models.CharField('調達先', max_length=100, blank=True, default='')
    required_qty = models.DecimalField('必要数量', max_digits=12, decimal_places=4)
    order_qty = models.DecimalField('発注数', max_digits=12, decimal_places=4, default=0)
    supply_date = models.DateField('支給予定日')
    ordered = models.BooleanField('発注済', default=False)
    ordered_at = models.DateField('発注日', null=True, blank=True)
    shipment_planned = models.BooleanField('便計画済み', default=False)
    issued = models.BooleanField('出庫済み', default=False)
    supplied_qty = models.DecimalField('支給済数量', max_digits=12, decimal_places=4, default=0)
    supplied = models.BooleanField('支給完了', default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'outsource_material_requirement'
        verbose_name = '材料所要量'
        verbose_name_plural = '材料所要量'
        ordering = ['supply_date', 'material_code']

    def __str__(self):
        return f'{self.split.order.case_no} - {self.material_code} ({self.supply_date})'


class SubcontractorDelivery(models.Model):
    """外作先納入（受入記録）"""
    split = models.ForeignKey(
        OutsourceSplit, on_delete=models.CASCADE,
        verbose_name='分割計画', related_name='deliveries'
    )
    delivery_date = models.DateField('納入日')
    qty = models.IntegerField('受入数量')
    inspector = models.CharField('検収者', max_length=50)
    notes = models.TextField('備考', blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'outsource_subcontractor_delivery'
        verbose_name = '外作先納入'
        verbose_name_plural = '外作先納入'
        ordering = ['delivery_date']

    def __str__(self):
        return f'{self.split.order.case_no} #{self.split.sequence} 受入 {self.delivery_date}'


class CustomerShipment(models.Model):
    """顧客出荷記録"""
    split = models.ForeignKey(
        OutsourceSplit, on_delete=models.CASCADE,
        verbose_name='分割計画', related_name='shipments'
    )
    shipment_date = models.DateField('出荷日')
    qty = models.IntegerField('出荷数量')
    person = models.CharField('担当者', max_length=50)
    notes = models.TextField('備考', blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'outsource_customer_shipment'
        verbose_name = '顧客出荷'
        verbose_name_plural = '顧客出荷'
        ordering = ['shipment_date']

    def __str__(self):
        return f'{self.split.order.case_no} #{self.split.sequence} 出荷 {self.shipment_date}'


class MaterialStockTransaction(models.Model):
    """材料在庫トランザクション（総量管理）"""
    TX_TYPE_CHOICES = [
        ('RECEIPT', '入庫'),
        ('ISSUE', '出庫'),
        ('ADJUST', '棚卸調整'),
    ]

    material_code = models.CharField('材料コード', max_length=50, db_index=True)
    material_name = models.CharField('材料名称', max_length=200, blank=True, default='')
    qty_change = models.IntegerField('増減数量（個）')
    tx_type = models.CharField('区分', max_length=20, choices=TX_TYPE_CHOICES)
    tx_date = models.DateField('取引日')
    reason = models.CharField('理由', max_length=200, blank=True, default='')
    ref_type = models.CharField('参照種別', max_length=50, blank=True, default='')
    ref_id = models.IntegerField('参照ID', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'outsource_material_stock_tx'
        verbose_name = '材料在庫トランザクション'
        verbose_name_plural = '材料在庫トランザクション'
        ordering = ['-tx_date', '-id']

    def __str__(self):
        return f'{self.material_code} {self.qty_change:+d}'


class ProductStockTransaction(models.Model):
    """完成品在庫トランザクション（総量管理）"""
    TX_TYPE_CHOICES = [
        ('RECEIPT', '入庫'),
        ('SHIP', '出庫'),
        ('ADJUST', '棚卸調整'),
    ]

    item_code = models.CharField('品目コード', max_length=50, db_index=True)
    item_name = models.CharField('品目名称', max_length=200, blank=True, default='')
    qty_change = models.IntegerField('増減数量（個）')
    tx_type = models.CharField('区分', max_length=20, choices=TX_TYPE_CHOICES)
    tx_date = models.DateField('取引日')
    reason = models.CharField('理由', max_length=200, blank=True, default='')
    ref_type = models.CharField('参照種別', max_length=50, blank=True, default='')
    ref_id = models.IntegerField('参照ID', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'outsource_product_stock_tx'
        verbose_name = '完成品在庫トランザクション'
        verbose_name_plural = '完成品在庫トランザクション'
        ordering = ['-tx_date', '-id']

    def __str__(self):
        return f'{self.item_code} {self.qty_change:+d}'
