from django import forms
from django.contrib import admin
from django.forms.models import BaseInlineFormSet
from django.db.models import Sum
from .models import (
    Product, Customer, Process, Line, Supplier, Calendar, CalendarDay,
    BOM, BOMItem, Routing, RoutingStep, RoutingStepMaterial, ProcessCycleTime, Contact
)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['product_code', 'product_name', 'category', 'unit', 'is_final_product', 'is_line_final_product', 'is_virtual_set', 'is_active']
    list_filter = ['category', 'is_active', 'is_final_product', 'is_line_final_product', 'is_virtual_set']
    search_fields = ['product_code', 'product_name']


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['customer_code', 'customer_name', 'short_name', 'is_active']
    list_filter = ['is_active']
    search_fields = ['customer_code', 'customer_name']


@admin.register(Process)
class ProcessAdmin(admin.ModelAdmin):
    list_display = ['process_code', 'process_name', 'line', 'management_unit', 'is_outsource', 'is_active']
    list_filter = ['management_unit', 'is_outsource', 'is_active', 'line']
    search_fields = ['process_code', 'process_name']


@admin.register(Line)
class LineAdmin(admin.ModelAdmin):
    list_display = ['line_code', 'line_name', 'line_type', 'is_active', 'use_direct_process']
    list_filter = ['line_type', 'is_active', 'use_direct_process']
    search_fields = ['line_code', 'line_name']


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ['supplier_code', 'supplier_name']
    search_fields = ['supplier_code', 'supplier_name']


@admin.register(Calendar)
class CalendarAdmin(admin.ModelAdmin):
    list_display = ['calendar_code', 'calendar_name']
    search_fields = ['calendar_code', 'calendar_name']


@admin.register(CalendarDay)
class CalendarDayAdmin(admin.ModelAdmin):
    list_display = ['calendar', 'target_date', 'is_working_day', 'work_minutes']
    list_filter = ['calendar', 'is_working_day']
    date_hierarchy = 'target_date'


class BOMItemInline(admin.TabularInline):
    model = BOMItem
    extra = 1


class ParentIsFinalFilter(admin.SimpleListFilter):
    title = '最終品'
    parameter_name = 'parent_is_final'

    def lookups(self, request, model_admin):
        return (
            ('yes', 'はい'),
            ('no', 'いいえ'),
        )

    def queryset(self, request, queryset):
        value = self.value()
        if value == 'yes':
            return queryset.filter(parent_product__is_final_product=True)
        if value == 'no':
            return queryset.filter(parent_product__is_final_product=False)
        return queryset


