from io import BytesIO
import re
from datetime import datetime

from django.http import HttpResponse
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db.models import Q, CharField, F, Value
from django.db.utils import OperationalError, ProgrammingError
from django.db.models.functions import Coalesce, NullIf
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
import django_filters

from accounts.role_utils import (
    build_chief_role_q,
    build_leader_role_q,
    build_supervisor_role_q,
    get_profile,
    get_profile_role,
)
from .access import can_manage_application
from .models import OvertimeApplication, OvertimeApprovalLog
from production.models_process_work_session import ProcessWorkSession
from production.models_brake_line_record import BrakeLineRecord
from .serializers import OvertimeApplicationSerializer, build_media_absolute_url

User = get_user_model()

# ロールの承認順序
APPROVAL_LEVELS = ['leader', 'supervisor', 'chief', 'manager']

# ステータスと承認済みロールの対応
STATUS_AFTER_APPROVE = {
    'leader': 'approved_leader',
    'supervisor': 'approved_supervisor',
    'chief': 'approved_chief',
    'manager': 'approved_manager',
}


def _build_operator_name_candidates(user):
    """申請者に対応する作業者名候補を返す。"""
    if not user:
        return []
    full_name = f"{user.last_name} {user.first_name}".strip()
    reverse_full_name = f"{user.first_name} {user.last_name}".strip()
    candidates = [
        full_name,
        reverse_full_name,
        (user.username or '').strip(),
    ]
    # 空文字と重複を除外
    return [name for i, name in enumerate(candidates) if name and name not in candidates[:i]]


def _normalize_operator_text(value):
    """作業者名の表記ゆれを吸収して比較するための正規化。"""
    text = str(value or '').strip().lower()
    if not text:
        return ''
    # 空白・括弧類を除去（半角/全角）
    text = re.sub(r'[\s\u3000\(\)（）]', '', text)
    return text


def _normalize_ascii_token(value):
    """
    文字化けしても残りやすい英数字トークン（例: PROMWIJITNATTAWAT）を抽出する。
    """
    text = str(value or '').lower()
    return re.sub(r'[^a-z0-9]+', '', text)


def _build_operator_name_variants(user):
    """作業者名の比較候補（表記ゆれ含む）を返す。"""
    if not user:
        return []
    last_name = str(user.last_name or '').strip()
    first_name = str(user.first_name or '').strip()
    username = str(user.username or '').strip()
    variants = [
        f'{last_name} {first_name}'.strip(),
        f'{first_name} {last_name}'.strip(),
        f'{last_name}({first_name})'.strip('()'),
        f'{last_name}（{first_name}）'.strip('（）'),
        f'{last_name}{first_name}'.strip(),
        username,
    ]
    unique = []
    seen = set()
    for raw in variants:
        key = _normalize_operator_text(raw)
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(raw)
    return unique


def _has_open_process_session(user):
    """
    ProcessWorkSession の未終了判定。
    旧データ向けに operator_name の表記ゆれ比較も行う。
    """
    if not user:
        return False
    candidate_names = _build_operator_name_variants(user)
    if not candidate_names:
        return False

    # まずは既存の完全一致で高速判定
    if ProcessWorkSession.objects.filter(
        session_type='WORK',
        status='OPEN',
        operator_name__in=candidate_names,
    ).exists():
        return True

    # 表記ゆれ吸収判定（括弧・空白差分）
    candidate_keys = {_normalize_operator_text(name) for name in candidate_names if name}
    candidate_ascii_keys = {
        _normalize_ascii_token(name)
        for name in candidate_names
        if _normalize_ascii_token(name)
    }
    open_rows = ProcessWorkSession.objects.filter(
        session_type='WORK',
        status='OPEN',
    ).values('operator_name', 'start_record__operator_name', 'end_record__operator_name')
    for row in open_rows:
        for operator_name in (
            row.get('operator_name'),
            row.get('start_record__operator_name'),
            row.get('end_record__operator_name'),
        ):
            normalized = _normalize_operator_text(operator_name)
            if normalized in candidate_keys:
                return True
            ascii_key = _normalize_ascii_token(operator_name)
            if ascii_key and len(ascii_key) >= 6 and ascii_key in candidate_ascii_keys:
                return True
    return False


