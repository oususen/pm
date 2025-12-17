from rest_framework import serializers
from .models import (
    Product, Customer, Process, Line, Supplier, Calendar, CalendarDay, WorkPattern, BreakTime,
    BOM, BOMItem, Routing, RoutingStep, RoutingStepMaterial
)


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
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
    class Meta:
        model = Supplier
        fields = '__all__'


class CalendarSerializer(serializers.ModelSerializer):
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
    child_product_name = serializers.CharField(source='child_product.product_name', read_only=True)
    process_name = serializers.CharField(source='process.process_name', read_only=True)
    line_name = serializers.CharField(source='line.line_name', read_only=True)

    class Meta:
        model = BOMItem
        fields = '__all__'

    def validate(self, attrs):
        sourcing_type = attrs.get('sourcing_type', getattr(self.instance, 'sourcing_type', None))
        time_unit = attrs.get('time_unit', getattr(self.instance, 'time_unit', 'MINUTE'))
        process = attrs.get('process', getattr(self.instance, 'process', None))

        if sourcing_type == 'MAKE' and process is None:
            raise serializers.ValidationError('自社製造の場合、工程は必須です。')

        # 工程時間の必須チェックは自社製造のみ
        if sourcing_type == 'MAKE':
            if time_unit not in ['MINUTE', 'DAY']:
                raise serializers.ValidationError('時間単位は MINUTE か DAY を指定してください。')

            if time_unit == 'MINUTE':
                duration_min = attrs.get('duration_min', getattr(self.instance, 'duration_min', None))
                if duration_min is None or duration_min <= 0:
                    raise serializers.ValidationError('時間単位=MINUTEのとき、所要時間(分)は1以上で入力してください。')
            else:
                lead_time_days = attrs.get('lead_time_days', getattr(self.instance, 'lead_time_days', 0))
                if lead_time_days is None or lead_time_days <= 0:
                    raise serializers.ValidationError('時間単位=DAYのとき、リードタイム(日)は1以上で入力してください。')
        elif sourcing_type == 'BUY':
            lead_time_days = attrs.get('lead_time_days', getattr(self.instance, 'lead_time_days', 0))
            if lead_time_days is None or lead_time_days <= 0:
                raise serializers.ValidationError('購買の場合、リードタイム(日)は1以上で入力してください。')

        return attrs


class BOMSerializer(serializers.ModelSerializer):
    items = BOMItemSerializer(many=True, read_only=True)
    parent_product_name = serializers.CharField(source='parent_product.product_name', read_only=True)
    parent_is_final = serializers.SerializerMethodField()
    parent_is_line_final = serializers.SerializerMethodField()

    class Meta:
        model = BOM
        fields = '__all__'

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
    process_name = serializers.CharField(source='process.process_name', read_only=True)
    line_name = serializers.CharField(source='line.line_name', read_only=True)
    output_product_code = serializers.CharField(source='output_product.product_code', read_only=True)
    output_product_name = serializers.CharField(source='output_product.product_name', read_only=True)
    display_label = serializers.SerializerMethodField()

    class Meta:
        model = RoutingStep
        fields = '__all__'

    def get_display_label(self, obj: RoutingStep) -> str:
        """
        A compact label used by UI dropdowns: step_no / process / line / output product code.
        """
        proc = obj.process.process_name if obj.process_id else ''
        line = obj.line.line_code if obj.line_id else ''
        out_code = obj.output_product.product_code if obj.output_product_id else ''
        parts = [
            f"Step {obj.step_no}",
            proc or '-',
            line or 'ライン無し',
        ]
        if out_code:
            parts.append(f"-> {out_code}")
        return " / ".join(parts)


class RoutingSerializer(serializers.ModelSerializer):
    steps = RoutingStepSerializer(many=True, read_only=True)
    product_name = serializers.CharField(source='product.product_name', read_only=True)

    class Meta:
        model = Routing
        fields = '__all__'


class RoutingStepMaterialSerializer(serializers.ModelSerializer):
    component_code = serializers.CharField(source='component.product_code', read_only=True)
    component_name = serializers.CharField(source='component.product_name', read_only=True)
    step_no = serializers.IntegerField(source='routing_step.step_no', read_only=True)

    class Meta:
        model = RoutingStepMaterial
        fields = '__all__'
