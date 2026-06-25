from django.conf import settings
from django.db import models


class ProductionRecordInquirySetting(models.Model):
    TAB_TANK = 'tank'
    TAB_FLOOR = 'floor'
    TAB_FLOOR_SHIPPING = 'floor-shipping'
    TAB_BLADE = 'blade'
    TAB_LASER = 'laser'
    TAB_BRAKE = 'brake'
    TAB_SPOT = 'spot'

    tab_key = models.CharField(max_length=30, unique=True, verbose_name='タブキー')
    tab_name = models.CharField(max_length=50, default='', blank=True, verbose_name='タブ表示名')
    sort_order = models.IntegerField(default=0, verbose_name='表示順')
    target_line_codes = models.JSONField(default=list, blank=True, verbose_name='対象ラインコード一覧')
    product_mappings = models.JSONField(default=list, blank=True, verbose_name='品番マッピング一覧')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='production_record_inquiry_settings',
        verbose_name='更新者',
    )

    class Meta:
        db_table = 'production_record_inquiry_setting'
        ordering = ['sort_order', 'id']
        verbose_name = '生産実績照会設定'
        verbose_name_plural = '生産実績照会設定'

    def __str__(self):
        return f'ProductionRecordInquirySetting(tab_key={self.tab_key}, tab_name={self.tab_name})'