def _has_open_brake_or_spot_action(user):
    """
    ブレーキ/ナット（スポット）アクション実績の未終了を判定する。
    同一キー（工程・品目・設備）の最新アクションが START/RESUME かつ
    その最新アクションを行ったのが対象ユーザー本人の場合のみ未終了扱い。
    別ユーザーが同キーで START/RESUME していても、申請者には影響しない。
    戻り値: (bool, list[dict]) — 未終了有無と、未終了アイテムの詳細リスト
    """
    _DISPLAY_FIELDS = [
        'id', 'plan_date',
        'process_id', 'process__process_name',
        'product_id', 'product_code', 'product__product_name',
        'equipment_id', 'equipment__equipment_name',
        'operator_action', 'operator_user_id',
    ]

    # Step 1: 対象ユーザーが関わったキー（工程・品目・設備）を特定
    user_item_keys = set()
    user_rows_by_key = {}

    if user and user.id:
        try:
            user_action_rows = list(
                BrakeLineRecord.objects
                .filter(operator_user_id=user.id, operator_action__in=['START', 'RESUME'])
                .values(*_DISPLAY_FIELDS)
                .order_by('-recorded_at', '-id')
            )
        except (OperationalError, ProgrammingError):
            user_action_rows = []

        for row in user_action_rows:
            product_key = row.get('product_id') or (row.get('product_code') or '').strip()
            if not product_key:
                continue
            item_key = (row.get('process_id'), product_key, row.get('equipment_id'))
            if item_key not in user_item_keys:
                user_item_keys.add(item_key)
                user_rows_by_key[item_key] = row

    # フォールバック: 旧データ（operator_user 未保存）だけ名前で補完
    if not user_item_keys:
        operator_name_candidates = _build_operator_name_variants(user)
        if not operator_name_candidates:
            return False, []
        candidate_keys = {_normalize_operator_text(name) for name in operator_name_candidates if name}
        candidate_ascii_keys = {
            _normalize_ascii_token(name)
            for name in operator_name_candidates
            if _normalize_ascii_token(name)
        }
        try:
            legacy_rows = (
                BrakeLineRecord.objects
                .filter(operator_user__isnull=True, operator_action__in=['START', 'RESUME'])
                .values(*_DISPLAY_FIELDS, 'operator')
                .order_by('-recorded_at', '-id')
            )
        except (OperationalError, ProgrammingError):
            legacy_rows = (
                BrakeLineRecord.objects
                .filter(operator_action__in=['START', 'RESUME'])
                .values(*_DISPLAY_FIELDS, 'operator')
                .order_by('-recorded_at', '-id')
            )
        for row in legacy_rows:
            normalized = _normalize_operator_text(row.get('operator'))
            ascii_key = _normalize_ascii_token(row.get('operator'))
            matched = (normalized in candidate_keys) or (
                ascii_key and len(ascii_key) >= 6 and ascii_key in candidate_ascii_keys
            )
            if not matched:
                continue
            product_key = row.get('product_id') or (row.get('product_code') or '').strip()
            if not product_key:
                continue
            item_key = (row.get('process_id'), product_key, row.get('equipment_id'))
            if item_key not in user_item_keys:
                user_item_keys.add(item_key)
                user_rows_by_key[item_key] = row

    if not user_item_keys:
        return False, []

    # Step 2: 各キーの全ユーザー含む最新アクションを確認
    from django.db.models import Q
    key_filter = Q()
    for (proc_id, prod_key, eq_id) in user_item_keys:
        q = Q(process_id=proc_id, equipment_id=eq_id)
        if isinstance(prod_key, int):
            q &= Q(product_id=prod_key)
        else:
            q &= Q(product_code=prod_key)
        key_filter |= q

    all_rows = (
        BrakeLineRecord.objects
        .filter(key_filter)
        .values(*_DISPLAY_FIELDS)
        .order_by('-recorded_at', '-id')
    )

    global_latest_by_key = {}
    for row in all_rows:
        product_key = row.get('product_id') or (row.get('product_code') or '').strip()
        if not product_key:
            continue
        item_key = (row.get('process_id'), product_key, row.get('equipment_id'))
        if item_key not in global_latest_by_key:
            global_latest_by_key[item_key] = row

    open_items = []
    for item_key in user_item_keys:
        latest = global_latest_by_key.get(item_key)
        if not latest:
            continue
        action = str(latest.get('operator_action') or '').upper()
        if action in {'START', 'RESUME'} and latest.get('operator_user_id') == user.id:
            user_row = user_rows_by_key[item_key]
            plan_date = user_row.get('plan_date')
            open_items.append({
                'id': user_row.get('id'),
                'plan_date': plan_date.isoformat() if hasattr(plan_date, 'isoformat') else str(plan_date or ''),
                'process_name': user_row.get('process__process_name') or '',
                'product_code': user_row.get('product_code') or '',
                'product_name': user_row.get('product__product_name') or '',
                'equipment_name': user_row.get('equipment__equipment_name') or '',
                'action': action,
            })

    return bool(open_items), open_items


