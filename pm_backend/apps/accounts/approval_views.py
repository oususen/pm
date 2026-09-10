from datetime import datetime, timedelta
from urllib.parse import urlencode

from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Q
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from notifications.models import Notification
from shipping.services.email_service import EmailService

from .models import (
    ApprovalRouteConfig,
    ApprovalRequest,
    ApprovalStep,
    ApprovalTask,
    UserProfile,
)
from .role_utils import build_chief_role_q, build_leader_role_q, build_supervisor_role_q
from .serializers import ApprovalRequestSerializer


STAGE_FLOW = ['creator', 'reviewer1', 'reviewer2', 'approver']
STAGE_TASK_TYPE = {
    'creator': 'CREATOR_CREATE',
    'reviewer1': 'REVIEWER1_REVIEW',
    'reviewer2': 'REVIEWER2_REVIEW',
    'approver': 'APPROVER_APPROVE',
}


def _display_user_name(user):
    if not user or not getattr(user, 'id', None):
        return ''
    return f'{user.last_name or ""} {user.first_name or ""}'.strip() or user.username


def _get_next_stage(route_config, current_stage):
    idx = STAGE_FLOW.index(current_stage)
    for next_stage in STAGE_FLOW[idx + 1:]:
        if next_stage == 'reviewer2' and not route_config.reviewer2_enabled:
            continue
        return next_stage
    return 'completed'


def _resolve_stage_users(route_config, stage, creator=None):
    """承認設定から段階の担当ユーザーを解決する"""
    allowed_users = list(getattr(route_config, f'{stage}_allowed_users').all())
    if allowed_users:
        return allowed_users

    role = getattr(route_config, f'{stage}_role', '')
    if not role:
        return []

    if creator:
        profile = getattr(creator, 'profile', None)
        if profile:
            users = User.objects.filter(is_active=True)

            if role == 'leader' and profile.unit_id:
                users = users.filter(build_leader_role_q(profile.unit_id))
            elif role == 'supervisor' and profile.team_id:
                users = users.filter(build_supervisor_role_q(profile.team_id))
            elif role == 'chief' and profile.group_id:
                users = users.filter(build_chief_role_q(profile.group_id))
            elif role == 'manager' and profile.division_id:
                users = users.filter(profile__role='manager', profile__division_id=profile.division_id)
            else:
                users = users.filter(profile__role=role)
            return list(users.distinct())

    return list(User.objects.filter(is_active=True, profile__role=role).distinct())


def _get_proxy_users(route_config, stage):
    return list(getattr(route_config, f'{stage}_proxy_users').all())


def _create_tasks(approval_request, task_type, users, due_date=None):
    created = 0
    for user in users:
        if not getattr(user, 'id', None):
            continue
        exists = ApprovalTask.objects.filter(
            request=approval_request,
            task_type=task_type,
            assigned_to=user,
            status='PENDING',
        ).exists()
        if exists:
            continue
        ApprovalTask.objects.create(
            request=approval_request,
            task_type=task_type,
            assigned_to=user,
            status='PENDING',
            due_date=due_date,
        )
        created += 1
    return created


def _mark_tasks_done(approval_request, task_type):
    now = datetime.now()
    ApprovalTask.objects.filter(
        request=approval_request,
        task_type=task_type,
        status='PENDING',
    ).update(status='DONE', done_at=now)


def _create_notification(title, description, user_ids, operator_name=''):
    today = datetime.now().date()
    notification = Notification.objects.create(
        title=title[:200],
        category='承認',
        domain='APPROVAL',
        valid_from=today,
        valid_to=today + timedelta(days=14),
        display_order=0,
        description=description or '',
        operator_name=operator_name,
    )
    notification.target_users.set(user_ids)
    return notification


