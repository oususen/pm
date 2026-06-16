import re
from rest_framework import serializers
from django.db.models import Sum
from .models import (
    Product, Customer, Process, Line, Supplier, Calendar, CalendarDay, WorkPattern, BreakTime,
    BOM, BOMItem, Routing, RoutingStep, RoutingStepMaterial, ProductGroup, ContainerCapacity, Equipment, Contact,
    KubotaSakaiTruck, MobileDevice, MobileDeviceInventory, ManualDocument, ProductCodeMapping,
    ProductStockLocation,
)

def build_media_absolute_url(request, raw_url):
    """メディアURLを返す。相対パスはそのまま返してブラウザのオリジンで解決させる。
    proxyやHTTPS環境でのMixed Content問題を避けるため絶対URLには変換しない。"""
    if not raw_url:
        return raw_url
    path = str(raw_url)
    if path.startswith(('http://', 'https://')):
        return path
    # /で始まる相対パス（例: /media/products/xxx.jpg）はそのまま返す
    if path.startswith('/'):
        return path
    # 相対パスの場合はMEDIA_URLを付与
    from django.conf import settings as django_settings
    media_url = django_settings.MEDIA_URL.rstrip('/')
    return f"{media_url}/{path}"


class ProductStockLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductStockLocation
        fields = ['id', 'location_name', 'sort_order']


class ProductSerializer(serializers.ModelSerializer):
    next_process_name = serializers.CharField(source='next_process.process_name', read_only=True)
    stock_locations_list = ProductStockLocationSerializer(source='stock_locations', many=True, read_only=True)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        raw_url = data.get('image_url')
        request = self.context.get('request')
        if raw_url and request:
            data['image_url'] = build_media_absolute_url(request, raw_url)
        return data

    class Meta:
        model = Product
        fields = '__all__'


class ProductGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductGroup
        fields = '__all__'


class ProductCodeMappingSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductCodeMapping
        fields = '__all__'


class ContainerCapacitySerializer(serializers.ModelSerializer):
    class Meta:
        model = ContainerCapacity
        fields = '__all__'


class EquipmentSerializer(serializers.ModelSerializer):
    line_name = serializers.CharField(source='line.line_name', read_only=True)
    process_name = serializers.CharField(source='process.process_name', read_only=True)

    class Meta:
        model = Equipment
        fields = '__all__'


class KubotaSakaiTruckSerializer(serializers.ModelSerializer):
    class Meta:
        model = KubotaSakaiTruck
        fields = '__all__'


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = '__all__'


class ProcessSerializer(serializers.ModelSerializer):
    line_name = serializers.CharField(source='line.line_name', read_only=True)

    class Meta:
        model = Process
        fields = '__all__'


class LineSerializer(serializers.ModelSerializer):
    class Meta:
        model = Line
        fields = '__all__'


class SupplierSerializer(serializers.ModelSerializer):
    @staticmethod
    def _normalize_supplier_code(value):
        text = str(value or '').strip()
        if not text:
            return text
        if re.fullmatch(r'\d+', text):
            return text.zfill(6)
        return text

    def validate_supplier_code(self, value):
        return self._normalize_supplier_code(value)

    class Meta:
        model = Supplier
        fields = '__all__'


class CalendarSerializer(serializers.ModelSerializer):
    created_by_name = serializers.SerializerMethodField()
    updated_by_name = serializers.SerializerMethodField()

    @staticmethod
    def _flags_by_type(calendar_type):
        if calendar_type == 'INTERNAL':
            return True, False
        if calendar_type == 'SUPPLIER':
            return False, True
        if calendar_type in ('COMPANY', 'CUSTOMER'):
            return False, False
        return False, False

    def validate(self, attrs):
        calendar_type = attrs.get('calendar_type', getattr(self.instance, 'calendar_type', None))
        if self.instance is None and not calendar_type:
            raise serializers.ValidationError({'calendar_type': 'カレンダ区分は必須です。'})
        is_line_assignable, is_supplier_assignable = self._flags_by_type(calendar_type)
        attrs['is_line_assignable'] = is_line_assignable
        attrs['is_supplier_assignable'] = is_supplier_assignable
        return attrs

    def get_created_by_name(self, obj):
        user = getattr(obj, 'created_by', None)
        if not user:
            return ''
        return user.get_full_name() or user.username or ''

    def get_updated_by_name(self, obj):
        user = getattr(obj, 'updated_by', None)
        if not user:
            return ''
        return user.get_full_name() or user.username or ''

    class Meta:
        model = Calendar
        fields = '__all__'


class BreakTimeSerializer(serializers.ModelSerializer):
    class Meta:
        model = BreakTime
        fields = '__all__'


class WorkPatternSerializer(serializers.ModelSerializer):
    break_times = BreakTimeSerializer(many=True, read_only=True)

    class Meta:
        model = WorkPattern
        fields = '__all__'