def find_approvers_for_role(applicant, role):
    """申請者の組織情報から指定ロールの承認者を検索する"""
    profile = get_profile(applicant)
    if not profile:
        return User.objects.none()

    if role == 'leader':
        if not profile.unit:
            return User.objects.none()
        return User.objects.filter(build_leader_role_q(profile.unit_id)).distinct()
    elif role == 'supervisor':
        if not profile.team:
            return User.objects.none()
        return User.objects.filter(build_supervisor_role_q(profile.team_id)).distinct()
    elif role == 'chief':
        if not profile.group:
            return User.objects.none()
        return User.objects.filter(build_chief_role_q(profile.group_id)).distinct()
    elif role == 'manager':
        if not profile.division:
            return User.objects.none()
        return User.objects.filter(
            profile__role='manager',
            profile__division=profile.division,
        )
    return User.objects.none()


def create_pending_logs(application, role):
    """指定ロールの承認者に対してpendingログを作成。返値: 作成件数"""
    approvers = find_approvers_for_role(application.applicant, role)
    # 申請者自身は除外
    approvers = approvers.exclude(id=application.applicant_id)
    count = 0
    for approver in approvers:
        OvertimeApprovalLog.objects.create(
            application=application,
            approver=approver,
            role=role,
            status='pending',
        )
        count += 1
    return count


def create_approval_notification(application, target_users, message):
    """既存Notificationモデルを使って承認依頼通知を作成"""
    try:
        from notifications.models import Notification
        import datetime
        applicant = application.applicant
        name = f"{applicant.last_name} {applicant.first_name}".strip() or applicant.username
        if application.start_time and application.end_time:
            time_str = f"{application.start_time.strftime('%H:%M')}〜{application.end_time.strftime('%H:%M')}"
            hours_str = f"時間数: {application.hours}H（深夜: {application.midnight_hours}H）\n"
        else:
            time_str = application.get_application_type_display()
            hours_str = ""
        end_date_str = f"〜{application.end_date}" if application.end_date else ""
        notif = Notification.objects.create(
            title=message,
            category='overtime',
            domain='overtime',
            valid_from=datetime.date.today(),
            valid_to=application.work_date + datetime.timedelta(days=14),
            description=(
                f"申請者: {name}\n"
                f"実施日: {application.work_date}{end_date_str}\n"
                f"種別: {time_str}\n"
                f"{hours_str}"
                f"理由: {application.reason}"
            ),
            operator_name=name,
        )
        notif.target_users.set(target_users)
    except Exception:
        pass  # 通知失敗は無視


