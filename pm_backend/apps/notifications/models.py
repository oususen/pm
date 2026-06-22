from django.db import models
from django.conf import settings
from accounts.models import Department


class Notification(models.Model):
    """通知マスタ"""
    title = models.CharField(max_length=200, verbose_name='タイトル')
    category = models.CharField(max_length=50, verbose_name='カテゴリ')
    domain = models.CharField(max_length=50, verbose_name='種別')
    target_departments = models.ManyToManyField(
        Department,
        blank=True,
        related_name='notifications',
        verbose_name='対象部署'
    )
    target_positions = models.JSONField(default=list, blank=True, verbose_name='対象役職')
    target_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='targeted_notifications',
        verbose_name='対象ユーザー'
    )
    valid_from = models.DateField(null=True, blank=True, verbose_name='有効開始日')
    valid_to = models.DateField(null=True, blank=True, verbose_name='有効終了日')
    display_order = models.IntegerField(default=0, verbose_name='表示順')
    description = models.TextField(blank=True, verbose_name='説明')
    operator_name = models.CharField(max_length=100, blank=True, verbose_name='入力者')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        db_table = 'notifications'
        ordering = ['display_order', 'id']
        verbose_name = '通知'
        verbose_name_plural = '通知'


class NotificationRead(models.Model):
    """通知既読状態（ユーザーごと）"""
    notification = models.ForeignKey(
        Notification,
        on_delete=models.CASCADE,
        related_name='reads',
        verbose_name='通知'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notification_reads',
        verbose_name='ユーザー'
    )
    read_at = models.DateTimeField(auto_now_add=True, verbose_name='既読日時')

    class Meta:
        db_table = 'notification_reads'
        unique_together = ['notification', 'user']
        verbose_name = '通知既読'
        verbose_name_plural = '通知既読'


class CallSession(models.Model):
    """社内通話セッション"""

    CALL_TYPE_CHOICES = [
        ('voice', '音声'),
        ('video', 'ビデオ'),
    ]

    STATUS_CHOICES = [
        ('ringing', '呼出中'),
        ('accepted', '通話中'),
        ('declined', '辞退'),
        ('ended', '終了'),
        ('missed', '不在'),
        ('canceled', 'キャンセル'),
    ]

    caller = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='outgoing_call_sessions',
        verbose_name='発信者'
    )
    callee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='incoming_call_sessions',
        verbose_name='着信者'
    )
    call_type = models.CharField(max_length=10, choices=CALL_TYPE_CHOICES, verbose_name='通話種別')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='ringing', verbose_name='状態')
    initiated_at = models.DateTimeField(auto_now_add=True, verbose_name='発信日時')
    accepted_at = models.DateTimeField(null=True, blank=True, verbose_name='応答日時')
    ended_at = models.DateTimeField(null=True, blank=True, verbose_name='終了日時')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        db_table = 'call_sessions'
        ordering = ['-initiated_at', '-id']
        verbose_name = '通話セッション'
        verbose_name_plural = '通話セッション'


class CallSignal(models.Model):
    """WebRTC用シグナリングデータ"""

    SIGNAL_TYPE_CHOICES = [
        ('offer', 'Offer'),
        ('answer', 'Answer'),
        ('ice_candidate', 'ICE Candidate'),
        ('hangup', 'Hangup'),
    ]

    session = models.ForeignKey(
        CallSession,
        on_delete=models.CASCADE,
        related_name='signals',
        verbose_name='通話セッション'
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_call_signals',
        verbose_name='送信者'
    )
    target_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='received_call_signals',
        verbose_name='送信先ユーザー'
    )
    signal_type = models.CharField(max_length=20, choices=SIGNAL_TYPE_CHOICES, verbose_name='シグナル種別')
    payload = models.JSONField(default=dict, blank=True, verbose_name='シグナル内容')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')

    class Meta:
        db_table = 'call_signals'
        ordering = ['id']
        verbose_name = '通話シグナル'
        verbose_name_plural = '通話シグナル'


class CallRecording(models.Model):
    """社内通話録音"""

    session = models.OneToOneField(
        CallSession,
        on_delete=models.CASCADE,
        related_name='recording',
        verbose_name='通話セッション'
    )
    file = models.FileField(upload_to='call_recordings/', verbose_name='録音ファイル')
    mime_type = models.CharField(max_length=100, verbose_name='MIMEタイプ')
    file_size = models.BigIntegerField(verbose_name='ファイルサイズ')
    duration_seconds = models.FloatField(null=True, blank=True, verbose_name='録音時間（秒）')
    recording_started_at = models.DateTimeField(null=True, blank=True, verbose_name='録音開始日時')
    recording_ended_at = models.DateTimeField(null=True, blank=True, verbose_name='録音終了日時')
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='call_recordings',
        verbose_name='録音登録者'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        db_table = 'call_recordings'
        ordering = ['-created_at', '-id']
        verbose_name = '通話録音'
        verbose_name_plural = '通話録音'


class PushSubscription(models.Model):
    """Web Push購読情報"""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='push_subscriptions',
        verbose_name='ユーザー'
    )
    endpoint = models.CharField(max_length=500, unique=True, verbose_name='エンドポイント')
    p256dh_key = models.TextField(verbose_name='公開鍵')
    auth_key = models.TextField(verbose_name='認証鍵')
    user_agent = models.CharField(max_length=255, blank=True, verbose_name='ユーザーエージェント')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        db_table = 'push_subscriptions'
        ordering = ['-updated_at', '-id']
        verbose_name = 'Push購読'
        verbose_name_plural = 'Push購読'


class NativePushToken(models.Model):
    """ネイティブ Push トークン"""

    PLATFORM_ANDROID = 'android'
    PLATFORM_IOS = 'ios'

    PLATFORM_CHOICES = [
        (PLATFORM_ANDROID, 'Android'),
        (PLATFORM_IOS, 'iOS'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='native_push_tokens',
        verbose_name='ユーザー'
    )
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES, verbose_name='プラットフォーム')
    token = models.CharField(max_length=512, unique=True, verbose_name='トークン')
    device_id = models.CharField(max_length=255, blank=True, verbose_name='端末ID')
    device_name = models.CharField(max_length=255, blank=True, verbose_name='端末名')
    app_version = models.CharField(max_length=100, blank=True, verbose_name='アプリバージョン')
    is_active = models.BooleanField(default=True, verbose_name='有効')
    last_seen_at = models.DateTimeField(auto_now=True, verbose_name='最終確認日時')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        db_table = 'native_push_tokens'
        ordering = ['-updated_at', '-id']
        verbose_name = 'ネイティブ Push トークン'
        verbose_name_plural = 'ネイティブ Push トークン'