class CalendarDaySerializer(serializers.ModelSerializer):
    work_pattern_name = serializers.CharField(source='work_pattern.pattern_name', read_only=True)

    class Meta:
        model = CalendarDay
        fields = '__all__'


class BOMItemSerializer(serializers.ModelSerializer):
    child_product_code = serializers.CharField(source='child_product.product_code', read_only=True)
    child_product_name = serializers.CharField(source='child_product.product_name', read_only=True)
    process_name = serializers.CharField(source='process.process_name', read_only=True)
    line_name = serializers.CharField(source='line.line_name', read_only=True)

    class Meta:
        model = BOMItem
        fields = '__all__'

    def validate(self, attrs):
        bom = attrs.get('bom', getattr(self.instance, 'bom', None))
        child_product = attrs.get('child_product', getattr(self.instance, 'child_product', None))
        sourcing_type = attrs.get('sourcing_type', getattr(self.instance, 'sourcing_type', None))
        time_unit = attrs.get('time_unit', getattr(self.instance, 'time_unit', 'MINUTE'))
        process = attrs.get('process', getattr(self.instance, 'process', None))

        if bom and child_product and getattr(bom, 'parent_product_id', None) == getattr(child_product, 'id', None):
            raise serializers.ValidationError({
                'child_product': '親製品と同じ製品は登録できません（自己参照BOM）。'
            })

        supplier = attrs.get('supplier', getattr(self.instance, 'supplier', None))

        if sourcing_type == 'SUBCON':
            # 外注は仕入先必須（工程・ラインはルーティング生成時に自動設定）
            if supplier is None:
                raise serializers.ValidationError('外注の場合、仕入先は必須です。')
            lead_time_days = attrs.get('lead_time_days', getattr(self.instance, 'lead_time_days', 0))
            if lead_time_days is None or lead_time_days < 0:
                raise serializers.ValidationError('外注の場合、リードタイム(日)は0以上で入力してください。')
        elif sourcing_type == 'MAKE':
            if process is None:
                raise serializers.ValidationError('自社製造の場合、工程は必須です。')
            # 工程時間の必須チェック
            if time_unit not in ['MINUTE', 'DAY']:
                raise serializers.ValidationError('時間単位は MINUTE か DAY を指定してください。')
            if time_unit == 'MINUTE':
                duration_min = attrs.get('duration_min', getattr(self.instance, 'duration_min', None))
                if duration_min is None or duration_min <= 0:
                    raise serializers.ValidationError('時間単位=MINUTEのとき、所要時間(分)は1以上で入力してください。')
            else:
                lead_time_days = attrs.get('lead_time_days', getattr(self.instance, 'lead_time_days', 0))
                if lead_time_days is None or lead_time_days < 0:
                    raise serializers.ValidationError('時間単位=DAYのとき、リードタイム(日)は0以上で入力してください。')
        elif sourcing_type == 'BUY':
            lead_time_days = attrs.get('lead_time_days', getattr(self.instance, 'lead_time_days', 0))
            if lead_time_days is None or lead_time_days <= 0:
                raise serializers.ValidationError('購買の場合、リードタイム(日)は1以上で入力してください。')

        return attrs


class BOMListSerializer(serializers.ModelSerializer):
    """一覧用の軽量シリアライザ（itemsを含まない）"""
    parent_product_name = serializers.CharField(source='parent_product.product_name', read_only=True)
    parent_product_code = serializers.CharField(source='parent_product.product_code', read_only=True)
    parent_is_final = serializers.BooleanField(source='parent_product.is_final_product', read_only=True, default=False)
    parent_is_line_final = serializers.BooleanField(source='parent_product.is_line_final_product', read_only=True, default=False)

    class Meta:
        model = BOM
        fields = '__all__'


class BOMSerializer(serializers.ModelSerializer):
    items = BOMItemSerializer(many=True, read_only=True)
    parent_product_name = serializers.CharField(source='parent_product.product_name', read_only=True)
    parent_product_code = serializers.CharField(source='parent_product.product_code', read_only=True)
    parent_is_final = serializers.SerializerMethodField()
    parent_is_line_final = serializers.SerializerMethodField()

    class Meta:
        model = BOM
        fields = '__all__'

    def validate(self, attrs):
        parent_product = attrs.get('parent_product', getattr(self.instance, 'parent_product', None))
        version = attrs.get('version', getattr(self.instance, 'version', None))
        if parent_product and version:
            qs = BOM.objects.filter(parent_product=parent_product, version=version)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError('同一の親製品・版のBOMは既に存在します。既存BOMを編集してください。')
        return attrs

    def get_parent_is_final(self, obj: BOM):
        if obj.parent_product_id:
            try:
                return bool(getattr(obj.parent_product, 'is_final_product', False))
            except Product.DoesNotExist:
                return False
        return False

    def get_parent_is_line_final(self, obj: BOM):
        if obj.parent_product_id:
            try:
                return bool(getattr(obj.parent_product, 'is_line_final_product', False))
            except Product.DoesNotExist:
                return False
        return False


