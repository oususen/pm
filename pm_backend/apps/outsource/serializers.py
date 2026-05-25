from django.db import models
from rest_framework import serializers
from .models import (
    Subcontractor, OutsourceItem, OutsourceBOM, OutsourceMaterial,
    OutsourceOrder, OutsourceSplit, MaterialRequirement,
    SubcontractorDelivery, CustomerShipment,
    MaterialStockTransaction, ProductStockTransaction,
    SplitImportLog,
)


class SubcontractorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subcontractor
        fields = '__all__'


class OutsourceMaterialSerializer(serializers.ModelSerializer):
    supplier_display = serializers.CharField(source='supplier.supplier_name', read_only=True, default='')

    class Meta:
        model = OutsourceMaterial
        fields = '__all__'


class OutsourceBOMSerializer(serializers.ModelSerializer):
    supplier_display = serializers.CharField(source='supplier.supplier_name', read_only=True, default='')

    class Meta:
        model = OutsourceBOM
        fields = '__all__'


class OutsourceItemSerializer(serializers.ModelSerializer):
    subcontractor_name = serializers.CharField(source='subcontractor.name', read_only=True)
    bom_lines = OutsourceBOMSerializer(many=True, read_only=True)

    class Meta:
        model = OutsourceItem
        fields = '__all__'


class OutsourceItemListSerializer(serializers.ModelSerializer):
    subcontractor_name = serializers.CharField(source='subcontractor.name', read_only=True)
    bom_count = serializers.IntegerField(source='bom_lines.count', read_only=True)

    class Meta:
        model = OutsourceItem
        fields = [
            'id', 'item_code', 'product_number', 'item_name', 'subcontractor', 'subcontractor_name',
            'customer_delivery_lt', 'is_active', 'bom_count',
        ]


class SubcontractorDeliverySerializer(serializers.ModelSerializer):
    case_no = serializers.CharField(source='split.order.case_no', read_only=True)
    item_name = serializers.CharField(source='split.order.item_name', read_only=True)
    sequence = serializers.IntegerField(source='split.sequence', read_only=True)

    class Meta:
        model = SubcontractorDelivery
        fields = '__all__'


class CustomerShipmentSerializer(serializers.ModelSerializer):
    case_no = serializers.CharField(source='split.order.case_no', read_only=True)
    item_name = serializers.CharField(source='split.order.item_name', read_only=True)
    sequence = serializers.IntegerField(source='split.sequence', read_only=True)

    class Meta:
        model = CustomerShipment
        fields = '__all__'


class OutsourceSplitSerializer(serializers.ModelSerializer):
    delivered_qty = serializers.SerializerMethodField()
    shipped_qty = serializers.SerializerMethodField()
    auto_material_supplied = serializers.SerializerMethodField()
    auto_process_completed = serializers.SerializerMethodField()
    auto_shipped = serializers.SerializerMethodField()
    material_ordered_count = serializers.SerializerMethodField()
    material_total_count = serializers.SerializerMethodField()

    class Meta:
        model = OutsourceSplit
        fields = '__all__'

    def get_delivered_qty(self, obj):
        return obj.deliveries.aggregate(total=models.Sum('qty'))['total'] or 0

    def get_shipped_qty(self, obj):
        return obj.shipments.aggregate(total=models.Sum('qty'))['total'] or 0

    def get_auto_material_supplied(self, obj):
        reqs = obj.material_requirements.all()
        if not reqs.exists():
            return False
        return all(r.supplied for r in reqs)

    def get_auto_process_completed(self, obj):
        delivered = obj.deliveries.aggregate(total=models.Sum('qty'))['total'] or 0
        return delivered >= obj.qty

    def get_auto_shipped(self, obj):
        shipped = obj.shipments.aggregate(total=models.Sum('qty'))['total'] or 0
        return shipped >= obj.qty

    def get_material_ordered_count(self, obj):
        return obj.material_requirements.filter(ordered=True).count()

    def get_material_total_count(self, obj):
        return obj.material_requirements.count()


class MaterialRequirementSerializer(serializers.ModelSerializer):
    case_no = serializers.CharField(source='split.order.case_no', read_only=True)
    item_name = serializers.CharField(source='split.order.item_name', read_only=True)
    product_number = serializers.SerializerMethodField()
    process_date = serializers.DateField(source='split.process_date', read_only=True)
    painting_date = serializers.DateField(source='split.order.painting_date', read_only=True)

    class Meta:
        model = MaterialRequirement
        fields = '__all__'

    def get_product_number(self, obj):
        order = getattr(getattr(obj, 'split', None), 'order', None)
        if not order:
            return ''
        item = getattr(order, 'item', None)
        if item and item.product_number:
            return item.product_number
        code = (order.item_code or '').lstrip('B')
        if len(code) >= 10:
            return f'{code[:6]}-{code[6:10]}'
        return ''


class OutsourceOrderSerializer(serializers.ModelSerializer):
    item_code_display = serializers.CharField(source='item.item_code', read_only=True, default='')
    splits = OutsourceSplitSerializer(many=True, read_only=True)
    split_total_qty = serializers.SerializerMethodField()

    class Meta:
        model = OutsourceOrder
        fields = '__all__'

    def get_split_total_qty(self, obj):
        return sum(s.qty for s in obj.splits.all())


class OutsourceOrderListSerializer(serializers.ModelSerializer):
    split_count = serializers.IntegerField(source='splits.count', read_only=True)
    product_number = serializers.SerializerMethodField()
    has_bom = serializers.SerializerMethodField()
    max_procurement_lt = serializers.SerializerMethodField()
    max_procurement_material_code = serializers.SerializerMethodField()
    max_procurement_supplier_name = serializers.SerializerMethodField()

    class Meta:
        model = OutsourceOrder
        fields = [
            'id', 'case_no', 'item_code', 'product_number', 'item_name', 'order_qty',
            'painting_name', 'painting_date', 'earliest_start', 'latest_finish',
            'status', 'imported_at', 'split_count', 'has_bom',
            'max_procurement_lt', 'max_procurement_material_code', 'max_procurement_supplier_name',
        ]

    def _resolve_item(self, obj):
        item = getattr(obj, 'item', None)
        if item:
            return item
        code = (obj.item_code or '').strip()
        if not code:
            return None
        return OutsourceItem.objects.filter(item_code=code).first()

    def get_product_number(self, obj):
        item = self._resolve_item(obj)
        if item and item.product_number:
            return item.product_number
        code = (obj.item_code or '').lstrip('B')
        if len(code) >= 10:
            return f'{code[:6]}-{code[6:10]}'
        return ''

    def get_has_bom(self, obj):
        item = self._resolve_item(obj)
        if not item:
            return False
        return item.bom_lines.exists()

    def _get_max_lt_bom(self, obj):
        item = self._resolve_item(obj)
        if not item:
            return None
        return item.bom_lines.order_by('-procurement_lt', 'material_code').first()

    def get_max_procurement_lt(self, obj):
        bom = self._get_max_lt_bom(obj)
        return int(bom.procurement_lt) if bom else None

    def get_max_procurement_material_code(self, obj):
        bom = self._get_max_lt_bom(obj)
        return bom.material_code if bom else ''

    def get_max_procurement_supplier_name(self, obj):
        bom = self._get_max_lt_bom(obj)
        return bom.supplier_name if bom else ''


class SplitImportLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = SplitImportLog
        fields = '__all__'


class MaterialStockTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaterialStockTransaction
        fields = '__all__'


class ProductStockTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductStockTransaction
        fields = '__all__'
