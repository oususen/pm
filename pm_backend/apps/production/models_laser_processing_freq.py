from django.db import models


class LaserProcessingFreqPattern(models.Model):
    """レーザ加工頻度パターン"""

    FREQ_DAILY = 'DAILY'
    FREQ_WEEKLY = 'WEEKLY'
    FREQ_EVERY_N_DAYS = 'EVERY_N_DAYS'
    FREQ_CHOICES = [
        (FREQ_DAILY, '毎日'),
        (FREQ_WEEKLY, '毎週曜日'),
        (FREQ_EVERY_N_DAYS, 'N営業日ごと'),
    ]

    DAY_CHOICES = [
        (0, '月'), (1, '火'), (2, '水'), (3, '木'), (4, '金'),
    ]

    pattern_code = models.CharField(max_length=30, unique=True, verbose_name='パターンコード')
    pattern_name = models.CharField(max_length=100, verbose_name='パターン名')
    frequency_type = models.CharField(max_length=20, choices=FREQ_CHOICES, default=FREQ_DAILY, verbose_name='加工頻度種別')
    day_of_week = models.PositiveSmallIntegerField(null=True, blank=True, choices=DAY_CHOICES, verbose_name='加工曜日(0=月〜4=金)')
    interval_days = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name='間隔営業日数')
    is_active = models.BooleanField(default=True, verbose_name='有効')
    note = models.CharField(max_length=200, blank=True, default='', verbose_name='備考')

    class Meta:
        db_table = 't_laser_processing_freq_pattern'
        ordering = ['pattern_code']
        verbose_name = 'レーザ加工頻度パターン'
        verbose_name_plural = 'レーザ加工頻度パターン'

    def __str__(self):
        return f'{self.pattern_code} - {self.pattern_name}'
