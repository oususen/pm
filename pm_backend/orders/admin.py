from django.contrib import admin
from .models import LineDemand, Order, OrderLine, StgOrderRaw, StgOrderDaily


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
