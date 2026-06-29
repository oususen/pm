from django.db import models
from masters.models import Process, Product, Line


class SingleProcFinishedEntry(models.Model):
    """
    単独計画で入力された完成品番号・数量を保存するテーブル。
    ガントチャート/LineBacklogにはサブ品に変換して保存するが、
    再読込時に完成品番号を復元するためにこのテーブルを使用する。
    """
    line = models.ForeignKey(Line, on_delete=models.CASCADE)
    process = models.ForeignKey(Process, on_delete=models.CASCADE)
    plan_date = models.DateField()
    sequence_no = models.IntegerField()
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=0)

    class Meta:
        db_table = 't_singleproc_finished_entry'
        indexes = [
            models.Index(fields=['line', 'process', 'plan_date']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['line', 'process', 'plan_date', 'sequence_no'],
                name='uq_singleproc_finished_entry',
            ),
        ]
