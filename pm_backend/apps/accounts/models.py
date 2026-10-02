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
        ('office_staff', '事務員'),
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
    is_system_admin = models.BooleanField(default=False, verbose_name='システム管理者')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        db_table = 'accounts_userprofile'
        verbose_name = 'ユーザープロファイル'
        verbose_name_plural = 'ユーザープロファイル'

    def __str__(self):
        return f"{self.user.username} - {self.user.get_full_name() or self.user.email}"


class UnitLineMapping(models.Model):
    """グループと利用ラインの紐付"""

    unit = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name='line_mappings',
        verbose_name='グループ',
        limit_choices_to={'level': 'unit'},
    )
    line = models.ForeignKey(
        'masters.Line',
        on_delete=models.CASCADE,
        related_name='unit_mappings',
        verbose_name='ライン',
    )
    sort_order = models.IntegerField(default=0, verbose_name='表示順')
    is_default = models.BooleanField(default=False, verbose_name='初期ライン')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        db_table = 'accounts_unit_line_mapping'
        verbose_name = 'グループライン紐付'
        verbose_name_plural = 'グループライン紐付'
        unique_together = [['unit', 'line']]
        ordering = ['unit_id', '-is_default', 'sort_order', 'id']

    def __str__(self):
        return f"{self.unit.name} - {self.line.line_code}"


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
        ('orders.first_article', '受注: お久しぶり製品通知設定'),
        ('production', '生産'),
        ('production.process_input', '生産: 工程作業入力'),
        ('production.process_knowledge', '生産: 工程別コツ・注意事項'),
        ('production.record_inquiry', '生産: 生産実績照会'),
        ('production.record_edit', '生産: 実績変更'),
        ('production.scrap_record', '生産: 仕損品記録'),
        ('production.plan_input', '生産: 生産計画入力'),
        ('production.inventory', '生産: 在庫/残量一覧'),
        ('production.progress', '生産: 進度のみ'),
        ('production.scrap_history', '生産: 仕損履歴'),
        ('production.line_calendars', '生産: ライン勤務カレンダ'),
        ('production.morning_meeting', '生産: 朝礼'),
        ('production.line_monitor', '生産: ライン稼働監視'),
        ('overtime', '勤務'),
        ('overtime.shift_management', '勤務: シフト管理'),
        ('overtime.personal_summary', '勤務: 個人別残業集計'),
        ('purchase', '仕入'),
        ('purchase.plan_input', '仕入: 仕入れ計画'),
        ('purchase.inventory', '仕入: 在庫/残量'),
        ('purchase.progress', '仕入: 仕入れ進度'),
        ('purchase.receiving', '仕入: 仕入れ検収'),
        ('purchase.receiving_mobile', '仕入: 仕入れ検収（スマホ）'),
        ('purchase.receiving_confirm', '仕入: スマホ検収 確認'),
        ('purchase.actual_input', '仕入: 仕入れ実績入力'),
        ('purchase.actual_edit', '仕入: 納入実績編集'),
        ('purchase.actual_inquiry', '仕入: 納入実績照会'),
        ('purchase.supplier_calendar', '仕入: 仕入れ先カレンダ'),
        ('purchase.supplier_order_pattern', '仕入: 納入パターン設定'),
        ('purchase.delivery_schedule', '仕入: 納入予定'),
        ('purchase.order_proposals', '仕入: 外作・購入品注文'),
        ('purchase.auto_delivery_list', '仕入: 自動納入リスト送信'),
        ('shipping', '出荷'),
        ('shipping.instruction', '出荷: 出荷指示'),
        ('shipping.actual', '出荷: 出荷実績'),
        ('shipping.progress', '出荷: 出荷進度照会'),
        ('shipping.order_document', '出荷: 出荷指示書'),
        ('shipping.hirakata_pickup', '出荷: 枚方集荷依頼書'),
        ('shipping.fujishoji_document', '出荷: 富士商事出荷指示書'),
        ('shipping.kubota_sakai_due_adjustment', '出荷: クボタ堺納期調整'),
        ('shipping.kubota_sakai_trip_planning', '出荷: クボタ堺便計画'),
        ('shipping.trip_execution', '出荷: 便確認（実行）'),
        ('shipping.trip_progress', '出荷: 便確認（業務員）'),
        ('shipping.trip_progress_summary', '出荷: 便進捗確認（一覧）'),
        ('shipping.progress_edit', '出荷: 出荷進度管理'),
        ('shipping.ship_to_lead_time', '出荷: 納入地別出荷加算日数'),
        ('consumables', '消耗品'),
        ('consumables.inventory', '消耗品: 在庫一覧'),
        ('consumables.operations', '消耗品: 入出庫・注文依頼'),
        ('consumables.dispatch', '消耗品: 発注準備・注文書'),
        ('consumables.history', '消耗品: 入出庫履歴'),
        ('consumables.masters', '消耗品: マスタ'),
        ('inventory', '在庫'),
        ('stocktake', '在庫: 棚卸入力'),
        ('stocktake.area', '在庫: 棚卸エリア管理'),
        ('stocktake.delete', '在庫: 棚卸履歴削除'),
        ('quality', '品質'),
        ('quality.equipment_inspection_master', '品質: 設備点検項目作成'),
        ('quality.equipment_inspection_operation', '品質: 設備点検実施'),
        ('quality.equipment_inspection_monthly_review', '品質: 設備点検月間確認'),
        ('quality.equipment_inspection', '品質: 設備点検実施（旧キー互換）'),
        ('quality.integrated_checksheet_template', '品質: 工程一体チェックシート（テンプレート管理）'),
        ('quality.integrated_checksheet_operation', '品質: 工程一体チェックシート（チェック実施）'),
        ('quality.integrated_checksheet_review', '品質: 工程一体チェックシート（確認）'),
        ('ocr', 'OCR・文書読取'),
        ('ai.chat', 'AIフル画面とドロワー'),
        ('ai.analysis', 'AI分析'),
        ('notifications', '通知'),
        ('notifications.create', '通知: 通知作成'),
        ('engineering_change', '設変'),
        ('outsource', 'FB外作管理'),
        ('outsource.first_article', 'FB外作: お久しぶり製品通知設定'),
        ('masters', 'マスタ'),
        ('masters.product', 'マスタ: 品番マスタ'),
        ('masters.product_group', 'マスタ: 製品グループ'),
        ('masters.container_capacity', 'マスタ: 容器マスタ'),
        ('masters.equipment', 'マスタ: 設備マスタ'),
        ('masters.bom', 'マスタ: 構成マスタ'),
        ('masters.routing', 'マスタ: ルーティングマスタ'),
        ('masters.customer', 'マスタ: 得意先マスタ'),
        ('masters.supplier', 'マスタ: 仕入先マスタ'),
        ('masters.process', 'マスタ: 工程マスタ'),
        ('masters.line', 'マスタ: ラインマスタ'),
        ('masters.calendar', 'マスタ: カレンダマスタ'),
        ('masters.work_pattern', 'マスタ: 勤務パターン'),
        ('masters.contact', 'マスタ: 連絡先マスタ'),
        ('masters.kubota_sakai_truck', 'マスタ: クボタ堺便マスタ'),
        ('masters.sourcing_bulk_change', 'マスタ: 加工先一括変更'),
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
        ('settings.approval_routes', '設定: 承認設定'),
        ('settings.material_order_email_config', '設定: 材料注文書メール設定'),
        ('settings.stocktake_init', '設定: 棚卸初期化'),
        ('settings.orphan_backlog_maintenance', '設定: 孤立ライン実績メンテナンス'),
        ('settings.lock_date', '設定: 締め日管理'),
        ('settings.kubota_import', '設定: クボタ堺取り込み通知設定'),
        ('settings.kubota_sakai_config', '設定: クボタ堺便計画設定'),
        ('settings.android_app', '設定: Androidアプリ配布'),
        ('settings.shipping_progress_horizon', '設定: 出荷進度再計算日数'),
        ('settings.ai', '設定: AI設定'),
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