@admin.register(BOM)
class BOMAdmin(admin.ModelAdmin):
    list_display = ['parent_product', 'version', 'valid_from', 'valid_to', 'is_coproduct', 'is_active']
    list_filter = ['is_active', 'is_coproduct', ParentIsFinalFilter]
    inlines = [BOMItemInline]
    actions = ['export_bom_tree_excel']

    def export_bom_tree_excel(self, request, queryset):
        try:
            from openpyxl import Workbook
        except ImportError:
            self.message_user(request, "openpyxl がインストールされていません。pip install openpyxl を実行してください。", level='error')
            return

        from datetime import date
        wb = Workbook()
        ws = wb.active
        ws.title = 'BOM Tree'
        ws.append(['BOM ID', '親製品', '部番表示', '製品名', '階層', '数量', '工程', 'ライン', '仕入先'])

        today = date.today()

        def pick_child_bom(product):
            qs = BOM.objects.filter(
                parent_product=product,
                is_active=True,
                valid_from__lte=today,
            ).order_by('-valid_from', '-id')
            child = qs.first()
            if child:
                return child
            return BOM.objects.filter(
                parent_product=product,
                is_active=True,
            ).order_by('-valid_from', '-id').first()

        def walk_bom(bom, parent_prefix='', level=0, visited=None):
            if visited is None:
                visited = set()
            if bom.id in visited:
                return
            visited.add(bom.id)

            # root row
            if level == 0:
                root_label = '最上位組立（最終工程）'
                display_name = f"{root_label} [{bom.parent_product.product_code}]" if bom.parent_product else root_label
                process_display = ''
                line_display = ''
                if bom.parent_product_id:
                    default_routing = Routing.objects.filter(product_id=bom.parent_product_id, is_default=True).order_by('-id').first()
                    if default_routing:
                        last_step = default_routing.steps.order_by('step_no').last()
                        if last_step:
                            if last_step.process:
                                process_display = f"{last_step.process.process_code} - {last_step.process.process_name}"
                            if last_step.line:
                                line_display = f"{last_step.line.line_code} - {last_step.line.line_name}"

                ws.append([
                    bom.id,
                    bom.parent_product.product_code if bom.parent_product else '',
                    display_name,
                    bom.parent_product.product_name if bom.parent_product else '',
                    level,
                    '',
                    process_display,
                    line_display,
                    ''
                ])

            items = list(BOMItem.objects.filter(bom=bom).select_related('child_product', 'process', 'line', 'supplier').order_by('id'))
            for idx, item in enumerate(items):
                is_last = idx == len(items) - 1
                connector = '└─ ' if is_last else '├─ '
                display_prefix = parent_prefix + connector
                display_name = display_prefix + (item.child_product.product_code if item.child_product else '')

                ws.append([
                    bom.id,
                    bom.parent_product.product_code if bom.parent_product else '',
                    display_name,
                    item.child_product.product_name if item.child_product else '',
                    level + 1,
                    item.quantity,
                    f"{item.process.process_code} - {item.process.process_name}" if item.process else '',
                    f"{item.line.line_code} - {item.line.line_name}" if item.line else '',
                    item.supplier.supplier_name if item.supplier else '',
                ])

                child_bom = pick_child_bom(item.child_product) if item.child_product else None
                if child_bom and child_bom.id not in visited:
                    child_prefix = parent_prefix + ('   ' if is_last else '│  ')
                    walk_bom(child_bom, parent_prefix=child_prefix, level=level + 1, visited=visited)

        for bom in queryset.select_related('parent_product'):
            walk_bom(bom, parent_prefix='', level=0, visited=set())

        from django.http import HttpResponse
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename=\"bom_tree.xlsx\"'
        wb.save(response)
        return response

    export_bom_tree_excel.short_description = '選択BOMの階層をExcel出力'


def _find_parent_step_ids(step):
    if not step or not step.routing_id:
        return []

    if step.hierarchy_path and '.' in step.hierarchy_path:
        parent_path = step.hierarchy_path.rsplit('.', 1)[0]
        parent_ids = list(
            RoutingStep.objects.filter(
                routing_id=step.routing_id,
                hierarchy_path=parent_path,
            ).values_list('id', flat=True)
        )
        if parent_ids:
            return parent_ids

    if step.remark:
        parent_ids = list(
            RoutingStep.objects.filter(
                routing_id=step.routing_id,
                output_product__product_code=step.remark,
            ).values_list('id', flat=True)
        )
        if parent_ids:
            return parent_ids

    return []


def _resolve_usage_quantity(step):
    if not step or not step.output_product_id:
        return None

    parent_ids = _find_parent_step_ids(step)
    if parent_ids:
        total = RoutingStepMaterial.objects.filter(
            routing_step_id__in=parent_ids,
            component_id=step.output_product_id,
        ).aggregate(total_quantity=Sum('quantity'))['total_quantity']
        if total is not None:
            return total

    if step.remark:
        bom_qty = BOMItem.objects.filter(
            bom__parent_product__product_code=step.remark,
            child_product_id=step.output_product_id,
        ).order_by('-bom__valid_from', '-bom_id').values_list('quantity', flat=True).first()
        if bom_qty is not None:
            return bom_qty

    return None


def _apply_hierarchy_defaults(step):
    """
    階層未設定の工程に、管理画面運用向けの最小デフォルトを付与する。
    """
    if not step:
        return

    raw_path = (step.hierarchy_path or '').strip()
    if raw_path:
        step.hierarchy_path = raw_path
        if raw_path == 'final':
            step.hierarchy_depth = 0
        else:
            segments = [seg for seg in raw_path.split('.') if seg]
            step.hierarchy_depth = len(segments) if segments else 1
        return

    routing_product_id = None
    if step.routing_id:
        try:
            routing_product_id = step.routing.product_id
        except Routing.DoesNotExist:
            routing_product_id = None

    # ルート製品を出力する工程は最終工程として扱う
    if routing_product_id and step.output_product_id == routing_product_id:
        step.hierarchy_path = 'final'
        step.hierarchy_depth = 0
        return

    # それ以外はトップ階層として parallel_group を階層キーに採用
    parallel_group = step.parallel_group or 1
    step.hierarchy_path = str(parallel_group)
    step.hierarchy_depth = 1


