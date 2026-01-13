from django.conf import settings
from django.db import models


class Department(models.Model):
    """部署テーブル"""
    LEVEL_CHOICES = [
        ('division', '事業部'),
        ('group', '係'),
        ('team', '班'),
    ]

    name = models.CharField(max_length=100, verbose_name='部署名')
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, verbose_name='階層')
    parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='children',
        verbose_name='親部署'
    )
    display_id = models.IntegerField(verbose_name='表示順')

    class Meta:
        db_table = 'accounts_department'
        unique_together = [['name', 'level']]
        verbose_name = '部署'
        verbose_name_plural = '部署'
        ordering = ['display_id', 'id']

    def __str__(self):
        return f"{self.name} ({self.get_level_display()})"


class UserProfile(models.Model):
    """ユーザープロファイル（auth_userの拡張）"""
    ROLE_CHOICES = [
        ('staff', '一般'),
        ('supervisor', '班長'),
        ('chief', '係長'),
        ('manager', '事業部長'),
    ]

    EMPLOYMENT_TYPE_CHOICES = [
        ('regular', '正社員'),
        ('skilled', '特定技能実習生'),
        ('intern', '実習生'),
        ('temporary', '人材派遣'),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='profile',
        verbose_name='ユーザー'
    )

    employee_code = models.CharField(max_length=32, unique=True, blank=True, null=True, verbose_name='社員コード')
    position = models.CharField(max_length=100, blank=True, verbose_name='役職')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='staff', verbose_name='役割')
    employment_type = models.CharField(
        max_length=20,
        choices=EMPLOYMENT_TYPE_CHOICES,
        default='regular',
        verbose_name='雇用形態'
    )

    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users',
        verbose_name='所属部署'
    )
    division = models.CharField(max_length=100, blank=True, verbose_name='事業部')
    group = models.CharField(max_length=100, blank=True, verbose_name='係')
    team = models.CharField(max_length=100, blank=True, verbose_name='班')

    joined_on = models.DateField(null=True, blank=True, verbose_name='入社日')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        db_table = 'accounts_userprofile'
        verbose_name = 'ユーザープロファイル'
        verbose_name_plural = 'ユーザープロファイル'

    def __str__(self):
        return f"{self.user.username} - {self.user.get_full_name() or self.user.email}"


class UserSmtpConfig(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='smtp_config',
    )
    smtp_host = models.CharField(max_length=255)
    smtp_port = models.PositiveIntegerField(null=True, blank=True)
    smtp_user = models.CharField(max_length=255)
    smtp_password = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    is_admin = models.BooleanField(default=False)

    class Meta:
        db_table = 'accounts_user_smtp_configs'
