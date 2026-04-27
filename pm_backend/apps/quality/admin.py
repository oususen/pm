from django.contrib import admin

from .models import (
    ProductChecksheetBatch,
    ProductChecksheetField,
    ProductChecksheetPhoto,
    ProductChecksheetRecord,
    ProductChecksheetTask,
    ProductChecksheetTemplate,
    ProductChecksheetWorkflowLog,
)


class ProductChecksheetFieldInline(admin.TabularInline):
    model = ProductChecksheetField
    extra = 0


@admin.register(ProductChecksheetTemplate)
class ProductChecksheetTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "line", "process", "product", "version", "status", "is_active", "updated_at")
    list_filter = ("status", "is_active", "line", "process")
    search_fields = ("name", "product__product_code", "product__product_name")
    inlines = [ProductChecksheetFieldInline]


@admin.register(ProductChecksheetBatch)
class ProductChecksheetBatchAdmin(admin.ModelAdmin):
    list_display = ("product", "line", "process", "lot_no", "quantity", "status", "created_at")
    list_filter = ("status", "line", "process")
    search_fields = ("lot_no", "product__product_code", "product__product_name")


@admin.register(ProductChecksheetRecord)
class ProductChecksheetRecordAdmin(admin.ModelAdmin):
    list_display = ("batch", "sequence_no", "status", "planned_ship_date", "shipment_unit_no", "shipment_sequence_no")
    list_filter = ("status", "planned_ship_date")
    search_fields = ("batch__lot_no", "batch__product__product_code")


@admin.register(ProductChecksheetTask)
class ProductChecksheetTaskAdmin(admin.ModelAdmin):
    list_display = ("template", "task_type", "assigned_to", "status", "created_at")
    list_filter = ("task_type", "status")


@admin.register(ProductChecksheetWorkflowLog)
class ProductChecksheetWorkflowLogAdmin(admin.ModelAdmin):
    list_display = ("template", "action", "actor", "created_at")
    list_filter = ("action",)


admin.site.register(ProductChecksheetPhoto)