class RoutingStepInlineForm(forms.ModelForm):
    usage_quantity = forms.IntegerField(
        label='使用個数',
        required=False,
        min_value=0,
    )

    class Meta:
        model = RoutingStep
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'remark' in self.fields:
            self.fields['remark'].label = '親製品'
        if self.instance and self.instance.pk:
            usage_initial = _resolve_usage_quantity(self.instance)
            if usage_initial is not None:
                self.fields['usage_quantity'].initial = int(usage_initial)


class RoutingStepInlineFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()

        # (step_no, parallel_group) は1ルーティング内で重複禁止
        seen_keys = {}
        for inline_form in self.forms:
            cleaned = getattr(inline_form, 'cleaned_data', None)
            if not cleaned or cleaned.get('DELETE'):
                continue

            step_no = cleaned.get('step_no')
            parallel_group = cleaned.get('parallel_group')
            if step_no is None or parallel_group is None:
                continue

            key = (step_no, parallel_group)
            first_form = seen_keys.get(key)
            if first_form is not None:
                message = '同一ルーティング内で「工程番号」と「並列グループ」の組み合わせが重複しています。'
                inline_form.add_error('step_no', message)
                inline_form.add_error('parallel_group', message)
                first_form.add_error('step_no', message)
                first_form.add_error('parallel_group', message)
                continue
            seen_keys[key] = inline_form

            qs = RoutingStep.objects.filter(
                routing=self.instance,
                step_no=step_no,
                parallel_group=parallel_group,
            )
            if inline_form.instance.pk:
                qs = qs.exclude(pk=inline_form.instance.pk)
            if qs.exists():
                message = '既存データと「工程番号」「並列グループ」が重複しています。値を変更してください。'
                inline_form.add_error('step_no', message)
                inline_form.add_error('parallel_group', message)


class RoutingStepInline(admin.TabularInline):
    model = RoutingStep
    form = RoutingStepInlineForm
    formset = RoutingStepInlineFormSet
    extra = 1
    readonly_fields = ['hierarchy_indicator']
    autocomplete_fields = ['output_product']
    fields = [
        'hierarchy_indicator', 'step_no', 'parallel_group', 'process', 'line',
        'supplier', 'output_product', 'time_unit', 'lead_time_days', 'duration_min',
        'usage_quantity', 'remark'
    ]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        process_id = request.GET.get('process')
        if process_id:
            return qs.filter(process_id=process_id)
        return qs

    def hierarchy_indicator(self, obj):
        if not obj:
            return ''
        indent = '  ' * (obj.hierarchy_depth or 0)
        label = obj.hierarchy_path or str(obj.step_no or '')
        return f"{indent}{label}"
    hierarchy_indicator.short_description = '階層'


class RoutingStepMaterialInline(admin.TabularInline):
    model = RoutingStepMaterial
    extra = 1


@admin.register(RoutingStep)
class RoutingStepAdmin(admin.ModelAdmin):
    list_display = ['routing_label', 'step_no', 'parallel_group', 'hierarchy_path', 'process', 'line', 'supplier', 'output_product', 'time_unit', 'lead_time_days', 'duration_min']
    list_filter = ['process', 'line', 'supplier', 'time_unit']
    search_fields = ['routing__routing_code', 'routing__product__product_code', 'process__process_code', 'line__line_code']
    autocomplete_fields = ['output_product']
    readonly_fields = ['parallel_group', 'hierarchy_path']
    inlines = [RoutingStepMaterialInline]

    def routing_label(self, obj):
        """
        ルーティング名に加工後品目コードを付与して、同じルート内でも識別しやすくする。
        """
        # 製品コードを一度だけ表示
        product_code = ''
        if obj.routing_id:
            try:
                product_code = obj.routing.product.product_code if obj.routing.product_id else ''
            except Product.DoesNotExist:
                product_code = f"(missing Product id={obj.routing.product_id})"
        out_code = obj.output_product.product_code if obj.output_product_id else ''
        return f"{product_code} -> {out_code}" if out_code else product_code
    routing_label.short_description = 'ルーティング'


