from django.conf import settings
from django.db import models


class ProductionActualReconcileReport(models.Model):
    MODE_CHOICES = [
        ('CHECK', '比較'),
        ('FIX', '修正'),
    ]
    STATUS_CHOICES = [
        ('SUCCESS', '成功'),
        ('FAILED', '失敗'),
    ]

    task_config = models.ForeignKey(
        'production.ScheduleConfig',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='production_actual_reconcile_reports',
        verbose_name='実行設定',
    )
    mode = models.CharField(max_length=10, choices=MODE_CHOICES, default='CHECK', verbose_name='実行モード')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='SUCCESS', verbose_name='実行結果')
    compared_count = models.IntegerField(default=0, verbose_name='比較件数')
    diff_count = models.IntegerField(default=0, verbose_name='差分件数')
    fixed_count = models.IntegerField(default=0, verbose_name='修正件数')
    message = models.TextField(blank=True, default='', verbose_name='実行メッセージ')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='production_actual_reconcile_reports',
        verbose_name='実行者',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        db_table = 'production_production_actual_reconcile_report'
        verbose_name = '生産実績整合レポート'
        verbose_name_plural = '生産実績整合レポート'
        ordering = ['-id']


class ProductionActualReconcileReportDetail(models.Model):
    report = models.ForeignKey(
        ProductionActualReconcileReport,
        on_delete=models.CASCADE,
        related_name='details',
        verbose_name='レポート',
    )
    line = models.ForeignKey(
        'masters.Line',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='production_actual_reconcile_details',
        verbose_name='ライン',
    )
    process = models.ForeignKey(
        'masters.Process',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='production_actual_reconcile_details',
        verbose_name='工程',
    )
    product = models.ForeignKey(
        'masters.Product',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='production_actual_reconcile_details',
        verbose_name='製品',
    )
    plan_date = models.DateField(verbose_name='計画日')
    expected_qty = models.IntegerField(default=0, verbose_name='期待実績')
    backlog_qty = models.IntegerField(default=0, verbose_name='Backlog実績')
    diff_qty = models.IntegerField(default=0, verbose_name='差分')
    fixed = models.BooleanField(default=False, verbose_name='修正済み')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')

    class Meta:
        db_table = 'production_production_actual_reconcile_report_detail'
        verbose_name = '生産実績整合レポート明細'
        verbose_name_plural = '生産実績整合レポート明細'
        indexes = [
            models.Index(fields=['report', 'plan_date']),
            models.Index(fields=['line', 'process', 'product', 'plan_date']),
        ]
