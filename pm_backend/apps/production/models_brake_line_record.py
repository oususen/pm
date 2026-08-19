from django.db import models
from django.conf import settings

from masters.models import Equipment, Line, Process, Product


class BrakeLineRecord(models.Model):
    """
    ブレーキライン作業記録
    レーザ実績の operator_action と同様の状態管理を行う。
    START / END / PAUSE / RESUME / TEMP_END
    """

    OPERATOR_ACTION_START    = 'START'
    OPERATOR_ACTION_END      = 'END'
    OPERATOR_ACTION_PAUSE    = 'PAUSE'
    OPERATOR_ACTION_TEMP_END = 'TEMP_END'  # 旧名「一時終了」→「強制終了」に変更(2026-08)
    OPERATOR_ACTION_RESUME   = 'RESUME'
    OPERATOR_ACTION_CHOICES  = [
        (OPERATOR_ACTION_START,    '開始'),
        (OPERATOR_ACTION_END,      '終了'),
        (OPERATOR_ACTION_PAUSE,    '中断'),
        (OPERATOR_ACTION_TEMP_END, '強制終了'),
        (OPERATOR_ACTION_RESUME,   '再開'),
    ]

    id          = models.BigAutoField(primary_key=True)
    plan_date   = models.DateField(verbose_name='計画日')
    line        = models.ForeignKey(Line,      on_delete=models.CASCADE,  verbose_name='ライン')
    process     = models.ForeignKey(Process,   on_delete=models.CASCADE,  verbose_name='工程')
    product     = models.ForeignKey(Product,   on_delete=models.SET_NULL, null=True, blank=True, verbose_name='製品')
    product_code = models.CharField(max_length=50, blank=True, default='', verbose_name='品番')
    equipment   = models.ForeignKey(Equipment, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='設備')
    operator    = models.CharField(max_length=100, blank=True, default='', verbose_name='作業者')
    operator_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='brake_line_records',
        verbose_name='作業者ユーザー',
    )
    operator_action        = models.CharField(max_length=20, choices=OPERATOR_ACTION_CHOICES, verbose_name='アクション')
    operator_action_reason = models.CharField(max_length=200, blank=True, default='', verbose_name='理由')
    qty         = models.IntegerField(default=0, verbose_name='加工数（END時）')
    sequence_no = models.IntegerField(default=1, verbose_name='シーケンスNo')
    recorded_at = models.DateTimeField(auto_now_add=True, verbose_name='記録日時')

    class Meta:
        db_table        = 'brake_line_record'
        verbose_name    = 'ブレーキライン作業記録'
        verbose_name_plural = 'ブレーキライン作業記録'
        ordering        = ['-recorded_at']
        indexes         = [
            models.Index(fields=['plan_date', 'process', 'product'], name='blr_date_proc_prod_idx'),
        ]

    def __str__(self):
        return f"{self.plan_date} {self.product_code} {self.operator_action}"
