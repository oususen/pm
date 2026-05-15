from rest_framework import serializers

from .models import (
    PurchaseOrderApprovalConfig,
    PurchaseOrderProposal,
    PurchaseOrderProposalApproval,
    PurchaseOrderProposalLine,
    PurchaseOrderTask,
    PurchasePlanLockSetting,
    SupplierOrderPattern,
    SupplierOrderSchedule,
)


def _display_user_name(user):
    if not user:
        return ''
    last_name = (getattr(user, 'last_name', '') or '').strip()
    first_name = (getattr(user, 'first_name', '') or '').strip()
    if last_name or first_name:
        return f'{last_name} {first_name}'.strip()
    full_name = (user.get_full_name() or '').strip()
    if full_name:
        return full_name
    return (getattr(user, 'username', '') or '').strip()


class PurchasePlanLockSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = PurchasePlanLockSetting
        fields = ['id', 'lock_days', 'updated_at', 'updated_by']
        read_only_fields = ['id', 'updated_at', 'updated_by']


class SupplierOrderPatternSerializer(serializers.ModelSerializer):
    recurrence_type_display = serializers.CharField(source='get_recurrence_type_display', read_only=True)

    class Meta:
        model = SupplierOrderPattern
        fields = [
            'id',
            'pattern_code',
            'pattern_name',
            'recurrence_type',
            'recurrence_type_display',
            'day_of_week',
            'nth_week',
            'day_of_month',
            'is_active',
            'note',
        ]

    def validate(self, attrs):
        recurrence_type = attrs.get('recurrence_type', getattr(self.instance, 'recurrence_type', None))
        day_of_week = attrs.get('day_of_week', getattr(self.instance, 'day_of_week', None))
        nth_week = attrs.get('nth_week', getattr(self.instance, 'nth_week', None))
        day_of_month = attrs.get('day_of_month', getattr(self.instance, 'day_of_month', None))

        if day_of_week is not None and not (0 <= int(day_of_week) <= 6):
            raise serializers.ValidationError({'day_of_week': '曜日は0(月)〜6(日)で指定してください。'})
        if nth_week is not None and not (1 <= int(nth_week) <= 5):
            raise serializers.ValidationError({'nth_week': '第N週は1〜5で指定してください。'})
        if day_of_month is not None and not (1 <= int(day_of_month) <= 31):
            raise serializers.ValidationError({'day_of_month': '日付は1〜31で指定してください。'})

        if recurrence_type == SupplierOrderPattern.RECURRENCE_WEEKLY:
            if day_of_week is None:
                raise serializers.ValidationError({'day_of_week': '曜日を指定してください。'})
        elif recurrence_type == SupplierOrderPattern.RECURRENCE_MONTHLY_DATE:
            if day_of_month is None:
                raise serializers.ValidationError({'day_of_month': '日付を指定してください。'})
        elif recurrence_type == SupplierOrderPattern.RECURRENCE_MONTHLY_NTH_DOW:
            if nth_week is None:
                raise serializers.ValidationError({'nth_week': '第N週を指定してください。'})
            if day_of_week is None:
                raise serializers.ValidationError({'day_of_week': '曜日を指定してください。'})

        return attrs


class SupplierOrderScheduleSerializer(serializers.ModelSerializer):
    supplier_code = serializers.CharField(source='supplier.supplier_code', read_only=True)
    supplier_name = serializers.CharField(source='supplier.supplier_name', read_only=True)
    pattern_code = serializers.CharField(source='pattern.pattern_code', read_only=True)
    pattern_name = serializers.CharField(source='pattern.pattern_name', read_only=True)

    class Meta:
        model = SupplierOrderSchedule
        fields = [
            'id',
            'supplier',
            'supplier_code',
            'supplier_name',
            'pattern',
            'pattern_code',
            'pattern_name',
            'lead_time_days',
            'is_enabled',
            'note',
        ]


class PurchaseOrderProposalLineSerializer(serializers.ModelSerializer):
    product_code = serializers.CharField(source='product.product_code', read_only=True)
    product_name = serializers.CharField(source='product.product_name', read_only=True)
    line_code = serializers.CharField(source='line.line_code', read_only=True)
    line_name = serializers.CharField(source='line.line_name', read_only=True)

    class Meta:
        model = PurchaseOrderProposalLine
        fields = [
            'id',
            'proposal',
            'product',
            'product_code',
            'product_name',
            'line',
            'line_code',
            'line_name',
            'shortage_date',
            'shortage_qty',
            'next_delivery_date',
            'order_qty',
            'snapshot_stock',
            'snapshot_min_stock',
            'note',
        ]
        read_only_fields = ['id', 'proposal']

    def validate_order_qty(self, value):
        if value < 0:
            raise serializers.ValidationError('発注数量は0以上で指定してください。')
        return value


class PurchaseOrderProposalApprovalSerializer(serializers.ModelSerializer):
    approved_by_username = serializers.CharField(source='approved_by.username', read_only=True)
    approved_by_name = serializers.SerializerMethodField()

    class Meta:
        model = PurchaseOrderProposalApproval
        fields = [
            'id',
            'proposal',
            'approval_level',
            'action',
            'approved_by',
            'approved_by_username',
            'approved_by_name',
            'approved_at',
            'comment',
        ]
        read_only_fields = ['id', 'proposal', 'approved_by', 'approved_at']

    def get_approved_by_name(self, obj):
        if not obj.approved_by_id:
            return ''
        return _display_user_name(obj.approved_by)


