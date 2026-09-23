from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import (
    PurchaseOrderProposal,
    PurchaseOrderProposalEmailConfig,
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
            'days_of_week',
            'nth_weeks',
            'days_of_month',
            'interval_days',
            'is_active',
            'note',
        ]

    def _parse_days_of_week(self, value):
        if not value:
            return []
        if isinstance(value, list):
            return [int(d) for d in value]
        return [int(d.strip()) for d in str(value).split(',') if d.strip()]

    def _parse_csv_ints(self, value):
        if not value:
            return []
        if isinstance(value, list):
            return [int(d) for d in value]
        return [int(d.strip()) for d in str(value).split(',') if d.strip()]

    def _normalize_csv(self, attrs, field):
        raw = attrs.get(field)
        if isinstance(raw, list):
            attrs[field] = ','.join(str(d) for d in raw)

    def validate(self, attrs):
        recurrence_type = attrs.get('recurrence_type', getattr(self.instance, 'recurrence_type', None))

        self._normalize_csv(attrs, 'days_of_week')
        self._normalize_csv(attrs, 'days_of_month')
        self._normalize_csv(attrs, 'nth_weeks')

        days_of_week_raw = attrs.get('days_of_week', getattr(self.instance, 'days_of_week', ''))
        days_of_month_raw = attrs.get('days_of_month', getattr(self.instance, 'days_of_month', ''))
        nth_weeks_raw = attrs.get('nth_weeks', getattr(self.instance, 'nth_weeks', ''))

        days = self._parse_csv_ints(days_of_week_raw)
        for d in days:
            if not (0 <= d <= 6):
                raise serializers.ValidationError({'days_of_week': '曜日は0(月)〜6(日)で指定してください。'})

        months = self._parse_csv_ints(days_of_month_raw)
        for d in months:
            if not (1 <= d <= 31):
                raise serializers.ValidationError({'days_of_month': '日付は1〜31で指定してください。'})

        weeks = self._parse_csv_ints(nth_weeks_raw)
        for w in weeks:
            if not (1 <= w <= 5):
                raise serializers.ValidationError({'nth_weeks': '第N週は1〜5で指定してください。'})

        if recurrence_type == SupplierOrderPattern.RECURRENCE_WEEKLY:
            if not days:
                raise serializers.ValidationError({'days_of_week': '曜日を1つ以上指定してください。'})
        elif recurrence_type == SupplierOrderPattern.RECURRENCE_MONTHLY_DATE:
            if not months:
                raise serializers.ValidationError({'days_of_month': '日付を1つ以上指定してください。'})
        elif recurrence_type == SupplierOrderPattern.RECURRENCE_MONTHLY_NTH_DOW:
            if not weeks:
                raise serializers.ValidationError({'nth_weeks': '第N週を1つ以上指定してください。'})
            if not days:
                raise serializers.ValidationError({'days_of_week': '曜日を1つ以上指定してください。'})
        elif recurrence_type == SupplierOrderPattern.RECURRENCE_EVERY_N_BUSINESS_DAYS:
            interval_days = attrs.get('interval_days', getattr(self.instance, 'interval_days', None))
            if not interval_days or interval_days < 1:
                raise serializers.ValidationError({'interval_days': '間隔日数は1以上で指定してください。'})

        return attrs


class SupplierOrderScheduleSerializer(serializers.ModelSerializer):
    supplier_code = serializers.CharField(source='supplier.supplier_code', read_only=True)
    supplier_name = serializers.CharField(source='supplier.supplier_name', read_only=True)
    pattern_code = serializers.CharField(source='pattern.pattern_code', read_only=True)
    pattern_name = serializers.CharField(source='pattern.pattern_name', read_only=True)
    next_order_date = serializers.SerializerMethodField()

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
            'start_date',
            'lead_time_days',
            'is_enabled',
            'note',
            'next_order_date',
        ]

    def get_next_order_date(self, obj):
        from datetime import date
        from django.apps import apps
        CalendarDay = apps.get_model('masters', 'CalendarDay')
        supplier = obj.supplier
        if not supplier or not supplier.calendar_id:
            return None
        today = date.today()
        nearest = (
            CalendarDay.objects
            .filter(
                calendar_id=supplier.calendar_id,
                is_order_day=True,
                target_date__gte=today,
            )
            .order_by('target_date')
            .values_list('target_date', flat=True)
            .first()
        )
        return nearest

    def validate(self, attrs):
        pattern = attrs.get('pattern', getattr(self.instance, 'pattern', None))
        start_date = attrs.get('start_date', getattr(self.instance, 'start_date', None))
        if pattern and pattern.recurrence_type == SupplierOrderPattern.RECURRENCE_EVERY_N_BUSINESS_DAYS and not start_date:
            raise serializers.ValidationError({'start_date': '開始基準日を指定してください。'})
        return attrs


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


class PurchaseOrderProposalEmailConfigSerializer(serializers.ModelSerializer):
    cc_user_details = serializers.SerializerMethodField()
    supplier_code = serializers.CharField(source='supplier.supplier_code', read_only=True)
    supplier_name = serializers.CharField(source='supplier.supplier_name', read_only=True)
    cc_users = serializers.PrimaryKeyRelatedField(
        queryset=get_user_model().objects.all(),
        many=True,
        required=False,
    )

    class Meta:
        model = PurchaseOrderProposalEmailConfig
        fields = [
            'id',
            'supplier',
            'supplier_code',
            'supplier_name',
            'body',
            'cc_users',
            'cc_user_details',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'supplier_code', 'supplier_name', 'cc_user_details', 'created_at', 'updated_at']

    def get_cc_user_details(self, obj):
        users = obj.cc_users.all().order_by('username')
        return [
            {
                'id': user.id,
                'username': user.username,
                'employee_code': getattr(getattr(user, 'profile', None), 'employee_code', ''),
                'name': _display_user_name(user),
                'email': user.email or '',
            }
            for user in users
        ]


class PurchaseOrderProposalApprovalSerializer(serializers.ModelSerializer):
    approved_by_username = serializers.CharField(source='approved_by.username', read_only=True)
    approved_by_name = serializers.SerializerMethodField()
    approved_by_email = serializers.CharField(source='approved_by.email', read_only=True)

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
            'approved_by_email',
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
    assigned_to_email = serializers.CharField(source='assigned_to.email', read_only=True)
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
            'assigned_to_email',
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
