from django.db import models
from rest_framework import serializers
from .models import (
    Subcontractor, OutsourceItem, OutsourceBOM,
    OutsourceOrder, OutsourceSplit, MaterialRequirement,
    SubcontractorDelivery, CustomerShipment,
)


class SubcontractorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subcontractor
        fields = '__all__'


class OutsourceBOMSerializer(serializers.ModelSerializer):
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
            'id', 'item_code', 'item_name', 'subcontractor', 'subcontractor_name',
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

    class Meta:
        model = OutsourceSplit
        fields = '__all__'

    def get_delivered_qty(self, obj):
        return obj.deliveries.aggregate(total=models.Sum('qty'))['total'] or 0

    def get_shipped_qty(self, obj):
        return obj.shipments.aggregate(total=models.Sum('qty'))['total'] or 0


class MaterialRequirementSerializer(serializers.ModelSerializer):
    case_no = serializers.CharField(source='split.order.case_no', read_only=True)
    item_name = serializers.CharField(source='split.order.item_name', read_only=True)
    process_date = serializers.DateField(source='split.process_date', read_only=True)
    painting_date = serializers.DateField(source='split.order.painting_date', read_only=True)

    class Meta:
        model = MaterialRequirement
        fields = '__all__'


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

    class Meta:
        model = OutsourceOrder
        fields = [
            'id', 'case_no', 'item_code', 'item_name', 'order_qty',
            'painting_name', 'painting_date', 'earliest_start', 'latest_finish',
            'status', 'imported_at', 'split_count',
        ]
