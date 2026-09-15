from django.conf import settings
from django.db import models


class ShiftLine(models.Model):
    """勤務ライン"""
    name = models.CharField(max_length=50, verbose_name='ライン名')
    sort_order = models.IntegerField(default=0, verbose_name='表示順')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['sort_order', 'id']
        verbose_name = '勤務ライン'
        verbose_name_plural = '勤務ライン'

    def __str__(self):
        return self.name


class ShiftWorker(models.Model):
    """シフト作業者（ライン別）"""
    SHIFT_CHOICES = [
        ('朝', '朝勤'),
        ('昼', '昼勤'),
        ('夜', '夜勤'),
    ]

    shift_line = models.ForeignKey(
        ShiftLine, on_delete=models.CASCADE, related_name='workers',
        verbose_name='勤務ライン'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name='ユーザー'
    )
    name = models.CharField(max_length=50, verbose_name='作業者名')
    shift_type = models.CharField(
        max_length=2, choices=SHIFT_CHOICES, default='朝', verbose_name='勤務帯'
    )
    work_start = models.TimeField(default='08:00', verbose_name='出勤時刻')
    work_end = models.TimeField(default='17:00', verbose_name='退勤時刻')
    sort_order = models.IntegerField(default=0, verbose_name='表示順')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['sort_order', 'id']
        verbose_name = 'シフト作業者'
        verbose_name_plural = 'シフト作業者'

    def __str__(self):
        return f'{self.name}（{self.shift_line.name}）'


class ShiftLineProcess(models.Model):
    """勤務ライン×工程の紐付け（色・必要時間・表示順）"""
    shift_line = models.ForeignKey(
        ShiftLine, on_delete=models.CASCADE, related_name='line_processes',
        verbose_name='勤務ライン'
    )
    process = models.ForeignKey(
        'masters.Process', on_delete=models.CASCADE,
        verbose_name='工程'
    )
    color = models.CharField(max_length=7, default='#64748b', verbose_name='表示色')
    required_hours = models.DecimalField(
        max_digits=5, decimal_places=2, default=1, verbose_name='必要時間(h)'
    )
    sort_order = models.IntegerField(default=0, verbose_name='表示順')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['sort_order', 'id']
        unique_together = [('shift_line', 'process')]
        verbose_name = 'ライン工程設定'
        verbose_name_plural = 'ライン工程設定'

    def __str__(self):
        return f'{self.shift_line.name} - {self.process.process_name}'


class ShiftAssignment(models.Model):
    """シフト配置"""
    shift_line = models.ForeignKey(
        ShiftLine, on_delete=models.CASCADE, related_name='assignments',
        verbose_name='勤務ライン'
    )
    worker = models.ForeignKey(
        ShiftWorker, on_delete=models.CASCADE, related_name='assignments',
        verbose_name='作業者'
    )
    process = models.ForeignKey(
        'masters.Process', on_delete=models.CASCADE,
        verbose_name='工程'
    )
    date = models.DateField(verbose_name='日付')
    start_time = models.TimeField(verbose_name='開始時刻')
    work_hours = models.DecimalField(
        max_digits=4, decimal_places=2, verbose_name='実働時間(h)'
    )
    units = models.IntegerField(default=0, verbose_name='台数')
    comment = models.CharField(max_length=200, blank=True, default='', verbose_name='コメント')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['date', 'start_time']
        verbose_name = 'シフト配置'
        verbose_name_plural = 'シフト配置'

    def __str__(self):
        return f'{self.date} {self.worker.name} {self.start_time}'