class RoutingStepSerializer(serializers.ModelSerializer):
    process_name = serializers.CharField(source='process.process_name', read_only=True, default='')
    line_name = serializers.CharField(source='line.line_name', read_only=True)
    output_product_code = serializers.CharField(source='output_product.product_code', read_only=True)
    output_product_name = serializers.CharField(source='output_product.product_name', read_only=True)
    supplier_code = serializers.SerializerMethodField()
    supplier_name = serializers.SerializerMethodField()
    source_bom_item_is_coproduct_driver = serializers.BooleanField(
        source='source_bom_item.is_coproduct_driver',
        read_only=True,
        default=False,
    )
    representative_part = serializers.SerializerMethodField()
    display_label = serializers.SerializerMethodField()
    usage_quantity = serializers.SerializerMethodField()

    class Meta:
        model = RoutingStep
        fields = '__all__'

    _HIERARCHY_PATH_RE = re.compile(r'^[0-9]+(\.[0-9]+)*$')

    def _validate_hierarchy_path(self, attrs):
        hp = attrs.get('hierarchy_path')
        if hp is None and self.instance is not None:
            return
        if hp is not None:
            hp = str(hp).strip()
        if not hp:
            raise serializers.ValidationError({'hierarchy_path': '階層パスは必須です。'})
        if hp == 'final':
            raise serializers.ValidationError({'hierarchy_path': 'finalは予約語のため手入力できません。自動設定されます。'})
        if not self._HIERARCHY_PATH_RE.match(hp):
            raise serializers.ValidationError({'hierarchy_path': '階層パスは数字とドット区切りのみ有効です（例: 1, 1.1, 1.2.1）。'})

        routing = attrs.get('routing')
        if not routing and self.instance:
            routing = self.instance.routing
        if routing:
            qs = RoutingStep.objects.filter(routing=routing, hierarchy_path=hp)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError({'hierarchy_path': f'階層パス "{hp}" は同一ルーティング内で重複しています。'})

            if '.' in hp:
                parent_path = hp.rsplit('.', 1)[0]
                parent_qs = RoutingStep.objects.filter(routing=routing, hierarchy_path=parent_path)
                if self.instance:
                    parent_qs = parent_qs.exclude(pk=self.instance.pk)
                if not parent_qs.exists():
                    raise serializers.ValidationError({'hierarchy_path': f'親パス "{parent_path}" が存在しません。先に親工程を作成してください。'})

        attrs['hierarchy_path'] = hp

    def validate(self, attrs):
        attrs = super().validate(attrs)
        self._validate_hierarchy_path(attrs)

        process = attrs.get('process')
        if not process and self.instance is not None:
            process = getattr(self.instance, 'process', None)

        should_fill_line = False
        if self.instance is None:
            should_fill_line = not attrs.get('line')
        elif 'process' in attrs and 'line' not in attrs:
            should_fill_line = True
        elif 'line' in attrs and not attrs.get('line'):
            should_fill_line = True

        if should_fill_line and process and getattr(process, 'line_id', None):
            attrs['line'] = process.line
        return attrs

    def get_display_label(self, obj: RoutingStep) -> str:
        """
        A compact label used by UI dropdowns: step_no / process / line / output product code.
        """
        proc = obj.process.process_name if obj.process_id else ''
        line = obj.line.line_code if obj.line_id else ''
        out_code = obj.output_product.product_code if obj.output_product_id else ''
        parts = [
            f"Step {obj.step_no}-G{getattr(obj, 'parallel_group', 1)}",
            proc or '-',
            line or 'ライン無し',
        ]
        if out_code:
            parts.append(f"-> {out_code}")
        return " / ".join(parts)

    def _resolve_display_supplier(self, obj: RoutingStep):
        if getattr(obj, 'supplier_id', None):
            return getattr(obj, 'supplier', None)
        src = getattr(obj, 'source_bom_item', None)
        if src and getattr(src, 'supplier_id', None):
            return getattr(src, 'supplier', None)
        return None

    def get_supplier_code(self, obj: RoutingStep):
        supplier = self._resolve_display_supplier(obj)
        return getattr(supplier, 'supplier_code', None) if supplier else None

    def get_supplier_name(self, obj: RoutingStep):
        supplier = self._resolve_display_supplier(obj)
        return getattr(supplier, 'supplier_name', None) if supplier else None

    def get_representative_part(self, obj: RoutingStep) -> bool:
        if getattr(obj, 'source_bom_item_id', None):
            src = getattr(obj, 'source_bom_item', None)
            if src is not None:
                return bool(getattr(src, 'is_coproduct_driver', False))
        representative_ids = self.context.get('representative_child_ids') or set()
        if not obj.output_product_id:
            return False
        return int(obj.output_product_id) in representative_ids

    def get_usage_quantity(self, obj: RoutingStep):
        if not obj.output_product_id:
            return None

        if obj.hierarchy_path and '.' in obj.hierarchy_path:
            parent_path = obj.hierarchy_path.rsplit('.', 1)[0]
            parent_ids = RoutingStep.objects.filter(
                routing_id=obj.routing_id,
                hierarchy_path=parent_path,
            ).values_list('id', flat=True)
            total = RoutingStepMaterial.objects.filter(
                routing_step_id__in=parent_ids,
                component_id=obj.output_product_id,
            ).aggregate(total_quantity=Sum('quantity'))['total_quantity']
            if total is not None:
                return total

        if obj.remark:
            parent_ids = RoutingStep.objects.filter(
                routing_id=obj.routing_id,
                output_product__product_code=obj.remark,
            ).values_list('id', flat=True)
            total = RoutingStepMaterial.objects.filter(
                routing_step_id__in=parent_ids,
                component_id=obj.output_product_id,
            ).aggregate(total_quantity=Sum('quantity'))['total_quantity']
            if total is not None:
                return total

            bom_qty = BOMItem.objects.filter(
                bom__parent_product__product_code=obj.remark,
                child_product_id=obj.output_product_id,
            ).order_by('-bom__valid_from', '-bom_id').values_list('quantity', flat=True).first()
            if bom_qty is not None:
                return bom_qty

        return None