def _frontend_base_url(request=None):
    if request is not None:
        origin = request.META.get('HTTP_ORIGIN')
        if origin:
            return origin.rstrip('/')
        referer = request.META.get('HTTP_REFERER')
        if referer:
            parts = referer.split('/', 3)
            if len(parts) >= 3:
                return '/'.join(parts[:3]).rstrip('/')
    return ''


def _approval_request_path(approval_request):
    if approval_request.route_config.item_key == 'laser_material_order':
        start_date = (approval_request.context or {}).get('start_date') or ''
        query = urlencode({'tab': 'laser', 'start_date': start_date})
        return f'/production/plan-input?{query}'
    return '/tasks'


def _approval_request_url(approval_request, request=None):
    path = _approval_request_path(approval_request)
    base_url = _frontend_base_url(request)
    return f'{base_url}{path}' if base_url else path


def _approval_context_label(approval_request):
    if not approval_request:
        return ''
    context = approval_request.context or {}
    labels = []
    supplier = context.get('supplier')
    supplier_label = {'SATO': '佐藤商事', 'MEISEI': '名成鋼機'}.get(supplier, '')
    if supplier_label:
        labels.append(supplier_label)
    start_date = context.get('lock_start_date')
    end_date = context.get('lock_end_date')
    if start_date and end_date:
        labels.append(f'{start_date}～{end_date}')
    return ' '.join(labels)


def _approval_item_label(route_config, approval_request=None):
    context_label = _approval_context_label(approval_request)
    return f'{route_config.item_name} {context_label}' if context_label else route_config.item_name


def _send_stage_email(route_config, stage, users, operator_user, approval_request=None, request=None):
    """承認設定で有効な段階メールを、対象ユーザーへ送信する。"""
    if not getattr(route_config, f'{stage}_email_notification_enabled', False):
        return
    emails = [user.email for user in users if user.email]
    if not emails:
        return
    stage_label = dict(ApprovalRequest.STAGE_CHOICES).get(stage, stage)
    item_label = _approval_item_label(route_config, approval_request)
    link_text = f'\n\n確認リンク:\n{_approval_request_url(approval_request, request)}' if approval_request else ''
    EmailService().send_plain_email(
        to_emails=emails,
        subject=f'[{item_label}] {stage_label}依頼',
        body=f'{_display_user_name(operator_user)}さんから{item_label}の{stage_label}依頼があります。{link_text}',
        user_id=operator_user.id,
    )


def _get_result_users(approval_request, route_config):
    """承認・却下結果の通知先を、全段階の担当者候補から解決する。"""
    users = [approval_request.creator]
    for stage in STAGE_FLOW:
        if stage == 'creator':
            continue
        if stage == 'reviewer2' and not route_config.reviewer2_enabled:
            continue
        users.extend(_resolve_stage_users(route_config, stage, creator=approval_request.creator))
        users.extend(_get_proxy_users(route_config, stage))
    return list({user.id: user for user in users if getattr(user, 'id', None)}.values())


def _send_result_email(route_config, result_type, users, operator_user, reason='', approval_request=None, request=None):
    """承認設定で有効な結果メールを、全段階担当者へ送信する。"""
    field = f'{result_type}_result_email_notification_enabled'
    if not getattr(route_config, field, False):
        return
    emails = [user.email for user in users if user.email]
    if not emails:
        return
    action_label = '承認' if result_type == 'approved' else '却下'
    item_label = _approval_item_label(route_config, approval_request)
    reason_text = f'\n理由: {reason}' if reason else ''
    link_text = f'\n\n確認リンク:\n{_approval_request_url(approval_request, request)}' if approval_request else ''
    EmailService().send_plain_email(
        to_emails=emails,
        subject=f'[{item_label}] {action_label}結果',
        body=f'{_display_user_name(operator_user)}さんが{item_label}を{action_label}しました。{reason_text}{link_text}',
        user_id=operator_user.id,
    )


