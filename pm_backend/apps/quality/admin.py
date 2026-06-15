from django.contrib import admin

from .models import (
    EquipmentInspectionConfirmation,
    EquipmentInspectionItem,
    EquipmentInspectionItemAttachment,
    EquipmentInspectionRecord,
    EquipmentInspectionResult,
    EquipmentInspectionTask,
    EquipmentInspectionTemplate,
    EquipmentInspectionWorkflowLog,
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


class EquipmentInspectionItemAttachmentInline(admin.TabularInline):
    model = EquipmentInspectionItemAttachment
    extra = 0


class EquipmentInspectionItemInline(admin.TabularInline):
    model = EquipmentInspectionItem
    extra = 0


class EquipmentInspectionResultInline(admin.TabularInline):
    model = EquipmentInspectionResult
    extra = 0


@admin.register(EquipmentInspectionTemplate)
class EquipmentInspectionTemplateAdmin(admin.ModelAdmin):
    list_display = ("sheet_code", "sheet_name", "title", "version", "status", "is_active", "updated_at")
    list_filter = ("status", "is_active")
    search_fields = ("sheet_code", "sheet_name", "title")
    filter_horizontal = ("processes", "lines")
    inlines = [EquipmentInspectionItemInline]


@admin.register(EquipmentInspectionItem)
class EquipmentInspectionItemAdmin(admin.ModelAdmin):
    list_display = ("template", "section_type", "display_order", "inspection_no", "record_type", "is_active")
    list_filter = ("section_type", "record_type", "is_active")
    search_fields = ("template__sheet_code", "item_name", "standard", "criteria")
    inlines = [EquipmentInspectionItemAttachmentInline]


@admin.register(EquipmentInspectionRecord)
class EquipmentInspectionRecordAdmin(admin.ModelAdmin):
    list_display = ("sheet_code", "sheet_name", "operation_date", "section_type", "status", "overall_result", "operator")
    list_filter = ("section_type", "status", "overall_result", "operation_date")
    search_fields = ("sheet_code", "sheet_name", "template_title", "operator__username")
    inlines = [EquipmentInspectionResultInline]


@admin.register(EquipmentInspectionTask)
class EquipmentInspectionTaskAdmin(admin.ModelAdmin):
    list_display = ("template", "task_type", "assigned_to", "status", "due_date", "created_at")
    list_filter = ("task_type", "status")
    search_fields = ("template__sheet_code", "template__sheet_name", "assigned_to__username")


@admin.register(EquipmentInspectionWorkflowLog)
class EquipmentInspectionWorkflowLogAdmin(admin.ModelAdmin):
    list_display = ("template", "action", "from_status", "to_status", "actor", "created_at")
    list_filter = ("action", "from_status", "to_status")
    search_fields = ("template__sheet_code", "template__sheet_name", "actor__username", "comment")


@admin.register(EquipmentInspectionConfirmation)
class EquipmentInspectionConfirmationAdmin(admin.ModelAdmin):
    list_display = ("sheet_code", "sheet_name", "target_month", "confirm_type", "week_index", "confirmed_by", "confirmed_at")
    list_filter = ("confirm_type", "target_month")
    search_fields = ("sheet_code", "sheet_name", "confirmed_by__username", "comment")


admin.site.register(EquipmentInspectionItemAttachment)
admin.site.register(EquipmentInspectionResult)


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


from .models_integrated_checksheet import (
    IntegratedChecksheetBatch,
    IntegratedChecksheetItem,
    IntegratedChecksheetProcessBlock,
    IntegratedChecksheetTemplate,
    IntegratedChecksheetUnit,
)


class IntegratedProcessBlockInline(admin.TabularInline):
    model = IntegratedChecksheetProcessBlock
    extra = 0


class IntegratedItemInline(admin.TabularInline):
    model = IntegratedChecksheetItem
    extra = 0


@admin.register(IntegratedChecksheetTemplate)
class IntegratedChecksheetTemplateAdmin(admin.ModelAdmin):
    list_display = ("product", "name", "version", "status", "is_active", "updated_at")
    list_filter = ("status", "is_active")
    search_fields = ("name", "product__product_code", "product__product_name")
    inlines = [IntegratedProcessBlockInline]


@admin.register(IntegratedChecksheetBatch)
class IntegratedChecksheetBatchAdmin(admin.ModelAdmin):
    list_display = ("product", "line", "plan_date", "quantity", "status", "created_at")
    list_filter = ("status", "line")
    search_fields = ("product__product_code", "lot_no")