def advance_to_next_level(application):
    """
    現在のステータスから次の承認レベルへ進める。
    リーダーと班長は並列: 提出時に両方にpendingログを同時作成。
    班長が承認すれば係長へ進む（リーダー未承認でも可）。
    """
    applicant = application.applicant
    applicant_name = f"{applicant.last_name} {applicant.first_name}".strip() or applicant.username

    if application.status == 'submitted':
        # リーダーと班長に同時にpendingログを作成（並列フロー）
        leader_count = create_pending_logs(application, 'leader')
        supervisor_count = create_pending_logs(application, 'supervisor')

        if leader_count > 0 or supervisor_count > 0:
            # 承認依頼通知は送らない（承認待ち画面で確認する運用）
            return

        # リーダーも班長もいない場合は係長以降へ
        start_idx = 2  # chief から
    elif application.status == 'approved_leader':
        # リーダーのみ承認済み: 班長はすでにpendingなので何もしない
        return
    elif application.status == 'approved_supervisor':
        start_idx = 2  # chief から
    elif application.status == 'approved_chief':
        start_idx = 3  # manager から
    else:
        return

    # 係長・課長レベルへ進める
    for i in range(start_idx, len(APPROVAL_LEVELS)):
        role = APPROVAL_LEVELS[i]
        count = create_pending_logs(application, role)
        if count > 0:
            # 承認依頼通知は送らない（承認待ち画面で確認する運用）
            return

    # 全レベル完了 → 最終承認
    application.status = 'approved_manager'
    application.save(update_fields=['status', 'updated_at'])
    create_approval_notification(
        application,
        [applicant],
        f"【残業申請 承認完了】{application.work_date} の申請が承認されました",
    )


class OvertimeApplicationFilter(django_filters.FilterSet):
    work_date__gte = django_filters.DateFilter(field_name='work_date', lookup_expr='gte')
    work_date__lte = django_filters.DateFilter(field_name='work_date', lookup_expr='lte')
    status = django_filters.CharFilter(field_name='status')
    applicant = django_filters.NumberFilter(field_name='applicant')
    section_name = django_filters.CharFilter(field_name='applicant__profile__group__name')
    team_name = django_filters.CharFilter(field_name='team__name')
    group_name = django_filters.CharFilter(field_name='applicant__profile__unit__name')

    class Meta:
        model = OvertimeApplication
        fields = [
            'work_date__gte', 'work_date__lte', 'status', 'applicant',
            'section_name', 'team_name', 'group_name',
        ]