def _advance_to_stage(approval_request, route_config, next_stage, operator_user, request=None):
    """次の段階にタスク・通知を生成する"""
    if next_stage == 'completed':
        return

    task_enabled = getattr(route_config, f'{next_stage}_task_enabled', True)
    app_notify = getattr(route_config, f'{next_stage}_app_notification_enabled', True)

    target_users = _resolve_stage_users(route_config, next_stage, creator=approval_request.creator)
    proxy_users = _get_proxy_users(route_config, next_stage)
    all_users = list({u.id: u for u in target_users + proxy_users}.values())

    task_type = STAGE_TASK_TYPE.get(next_stage, '')
    if task_enabled and task_type and all_users:
        _create_tasks(approval_request, task_type, all_users)

    if app_notify and all_users:
        item_name = _approval_item_label(route_config, approval_request)
        operator_name = _display_user_name(operator_user)
        stage_labels = dict(ApprovalRequest.STAGE_CHOICES)
        stage_label = stage_labels.get(next_stage, next_stage)
        _create_notification(
            title=f'[{item_name}] {stage_label}依頼',
            description=f'{operator_name}さんから{item_name}の{stage_label}依頼があります。',
            user_ids=[u.id for u in all_users],
            operator_name=operator_name,
        )

    _send_stage_email(route_config, next_stage, all_users, operator_user, approval_request=approval_request, request=request)


