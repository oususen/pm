from rest_framework import serializers
from django.contrib.auth import get_user_model

from masters.serializers import build_media_absolute_url

from .models import (
    Consumable,
    ConsumableDispatchOrder,
    ConsumableDispatchOrderItem,
    ConsumableOrderEmailConfig,
    ConsumableRequest,
    ConsumableStockMovement,
    ConsumableSupplier,
)
from .services import display_user_name


class ConsumableOrderEmailConfigSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    cc_users = serializers.PrimaryKeyRelatedField(
        queryset=get_user_model().objects.all(), many=True, required=False,
    )
    cc_user_details = serializers.SerializerMethodField()

    class Meta:
        model = ConsumableOrderEmailConfig
        fields = ['id', 'supplier', 'supplier_name', 'body', 'cc_users', 'cc_user_details', 'created_at', 'updated_at']
        read_only_fields = ['id', 'supplier_name', 'cc_user_details', 'created_at', 'updated_at']

    def get_cc_user_details(self, obj):
        return [
            {
                'id': user.id,
                'username': user.username,
                'employee_code': getattr(getattr(user, 'profile', None), 'employee_code', ''),
                'name': display_user_name(user),
                'email': user.email or '',
            }
            for user in obj.cc_users.all().order_by('username')
        ]


class ConsumableSupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConsumableSupplier
        fields = [
            'id', 'name', 'contact_person', 'phone', 'email', 'address', 'note',
            'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']


class ConsumableSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source='supplier.name', read_only=True, default='')
    image_url = serializers.SerializerMethodField()
    is_shortage = serializers.SerializerMethodField()
    order_status = serializers.SerializerMethodField()
    order_status_label = serializers.SerializerMethodField()

    class Meta:
        model = Consumable
        fields = [
            'id', 'code', 'order_code', 'name', 'category', 'unit', 'storage_location',
            'stock_quantity', 'safety_stock', 'order_unit', 'unit_price',
            'supplier', 'supplier_name', 'image', 'image_url', 'note', 'is_active',
            'is_shortage', 'order_status', 'order_status_label',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['image', 'created_at', 'updated_at']

    def validate_stock_quantity(self, value):
        # 在庫数は新規登録時のみ設定可。以降は入庫・出庫でのみ変更する
        if self.instance is not None and value != self.instance.stock_quantity:
            raise serializers.ValidationError('在庫数はマスタ編集では変更できません。入庫・出庫で変更してください。')
        return value

    def get_image_url(self, obj):
        if not obj.image:
            return ''
        return build_media_absolute_url(self.context.get('request'), obj.image.url)

    def get_is_shortage(self, obj):
        return obj.stock_quantity <= obj.safety_stock

    def get_order_status(self, obj):
        # 一覧では view が context に一括取得したマップを渡す（N+1回避）
        status_map = self.context.get('order_status_map')
        if status_map is None:
            from .services import open_request_status_map
            status_map = open_request_status_map([obj.id])
        return status_map.get(obj.id, '')

    def get_order_status_label(self, obj):
        status = self.get_order_status(obj)
        return dict(ConsumableRequest.STATUS_CHOICES).get(status, '未発注')


class ConsumableRequestSerializer(serializers.ModelSerializer):
    consumable_code = serializers.CharField(source='consumable.code', read_only=True)
    consumable_name = serializers.CharField(source='consumable.name', read_only=True)
    unit = serializers.CharField(source='consumable.unit', read_only=True)
    supplier_id = serializers.IntegerField(source='consumable.supplier_id', read_only=True)
    supplier_name = serializers.CharField(source='consumable.supplier.name', read_only=True, default='')
    status_label = serializers.CharField(source='get_status_display', read_only=True)
    request_type_label = serializers.CharField(source='get_request_type_display', read_only=True)

    class Meta:
        model = ConsumableRequest
        fields = [
            'id', 'consumable', 'consumable_code', 'consumable_name', 'unit',
            'supplier_id', 'supplier_name',
            'quantity', 'unit_price', 'total_amount', 'deadline',
            'requester', 'requester_name',
            'division_name', 'group_name', 'team_name', 'unit_name',
            'request_type', 'request_type_label', 'status', 'status_label', 'note',
            'requested_at', 'ordered_at', 'completed_at', 'updated_at',
        ]
        read_only_fields = [
            'unit_price', 'total_amount', 'requester_name',
            'division_name', 'group_name', 'team_name', 'unit_name',
            'request_type', 'status', 'requested_at', 'ordered_at', 'completed_at', 'updated_at',
        ]


class ConsumableStockMovementSerializer(serializers.ModelSerializer):
    consumable_code = serializers.CharField(source='consumable.code', read_only=True)
    consumable_name = serializers.CharField(source='consumable.name', read_only=True)
    unit = serializers.CharField(source='consumable.unit', read_only=True)
    movement_type_label = serializers.CharField(source='get_movement_type_display', read_only=True)
    inbound_type_label = serializers.CharField(source='get_inbound_type_display', read_only=True)

    class Meta:
        model = ConsumableStockMovement
        fields = [
            'id', 'consumable', 'consumable_code', 'consumable_name', 'unit',
            'movement_type', 'movement_type_label', 'inbound_type', 'inbound_type_label',
            'request', 'quantity', 'stock_after',
            'worker', 'worker_name', 'division_name', 'group_name', 'team_name', 'unit_name',
            'usage_line', 'unit_price', 'total_amount', 'note', 'moved_at',
        ]


class ConsumableDispatchOrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConsumableDispatchOrderItem
        fields = [
            'id', 'consumable', 'request', 'code', 'order_code', 'name', 'quantity', 'unit',
            'unit_price', 'total_amount', 'deadline', 'note',
        ]


class ConsumableDispatchOrderSerializer(serializers.ModelSerializer):
    items = ConsumableDispatchOrderItemSerializer(many=True, read_only=True)
    status_label = serializers.CharField(source='get_status_display', read_only=True)
    approval_status = serializers.CharField(source='approval_request.status', read_only=True, default='')
    approval_status_label = serializers.CharField(
        source='approval_request.get_status_display', read_only=True, default=''
    )
    approval_stage = serializers.CharField(source='approval_request.current_stage', read_only=True, default='')
    created_by_name = serializers.SerializerMethodField()
    supplier_email = serializers.CharField(source='supplier.email', read_only=True, default='')
    pdf_url = serializers.SerializerMethodField()
    reject_reason = serializers.CharField(source='approval_request.reject_reason', read_only=True, default='')
    my_pending_task_types = serializers.SerializerMethodField()

    class Meta:
        model = ConsumableDispatchOrder
        fields = [
            'id', 'order_number', 'business_date', 'daily_count',
            'supplier', 'supplier_name', 'supplier_email', 'total_items', 'total_amount',
            'status', 'status_label', 'approval_request', 'approval_status', 'approval_status_label',
            'approval_stage', 'pdf_url', 'sent_at', 'sent_email', 'received_at', 'note',
            'created_by', 'created_by_name', 'created_at', 'items',
            'reject_reason', 'my_pending_task_types',
        ]

    def get_created_by_name(self, obj):
        from .services import display_user_name
        return display_user_name(obj.created_by)

    def get_pdf_url(self, obj):
        if not obj.pdf_file:
            return ''
        return build_media_absolute_url(self.context.get('request'), obj.pdf_file.url)

    def get_my_pending_task_types(self, obj):
        """ログインユーザーに割り当てられた未処理の承認タスク（画面の確認・承認ボタン表示用）"""
        request = self.context.get('request')
        if not obj.approval_request_id or not request or not request.user.is_authenticated:
            return []
        return list(
            obj.approval_request.tasks.filter(assigned_to=request.user, status='PENDING')
            .values_list('task_type', flat=True)
        )
