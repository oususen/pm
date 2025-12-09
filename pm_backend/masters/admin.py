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


class RoutingStepInline(admin.TabularInline):
    model = RoutingStep
    extra = 1


class RoutingStepMaterialInline(admin.TabularInline):
    model = RoutingStepMaterial
    extra = 1


@admin.register(RoutingStep)
class RoutingStepAdmin(admin.ModelAdmin):
    list_display = ['routing', 'step_no', 'process', 'line', 'output_product', 'time_unit', 'lead_time_days', 'duration_min']
    list_filter = ['process', 'line', 'time_unit']
    search_fields = ['routing__routing_code', 'routing__product__product_code', 'process__process_code', 'line__line_code']
    inlines = [RoutingStepMaterialInline]


@admin.register(Routing)
class RoutingAdmin(admin.ModelAdmin):
    list_display = ['product', 'routing_code', 'is_default', 'is_active']
    list_filter = ['is_active', 'is_default']
    inlines = [RoutingStepInline]