@admin.register(Routing)
class RoutingAdmin(admin.ModelAdmin):
    change_form_template = 'admin/masters/routing/change_form.html'
    list_display = ['product_display', 'routing_code', 'is_default', 'is_active']
    list_filter = ['is_active', 'is_default']
    inlines = [RoutingStepInline]
    actions = ['export_excel']

    @admin.display(description='製品', ordering='product__product_code')
    def product_display(self, obj):
        """
        Product FK might point to a missing row (legacy data); avoid crashing the admin list.
        """
        if not obj.product_id:
            return ''
        try:
            return obj.product
        except Product.DoesNotExist:
            return f"(missing Product id={obj.product_id})"

    def _save_usage_quantity_values(self, formset):
        for inline_form in formset.forms:
            cleaned = getattr(inline_form, 'cleaned_data', None)
            if not cleaned or cleaned.get('DELETE'):
                continue

            step = inline_form.instance
            usage_quantity = cleaned.get('usage_quantity')
            if usage_quantity is None or not step.pk or not step.output_product_id:
                continue

            parent_ids = _find_parent_step_ids(step)
            if len(parent_ids) != 1:
                continue

            material, _ = RoutingStepMaterial.objects.get_or_create(
                routing_step_id=parent_ids[0],
                component_id=step.output_product_id,
                defaults={
                    'quantity': usage_quantity,
                    'consume_timing': 'START',
                }
            )
            if material.quantity != usage_quantity:
                material.quantity = usage_quantity
                material.save()

    def save_formset(self, request, form, formset, change):
        if formset.model is RoutingStep:
            for inline_form in formset.forms:
                cleaned = getattr(inline_form, 'cleaned_data', None)
                if not cleaned or cleaned.get('DELETE'):
                    continue
                _apply_hierarchy_defaults(inline_form.instance)

        super().save_formset(request, form, formset, change)

        if formset.model is RoutingStep:
            self._save_usage_quantity_values(formset)

    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        extra_context = extra_context or {}
        extra_context['process_filter_choices'] = Process.objects.order_by('process_code', 'process_name')
        extra_context['selected_process_filter'] = request.GET.get('process', '')
        params = request.GET.copy()
        if 'process' in params:
            params.pop('process')
        extra_context['process_filter_query'] = params.urlencode()
        return super().changeform_view(
            request,
            object_id=object_id,
            form_url=form_url,
            extra_context=extra_context,
        )

    def export_excel(self, request, queryset):
        from openpyxl import Workbook
        from django.http import HttpResponse
        wb = Workbook()
        ws = wb.active
        ws.title = 'Routing'
        ws.append([
            'Routing Code', 'Product Code', 'Product Name',
            'Step No', 'Hierarchy Path', 'Process Code', 'Process Name',
            'Line Code', 'Line Name', '外作先コード', '外作先名', 'Output Product', 'Time Unit',
            'Lead Time (Days)', 'Duration (Min)', 'Remark'
        ])

        for routing in queryset.select_related('product'):
            steps = routing.steps.select_related('process', 'line', 'supplier', 'output_product').order_by('step_no')
            for step in steps:
                ws.append([
                    routing.routing_code,
                    routing.product.product_code if routing.product else '',
                    routing.product.product_name if routing.product else '',
                    step.step_no,
                    step.hierarchy_path or '',
                    step.process.process_code if step.process else '',
                    step.process.process_name if step.process else '',
                    step.line.line_code if step.line else '',
                    step.line.line_name if step.line else '',
                    step.supplier.supplier_code if step.supplier else '',
                    step.supplier.supplier_name if step.supplier else '',
                    step.output_product.product_code if step.output_product else '',
                    step.time_unit,
                    step.lead_time_days,
                    step.duration_min or '',
                    step.remark or '',
                ])

        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="routings.xlsx"'
        wb.save(response)
        return response

    export_excel.short_description = '選択したルーティングをExcel出力'


@admin.register(ProcessCycleTime)
class ProcessCycleTimeAdmin(admin.ModelAdmin):
    list_display = ['product', 'process', 'line', 'cycle_time_min', 'setup_time_min', 'lot_size', 'is_active', 'valid_from', 'valid_to']
    list_filter = ['is_active', 'process', 'line']
    search_fields = ['product__product_code', 'product__product_name', 'process__process_code', 'process__process_name']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('基本情報', {
            'fields': ('product', 'process', 'line')
        }),
        ('時間設定', {
            'fields': ('cycle_time_min', 'setup_time_min', 'lot_size')
        }),
        ('有効期間', {
            'fields': ('is_active', 'valid_from', 'valid_to')
        }),
        ('システム情報', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ['company_name', 'contact_type', 'contact_person', 'email', 'phone', 'display_order', 'is_active']
    list_filter = ['contact_type', 'is_active']
    search_fields = ['company_name', 'contact_person', 'email']
    ordering = ['display_order', 'id']