class UserFavorite(models.Model):
    """ユーザーごとのお気に入り保存設定"""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='favorites',
    )
    screen_key = models.CharField(max_length=100, verbose_name='画面キー')
    name = models.CharField(max_length=100, verbose_name='お気に入り名')
    payload = models.JSONField(default=dict, verbose_name='保存内容')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        db_table = 'accounts_user_favorite'
        verbose_name = 'ユーザーお気に入り'
        verbose_name_plural = 'ユーザーお気に入り'
        unique_together = [['user', 'screen_key', 'name']]
        ordering = ['screen_key', 'name', 'id']


class ApprovalRouteConfig(models.Model):
    """承認項目ごとの役割ベース承認ルート設定"""

    ROLE_CHOICES = UserProfile.ROLE_CHOICES

    item_key = models.CharField(max_length=80, unique=True, verbose_name='承認項目キー')
    item_name = models.CharField(max_length=100, verbose_name='承認項目名')
    creator_role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='leader', verbose_name='作成者')
    creator_department = models.ForeignKey(
        Department, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='approval_route_creator', verbose_name='作成者部署',
    )
    creator_task_enabled = models.BooleanField(default=True, verbose_name='作成者タスク作成')
    creator_app_notification_enabled = models.BooleanField(default=True, verbose_name='作成者アプリ通知')
    creator_email_notification_enabled = models.BooleanField(default=False, verbose_name='作成者メール通知')
    creator_allowed_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='approval_route_creator_allowed',
        verbose_name='作成者限定ユーザー',
    )
    creator_authorized_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='approval_route_creator_authorized',
        verbose_name='作成可能ユーザー',
    )
    creator_proxy_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='approval_route_creator_proxy',
        verbose_name='作成者代理ユーザー',
    )
    reviewer1_role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='supervisor', verbose_name='確認者1')
    reviewer1_department = models.ForeignKey(
        Department, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='approval_route_reviewer1', verbose_name='確認者1部署',
    )
    reviewer1_task_enabled = models.BooleanField(default=True, verbose_name='確認者1タスク作成')
    reviewer1_app_notification_enabled = models.BooleanField(default=True, verbose_name='確認者1アプリ通知')
    reviewer1_email_notification_enabled = models.BooleanField(default=False, verbose_name='確認者1メール通知')
    reviewer1_allowed_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='approval_route_reviewer1_allowed',
        verbose_name='確認者1限定ユーザー',
    )
    reviewer1_proxy_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='approval_route_reviewer1_proxy',
        verbose_name='確認者1代理ユーザー',
    )
    reviewer2_role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='chief', verbose_name='確認者2')
    reviewer2_department = models.ForeignKey(
        Department, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='approval_route_reviewer2', verbose_name='確認者2部署',
    )
    reviewer2_enabled = models.BooleanField(default=True, verbose_name='確認者2使用')
    reviewer2_task_enabled = models.BooleanField(default=True, verbose_name='確認者2タスク作成')
    reviewer2_app_notification_enabled = models.BooleanField(default=True, verbose_name='確認者2アプリ通知')
    reviewer2_email_notification_enabled = models.BooleanField(default=False, verbose_name='確認者2メール通知')
    reviewer2_allowed_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='approval_route_reviewer2_allowed',
        verbose_name='確認者2限定ユーザー',
    )
    reviewer2_proxy_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='approval_route_reviewer2_proxy',
        verbose_name='確認者2代理ユーザー',
    )
    approver_role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='manager', verbose_name='承認者')
    approver_department = models.ForeignKey(
        Department, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='approval_route_approver', verbose_name='承認者部署',
    )
    approver_task_enabled = models.BooleanField(default=True, verbose_name='承認者タスク作成')
    approver_app_notification_enabled = models.BooleanField(default=True, verbose_name='承認者アプリ通知')
    approver_email_notification_enabled = models.BooleanField(default=False, verbose_name='承認者メール通知')
    approver_allowed_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='approval_route_approver_allowed',
        verbose_name='承認者限定ユーザー',
    )
    approver_proxy_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='approval_route_approver_proxy',
        verbose_name='承認者代理ユーザー',
    )
    approved_result_app_notification_enabled = models.BooleanField(default=True, verbose_name='承認結果アプリ通知')
    approved_result_email_notification_enabled = models.BooleanField(default=False, verbose_name='承認結果メール通知')
    rejected_result_app_notification_enabled = models.BooleanField(default=True, verbose_name='却下結果アプリ通知')
    rejected_result_email_notification_enabled = models.BooleanField(default=False, verbose_name='却下結果メール通知')
    is_active = models.BooleanField(default=True, verbose_name='有効')
    note = models.CharField(max_length=200, blank=True, default='', verbose_name='備考')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        db_table = 'accounts_approval_route_config'
        verbose_name = '承認ルート設定'
        verbose_name_plural = '承認ルート設定'
        ordering = ['item_key', 'id']

    def __str__(self):
        return f'{self.item_key}: {self.item_name}'


