from django.conf import settings
from django.db import models


class Department(models.Model):
    """部署テーブル"""
    LEVEL_CHOICES = [
        ('division', '事業部'),
        ('group', '係'),
        ('team', '班'),
        ('unit', 'グループ'),
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
        ('manager', '事業部長・課長'),
        ('chief', '係長'),
        ('supervisor', '班長'),
        ('leader', 'リーダー'),
        ('staff', '一般'),
    ]

    EMPLOYMENT_TYPE_CHOICES = [
        ('regular', '正準社員'),
        ('dispatch', '人材派遣'),
        ('intern', '実習生'),
        ('skilled', '特定技能実習生'),
        ('contract', '嘱託社員'),
        ('part', 'パート'),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='profile',
        verbose_name='ユーザー'
    )

    employee_code = models.CharField(max_length=32, unique=True, blank=True, null=True, verbose_name='社員コード')
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
    division = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='division_users',
        verbose_name='事業部',
        limit_choices_to={'level': 'division'}
    )
    group = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='group_users',
        verbose_name='係',
        limit_choices_to={'level': 'group'}
    )
    team = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='team_users',
        verbose_name='班',
        limit_choices_to={'level': 'team'}
    )
    supervisor_teams = models.ManyToManyField(
        Department,
        blank=True,
        related_name='supervisor_users',
        verbose_name='班長担当班',
        limit_choices_to={'level': 'team'},
    )
    leader_units = models.ManyToManyField(
        Department,
        blank=True,
        related_name='leader_users',
        verbose_name='リーダー担当グループ',
        limit_choices_to={'level': 'unit'},
    )
    unit = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='unit_users',
        verbose_name='グループ',
        limit_choices_to={'level': 'unit'}
    )

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


class UserPermission(models.Model):
    RESOURCE_CHOICES = [
        ('dashboard', 'ダッシュボード'),
        ('orders', '受注'),
        ('orders.list', '受注: 受注一覧'),
        ('orders.csv_import', '受注: 受注取込'),
        ('orders.kubota_analysis', '受注: クボタ内示変化推移分析'),
        ('orders.line_expand', '受注: ライン展開'),
        ('production', '生産'),
        ('production.process_input', '生産: 工程作業入力'),
        ('production.record_edit', '生産: 実績変更'),
        ('production.scrap_record', '生産: 仕損品記録'),
        ('production.plan_input', '生産: 生産計画入力'),
        ('production.inventory', '生産: 在庫/残量一覧'),
        ('production.scrap_history', '生産: 仕損履歴'),
        ('production.line_calendars', '生産: ライン勤務カレンダ'),
        ('production.line_monitor', '生産: ライン稼働監視'),
        ('purchase', '仕入'),
        ('purchase.plan_input', '仕入: 仕入れ計画'),
        ('purchase.inventory', '仕入: 在庫/残量'),
        ('purchase.progress', '仕入: 仕入れ進度'),
        ('purchase.actual_input', '仕入: 仕入れ実績入力'),
        ('purchase.actual_inquiry', '仕入: 納入実績照会'),
        ('purchase.supplier_calendar', '仕入: 仕入れ先カレンダ'),
        ('purchase.order_proposals', '仕入: 発注提案'),
        ('shipping', '出荷'),
        ('inventory', '在庫'),
        ('quality', '品質'),
        ('notifications', '通知'),
        ('notifications.create', '通知: 通知作成'),
        ('engineering_change', '設変'),
        ('masters', 'マスタ'),
        ('settings', '設定'),
        ('settings.profile', '設定: プロフィール編集'),
        ('settings.users', '設定: ユーザー管理'),
        ('settings.departments', '設定: 組織管理'),
        ('settings.user_permissions', '設定: ユーザー権限編集'),
        ('settings.permission_templates', '設定: 権限テンプレート'),
        ('settings.smtp', '設定: SMTP設定'),
        ('settings.purchase_plan_lock', '設定: 仕入計画ロック設定'),
        ('settings.production_plan_lock', '設定: 生産計画ロック設定'),
        ('settings.scheduled_tasks', '設定: 定時タスク設定'),
        ('settings.supplier_order_schedule', '設定: 発注スケジュール設定'),
        ('settings.purchase_order_approval', '設定: 発注承認者設定'),
        ('settings.stocktake_init', '設定: 棚卸初期化'),
        ('users', 'ユーザー管理'),
        ('manual', 'マニュアル'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='permissions',
    )
    resource = models.CharField(max_length=50, choices=RESOURCE_CHOICES)
    can_view = models.BooleanField(default=False)
    can_edit = models.BooleanField(default=False)

    class Meta:
        db_table = 'accounts_userpermission'
        unique_together = [['user', 'resource']]


class DepartmentPermission(models.Model):
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name='permissions',
    )
    resource = models.CharField(max_length=50, choices=UserPermission.RESOURCE_CHOICES)
    can_view = models.BooleanField(default=False)
    can_edit = models.BooleanField(default=False)

    class Meta:
        db_table = 'accounts_departmentpermission'
        unique_together = [['department', 'resource']]


class PositionPermission(models.Model):
    position_name = models.CharField(max_length=100)
    resource = models.CharField(max_length=50, choices=UserPermission.RESOURCE_CHOICES)
    can_view = models.BooleanField(default=False)
    can_edit = models.BooleanField(default=False)

    class Meta:
        db_table = 'accounts_positionpermission'
        unique_together = [['position_name', 'resource']]


class DepartmentPositionPermission(models.Model):
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name='position_permissions',
    )
    position_name = models.CharField(max_length=100)
    resource = models.CharField(max_length=50, choices=UserPermission.RESOURCE_CHOICES)
    can_view = models.BooleanField(default=False)
    can_edit = models.BooleanField(default=False)

    class Meta:
        db_table = 'accounts_department_position_permission'
        unique_together = [['department', 'position_name', 'resource']]