class PurchaseOrderTaskSerializer(serializers.ModelSerializer):
    assigned_to_username = serializers.CharField(source='assigned_to.username', read_only=True)
    assigned_to_name = serializers.SerializerMethodField()
    proposal_no = serializers.CharField(source='proposal.proposal_no', read_only=True)
    proposal_status = serializers.CharField(source='proposal.status', read_only=True)
    supplier_code = serializers.CharField(source='proposal.supplier.supplier_code', read_only=True)
    supplier_name = serializers.CharField(source='proposal.supplier.supplier_name', read_only=True)

    class Meta:
        model = PurchaseOrderTask
        fields = [
            'id',
            'proposal',
            'proposal_no',
            'proposal_status',
            'supplier_code',
            'supplier_name',
            'task_type',
            'assigned_to',
            'assigned_to_username',
            'assigned_to_name',
            'status',
            'due_date',
            'created_at',
            'done_at',
        ]
        read_only_fields = ['id', 'created_at', 'done_at']

    def get_assigned_to_name(self, obj):
        if not obj.assigned_to_id:
            return ''
        return _display_user_name(obj.assigned_to)


class PurchaseOrderProposalListSerializer(serializers.ModelSerializer):
    supplier_code = serializers.CharField(source='supplier.supplier_code', read_only=True)
    supplier_name = serializers.CharField(source='supplier.supplier_name', read_only=True)
    supplier_order_email = serializers.CharField(source='supplier.order_email', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    created_by_name = serializers.SerializerMethodField()
    created_by_email = serializers.CharField(source='created_by.email', read_only=True)
    line_count = serializers.IntegerField(source='lines.count', read_only=True)
    pending_tasks = serializers.SerializerMethodField()

    class Meta:
        model = PurchaseOrderProposal
        fields = [
            'id',
            'proposal_no',
            'supplier',
            'supplier_code',
            'supplier_name',
            'supplier_order_email',
            'order_date',
            'desired_delivery_date',
            'next_delivery_date',
            'status',
            'created_by',
            'created_by_username',
            'created_by_name',
            'created_by_email',
            'note',
            'generated_at',
            'updated_at',
            'sent_at',
            'line_count',
            'pending_tasks',
        ]

    def get_created_by_name(self, obj):
        if not obj.created_by_id:
            return ''
        return _display_user_name(obj.created_by)

    def get_pending_tasks(self, obj):
        tasks = obj.tasks.filter(status=PurchaseOrderTask.STATUS_PENDING).values_list('task_type', flat=True)
        return list(tasks)


class PurchaseOrderProposalDetailSerializer(serializers.ModelSerializer):
    supplier_code = serializers.CharField(source='supplier.supplier_code', read_only=True)
    supplier_name = serializers.CharField(source='supplier.supplier_name', read_only=True)
    supplier_order_email = serializers.CharField(source='supplier.order_email', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    created_by_name = serializers.SerializerMethodField()
    created_by_email = serializers.CharField(source='created_by.email', read_only=True)
    lines = PurchaseOrderProposalLineSerializer(many=True, read_only=True)
    approvals = PurchaseOrderProposalApprovalSerializer(many=True, read_only=True)
    tasks = PurchaseOrderTaskSerializer(many=True, read_only=True)

    class Meta:
        model = PurchaseOrderProposal
        fields = [
            'id',
            'proposal_no',
            'supplier',
            'supplier_code',
            'supplier_name',
            'supplier_order_email',
            'order_date',
            'desired_delivery_date',
            'next_delivery_date',
            'status',
            'created_by',
            'created_by_username',
            'created_by_name',
            'created_by_email',
            'note',
            'generated_at',
            'updated_at',
            'sent_at',
            'lines',
            'approvals',
            'tasks',
        ]

    def get_created_by_name(self, obj):
        if not obj.created_by_id:
            return ''
        return _display_user_name(obj.created_by)


class PurchaseOrderApprovalConfigSerializer(serializers.ModelSerializer):
    approver_user_names = serializers.SerializerMethodField()
    proxy_approver_user_names = serializers.SerializerMethodField()
    notify_user_names = serializers.SerializerMethodField()

    class Meta:
        model = PurchaseOrderApprovalConfig
        fields = [
            'id',
            'approval_level',
            'level_name',
            'approver_users',
            'proxy_approver_users',
            'notify_users',
            'approver_user_names',
            'proxy_approver_user_names',
            'notify_user_names',
        ]

    def get_approver_user_names(self, obj):
        names = []
        for user in obj.approver_users.all():
            names.append(_display_user_name(user))
        return names

    def get_notify_user_names(self, obj):
        names = []
        for user in obj.notify_users.all():
            names.append(_display_user_name(user))
        return names

    def get_proxy_approver_user_names(self, obj):
        names = []
        for user in obj.proxy_approver_users.all():
            names.append(_display_user_name(user))
        return names