class ApprovalRequestViewSet(viewsets.ModelViewSet):
    queryset = ApprovalRequest.objects.select_related(
        'route_config', 'creator',
    ).prefetch_related(
        'steps__user', 'tasks__assigned_to',
    )
    serializer_class = ApprovalRequestSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['route_config__item_name', 'context']
    ordering = ['-created_at']

    def get_queryset(self):
        qs = super().get_queryset()
        item_key = self.request.query_params.get('item_key')
        if item_key:
            qs = qs.filter(route_config__item_key=item_key)
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        task_filters = {}
        if str(self.request.query_params.get('assigned_to_me') or '').lower() in ('1', 'true', 'yes'):
            task_filters['tasks__assigned_to'] = self.request.user
        task_status = self.request.query_params.get('task_status')
        if task_status:
            task_filters['tasks__status'] = task_status
        if task_filters:
            qs = qs.filter(**task_filters).distinct()
        context_filter = self.request.query_params.get('context_match')
        if context_filter:
            import json
            try:
                match = json.loads(context_filter)
                for k, v in match.items():
                    qs = qs.filter(**{f'context__{k}': v})
            except (json.JSONDecodeError, TypeError):
                pass
        return qs

    def perform_create(self, serializer):
        serializer.save(creator=self.request.user, status='created', current_stage='creator')

    @action(detail=True, methods=['post'], url_path='submit')
    def submit_for_review(self, request, pk=None):
        """作成者が確認依頼を出す"""
        approval = self.get_object()
        if approval.status not in ('created', 'rejected'):
            return Response({'detail': 'この状態では確認依頼できません。'}, status=status.HTTP_400_BAD_REQUEST)
        if approval.route_config.item_key == 'laser_material_order':
            supplier = (approval.context or {}).get('supplier')
            saved_files = (approval.context or {}).get('material_order_pdf_files') or {}
            if not supplier or supplier not in saved_files:
                return Response({'detail': '先にこの仕入先の注文書を作成してください。'}, status=status.HTTP_400_BAD_REQUEST)

        route_config = approval.route_config
        next_stage = _get_next_stage(route_config, 'creator')

        with transaction.atomic():
            ApprovalStep.objects.create(
                request=approval,
                stage='creator',
                user=request.user,
                action='confirmed',
            )
            _mark_tasks_done(approval, 'CREATOR_CREATE')
            _mark_tasks_done(approval, 'CREATOR_FIX')

            approval.status = 'reviewing'
            approval.current_stage = next_stage
            approval.reject_reason = ''
            approval.save()

            _advance_to_stage(approval, route_config, next_stage, request.user, request=request)

        return Response(self.get_serializer(self.get_object()).data)

    @action(detail=True, methods=['post'], url_path='confirm')
    def confirm(self, request, pk=None):
        """確認者が確認済みにする"""
        approval = self.get_object()
        if approval.status != 'reviewing':
            return Response({'detail': 'この状態では確認できません。'}, status=status.HTTP_400_BAD_REQUEST)

        current = approval.current_stage
        if current not in ('reviewer1', 'reviewer2'):
            return Response({'detail': 'この段階では確認できません。'}, status=status.HTTP_400_BAD_REQUEST)

        route_config = approval.route_config
        next_stage = _get_next_stage(route_config, current)

        with transaction.atomic():
            ApprovalStep.objects.create(
                request=approval,
                stage=current,
                user=request.user,
                action='confirmed',
            )
            _mark_tasks_done(approval, STAGE_TASK_TYPE[current])

            approval.current_stage = next_stage
            approval.save()

            _advance_to_stage(approval, route_config, next_stage, request.user, request=request)

        return Response(self.get_serializer(self.get_object()).data)

    @action(detail=True, methods=['post'], url_path='approve')
    def approve(self, request, pk=None):
        """承認者が承認する"""
        approval = self.get_object()
        if approval.status != 'reviewing' or approval.current_stage != 'approver':
            return Response({'detail': 'この状態では承認できません。'}, status=status.HTTP_400_BAD_REQUEST)

        route_config = approval.route_config

        with transaction.atomic():
            ApprovalStep.objects.create(
                request=approval,
                stage='approver',
                user=request.user,
                action='approved',
            )
            _mark_tasks_done(approval, 'APPROVER_APPROVE')

            approval.status = 'approved'
            approval.current_stage = 'completed'
            approval.save()

            result_users = _get_result_users(approval, route_config)
            if route_config.approved_result_app_notification_enabled:
                _create_notification(
                    title=f'[{_approval_item_label(route_config, approval)}] 承認完了',
                    description=f'{_display_user_name(request.user)}さんが{_approval_item_label(route_config, approval)}を承認しました。',
                    user_ids=[user.id for user in result_users],
                    operator_name=_display_user_name(request.user),
                )
            _send_result_email(route_config, 'approved', result_users, request.user, approval_request=approval, request=request)

        return Response(self.get_serializer(self.get_object()).data)

    @action(detail=True, methods=['post'], url_path='reject')
    def reject(self, request, pk=None):
        """却下 → 作成者に差し戻し"""
        approval = self.get_object()
        if approval.status != 'reviewing':
            return Response({'detail': 'この状態では却下できません。'}, status=status.HTTP_400_BAD_REQUEST)

        route_config = approval.route_config
        reason = request.data.get('reason', '')

        with transaction.atomic():
            ApprovalStep.objects.create(
                request=approval,
                stage=approval.current_stage,
                user=request.user,
                action='rejected',
                comment=reason,
            )
            current_task_type = STAGE_TASK_TYPE.get(approval.current_stage, '')
            if current_task_type:
                _mark_tasks_done(approval, current_task_type)

            approval.status = 'rejected'
            approval.current_stage = 'creator'
            approval.reject_reason = reason
            approval.save()

            _create_tasks(approval, 'CREATOR_FIX', [approval.creator])

            result_users = _get_result_users(approval, route_config)
            if route_config.rejected_result_app_notification_enabled:
                _create_notification(
                    title=f'[{_approval_item_label(route_config, approval)}] 却下',
                    description=f'{_display_user_name(request.user)}さんが{_approval_item_label(route_config, approval)}を却下しました。理由: {reason}',
                    user_ids=[user.id for user in result_users],
                    operator_name=_display_user_name(request.user),
                )
            _send_result_email(route_config, 'rejected', result_users, request.user, reason=reason, approval_request=approval, request=request)

        return Response(self.get_serializer(self.get_object()).data)
