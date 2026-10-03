from django.conf import settings
from django.db import models

from ai.config.models import AIAnalysisExecutionPolicy, AIDataPolicy, AIKnowledgeDocument, AIKnowledgeSource, AIProviderConfig, AIToolPolicy


class AISearchConfig(models.Model):
    """AIチャットのDB検索対象設定"""
    model_path = models.CharField(max_length=100, verbose_name='モデルパス')
    label = models.CharField(max_length=50, verbose_name='表示ラベル')
    search_fields = models.JSONField(verbose_name='検索フィールド')
    display_fields = models.JSONField(verbose_name='表示フィールド')
    display_template = models.CharField(max_length=300, verbose_name='表示テンプレート')
    filter_json = models.JSONField(default=dict, blank=True, verbose_name='フィルタ条件')
    is_active = models.BooleanField(default=True, verbose_name='有効')
    display_order = models.IntegerField(default=0, verbose_name='表示順')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ai_search_config'
        ordering = ['display_order', 'label']
        verbose_name = 'AI検索設定'
        verbose_name_plural = 'AI検索設定'

    def __str__(self):
        return f'{self.label}（{self.model_path}）'


class AIConversation(models.Model):
    """社内AIチャットの会話履歴。利用者本人だけが一覧・再開・削除できる。"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='ai_conversations', verbose_name='利用者',
    )
    screen_context = models.CharField(max_length=40, blank=True, default='', verbose_name='起点画面')
    provider = models.CharField(max_length=30, blank=True, default='', verbose_name='最後に使用したプロバイダ')
    title = models.CharField(max_length=100, blank=True, default='', verbose_name='会話タイトル')
    messages = models.JSONField(default=list, verbose_name='会話内容')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ai_conversation'
        ordering = ['-updated_at']
        verbose_name = '社内AI会話履歴'
        verbose_name_plural = '社内AI会話履歴'

    def __str__(self):
        return self.title or f'会話{self.pk}'


class AIAnalysisRun(models.Model):
    """分析の実行履歴(AI分析基盤仕様書§5.5)。成功・失敗・中止・期限切れ・状態不明のすべてを1行ずつ残す。

    コード本文・結果の中身・取得した明細行・個人情報・AIの応答本文は保存しない(ハッシュと件数と理由だけ)。
    保存期間は未確定のため、削除しない。実行者は、ユーザーが削除されたらNULLになる(表示は「削除済みユーザー」)。
    """
    STATUS_CHOICES = [
        ('running', '実行中'), ('success', '成功'), ('failed', '失敗'), ('cancelled', '中止'),
        ('expired', '期限切れ'), ('unknown', '生存確認失敗・状態不明'),
    ]

    plan_id = models.CharField(max_length=64, verbose_name='分析案ID')
    template_id = models.PositiveBigIntegerField(null=True, blank=True, verbose_name='テンプレートID')
    template_version = models.PositiveIntegerField(null=True, blank=True, verbose_name='テンプレート版')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name='ai_analysis_runs', verbose_name='実行者',
    )
    views = models.JSONField(default=list, verbose_name='利用ビュー・取得列')
    date_from = models.DateField(verbose_name='期間開始')
    date_to = models.DateField(verbose_name='期間終了')
    conditions = models.TextField(blank=True, default='', verbose_name='条件')
    method_approved_at = models.DateTimeField(null=True, blank=True, verbose_name='分析案の承認日時')
    data_approved_at = models.DateTimeField(null=True, blank=True, verbose_name='データ範囲の承認日時')
    # 件数は、承認・COUNT・取得・送信・投入を区別する(ビュー名→件数)
    approved_counts = models.JSONField(null=True, blank=True, verbose_name='承認時の件数')
    snapshot_counts = models.JSONField(null=True, blank=True, verbose_name='実行時のスナップショットのCOUNT')
    fetched_rows = models.JSONField(null=True, blank=True, verbose_name='1回目の取得行数')
    sent_rows = models.JSONField(null=True, blank=True, verbose_name='2回目の送信行数')
    loaded_rows = models.JSONField(null=True, blank=True, verbose_name='コンテナへの投入行数')
    unique_key_check = models.JSONField(null=True, blank=True, verbose_name='一意キー重複の確認結果')
    sql_sha256 = models.CharField(max_length=64, null=True, blank=True, verbose_name='SQLのハッシュ(別のSQLがない実行はNULL)')
    python_sha256 = models.CharField(max_length=64, null=True, blank=True, verbose_name='Pythonのハッシュ(コードを作る前に終わった実行はNULL)')
    settings_snapshot = models.JSONField(default=dict, verbose_name='実行時の設定値')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='running', verbose_name='状態')
    reason = models.CharField(max_length=80, blank=True, default='', verbose_name='失敗理由コード')
    detail = models.CharField(max_length=300, blank=True, default='', verbose_name='理由の説明(データを含まない)')
    cleanup = models.JSONField(default=dict, verbose_name='後始末の結果(closed / pending / failed)')
    worker_id = models.CharField(max_length=120, verbose_name='実行を担当するプロセス')
    heartbeat_at = models.DateTimeField(verbose_name='生存確認の最終更新')
    started_at = models.DateTimeField(verbose_name='開始')
    fetched_at = models.DateTimeField(null=True, blank=True, verbose_name='取得完了')
    sent_at = models.DateTimeField(null=True, blank=True, verbose_name='送信完了')
    loaded_at = models.DateTimeField(null=True, blank=True, verbose_name='投入完了(コンテナ内の件数・一意キーの照合を含む)')
    finished_at = models.DateTimeField(null=True, blank=True, verbose_name='終了')
    fetch_seconds = models.FloatField(null=True, blank=True, verbose_name='取得の所要秒')
    transfer_seconds = models.FloatField(null=True, blank=True, verbose_name='送信の所要秒')
    launcher_seconds = models.FloatField(null=True, blank=True, verbose_name='launcherの実行・応答待ちの秒')
    container_load_seconds = models.FloatField(null=True, blank=True, verbose_name='コンテナ内の投入の秒')
    python_seconds = models.FloatField(null=True, blank=True, verbose_name='Python実行の秒')

    class Meta:
        db_table = 'ai_analysis_run'
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['user', '-started_at'], name='ai_run_user_started'),
            models.Index(fields=['status', 'heartbeat_at'], name='ai_run_status_heartbeat'),
        ]
        verbose_name = 'AI分析実行履歴'
        verbose_name_plural = 'AI分析実行履歴'

    def __str__(self):
        return f'実行{self.pk}（{self.get_status_display()}）'
