from io import BytesIO

from django.http import HttpResponse
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db.models import Q, CharField, F, Value
from django.db.models.functions import Coalesce, NullIf
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
import django_filters

from .access import can_manage_application
from .models import OvertimeApplication, OvertimeApprovalLog
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


def find_approvers_for_role(applicant, role):
    """申請者の組織情報から指定ロールの承認者を検索する"""
    try:
        profile = applicant.profile
    except Exception:
        return User.objects.none()

    if role == 'leader':
        if not profile.unit:
            return User.objects.none()
        # leader_units に申請者のグループが含まれるリーダーを検索
        return User.objects.filter(
            profile__role='leader',
            profile__leader_units=profile.unit,
        ).distinct()
    elif role == 'supervisor':
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
            pending_users = [
                log.approver
                for log in application.approval_logs.filter(
                    role__in=['leader', 'supervisor'], status='pending'
                )
                if log.approver
            ]
            create_approval_notification(
                application,
                pending_users,
                f"【残業申請 承認依頼】{applicant_name} / {application.work_date}",
            )
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

    class Meta:
        model = OvertimeApplication
        fields = ['work_date__gte', 'work_date__lte', 'status', 'applicant']


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
        try:
            role = user.profile.role
        except Exception:
            role = 'staff'

        # 管理職は全申請を閲覧可能、それ以外は自分の申請のみ
        qs = OvertimeApplication.objects.select_related(
            'applicant', 'created_by', 'team'
        ).prefetch_related('approval_logs__approver')

        if role in ('manager', 'chief', 'supervisor'):
            filtered_qs = qs
        elif role == 'leader':
            # 担当グループ（leader_units）のメンバーの申請のみ閲覧可能
            leader_units = user.profile.leader_units.all()
            if leader_units.exists():
                filtered_qs = qs.filter(applicant__profile__unit__in=leader_units)
            else:
                filtered_qs = qs.filter(applicant=user)
        else:
            filtered_qs = qs.filter(applicant=user)

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

        # 次の承認レベルへ進める（通知は一括でまとめて送る）
        chief_approvers = {}  # approver_id -> User
        auto_approved = []

        for app in approved_apps:
            # approved_supervisor 以降から次レベルを探す（リーダーは並列なのでスキップ）
            if app.status == 'approved_supervisor':
                start_idx = 2
            elif app.status == 'approved_chief':
                start_idx = 3
            else:
                # approved_leader または想定外: 班長がすでにpendingなので何もしない
                continue

            advanced = False
            for i in range(start_idx, len(APPROVAL_LEVELS)):
                role = APPROVAL_LEVELS[i]
                count = create_pending_logs(app, role)
                if count > 0:
                    for pending_log in app.approval_logs.filter(role=role, status='pending'):
                        if pending_log.approver:
                            chief_approvers[pending_log.approver.id] = pending_log.approver
                    advanced = True
                    break

            if not advanced:
                # 承認者なし → 最終承認
                app.status = 'approved_manager'
                app.save(update_fields=['status', 'updated_at'])
                auto_approved.append(app)
                create_approval_notification(
                    app, [app.applicant],
                    f"【残業申請 承認完了】{app.work_date} の申請が承認されました",
                )

        # 係長への一括通知（1通）
        notify_apps = [a for a in approved_apps if a not in auto_approved]
        if notify_apps and chief_approvers:
            approver_name = f"{user.last_name} {user.first_name}".strip() or user.username
            applicant_names = "、".join(dict.fromkeys(
                f"{a.applicant.last_name}{a.applicant.first_name}".strip() or a.applicant.username
                for a in notify_apps
            ))
            create_approval_notification(
                notify_apps[0],
                list(chief_approvers.values()),
                f"【残業申請 一括確認依頼】{approver_name} より {len(notify_apps)}件（{applicant_names}）",
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
            qs = self.get_queryset().filter(id__in=id_list).order_by('work_date', 'applicant_id')
        else:
            qs = self.filter_queryset(self.get_queryset()).order_by('work_date', 'applicant_id')

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
        ).distinct().order_by('work_date', 'created_at')

        serializer = self.get_serializer(apps, many=True)
        return Response(serializer.data)
