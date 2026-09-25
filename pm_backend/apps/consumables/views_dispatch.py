"""注文依頼・注文書API"""
from datetime import datetime
from decimal import Decimal
from io import BytesIO
from urllib.parse import quote

from django.db import IntegrityError, transaction
from django.http import HttpResponse
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.models import ApprovalRequest, ApprovalRouteConfig
from accounts.permissions import HasResourcePermissionOrReadOnly
from production.serializers_camera_actual import resolve_business_date
from purchase.order_proposal_views import _get_route_proxy_users, _resolve_route_stage_users
from shipping.services.email_service import EmailService

from .dispatch_service import APPROVAL_ITEM_KEY, build_order_email, save_dispatch_order_pdf
from .models import (
    Consumable,
    ConsumableDispatchOrder,
    ConsumableDispatchOrderItem,
    ConsumableRequest,
    ConsumableStockMovement,
)
from .serializers import ConsumableDispatchOrderSerializer, ConsumableRequestSerializer
from .services import display_user_name, org_snapshot
from .views import _resolve_worker, _to_int

R = ConsumableRequest

# 依頼の手動状態変更で許可する遷移（発注済・入庫済は注文書の送信・入庫でのみ変わる）
ALLOWED_TRANSITIONS = {
    R.STATUS_REQUESTED: {R.STATUS_PREPARING, R.STATUS_REJECTED, R.STATUS_CANCELLED},
    R.STATUS_PREPARING: {R.STATUS_REQUESTED, R.STATUS_REJECTED, R.STATUS_CANCELLED},
    R.STATUS_REJECTED: {R.STATUS_REQUESTED},
    R.STATUS_CANCELLED: {R.STATUS_REQUESTED},
}