class ApprovalRequest(models.Model):
    """承認申請インスタンス"""

    STATUS_CHOICES = [
        ('created', '作成済み'),
        ('reviewing', '確認中'),
        ('approved', '承認済み'),
        ('rejected', '却下'),
        ('sent', '送信済み'),
    ]
    STAGE_CHOICES = [
        ('creator', '作成者'),
        ('reviewer1', '確認①'),
        ('reviewer2', '確認②'),
        ('approver', '承認者'),
        ('completed', '完了'),
    ]

    route_config = models.ForeignKey(
        ApprovalRouteConfig,
        on_delete=models.PROTECT,
        related_name='requests',
        verbose_name='承認ルート設定',
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='created', verbose_name='ステータス')
    current_stage = models.CharField(max_length=20, choices=STAGE_CHOICES, default='creator', verbose_name='現在の段階')
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='approval_requests_created',
        verbose_name='作成者',
    )
    context = models.JSONField(default=dict, verbose_name='申請コンテキスト')
    pdf_file = models.FileField(upload_to='approval/', blank=True, default='', verbose_name='PDFファイル')
    reject_reason = models.TextField(blank=True, default='', verbose_name='却下理由')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        db_table = 'accounts_approval_request'
        verbose_name = '承認申請'
        verbose_name_plural = '承認申請'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.route_config.item_key} #{self.id} ({self.get_status_display()})'


