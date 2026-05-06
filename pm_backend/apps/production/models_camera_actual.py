from django.db import models
from masters.models import Line, Process, Product


class CameraCountEvent(models.Model):
    """カメラ検知イベント原本。camera_event_idで冪等制御する。"""

    STATUS_ACCEPTED = "accepted"
    STATUS_REPLAYED = "replayed"
    STATUS_CHOICES = [
        (STATUS_ACCEPTED, "accepted"),
        (STATUS_REPLAYED, "replayed"),
    ]

    id = models.BigAutoField(primary_key=True)
    camera_event_id = models.CharField(max_length=64, unique=True, verbose_name="カメライベントID")
    line = models.ForeignKey(Line, on_delete=models.CASCADE, verbose_name="ライン")
    process = models.ForeignKey(Process, on_delete=models.CASCADE, verbose_name="工程")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="製品")
    count = models.IntegerField(default=1, verbose_name="加算数")
    event_at_client = models.DateTimeField(verbose_name="端末検知時刻")
    event_at_server = models.DateTimeField(auto_now_add=True, verbose_name="サーバ受信時刻")
    business_date = models.DateField(verbose_name="業務日")
    device_id = models.CharField(max_length=128, blank=True, default="", verbose_name="端末ID")
    confidence = models.DecimalField(max_digits=6, decimal_places=4, null=True, blank=True, verbose_name="信頼度")
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_ACCEPTED, verbose_name="状態")

    class Meta:
        db_table = "t_camera_count_event"
        verbose_name = "カメラカウントイベント"
        verbose_name_plural = "カメラカウントイベント"
        indexes = [
            models.Index(fields=["business_date", "line", "process", "product"]),
            models.Index(fields=["event_at_server"]),
        ]


class ProductionResultDaily(models.Model):
    """ライン×工程×製品の日次実績集計。"""

    id = models.BigAutoField(primary_key=True)
    business_date = models.DateField(verbose_name="業務日")
    line = models.ForeignKey(Line, on_delete=models.CASCADE, verbose_name="ライン")
    process = models.ForeignKey(Process, on_delete=models.CASCADE, verbose_name="工程")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="製品")
    actual_count = models.IntegerField(default=0, verbose_name="実績数")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新日時")

    class Meta:
        db_table = "t_production_result_daily"
        verbose_name = "日次生産実績"
        verbose_name_plural = "日次生産実績"
        unique_together = [["business_date", "line", "process", "product"]]
        indexes = [
            models.Index(fields=["business_date", "line", "process", "product"]),
        ]