class ConsumableRequestViewSet(viewsets.ModelViewSet):
    queryset = ConsumableRequest.objects.select_related('consumable', 'consumable__supplier')
    serializer_class = ConsumableRequestSerializer
    permission_classes = [IsAuthenticated, HasResourcePermissionOrReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'request_type', 'consumable']
    search_fields = ['consumable__code', 'consumable__name', 'requester_name', 'note']
    ordering = ['-requested_at', '-id']

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params
        statuses = [s for s in params.get('statuses', '').split(',') if s]
        if statuses:
            qs = qs.filter(status__in=statuses)
        if params.get('supplier'):
            qs = qs.filter(consumable__supplier_id=params.get('supplier'))
        if params.get('undispatched') == '1':
            # まだ注文書に載っていない依頼
            qs = qs.filter(dispatch_items__isnull=True)
        return qs

    def create(self, request, *args, **kwargs):
        """
        注文依頼の登録。direct=true は発注担当が直接「発注準備」で登録する
        （syomohin の「発注準備に追加」と同じ）。
        """
        consumable = Consumable.objects.filter(id=request.data.get('consumable'), is_active=True).first()
        if consumable is None:
            return Response({'detail': '消耗品が見つかりません'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            quantity = _to_int(request.data.get('quantity'), 0)
            requester = _resolve_worker(request, field='requester')
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        if quantity <= 0:
            return Response({'detail': '数量は1以上で入力してください'}, status=status.HTTP_400_BAD_REQUEST)
        deadline = request.data.get('deadline') or '通常'
        if deadline not in dict(R.DEADLINE_CHOICES):
            return Response({'detail': '納期が正しくありません'}, status=status.HTTP_400_BAD_REQUEST)

        is_direct = str(request.data.get('direct', '')).lower() in ('1', 'true')
        req = ConsumableRequest.objects.create(
            consumable=consumable,
            quantity=quantity,
            unit_price=consumable.unit_price,
            total_amount=consumable.unit_price * quantity,
            deadline=deadline,
            requester=requester,
            requester_name=display_user_name(requester),
            request_type='manual',
            status=R.STATUS_PREPARING if is_direct else R.STATUS_REQUESTED,
            note=request.data.get('note', '') or '',
            requested_at=datetime.now(),
            created_by=request.user,
            **org_snapshot(requester),
        )
        return Response(self.get_serializer(req).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        req = self.get_object()
        if req.status not in (R.STATUS_REQUESTED, R.STATUS_PREPARING) or req.dispatch_items.exists():
            return Response({'detail': 'この依頼は変更できません（注文書作成済み・発注済みなど）'},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            quantity = _to_int(request.data.get('quantity', req.quantity), 0)
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        if quantity <= 0:
            return Response({'detail': '数量は1以上で入力してください'}, status=status.HTTP_400_BAD_REQUEST)
        deadline = request.data.get('deadline', req.deadline)
        if deadline not in dict(R.DEADLINE_CHOICES):
            return Response({'detail': '納期が正しくありません'}, status=status.HTTP_400_BAD_REQUEST)
        req.quantity = quantity
        req.total_amount = req.unit_price * quantity
        req.deadline = deadline
        req.note = request.data.get('note', req.note) or ''
        req.save(update_fields=['quantity', 'total_amount', 'deadline', 'note', 'updated_at'])
        return Response(self.get_serializer(req).data)

    def partial_update(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        req = self.get_object()
        if req.status in (R.STATUS_ORDERED, R.STATUS_RECEIVED) or req.dispatch_items.exists():
            return Response({'detail': '注文書作成済み・発注済みの依頼は削除できません'},
                            status=status.HTTP_400_BAD_REQUEST)
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=['post'], url_path='set-status')
    def set_status(self, request, pk=None):
        """依頼の状態変更（発注準備にする／却下／キャンセル／依頼中に戻す）"""
        req = self.get_object()
        new_status = request.data.get('status')
        if new_status not in ALLOWED_TRANSITIONS.get(req.status, set()):
            return Response({'detail': f'「{req.get_status_display()}」からこの状態には変更できません'},
                            status=status.HTTP_400_BAD_REQUEST)
        if req.dispatch_items.exists():
            return Response({'detail': '注文書に載っている依頼は変更できません。先に注文書を削除してください。'},
                            status=status.HTTP_400_BAD_REQUEST)
        req.status = new_status
        req.save(update_fields=['status', 'updated_at'])
        return Response(self.get_serializer(req).data)


def _get_route_config():
    return ApprovalRouteConfig.objects.filter(item_key=APPROVAL_ITEM_KEY, is_active=True).first()


def _can_create_dispatch_order(route_config, user):
    """承認設定の作成者（役割・部署・作成可能ユーザー・代理）に含まれるか"""
    if user.is_superuser:
        return True
    users = _resolve_route_stage_users(route_config, 'creator', creator=user) + _get_route_proxy_users(route_config, 'creator')
    return any(u.id == user.id for u in users)


def _next_order_number(business_date):
    prefix = f'PO-{business_date.strftime("%Y%m%d")}-'
    last = (
        ConsumableDispatchOrder.objects.filter(order_number__startswith=prefix)
        .order_by('-order_number').values_list('order_number', flat=True).first()
    )
    seq = int(last.rsplit('-', 1)[1]) + 1 if last else 1
    return f'{prefix}{seq:03d}'


class ConsumableDispatchOrderViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ConsumableDispatchOrder.objects.select_related(
        'supplier', 'created_by', 'approval_request', 'approval_request__route_config'
    ).prefetch_related('items')
    serializer_class = ConsumableDispatchOrderSerializer
    permission_classes = [IsAuthenticated, HasResourcePermissionOrReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'supplier']
    search_fields = ['order_number', 'supplier_name']
    ordering = ['-created_at', '-id']

    @action(detail=False, methods=['get'], url_path='route-status')
    def route_status(self, request):
        """承認ルートの設定有無と、ログインユーザーが注文書を作成できるか"""
        route_config = _get_route_config()
        return Response({
            'route_configured': route_config is not None,
            'can_create': bool(route_config and _can_create_dispatch_order(route_config, request.user)),
        })

    @action(detail=False, methods=['post'], url_path='create-order')
    def create_order(self, request):
        """発注準備の依頼から、購入先単位で注文書を作成し、承認申請を作る"""
        route_config = _get_route_config()
        if route_config is None:
            return Response({'detail': '承認設定に「消耗品注文書」がありません。設定 > 承認設定で登録してください。'},
                            status=status.HTTP_400_BAD_REQUEST)
        if not _can_create_dispatch_order(route_config, request.user):
            return Response({'detail': '注文書の作成権限がありません（承認設定の作成者を確認してください）'},
                            status=status.HTTP_403_FORBIDDEN)

        supplier_id = request.data.get('supplier')
        try:
            request_ids = {int(x) for x in (request.data.get('request_ids') or [])}
        except (TypeError, ValueError):
            return Response({'detail': '依頼IDが正しくありません'}, status=status.HTTP_400_BAD_REQUEST)
        if not supplier_id or not request_ids:
            return Response({'detail': '購入先と依頼を指定してください'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            requests = list(
                ConsumableRequest.objects.select_for_update()
                .select_related('consumable', 'consumable__supplier')
                .filter(id__in=request_ids, status=R.STATUS_PREPARING, dispatch_items__isnull=True,
                        consumable__supplier_id=supplier_id)
            )
            if len(requests) != len(request_ids):
                return Response(
                    {'detail': '発注準備でない依頼・購入先が異なる依頼・注文書作成済みの依頼が含まれています。画面を更新してください。'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            supplier = requests[0].consumable.supplier
            now = datetime.now()
            business_date = resolve_business_date(now)
            daily_count = ConsumableDispatchOrder.objects.filter(
                supplier=supplier, business_date=business_date
            ).count() + 1

            dispatch_order = None
            for _ in range(3):  # 番号の同時採番に備えて再試行
                try:
                    with transaction.atomic():
                        dispatch_order = ConsumableDispatchOrder.objects.create(
                            order_number=_next_order_number(business_date),
                            business_date=business_date,
                            daily_count=daily_count,
                            supplier=supplier,
                            supplier_name=supplier.name,
                            total_items=len(requests),
                            total_amount=sum((r.total_amount for r in requests), Decimal('0')),
                            note=request.data.get('note', '') or '',
                            created_by=request.user,
                            created_at=now,
                        )
                    break
                except IntegrityError:
                    continue
            if dispatch_order is None:
                return Response({'detail': '注文書番号の採番に失敗しました。もう一度実行してください。'},
                                status=status.HTTP_409_CONFLICT)

            for req in sorted(requests, key=lambda r: r.consumable.code):
                ConsumableDispatchOrderItem.objects.create(
                    dispatch_order=dispatch_order,
                    consumable=req.consumable,
                    request=req,
                    code=req.consumable.code,
                    order_code=req.consumable.order_code,
                    name=req.consumable.name,
                    quantity=req.quantity,
                    unit=req.consumable.unit,
                    unit_price=req.unit_price,
                    total_amount=req.total_amount,
                    deadline=req.deadline,
                    note=req.note,
                )

            dispatch_order.approval_request = ApprovalRequest.objects.create(
                route_config=route_config,
                creator=request.user,
                status='created',
                current_stage='creator',
                context={
                    'dispatch_order_id': dispatch_order.id,
                    'order_number': dispatch_order.order_number,
                    'supplier_name': supplier.name,
                },
            )
            dispatch_order.save(update_fields=['approval_request'])
            save_dispatch_order_pdf(dispatch_order)

        return Response(self.get_serializer(self.get_queryset().get(id=dispatch_order.id)).data,
                        status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        """未送信の注文書を削除する（依頼は発注準備に戻り、承認申請も削除する）"""
        dispatch_order = self.get_object()
        if dispatch_order.status != ConsumableDispatchOrder.STATUS_UNSENT:
            return Response({'detail': '送信済みの注文書は削除できません'}, status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            approval = dispatch_order.approval_request
            if dispatch_order.pdf_file:
                dispatch_order.pdf_file.delete(save=False)
            dispatch_order.delete()
            if approval:
                approval.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['get'])
    def pdf(self, request, pk=None):
        dispatch_order = self.get_object()
        if not dispatch_order.pdf_file:
            save_dispatch_order_pdf(dispatch_order)
        with dispatch_order.pdf_file.open('rb') as f:
            content = f.read()
        response = HttpResponse(content, content_type='application/pdf')
        disposition = 'attachment' if request.query_params.get('download') == '1' else 'inline'
        filename = dispatch_order.pdf_file.name.rsplit('/', 1)[-1]
        response['Content-Disposition'] = f"{disposition}; filename*=UTF-8''{quote(filename)}"
        return response

    @action(detail=True, methods=['post'])
    def send(self, request, pk=None):
        """承認済みの注文書を購入先へメール送信する。送信後、依頼は発注済になる"""
        dispatch_order = self.get_object()
        approval = dispatch_order.approval_request
        if dispatch_order.status != ConsumableDispatchOrder.STATUS_UNSENT:
            return Response({'detail': 'この注文書は送信済みです'}, status=status.HTTP_400_BAD_REQUEST)
        if not approval or approval.status != 'approved':
            return Response({'detail': '承認が完了していないため送信できません'}, status=status.HTTP_400_BAD_REQUEST)
        email = (request.data.get('email') or dispatch_order.supplier.email or '').strip()
        if not email:
            return Response({'detail': '送信先メールアドレスがありません（購入先マスタに登録してください）'},
                            status=status.HTTP_400_BAD_REQUEST)

        # 承認欄を最新にしてから送る
        content = save_dispatch_order_pdf(dispatch_order)
        subject, body = build_order_email(dispatch_order)
        result = EmailService().send_email_with_attachment(
            to_emails=[email],
            subject=subject,
            body=body,
            attachment_data=BytesIO(content),
            attachment_filename=dispatch_order.pdf_file.name.rsplit('/', 1)[-1],
            user_id=request.user.id,
        )
        if not result.get('success'):
            return Response({'detail': f"メール送信に失敗しました: {result.get('message', '')}"},
                            status=status.HTTP_400_BAD_REQUEST)

        now = datetime.now()
        with transaction.atomic():
            dispatch_order.status = ConsumableDispatchOrder.STATUS_SENT
            dispatch_order.sent_at = now
            dispatch_order.sent_email = email
            dispatch_order.save(update_fields=['status', 'sent_at', 'sent_email'])
            approval.status = 'sent'
            approval.save(update_fields=['status', 'updated_at'])
            ConsumableRequest.objects.filter(dispatch_items__dispatch_order=dispatch_order).update(
                status=R.STATUS_ORDERED, ordered_at=now, updated_at=now
            )
        return Response(self.get_serializer(self.get_queryset().get(id=dispatch_order.id)).data)

    @action(detail=True, methods=['post'])
    def receive(self, request, pk=None):
        """注文書単位の一括入庫（syomohin の「発注分入庫」と同じ）"""
        dispatch_order = self.get_object()
        if dispatch_order.status != ConsumableDispatchOrder.STATUS_SENT:
            return Response({'detail': '送信済みの注文書だけ入庫できます'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            worker = _resolve_worker(request)
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        now = datetime.now()
        snapshot = org_snapshot(worker)
        note = request.data.get('note') or f'注文書一括入庫（{dispatch_order.order_number}）'
        with transaction.atomic():
            locked = ConsumableDispatchOrder.objects.select_for_update().get(id=dispatch_order.id)
            if locked.status != ConsumableDispatchOrder.STATUS_SENT:
                return Response({'detail': 'この注文書は入庫済みです'}, status=status.HTTP_400_BAD_REQUEST)
            for item in dispatch_order.items.all():
                consumable = Consumable.objects.select_for_update().get(id=item.consumable_id)
                consumable.stock_quantity += item.quantity
                consumable.save(update_fields=['stock_quantity', 'updated_at'])
                ConsumableStockMovement.objects.create(
                    consumable=consumable,
                    movement_type=ConsumableStockMovement.TYPE_INBOUND,
                    inbound_type=ConsumableStockMovement.INBOUND_DISPATCH,
                    request_id=item.request_id,
                    quantity=item.quantity,
                    stock_after=consumable.stock_quantity,
                    worker=worker,
                    worker_name=display_user_name(worker),
                    unit_price=item.unit_price,
                    total_amount=item.total_amount,
                    note=note,
                    moved_at=now,
                    created_by=request.user,
                    **snapshot,
                )
            ConsumableRequest.objects.filter(
                dispatch_items__dispatch_order=dispatch_order, status=R.STATUS_ORDERED
            ).update(status=R.STATUS_RECEIVED, completed_at=now, updated_at=now)
            locked.status = ConsumableDispatchOrder.STATUS_RECEIVED
            locked.received_at = now
            locked.save(update_fields=['status', 'received_at'])
        return Response(self.get_serializer(self.get_queryset().get(id=dispatch_order.id)).data)