class RoutingSerializer(serializers.ModelSerializer):
    steps = RoutingStepSerializer(many=True, read_only=True)
    product_code = serializers.CharField(source='product.product_code', read_only=True)
    product_name = serializers.CharField(source='product.product_name', read_only=True)

    def validate(self, attrs):
        valid_from = attrs.get('valid_from_datetime', getattr(self.instance, 'valid_from_datetime', None))
        valid_to = attrs.get('valid_to_datetime', getattr(self.instance, 'valid_to_datetime', None))
        if valid_from and valid_to and valid_from > valid_to:
            raise serializers.ValidationError('有効終了日時は有効開始日時以降で入力してください。')
        return attrs

    class Meta:
        model = Routing
        fields = '__all__'


class RoutingListSerializer(serializers.ModelSerializer):
    product_code = serializers.CharField(source='product.product_code', read_only=True)
    product_name = serializers.CharField(source='product.product_name', read_only=True)

    def validate(self, attrs):
        valid_from = attrs.get('valid_from_datetime', getattr(self.instance, 'valid_from_datetime', None))
        valid_to = attrs.get('valid_to_datetime', getattr(self.instance, 'valid_to_datetime', None))
        if valid_from and valid_to and valid_from > valid_to:
            raise serializers.ValidationError('有効終了日時は有効開始日時以降で入力してください。')
        return attrs

    class Meta:
        model = Routing
        fields = [
            'id',
            'product',
            'routing_code',
            'description',
            'is_default',
            'is_active',
            'created_at',
            'updated_at',
            'valid_from_datetime',
            'valid_to_datetime',
            'product_code',
            'product_name',
        ]


class RoutingStepMaterialSerializer(serializers.ModelSerializer):
    component_code = serializers.CharField(source='component.product_code', read_only=True)
    component_name = serializers.CharField(source='component.product_name', read_only=True)
    step_no = serializers.IntegerField(source='routing_step.step_no', read_only=True)

    class Meta:
        model = RoutingStepMaterial
        fields = '__all__'


class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = '__all__'


class MobileDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = MobileDevice
        fields = '__all__'


class MobileDeviceInventorySerializer(serializers.ModelSerializer):
    management_no = serializers.CharField(source='device.management_no', read_only=True)
    checked_by_name = serializers.SerializerMethodField()
    approved_by_name = serializers.SerializerMethodField()

    class Meta:
        model = MobileDeviceInventory
        fields = '__all__'

    def get_checked_by_name(self, obj):
        if obj.checked_by:
            return obj.checked_by.get_full_name() or obj.checked_by.username
        return ''

    def get_approved_by_name(self, obj):
        if obj.approved_by:
            return obj.approved_by.get_full_name() or obj.approved_by.username
        return ''


class ManualDocumentSerializer(serializers.ModelSerializer):
    updated_by_name = serializers.SerializerMethodField()

    class Meta:
        model = ManualDocument
        fields = '__all__'

    def get_updated_by_name(self, obj):
        if obj.updated_by:
            return obj.updated_by.get_full_name() or obj.updated_by.username
        return ''