class OvertimeApplicationViewSet(viewsets.ModelViewSet):
    serializer_class = OvertimeApplicationSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    filter_backends = [DjangoFilterBackend]
    filterset_class = OvertimeApplicationFilter
    pagination_class = None
    ordering_fields = ['work_date', 'created_at', 'status']
    ordering = ['-work_date', '-created_at']

    def get_queryset(self):
        user = self.request.user
        profile = get_profile(user)
        role = get_profile_role(profile) or 'staff'

        # 管理職は全申請を閲覧可能、それ以外は自分の申請のみ
        qs = OvertimeApplication.objects.select_related(
            'applicant', 'created_by', 'team'
        ).prefetch_related('approval_logs__approver')

        own_q = Q(applicant=user) | Q(created_by=user)

        if role in ('manager', 'chief', 'supervisor'):
            filtered_qs = qs
        else:
            if profile:
                team_ids = set()
                unit_ids = set()
                if role in ('supervisor', 'chief', 'manager'):
                    if getattr(profile, 'team_id', None):
                        team_ids.add(profile.team_id)
                    team_ids.update(profile.supervisor_teams.values_list('id', flat=True))
                if role in ('leader', 'supervisor', 'chief', 'manager'):
                    if getattr(profile, 'unit_id', None):
                        unit_ids.add(profile.unit_id)
                    unit_ids.update(profile.leader_units.values_list('id', flat=True))
                if team_ids or unit_ids:
                    team_q = Q(applicant__profile__team_id__in=team_ids) if team_ids else Q()
                    unit_q = Q(applicant__profile__unit_id__in=unit_ids) if unit_ids else Q()
                    filtered_qs = qs.filter(own_q | team_q | unit_q)
                else:
                    filtered_qs = qs.filter(own_q)
            else:
                filtered_qs = qs.filter(own_q)

        # 一覧は申請者のユーザーID（社員コード）昇順を基本とする。
        return filtered_qs.annotate(
            applicant_sort_code=Coalesce(
                NullIf(F('applicant__profile__employee_code'), Value('')),
                F('applicant__username'),
                output_field=CharField(),
            )
        ).order_by('applicant_sort_code', 'work_date', 'created_at', 'id')

    def update(self, request, *args, **kwargs):
        app = self.get_object()
        if not can_manage_application(request.user, app):
            return Response({'detail': '権限がありません。'}, status=status.HTTP_403_FORBIDDEN)
        if app.status not in ('draft', 'submitted', 'rejected'):
            return Response(
                {'detail': '承認済み申請は編集できません。'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # 申請中だった場合は下書きに戻してpendingログをクリア
        if app.status == 'submitted':
            app.approval_logs.filter(status='pending').delete()
            app.status = 'draft'
            app.submitted_at = None
            app.save(update_fields=['status', 'submitted_at', 'updated_at'])
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        app = self.get_object()
        if not can_manage_application(request.user, app):
            return Response({'detail': '権限がありません。'}, status=status.HTTP_403_FORBIDDEN)
        if app.status not in ('draft', 'submitted', 'rejected'):
            return Response(
                {'detail': '承認済み申請は削除できません。'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # 申請中の場合はpendingログもクリアして削除
        if app.status == 'submitted':
            app.approval_logs.filter(status='pending').delete()
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=['post'], parser_classes=[MultiPartParser, FormParser])
    def upload_signature(self, request, pk=None):
        """サイン画像をアップロードする"""
        app = self.get_object()
        if not can_manage_application(request.user, app):
            return Response({'detail': '権限がありません。'}, status=status.HTTP_403_FORBIDDEN)
        sig = request.FILES.get('signature')
        if not sig:
            return Response({'detail': 'ファイルが見つかりません。'}, status=status.HTTP_400_BAD_REQUEST)
        if app.signature:
            app.signature.delete(save=False)
        app.signature = sig
        app.save(update_fields=['signature'])
        return Response({'signature': build_media_absolute_url(request, app.signature.url)})

    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        """申請を提出する"""
        app = self.get_object()
        if not can_manage_application(request.user, app):
            return Response({'detail': '権限がありません。'}, status=status.HTTP_403_FORBIDDEN)
        if app.status not in ('draft', 'rejected'):
            return Response(
                {'detail': '下書きまたは却下された申請のみ提出できます。'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        has_open_session = _has_open_process_session(app.applicant)
        if has_open_session:
            return Response(
                {
                    'detail_code': 'overtime.error.openProcessSession',
                    'detail': '加工実績に未終了のセッションがあります。セッションを終了してから申請してください。'
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        has_open_action, open_items = _has_open_brake_or_spot_action(app.applicant)
        if has_open_action:
            return Response(
                {
                    'detail_code': 'overtime.error.openBrakeSpotAction',
                    'detail': 'ブレーキ・ナット実績に未終了のアクションがあります。終了してから申請してください。',
                    'open_items': open_items,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 既存のpendingログをクリア（再申請の場合）
        app.approval_logs.filter(status='pending').delete()

        app.submitted_at = timezone.now()
        app.rejection_reason = ''

        # 記録のみ種別（午後半休・前日有給・連続有給）は承認フロー不要で自動承認
        if app.application_type not in OvertimeApplication.NEEDS_APPROVAL_TYPES:
            app.status = 'approved_manager'
            app.save(update_fields=['status', 'submitted_at', 'rejection_reason', 'updated_at'])
            applicant_name = (
                f"{app.applicant.last_name} {app.applicant.first_name}".strip() or app.applicant.username
            )
            create_approval_notification(
                app, [app.applicant],
                f"【{app.get_application_type_display()} 記録完了】{app.work_date}",
            )
        else:
            app.status = 'submitted'
            app.save(update_fields=['status', 'submitted_at', 'rejection_reason', 'updated_at'])
            # 最初の承認レベルへ
            advance_to_next_level(app)

        serializer = self.get_serializer(app)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """承認する"""
        app = self.get_object()
        user = request.user
        comment = request.data.get('comment', '')

        # 自分宛てのpending logを取得
        try:
            log = app.approval_logs.get(approver=user, status='pending')
        except OvertimeApprovalLog.DoesNotExist:
            return Response(
                {'detail': 'この申請の承認権限がありません。'},
                status=status.HTTP_403_FORBIDDEN,
            )

        # ログを承認済みに更新
        log.status = 'approved'
        log.comment = comment
        log.acted_at = timezone.now()
        log.save()

        # 同レベルの他のpendingログも承認済みに（同一レベル複数人の場合）
        app.approval_logs.filter(role=log.role, status='pending').update(
            status='approved', acted_at=timezone.now()
        )

        if log.role == 'leader':
            # リーダー承認: 班長はすでにpendingなので次レベルへは進めない
            # ステータスがまだ submitted の場合のみ approved_leader に更新
            if app.status == 'submitted':
                app.status = 'approved_leader'
                app.save(update_fields=['status', 'updated_at'])
        else:
            if log.role == 'supervisor':
                # 班長承認: 残っているリーダーpendingログを削除（不要になったため）
                app.approval_logs.filter(role='leader', status='pending').delete()
            # アプリケーションのステータスを更新
            app.status = STATUS_AFTER_APPROVE.get(log.role, app.status)
            app.save(update_fields=['status', 'updated_at'])
            # 次のレベルへ進む
            advance_to_next_level(app)

        serializer = self.get_serializer(app)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """却下する"""
        app = self.get_object()
        user = request.user
        reason = request.data.get('reason', '')
        comment = request.data.get('comment', '')

        try:
            log = app.approval_logs.get(approver=user, status='pending')
        except OvertimeApprovalLog.DoesNotExist:
            return Response(
                {'detail': 'この申請の承認権限がありません。'},
                status=status.HTTP_403_FORBIDDEN,
            )

        log.status = 'rejected'
        log.comment = comment
        log.acted_at = timezone.now()
        log.save()

        # 同レベルのpendingをクリア
        app.approval_logs.filter(role=log.role, status='pending').update(
            status='rejected', acted_at=timezone.now()
        )

        app.status = 'rejected'
        app.rejection_reason = reason or comment
        app.save(update_fields=['status', 'rejection_reason', 'updated_at'])

        # 申請者へ通知
        approver_name = (
            f"{user.last_name} {user.first_name}".strip() or user.username
        )
        create_approval_notification(
            app,
            [app.applicant],
            f"【残業申請 却下】{app.work_date} の申請が却下されました（{approver_name}）",
        )

        serializer = self.get_serializer(app)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def cancel_supervisor_approval(self, request, pk=None):
        """班長承認を取り消して一つ前の状態へ戻す"""
        app = self.get_object()
        user = request.user

        if app.status != 'approved_supervisor':
            return Response(
                {'detail': '班長承認済みの申請だけ取り消せます。'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        supervisor_logs = app.approval_logs.filter(role='supervisor')
        if not supervisor_logs.filter(approver=user, status='approved').exists():
            return Response(
                {'detail': 'あなたが承認した班長承認だけ取り消せます。'},
                status=status.HTTP_403_FORBIDDEN,
            )

        if app.approval_logs.filter(role__in=('chief', 'manager'), status='approved').exists():
            return Response(
                {'detail': '係長または部長が承認した後は班長承認を取り消せません。'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 後段の承認待ちを削除し、班長承認を承認待ちへ戻す
        app.approval_logs.filter(role__in=('chief', 'manager'), status='pending').delete()
        supervisor_logs.filter(status='approved').update(
            status='pending',
            comment='',
            acted_at=None,
        )

        has_approved_leader = app.approval_logs.filter(role='leader', status='approved').exists()
        if has_approved_leader:
            app.status = 'approved_leader'
        else:
            if not app.approval_logs.filter(role='leader', status='pending').exists():
                create_pending_logs(app, 'leader')
            app.status = 'submitted'
        app.updated_at = datetime.now()
        app.save(update_fields=['status', 'updated_at'])

        serializer = self.get_serializer(app)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def bulk_approve(self, request):
        """班長が複数申請を一括承認し、係長へ一括確認依頼する"""
        ids = request.data.get('ids', [])
        comment = request.data.get('comment', '')
        user = request.user

        if not ids:
            return Response({'detail': '申請IDが指定されていません。'}, status=status.HTTP_400_BAD_REQUEST)

        approved_apps = []
        for app_id in ids:
            try:
                app = OvertimeApplication.objects.select_related('applicant').get(id=app_id)
                log = app.approval_logs.get(approver=user, status='pending')
            except (OvertimeApplication.DoesNotExist, OvertimeApprovalLog.DoesNotExist):
                continue

            log.status = 'approved'
            log.comment = comment
            log.acted_at = timezone.now()
            log.save()

            app.approval_logs.filter(role=log.role, status='pending').update(
                status='approved', acted_at=timezone.now()
            )
            if log.role == 'supervisor':
                # 班長一括承認: 残っているリーダーpendingログを削除
                app.approval_logs.filter(role='leader', status='pending').delete()
            app.status = STATUS_AFTER_APPROVE.get(log.role, app.status)
            app.save(update_fields=['status', 'updated_at'])
            approved_apps.append(app)

        if not approved_apps:
            return Response({'detail': '処理できる申請がありませんでした。'}, status=status.HTTP_400_BAD_REQUEST)

        # 次の承認レベルへ進める（承認依頼通知は送らない: 承認待ち画面で確認）
        for app in approved_apps:
            if app.status == 'approved_supervisor':
                start_idx = 2
            elif app.status == 'approved_chief':
                start_idx = 3
            else:
                continue

            advanced = False
            for i in range(start_idx, len(APPROVAL_LEVELS)):
                role = APPROVAL_LEVELS[i]
                count = create_pending_logs(app, role)
                if count > 0:
                    advanced = True
                    break

            if not advanced:
                # 承認者なし → 最終承認（申請者への完了通知は残す）
                app.status = 'approved_manager'
                app.save(update_fields=['status', 'updated_at'])
                create_approval_notification(
                    app, [app.applicant],
                    f"【残業申請 承認完了】{app.work_date} の申請が承認されました",
                )

        return Response({'approved': len(approved_apps)})

    @action(detail=False, methods=['get'])
    def export_pdf(self, request):
        """フィルタ条件でPDFを出力する"""
        from .pdf_generator import generate_overtime_pdf

        ids_param = request.query_params.get('ids', '')
        if ids_param:
            try:
                id_list = [int(i) for i in ids_param.split(',') if i.strip()]
            except ValueError:
                id_list = []
            qs = self.get_queryset().filter(id__in=id_list).order_by('applicant_sort_code', 'work_date', 'created_at', 'id')
        else:
            qs = self.filter_queryset(self.get_queryset()).order_by('applicant_sort_code', 'work_date', 'created_at', 'id')

        filters = {
            'team_name': request.query_params.get('team_name', ''),
            'group_name': request.query_params.get('group_name', ''),
            'date_from': request.query_params.get('work_date__gte', ''),
            'date_to': request.query_params.get('work_date__lte', ''),
        }

        buf = generate_overtime_pdf(list(qs), filters)

        import urllib.parse
        team = filters['team_name'] or '全班'
        filename = f"残業申請書-{team}.pdf"
        encoded = urllib.parse.quote(filename)

        response = HttpResponse(buf.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f"attachment; filename*=UTF-8''{encoded}"
        return response

    @action(detail=False, methods=['get'])
    def pending_approvals(self, request):
        """自分が承認すべき申請一覧"""
        user = request.user
        apps = OvertimeApplication.objects.filter(
            approval_logs__approver=user,
            approval_logs__status='pending',
        ).select_related('applicant', 'created_by', 'team').prefetch_related(
            'approval_logs__approver'
        ).distinct().order_by('applicant__username', 'work_date', 'created_at', 'id')

        serializer = self.get_serializer(apps, many=True)
        return Response(serializer.data)
