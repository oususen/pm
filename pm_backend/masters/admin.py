from django.contrib import admin
from .models import (
    Product, Customer, Process, Line, Supplier, Calendar, CalendarDay,
    BOM, BOMItem, Routing, RoutingStep, RoutingStepMaterial
)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['product_code', 'product_name', 'category', 'unit', 'is_active']
    list_filter = ['category', 'is_active', 'is_final_product']
    search_fields = ['product_code', 'product_name']


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['customer_code', 'customer_name', 'short_name', 'is_active']
    list_filter = ['is_active']
    search_fields = ['customer_code', 'customer_name']


@admin.register(Process)
class ProcessAdmin(admin.ModelAdmin):
    list_display = ['process_code', 'process_name', 'is_outsource', 'is_active']
    list_filter = ['is_outsource', 'is_active']
    search_fields = ['process_code', 'process_name']


@admin.register(Line)
class LineAdmin(admin.ModelAdmin):
    list_display = ['line_code', 'line_name', 'is_active']
    list_filter = ['is_active']
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


@admin.register(BOM)
class BOMAdmin(admin.ModelAdmin):
    list_display = ['parent_product', 'version', 'valid_from', 'valid_to', 'is_active']
    list_filter = ['is_active']
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
        ws.append(['BOM ID', '親製品', '部番表示', '階層', '数量', '工程', 'ライン', '仕入先'])

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


class RoutingStepInline(admin.TabularInline):
    model = RoutingStep
    extra = 1
    readonly_fields = ['hierarchy_indicator']
    fields = ['hierarchy_indicator', 'step_no', 'process', 'line', 'output_product', 'time_unit', 'lead_time_days', 'duration_min', 'remark']

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
    list_display = ['routing', 'step_no', 'hierarchy_path', 'process', 'line', 'output_product', 'time_unit', 'lead_time_days', 'duration_min']
    list_filter = ['process', 'line', 'time_unit']
    search_fields = ['routing__routing_code', 'routing__product__product_code', 'process__process_code', 'line__line_code']
    inlines = [RoutingStepMaterialInline]


@admin.register(Routing)
class RoutingAdmin(admin.ModelAdmin):
    list_display = ['product', 'routing_code', 'is_default', 'is_active']
    list_filter = ['is_active', 'is_default']
    inlines = [RoutingStepInline]
    actions = ['export_excel']

    def export_excel(self, request, queryset):
        from openpyxl import Workbook
        from django.http import HttpResponse
        wb = Workbook()
        ws = wb.active
        ws.title = 'Routing'
        ws.append([
            'Routing Code', 'Product Code', 'Product Name',
            'Step No', 'Hierarchy Path', 'Process Code', 'Process Name',
            'Line Code', 'Line Name', 'Output Product', 'Time Unit',
            'Lead Time (Days)', 'Duration (Min)', 'Remark'
        ])

        for routing in queryset.select_related('product'):
            steps = routing.steps.select_related('process', 'line', 'output_product').order_by('step_no')
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
