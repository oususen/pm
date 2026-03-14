from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db.models import Q
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
import django_filters

from .models import OvertimeApplication, OvertimeApprovalLog
from .serializers import OvertimeApplicationSerializer

User = get_user_model()

# ロールの承認順序
APPROVAL_LEVELS = ['supervisor', 'chief', 'manager']

# ステータスと承認済みロールの対応
STATUS_AFTER_APPROVE = {
    'supervisor': 'approved_supervisor',
    'chief': 'approved_chief',
    'manager': 'approved_manager',
}


def find_approvers_for_role(applicant, role):
    """申請者の組織情報から指定ロールの承認者を検索する"""
    try:
        profile = applicant.profile
    except Exception:
        return User.objects.none()

    if role == 'supervisor':
        if not profile.team:
            return User.objects.none()
        # supervisor_teams に設定されている班長 OR 同じ班に所属する班長（どちらか）
        return User.objects.filter(
            Q(profile__role='supervisor', profile__supervisor_teams=profile.team) |
            Q(profile__role='supervisor', profile__team=profile.team)
        ).distinct()
    elif role == 'chief':
        if not profile.group:
            return User.objects.none()
        return User.objects.filter(
            profile__role='chief',
            profile__group=profile.group,
        )
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
        notif = Notification.objects.create(
            title=message,
            category='overtime',
            domain='overtime',
            valid_from=datetime.date.today(),
            valid_to=application.work_date + datetime.timedelta(days=14),
            description=(
                f"申請者: {name}\n"
                f"実施日: {application.work_date}\n"
                f"時間帯: {application.start_time.strftime('%H:%M')}〜{application.end_time.strftime('%H:%M')}\n"
                f"時間数: {application.hours}H（深夜: {application.midnight_hours}H）\n"
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
    次の承認者が見つからない場合はスキップして最終承認まで進める。
    """
    # 現在承認済みレベルのインデックスを特定
    current_level_idx = -1
    if application.status == 'submitted':
        current_level_idx = -1
    elif application.status == 'approved_supervisor':
        current_level_idx = 0
    elif application.status == 'approved_chief':
        current_level_idx = 1

    applicant = application.applicant

    # 次のレベルを探す
    for i in range(current_level_idx + 1, len(APPROVAL_LEVELS)):
        role = APPROVAL_LEVELS[i]
        count = create_pending_logs(application, role)
        if count > 0:
            # 通知作成
            applicant_name = (
                f"{applicant.last_name} {applicant.first_name}".strip() or applicant.username
            )
            pending_users = [
                log.approver
                for log in application.approval_logs.filter(role=role, status='pending')
                if log.approver
            ]
            create_approval_notification(
                application,
                pending_users,
                f"【残業申請 承認依頼】{applicant_name} / {application.work_date}",
            )
            return  # 次のレベルのpendingログ作成完了

    # 承認者が誰もいない or 全レベル完了 → 最終承認
    application.status = 'approved_manager'
    application.save(update_fields=['status', 'updated_at'])
    # 申請者に通知
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

    class Meta:
        model = OvertimeApplication
        fields = ['work_date__gte', 'work_date__lte', 'status', 'applicant']


class OvertimeApplicationViewSet(viewsets.ModelViewSet):
    serializer_class = OvertimeApplicationSerializer
    permission_classes = [IsAuthenticated]
    filterset_class = OvertimeApplicationFilter
    ordering_fields = ['work_date', 'created_at', 'status']
    ordering = ['-work_date', '-created_at']

    def get_queryset(self):
        user = self.request.user
        try:
            role = user.profile.role
        except Exception:
            role = 'staff'

        # 管理職は全申請を閲覧可能、それ以外は自分の申請のみ
        qs = OvertimeApplication.objects.select_related(
            'applicant', 'team'
        ).prefetch_related('approval_logs__approver')

        if role in ('manager', 'chief', 'supervisor'):
            return qs
        return qs.filter(applicant=user)

    def update(self, request, *args, **kwargs):
        app = self.get_object()
        if app.applicant != request.user:
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
        if app.applicant != request.user:
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

    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        """申請を提出する"""
        app = self.get_object()
        if app.applicant != request.user:
            return Response({'detail': '権限がありません。'}, status=status.HTTP_403_FORBIDDEN)
        if app.status not in ('draft', 'rejected'):
            return Response(
                {'detail': '下書きまたは却下された申請のみ提出できます。'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 既存のpendingログをクリア（再申請の場合）
        app.approval_logs.filter(status='pending').delete()

        app.status = 'submitted'
        app.submitted_at = timezone.now()
        app.rejection_reason = ''
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

        # アプリケーションのステータスを更新
        app.status = STATUS_AFTER_APPROVE.get(log.role, app.status)
        app.save(update_fields=['status', 'updated_at'])

        # 次のレベルへ進む
        advance_to_next_level(app)

        # approvedになった場合は申請者へ通知済み（advance_to_next_level内）

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

    @action(detail=False, methods=['get'])
    def pending_approvals(self, request):
        """自分が承認すべき申請一覧"""
        user = request.user
        apps = OvertimeApplication.objects.filter(
            approval_logs__approver=user,
            approval_logs__status='pending',
        ).select_related('applicant', 'team').prefetch_related(
            'approval_logs__approver'
        ).distinct().order_by('work_date', 'created_at')

        serializer = self.get_serializer(apps, many=True)
        return Response(serializer.data)