class ApprovalStep(models.Model):
    """承認フローの各段階の実行記録"""

    ACTION_CHOICES = [
        ('confirmed', '確認済み'),
        ('approved', '承認'),
        ('rejected', '却下'),
    ]

    request = models.ForeignKey(
        ApprovalRequest,
        on_delete=models.CASCADE,
        related_name='steps',
        verbose_name='承認申請',
    )
    stage = models.CharField(max_length=20, choices=ApprovalRequest.STAGE_CHOICES, verbose_name='段階')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='approval_steps',
        verbose_name='実行者',
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES, verbose_name='アクション')
    comment = models.TextField(blank=True, default='', verbose_name='コメント')
    acted_at = models.DateTimeField(auto_now_add=True, verbose_name='実行日時')

    class Meta:
        db_table = 'accounts_approval_step'
        verbose_name = '承認ステップ'
        verbose_name_plural = '承認ステップ'
        ordering = ['acted_at']

    def __str__(self):
        return f'{self.request_id} / {self.get_stage_display()} / {self.get_action_display()}'


class ApprovalTask(models.Model):
    """承認フロー用タスク"""

    TASK_TYPE_CHOICES = [
        ('CREATOR_CREATE', '作成'),
        ('REVIEWER1_REVIEW', '確認①'),
        ('REVIEWER2_REVIEW', '確認②'),
        ('APPROVER_APPROVE', '承認'),
        ('CREATOR_FIX', '差戻し修正'),
    ]
    STATUS_CHOICES = [
        ('PENDING', '未処理'),
        ('DONE', '完了'),
        ('SKIPPED', 'スキップ'),
    ]

    request = models.ForeignKey(
        ApprovalRequest,
        on_delete=models.CASCADE,
        related_name='tasks',
        verbose_name='承認申請',
    )
    task_type = models.CharField(max_length=30, choices=TASK_TYPE_CHOICES, verbose_name='タスク種別')
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='approval_tasks',
        verbose_name='担当者',
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING', verbose_name='ステータス')
    due_date = models.DateField(null=True, blank=True, verbose_name='期限')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    done_at = models.DateTimeField(null=True, blank=True, verbose_name='完了日時')

    class Meta:
        db_table = 'accounts_approval_task'
        verbose_name = '承認タスク'
        verbose_name_plural = '承認タスク'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.request_id} / {self.get_task_type_display()} / {self.get_status_display()}'
