from django.contrib import admin
from .models import (
    LineDemand, Order, OrderLine, StgOrderRaw, StgOrderDaily,
    StockAllocation, ProductionOrder, ProcessActual, ScrapRecord
)


class OrderLineInline(admin.TabularInline):
    model = OrderLine
    extra = 0
    fields = ['line_no', 'product_code', 'quantity', 'due_date', 'plant_code', 'ship_to_code']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_no', 'customer', 'order_type', 'version_no', 'status', 'order_date', 'created_at']
    list_filter = ['order_type', 'status', 'order_date']
    search_fields = ['order_no', 'source_file', 'customer__customer_name']
    inlines = [OrderLineInline]
    date_hierarchy = 'order_date'


@admin.register(OrderLine)
class OrderLineAdmin(admin.ModelAdmin):
    list_display = ['order', 'line_no', 'product_code', 'quantity', 'due_date']
    list_filter = ['due_date']
    search_fields = ['product_code', 'order__order_no']
    date_hierarchy = 'due_date'


@admin.register(StgOrderRaw)
class StgOrderRawAdmin(admin.ModelAdmin):
    list_display = ['customer_code', 'order_type', 'source_file', 'source_row_no', 'parse_status', 'created_at']
    list_filter = ['order_type', 'parse_status']
    search_fields = ['customer_code', 'product_code', 'source_file']
    readonly_fields = ['raw_payload']


@admin.register(StgOrderDaily)
class StgOrderDailyAdmin(admin.ModelAdmin):
    list_display = ['customer', 'product_code', 'order_type', 'due_date', 'quantity', 'created_at']
    list_filter = ['order_type', 'due_date']
    search_fields = ['product_code', 'customer__customer_name']
    date_hierarchy = 'due_date'


@admin.register(LineDemand)
class LineDemandAdmin(admin.ModelAdmin):
    list_display = ['line', 'product_code', 'plan_date', 'firm_qty', 'forecast_qty', 'plan_qty', 'actual_qty']
    list_filter = ['line', 'plan_date']
    search_fields = ['product_code', 'order_numbers']


# 製造実行系モデルの管理画面
@admin.register(StockAllocation)
class StockAllocationAdmin(admin.ModelAdmin):
    list_display = ['product', 'location', 'current_stock', 'reserved_qty', 'available_qty_display', 'min_stock_qty', 'is_bottleneck']
    list_filter = ['is_bottleneck', 'location']
    search_fields = ['product__product_code', 'product__product_name', 'location']
    readonly_fields = ['created_at', 'updated_at']

    def available_qty_display(self, obj):
        return obj.available_qty
    available_qty_display.short_description = '引当可能数量'


class ProcessActualInline(admin.TabularInline):
    model = ProcessActual
    extra = 0
    fields = ['routing_step', 'process', 'line', 'completed_qty', 'actual_duration_min', 'completed_at', 'operator']
    readonly_fields = ['created_at']


@admin.register(ProductionOrder)
class ProductionOrderAdmin(admin.ModelAdmin):
    list_display = ['order_no', 'product', 'line', 'order_qty', 'status', 'scheduled_start_date', 'scheduled_end_date', 'priority']
    list_filter = ['status', 'line', 'scheduled_start_date']
    search_fields = ['order_no', 'product__product_code', 'product__product_name']
    date_hierarchy = 'scheduled_start_date'
    inlines = [ProcessActualInline]
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('基本情報', {
            'fields': ('order_no', 'product', 'routing', 'line', 'order_qty')
        }),
        ('スケジュール', {
            'fields': ('scheduled_start_date', 'scheduled_end_date', 'actual_start_date', 'actual_end_date')
        }),
        ('ステータス', {
            'fields': ('status', 'priority', 'allocation')
        }),
        ('その他', {
            'fields': ('remark', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ProcessActual)
class ProcessActualAdmin(admin.ModelAdmin):
    list_display = ['production_order', 'process', 'line', 'completed_qty', 'actual_duration_min', 'completed_at', 'operator']
    list_filter = ['process', 'line', 'completed_at']
    search_fields = ['production_order__order_no', 'process__process_code', 'operator']
    date_hierarchy = 'completed_at'
    readonly_fields = ['created_at', 'updated_at']


@admin.register(ScrapRecord)
class ScrapRecordAdmin(admin.ModelAdmin):
    list_display = ['product_code', 'product_name', 'process', 'line', 'qty', 'recorded_at', 'reason', 'reason_detail', 'is_replenished', 'replenished_at']
    list_filter = ['process', 'line', 'reason', 'is_replenished']
    search_fields = ['product_code', 'product_name', 'batch_no', 'operator_name', 'reason_detail', 'remarks']
    readonly_fields = ['recorded_at']
