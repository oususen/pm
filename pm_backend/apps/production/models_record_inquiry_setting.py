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
    TAB_CHOICES = (
        (TAB_TANK, 'タンク'),
        (TAB_FLOOR, 'フロア'),
        (TAB_FLOOR_SHIPPING, 'フロア出荷'),
        (TAB_BLADE, 'ブレード'),
        (TAB_LASER, 'レーザ'),
        (TAB_BRAKE, 'ブレーキ'),
        (TAB_SPOT, 'スポット'),
    )

    tab_key = models.CharField(max_length=20, choices=TAB_CHOICES, unique=True, verbose_name='対象タブ')
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
        verbose_name = '生産実績照会設定'
        verbose_name_plural = '生産実績照会設定'

    def __str__(self):
        return f'ProductionRecordInquirySetting(tab_key={self.tab_key})'
