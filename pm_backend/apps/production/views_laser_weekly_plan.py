from collections import defaultdict
from io import BytesIO
from pathlib import Path
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_CEILING
from urllib.parse import quote

from django.conf import settings
from django.db.models import Q
from django.http import FileResponse, HttpResponse
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from masters.models import Product, Supplier
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfgen import canvas
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from accounts.models import ApprovalRequest, ApprovalRouteConfig
from accounts.serializers import ApprovalRequestSerializer
from shipping.services.email_service import EmailService

from .models_laser_weekly_plan import LaserMaterialOrderEmailConfig, LaserWeeklyMaterialDailyProgress, LaserWeeklyMaterialGroup, LaserWeeklyMaterialInitialProgress, LaserWeeklyMaterialOrderProgress, LaserWeeklyPatternDailyProgress, LaserWeeklyPatternInitialProgress, LaserWeeklyPatternManualQuantity, LaserWeeklyPlanManualQuantity, LaserWeeklyPlanTarget
from .models_laser_pattern import LaserPattern
from .models_line_plan import LinePlan
from .models_line_backlog import LineBacklog
from .serializers import LaserMaterialOrderEmailConfigSerializer, LaserWeeklyMaterialGroupSerializer, LaserWeeklyPlanTargetSerializer
from .services.recalc_start_date import _build_workday_helpers, _resolve_calendar_id


MATERIAL_ORDER_SUPPLIER_CODES = {
    LaserWeeklyMaterialOrderProgress.SUPPLIER_MEISEI: '000048',
    LaserWeeklyMaterialOrderProgress.SUPPLIER_SATO: '000131',
}

DEFAULT_MATERIAL_ORDER_EMAIL_BODY = (
    '{supplier_name} 御中\n\n'
    'いつもお世話になっております。\n'
    '材料注文書を送付いたします。添付PDFをご確認ください。\n'
    'このメールは送信専用です。ご返信はCC宛先へお願いします。\n\n'
    'ダイソウ工業株式会社'
)


def render_material_order_email_body(template, order_supplier, start_label='', end_label=''):
    body = (template or DEFAULT_MATERIAL_ORDER_EMAIL_BODY).strip() or DEFAULT_MATERIAL_ORDER_EMAIL_BODY
    return (
        body
        .replace('{supplier_name}', order_supplier.supplier_name or '')
        .replace('{start_date}', start_label or '')
        .replace('{end_date}', end_label or '')
    )


def append_material_order_reply_notice(body, cc_emails=None):
    """材料注文書メールには送信専用と返信先案内を必ず入れる。"""
    text = (body or '').strip()
    if '送信専用' in text and ('返信' in text or 'ご返信' in text):
        return text
    cc_list = [email for email in (cc_emails or []) if email]
    reply_to = f'CC宛先（{", ".join(cc_list)}）' if cc_list else 'CC宛先'
    notice = f'※このメールは送信専用です。ご返信は{reply_to}へお願いします。'
    return f'{text}\n\n{notice}' if text else notice


class LaserMaterialOrderEmailConfigViewSet(viewsets.ModelViewSet):
    serializer_class = LaserMaterialOrderEmailConfigSerializer
    pagination_class = None
    lookup_field = 'supplier'

    def get_queryset(self):
        return LaserMaterialOrderEmailConfig.objects.prefetch_related('cc_users').order_by('supplier')

    def _ensure_configs(self):
        for supplier, _label in LaserWeeklyMaterialOrderProgress.SUPPLIER_CHOICES:
            LaserMaterialOrderEmailConfig.objects.get_or_create(
                supplier=supplier,
                defaults={'body': DEFAULT_MATERIAL_ORDER_EMAIL_BODY},
            )

    def list(self, request, *args, **kwargs):
        self._ensure_configs()
        return super().list(request, *args, **kwargs)

    def get_object(self):
        supplier = self.kwargs.get(self.lookup_field)
        if supplier not in MATERIAL_ORDER_SUPPLIER_CODES:
            raise NotFound('仕入先が見つかりません。')
        obj, _created = LaserMaterialOrderEmailConfig.objects.get_or_create(
            supplier=supplier,
            defaults={'body': DEFAULT_MATERIAL_ORDER_EMAIL_BODY},
        )
        self.check_object_permissions(self.request, obj)
        return obj


class LaserWeeklyPlanTargetViewSet(viewsets.ModelViewSet):
    queryset = LaserWeeklyPlanTarget.objects.select_related('downstream_line', 'product', 'finished_product', 'laser_pattern__processing_freq_pattern')
    serializer_class = LaserWeeklyPlanTargetSerializer
    pagination_class = None


class LaserWeeklyMaterialGroupViewSet(viewsets.ModelViewSet):
    queryset = LaserWeeklyMaterialGroup.objects.prefetch_related('patterns')
    serializer_class = LaserWeeklyMaterialGroupSerializer


class LaserWeeklyPlanViewSet(viewsets.ViewSet):
    @action(detail=False, methods=['get', 'post'], url_path='material-order-approval')
    def material_order_approval(self, request):
        """材料発注の承認申請を仕入先別に取得または作成する。"""
        start_date = request.query_params.get('start_date') if request.method == 'GET' else request.data.get('start_date')
        try:
            plan_start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        except (TypeError, ValueError):
            return Response({'detail': 'start_date is required (YYYY-MM-DD)'}, status=status.HTTP_400_BAD_REQUEST)

        route_config = ApprovalRouteConfig.objects.filter(
            item_key='laser_material_order',
            is_active=True,
        ).first()
        if not route_config:
            return Response({'detail': '材料発注の承認ルートが設定されていません。'}, status=status.HTTP_400_BAD_REQUEST)

        if request.method == 'GET':
            approvals = ApprovalRequest.objects.filter(
                route_config=route_config,
                context__start_date=plan_start_date.isoformat(),
            ).order_by('-updated_at')
            by_supplier = {}
            for approval in approvals:
                supplier = (approval.context or {}).get('supplier')
                if supplier in MATERIAL_ORDER_SUPPLIER_CODES and supplier not in by_supplier:
                    by_supplier[supplier] = ApprovalRequestSerializer(approval).data
            return Response({'approvals': by_supplier})

        lock_start_date = request.data.get('lock_start_date')
        lock_end_date = request.data.get('lock_end_date')
        try:
            if lock_start_date and lock_end_date:
                lock_start_date = datetime.strptime(lock_start_date, '%Y-%m-%d').date()
                lock_end_date = datetime.strptime(lock_end_date, '%Y-%m-%d').date()
                if lock_end_date < lock_start_date:
                    raise ValueError
        except ValueError:
            return Response({'detail': 'ロック期間が不正です。'}, status=status.HTTP_400_BAD_REQUEST)

        supplier = request.data.get('supplier')
        if supplier not in MATERIAL_ORDER_SUPPLIER_CODES:
            return Response({'detail': '仕入先を指定してください。'}, status=status.HTTP_400_BAD_REQUEST)

        lookup = {
            'route_config': route_config,
            'context__start_date': plan_start_date.isoformat(),
        }
        if supplier in MATERIAL_ORDER_SUPPLIER_CODES:
            lookup['context__supplier'] = supplier
            lookup['context__lock_start_date'] = lock_start_date.isoformat() if lock_start_date else ''
            lookup['context__lock_end_date'] = lock_end_date.isoformat() if lock_end_date else ''
        approval = ApprovalRequest.objects.filter(**lookup).order_by('-updated_at').first()
        action_name = request.data.get('action')
        if action_name in ('reopen', 'adjust'):
            if not (lock_start_date and lock_end_date):
                return Response({'detail': '注文書期間を指定してください。'}, status=status.HTTP_400_BAD_REQUEST)
            if not approval:
                return Response({'detail': '修正対象の注文書が見つかりません。'}, status=status.HTTP_400_BAD_REQUEST)
            if action_name == 'reopen' and approval.status != 'created':
                return Response({'detail': '確認依頼前の注文書だけ修正できます。'}, status=status.HTTP_400_BAD_REQUEST)
            context = {**(approval.context or {})}
            if action_name == 'adjust':
                adjustments = {**(context.get('material_order_adjustments') or {})}
                adjustments[supplier] = {
                    'lock_start_date': lock_start_date.isoformat(),
                    'lock_end_date': lock_end_date.isoformat(),
                    'editing': True,
                    'started_at': datetime.now().isoformat(timespec='seconds'),
                    'started_by': request.user.id,
                }
                context['material_order_adjustments'] = adjustments
            else:
                context['order_created'] = False
            approval.context = context
            approval.save(update_fields=['context', 'updated_at'])
            return Response(ApprovalRequestSerializer(approval).data)

        created_approval = False
        if not approval:
            approval = ApprovalRequest.objects.create(
                route_config=route_config,
                creator=request.user,
                status='created',
                current_stage='creator',
                context={
                    'start_date': plan_start_date.isoformat(),
                    'supplier': supplier or '',
                    'lock_start_date': lock_start_date.isoformat() if lock_start_date else '',
                    'lock_end_date': lock_end_date.isoformat() if lock_end_date else '',
                },
            )
            created_approval = True

        if not (lock_start_date and lock_end_date):
            return Response({'detail': '注文書期間を指定してください。'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            saved_file = self._save_material_order_pdf_file(plan_start_date, lock_start_date, lock_end_date, supplier)
        except ValueError as exc:
            if created_approval and not approval.context.get('material_order_pdf_files'):
                approval.delete()
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        saved_files = {**approval.context.get('material_order_pdf_files', {})}
        saved_files[supplier] = saved_file
        context = {**approval.context, 'order_created': True}
        context.update({
            'supplier': supplier,
            'lock_start_date': lock_start_date.isoformat(),
            'lock_end_date': lock_end_date.isoformat(),
            'material_order_pdf_files': saved_files,
            'material_order_pdf_saved_at': datetime.now().isoformat(timespec='seconds'),
        })
        approval.context = context
        approval.save(update_fields=['context', 'updated_at'])
        return Response(ApprovalRequestSerializer(approval).data)

    @action(detail=False, methods=['get', 'post'], url_path='material-initial-progress')
    def material_initial_progress(self, request):
        try:
            plan_start_date = datetime.strptime(request.query_params.get('start_date') or request.data.get('start_date'), '%Y-%m-%d').date()
        except (TypeError, ValueError):
            return Response({'detail': 'start_date is required (YYYY-MM-DD)'}, status=status.HTTP_400_BAD_REQUEST)
        if request.method == 'GET':
            saved_map = {
                x.material_id: x
                for x in LaserWeeklyMaterialInitialProgress.objects.filter(plan_start_date=plan_start_date)
            }
            prev_start = plan_start_date - timedelta(days=7)
            prev_material_ids = set(
                LaserWeeklyMaterialDailyProgress.objects.filter(
                    progress_date__gte=prev_start,
                    progress_date__lt=plan_start_date,
                ).values_list('material_id', flat=True).distinct()
            )
            material_ids = set(saved_map.keys()) | prev_material_ids
            result = []
            for mid in material_ids:
                saved = saved_map.get(mid)
                if saved and saved.is_locked:
                    result.append({'material_id': mid, 'initial_progress': saved.initial_progress, 'is_locked': True})
                else:
                    auto_val = self._calc_material_auto_initial_progress(mid, plan_start_date)
                    result.append({'material_id': mid, 'initial_progress': auto_val, 'is_locked': False})
            return Response(result)
        items = request.data.get('items', [])
        for item in items:
            try:
                material_id, initial_progress, is_locked = int(item['material_id']), Decimal(str(item['initial_progress'])), bool(item.get('is_locked', False))
            except (InvalidOperation, KeyError, TypeError, ValueError):
                return Response({'detail': '期首進度の値が不正です。'}, status=status.HTTP_400_BAD_REQUEST)
            LaserWeeklyMaterialInitialProgress.objects.update_or_create(plan_start_date=plan_start_date, material_id=material_id, defaults={'initial_progress': initial_progress, 'is_locked': is_locked})
        return Response({'saved_count': len(items)})

    def _calc_material_auto_initial_progress(self, material_id, week_start_date):
        prev_start = week_start_date - timedelta(days=7)
        last_day = LaserWeeklyMaterialDailyProgress.objects.filter(
            material_id=material_id,
            progress_date__gte=prev_start,
            progress_date__lt=week_start_date,
        ).order_by('-progress_date').first()
        return float(last_day.progress) if last_day else 0

    @action(detail=False, methods=['post'], url_path='material-daily-progress')
    def save_material_daily_progress(self, request):
        items = request.data.get('items', [])
        if not isinstance(items, list):
            return Response({'detail': '日別進度データが不正です。'}, status=status.HTTP_400_BAD_REQUEST)
        raw_ids = set()
        for item in items:
            if isinstance(item, dict):
                try:
                    raw_ids.add(int(item.get('material_id', 0)))
                except (TypeError, ValueError):
                    pass
        material_ids = set(Product.objects.filter(id__in=raw_ids).values_list('id', flat=True))
        saved = 0
        for item in items:
            try:
                material_id = int(item['material_id'])
                if material_id not in material_ids:
                    continue
                progress_date = datetime.strptime(item['progress_date'], '%Y-%m-%d').date()
                progress = Decimal(str(item['progress']))
            except (InvalidOperation, KeyError, TypeError, ValueError):
                continue
            LaserWeeklyMaterialDailyProgress.objects.update_or_create(
                material_id=material_id, progress_date=progress_date,
                defaults={'progress': progress},
            )
            saved += 1
        return Response({'saved_count': saved})

    @action(detail=False, methods=['get', 'post'], url_path='material-order-progress')
    def material_order_progress(self, request):
        if request.method == 'GET':
            try:
                plan_start_date = datetime.strptime(request.query_params['start_date'], '%Y-%m-%d').date()
            except (KeyError, ValueError):
                return Response({'detail': 'start_date is required (YYYY-MM-DD)'}, status=status.HTTP_400_BAD_REQUEST)
            rows = LaserWeeklyMaterialOrderProgress.objects.filter(plan_start_date=plan_start_date, is_manual=False).select_related('material')
            return Response([{
                'material_id': row.material_id, 'required_date': row.required_date.isoformat(), 'delivery_date': row.delivery_date.isoformat(),
                'supplier': row.supplier, 'required_sheets': row.required_sheets, 'lot_multiple': row.lot_multiple,
                'required_lots': row.required_lots, 'order_lots': row.order_lots, 'order_sheets': row.order_sheets,
            } for row in rows])

        items = request.data.get('items', [])
        try:
            plan_start_date = datetime.strptime(request.data['start_date'], '%Y-%m-%d').date()
            material_ids = {int(item['material_id']) for item in items}
        except (KeyError, TypeError, ValueError):
            return Response({'detail': '発注進度の値が不正です。'}, status=status.HTTP_400_BAD_REQUEST)
        materials = Product.objects.in_bulk(material_ids)
        saved_count = 0
        for item in items:
            try:
                material = materials[int(item['material_id'])]
                required_date = datetime.strptime(item['required_date'], '%Y-%m-%d').date()
                delivery_date = datetime.strptime(item['delivery_date'], '%Y-%m-%d').date()
                required_sheets = int(item['required_sheets'])
                lot_multiple = int(item['lot_multiple'])
                sato_lots, meisei_lots = int(item['sato_lots']), int(item['meisei_lots'])
                sato_sheets, meisei_sheets = int(item.get('sato_sheets', 0)), int(item.get('meisei_sheets', 0))
                sato_enabled = bool(item.get('sato_enabled', False))
                if min(required_sheets, lot_multiple, sato_lots, meisei_lots, sato_sheets, meisei_sheets) < 0 or lot_multiple == 0:
                    raise ValueError
            except (KeyError, TypeError, ValueError):
                return Response({'detail': '発注進度の値が不正です。'}, status=status.HTTP_400_BAD_REQUEST)
            required_lots = int((Decimal(required_sheets) / Decimal(lot_multiple)).to_integral_value(rounding=ROUND_CEILING))
            if not sato_enabled:
                LaserWeeklyMaterialOrderProgress.objects.filter(
                    plan_start_date=plan_start_date, material=material, required_date=required_date,
                    supplier=LaserWeeklyMaterialOrderProgress.SUPPLIER_SATO, is_manual=False,
                ).delete()
            supplier_data = [(LaserWeeklyMaterialOrderProgress.SUPPLIER_MEISEI, meisei_lots, meisei_sheets)]
            if sato_enabled:
                supplier_data.append((LaserWeeklyMaterialOrderProgress.SUPPLIER_SATO, sato_lots, sato_sheets))
            for supplier, order_lots, order_sheets_val in supplier_data:
                LaserWeeklyMaterialOrderProgress.objects.update_or_create(
                    plan_start_date=plan_start_date, material=material, required_date=required_date, supplier=supplier, is_manual=False,
                    defaults={'delivery_date': delivery_date, 'required_sheets': required_sheets, 'lot_multiple': lot_multiple, 'required_lots': required_lots, 'order_lots': order_lots, 'order_sheets': order_sheets_val},
                )
                saved_count += 1
        return Response({'saved_count': saved_count})



    @action(detail=False, methods=['post'], url_path='material-order-reset')
    def reset_material_order_approval(self, request):
        """指定した注文書期間に紐づく材料発注承認と保存PDFをリセットする。"""
        if not (request.user.is_superuser or request.user.username == 'admin'):
            return Response({'detail': 'adminだけ承認リセットできます。'}, status=status.HTTP_403_FORBIDDEN)

        try:
            plan_start_date = datetime.strptime(request.data['start_date'], '%Y-%m-%d').date()
            lock_start_date = datetime.strptime(request.data['lock_start_date'], '%Y-%m-%d').date()
            lock_end_date = datetime.strptime(request.data['lock_end_date'], '%Y-%m-%d').date()
            if lock_end_date < lock_start_date:
                raise ValueError
        except (KeyError, TypeError, ValueError):
            return Response({'detail': '注文書期間を正しく指定してください。'}, status=status.HTTP_400_BAD_REQUEST)

        approvals = list(ApprovalRequest.objects.filter(
            route_config__item_key='laser_material_order',
            context__start_date=plan_start_date.isoformat(),
            context__lock_start_date=lock_start_date.isoformat(),
            context__lock_end_date=lock_end_date.isoformat(),
        ))
        media_root = Path(settings.MEDIA_ROOT).resolve()
        deleted_files = []
        for approval in approvals:
            context = approval.context or {}
            file_infos = []
            for file_group in (
                context.get('material_order_pdf_files', {}),
                context.get('material_order_adjustment_pdf_files', {}),
            ):
                file_infos.extend(file_group.values())
            for adjustment in context.get('material_order_adjustments', {}).values():
                if isinstance(adjustment, dict) and isinstance(adjustment.get('file'), dict):
                    file_infos.append(adjustment['file'])
            for info in file_infos:
                if not isinstance(info, dict):
                    continue
                relative_path = info.get('path')
                if not relative_path:
                    continue
                file_path = (media_root / relative_path).resolve()
                if str(file_path).startswith(str(media_root)) and file_path.exists():
                    file_path.unlink()
                    deleted_files.append(file_path.name)

        deleted_count, deleted_detail = ApprovalRequest.objects.filter(
            id__in=[approval.id for approval in approvals]
        ).delete()
        return Response({
            'deleted_count': deleted_count,
            'deleted_detail': deleted_detail,
            'deleted_files': deleted_files,
        })

    @action(detail=False, methods=['post'], url_path='material-order-send')
    def send_material_order(self, request):
        """承認済み材料注文書を仕入先別にメール送信する。"""
        try:
            plan_start_date = datetime.strptime(request.data['start_date'], '%Y-%m-%d').date()
        except (KeyError, TypeError, ValueError):
            return Response({'detail': 'start_date is required (YYYY-MM-DD)'}, status=status.HTTP_400_BAD_REQUEST)

        supplier = request.data.get('supplier')
        if supplier not in MATERIAL_ORDER_SUPPLIER_CODES:
            return Response({'detail': '仕入先を指定してください。'}, status=status.HTTP_400_BAD_REQUEST)
        lock_start_date = request.data.get('lock_start_date')
        lock_end_date = request.data.get('lock_end_date')
        try:
            if lock_start_date and lock_end_date:
                lock_start_date = datetime.strptime(lock_start_date, '%Y-%m-%d').date()
                lock_end_date = datetime.strptime(lock_end_date, '%Y-%m-%d').date()
                if lock_end_date < lock_start_date:
                    raise ValueError
        except ValueError:
            return Response({'detail': '注文書期間を正しく指定してください。'}, status=status.HTTP_400_BAD_REQUEST)

        supplier_code = MATERIAL_ORDER_SUPPLIER_CODES[supplier]
        try:
            order_supplier = Supplier.objects.get(supplier_code=supplier_code)
        except Supplier.DoesNotExist:
            return Response({'detail': f'仕入先マスタに発注先コード {supplier_code} を登録してください。'}, status=status.HTTP_400_BAD_REQUEST)
        if not order_supplier.order_email:
            return Response({'detail': f'{order_supplier.supplier_name} の送信メールアドレスを仕入先マスタに登録してください。'}, status=status.HTTP_400_BAD_REQUEST)

        approval_filter = {
            'route_config__item_key': 'laser_material_order',
            'context__start_date': plan_start_date.isoformat(),
            'context__supplier': supplier,
        }
        if lock_start_date and lock_end_date:
            approval_filter['context__lock_start_date'] = lock_start_date.isoformat()
            approval_filter['context__lock_end_date'] = lock_end_date.isoformat()
        approval = ApprovalRequest.objects.filter(**approval_filter).order_by('-updated_at').first()
        if not approval:
            return Response({'detail': '材料発注の承認申請が見つかりません。'}, status=status.HTTP_400_BAD_REQUEST)
        if approval.status not in ('approved', 'sent'):
            return Response({'detail': '承認済みの注文書だけ送信できます。'}, status=status.HTTP_400_BAD_REQUEST)

        context = approval.context or {}
        saved_files = context.get('material_order_pdf_files') or {}
        file_info = saved_files.get(supplier)
        if not isinstance(file_info, dict) or not file_info.get('path'):
            return Response({'detail': f'{order_supplier.supplier_name} の注文書PDFを先に作成してください。'}, status=status.HTTP_400_BAD_REQUEST)

        media_root = Path(settings.MEDIA_ROOT).resolve()
        file_path = (media_root / file_info['path']).resolve()
        if not str(file_path).startswith(str(media_root)) or not file_path.exists():
            return Response({'detail': '保存済みPDFファイルが見つかりません。注文書を再作成してください。'}, status=status.HTTP_400_BAD_REQUEST)

        start_label = context.get('lock_start_date') or ''
        end_label = context.get('lock_end_date') or ''
        subject = f'材料注文書 {start_label}～{end_label}' if start_label and end_label else '材料注文書'
        email_config = (
            LaserMaterialOrderEmailConfig.objects
            .prefetch_related('cc_users')
            .filter(supplier=supplier)
            .first()
        )
        cc_emails = [user.email for user in email_config.cc_users.all() if user.email] if email_config else []
        body = append_material_order_reply_notice(
            render_material_order_email_body(
                email_config.body if email_config else DEFAULT_MATERIAL_ORDER_EMAIL_BODY,
                order_supplier,
                start_label,
                end_label,
            ),
            cc_emails,
        )
        result = EmailService().send_email_with_attachment(
            to_emails=[order_supplier.order_email],
            cc_emails=cc_emails,
            subject=subject,
            body=body,
            attachment_data=BytesIO(file_path.read_bytes()),
            attachment_filename=file_info.get('stored_filename') or file_path.name,
            user_id=request.user.id,
        )
        if not result.get('success'):
            return Response({'detail': result.get('message') or 'メール送信に失敗しました。'}, status=status.HTTP_400_BAD_REQUEST)

        sent_files = {**(context.get('material_order_sent_files') or {})}
        sent_files[supplier] = {
            'sent_at': datetime.now().isoformat(timespec='seconds'),
            'to_email': order_supplier.order_email,
            'cc_emails': cc_emails,
            'filename': file_info.get('stored_filename') or file_path.name,
        }
        context = {**context, 'material_order_sent_files': sent_files}
        approval.context = context
        update_fields = ['context', 'updated_at']
        if supplier in sent_files:
            approval.status = 'sent'
            approval.current_stage = 'completed'
            update_fields.extend(['status', 'current_stage'])
        approval.save(update_fields=update_fields)
        return Response(ApprovalRequestSerializer(approval).data)

    @action(detail=False, methods=['post'], url_path='material-order-adjustment-save')
    def save_material_order_adjustment(self, request):
        """納期調整後の注文書PDFを元注文書とは別名で保存する。"""
        try:
            plan_start_date = datetime.strptime(request.data['start_date'], '%Y-%m-%d').date()
            lock_start_date = datetime.strptime(request.data['lock_start_date'], '%Y-%m-%d').date()
            lock_end_date = datetime.strptime(request.data['lock_end_date'], '%Y-%m-%d').date()
            if lock_end_date < lock_start_date:
                raise ValueError
        except (KeyError, TypeError, ValueError):
            return Response({'detail': '納期調整期間を正しく指定してください。'}, status=status.HTTP_400_BAD_REQUEST)

        supplier = request.data.get('supplier')
        if supplier not in MATERIAL_ORDER_SUPPLIER_CODES:
            return Response({'detail': '仕入先を指定してください。'}, status=status.HTTP_400_BAD_REQUEST)

        approval = ApprovalRequest.objects.filter(
            route_config__item_key='laser_material_order',
            context__start_date=plan_start_date.isoformat(),
            context__supplier=supplier,
            context__lock_start_date=lock_start_date.isoformat(),
            context__lock_end_date=lock_end_date.isoformat(),
        ).order_by('-updated_at').first()
        if not approval:
            return Response({'detail': '納期調整対象の注文書が見つかりません。'}, status=status.HTTP_400_BAD_REQUEST)

        context = approval.context or {}
        adjustment = (context.get('material_order_adjustments') or {}).get(supplier) or {}
        if not adjustment.get('editing'):
            return Response({'detail': '先に納期調整を開始してください。'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            saved_file = self._save_material_order_pdf_file(
                plan_start_date,
                lock_start_date,
                lock_end_date,
                supplier,
                filename_prefix='納期変更_laser_material_order',
                delete_old=False,
            )
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        adjustments = {**(context.get('material_order_adjustments') or {})}
        adjustments[supplier] = {
            **adjustment,
            'editing': False,
            'saved_at': datetime.now().isoformat(timespec='seconds'),
            'saved_by': request.user.id,
            'file': saved_file,
        }
        adjustment_files = {**(context.get('material_order_adjustment_pdf_files') or {})}
        adjustment_files[supplier] = saved_file
        approval.context = {
            **context,
            'material_order_adjustments': adjustments,
            'material_order_adjustment_pdf_files': adjustment_files,
        }
        approval.save(update_fields=['context', 'updated_at'])
        return Response({
            'approval': ApprovalRequestSerializer(approval).data,
            'file': saved_file,
        })

    @action(detail=False, methods=['get'], url_path='material-order-excel')
    def material_order_excel(self, request):
        try:
            plan_start_date = datetime.strptime(request.query_params['plan_start_date'], '%Y-%m-%d').date()
            export_start_date = datetime.strptime(request.query_params['start_date'], '%Y-%m-%d').date()
            export_end_date = datetime.strptime(request.query_params['end_date'], '%Y-%m-%d').date()
            supplier = request.query_params['supplier']
            supplier_code = MATERIAL_ORDER_SUPPLIER_CODES[supplier]
            if export_end_date < export_start_date:
                raise ValueError
        except (KeyError, ValueError):
            return Response({'detail': '出力条件が不正です。'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            order_supplier = Supplier.objects.get(supplier_code=supplier_code)
        except Supplier.DoesNotExist:
            return Response({'detail': f'仕入先マスタに発注先コード {supplier_code} を登録してください。'}, status=status.HTTP_400_BAD_REQUEST)

        supplier_name = order_supplier.supplier_name
        orders = list(LaserWeeklyMaterialOrderProgress.objects.filter(
            supplier=supplier, delivery_date__range=(export_start_date, export_end_date),
        ).filter(
            Q(plan_start_date=plan_start_date, is_manual=False) | Q(is_manual=True),
        ).filter(
            Q(order_lots__gt=0) | Q(order_sheets__gt=0),
        ).select_related('material').order_by('delivery_date', 'material__product_code'))
        if not orders:
            return Response({'detail': '出力対象の発注がありません。'}, status=status.HTTP_400_BAD_REQUEST)
        delivery_dates = []
        current_date = export_start_date
        while current_date <= export_end_date:
            delivery_dates.append(current_date)
            current_date += timedelta(days=1)
        by_material = defaultdict(list)
        for order in orders:
            by_material[order.material_id].append(order)

        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = supplier_name
        worksheet.sheet_view.showGridLines = False
        last_column = 6 + len(delivery_dates)
        thin = Side('thin')
        medium = Side('medium')
        border = Border(left=thin, right=thin, top=thin, bottom=thin)

        def set_range_outline(min_row, max_row, min_column, max_column, left_side=thin, right_side=thin):
            """結合セルを含む見出し範囲の外周罫線を欠けずに設定する。"""
            for row in range(min_row, max_row + 1):
                for column in range(min_column, max_column + 1):
                    cell = worksheet.cell(row=row, column=column)
                    cell.border = Border(
                        left=left_side if column == min_column else None,
                        right=right_side if column == max_column else None,
                        top=thin if row == min_row else None,
                        bottom=thin if row == max_row else None,
                    )
        worksheet.merge_cells(start_row=1, start_column=1, end_row=1, end_column=last_column)
        title = worksheet.cell(row=1, column=1, value='材 料 注 文 書')
        title.font = Font(name='MS PMincho', bold=True, size=20)
        title.alignment = Alignment(horizontal='center', vertical='center')
        worksheet.merge_cells(start_row=2, start_column=max(1, last_column - 1), end_row=2, end_column=last_column)
        issue_date = worksheet.cell(row=2, column=max(1, last_column - 1), value=f'{datetime.now():%Y/%m/%d}')
        issue_date.font = Font(name='MS PMincho', size=12)
        issue_date.alignment = Alignment(horizontal='right')
        worksheet.merge_cells(start_row=3, start_column=1, end_row=3, end_column=3)
        recipient = worksheet.cell(row=3, column=1, value=f'{supplier_name} 御中')
        recipient.font = Font(name='MS PMincho', bold=True, size=14)
        recipient.alignment = Alignment(horizontal='center')
        worksheet.merge_cells(start_row=4, start_column=1, end_row=4, end_column=3)
        contact_details = []
        if order_supplier.contact_person:
            contact_details.append(f'{order_supplier.contact_person} 様')
        if order_supplier.phone_number:
            contact_details.append(f'TEL: {order_supplier.phone_number}')
        contact = worksheet.cell(row=4, column=1, value='  '.join(contact_details))
        contact.font = Font(name='MS PMincho', size=11)
        contact.alignment = Alignment(horizontal='center')
        approval_start = max(7, last_column - 2)
        for column, label in enumerate(['承認', '確認', '作成'], approval_start):
            cell = worksheet.cell(row=3, column=column, value=label)
            cell.font = Font(name='MS PMincho', size=10)
            cell.border = border
            cell.alignment = Alignment(horizontal='center', vertical='center')
            cell = worksheet.cell(row=4, column=column, value='')
            cell.border = border
            cell.alignment = Alignment(horizontal='center', vertical='center')
        worksheet.merge_cells(start_row=5, start_column=approval_start, end_row=5, end_column=approval_start + 2)
        company_name = worksheet.cell(row=5, column=approval_start, value='ダイソウ工業株式会社')
        company_name.font = Font(name='MS PMincho', size=11)
        company_name.alignment = Alignment(horizontal='center', vertical='center')

        headers = ['№', '発注コード', '材質', '材寸', '発注単位', '発注量\n（合計）']
        header_fill = PatternFill('solid', fgColor='FFFFFF')
        for column, header in enumerate(headers, 1):
            worksheet.merge_cells(start_row=6, start_column=column, end_row=7, end_column=column)
            cell = worksheet.cell(row=6, column=column, value=header)
            cell.font = Font(name='MS PMincho', bold=True, size=12)
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
            set_range_outline(6, 7, column, column, right_side=medium if column == 6 else thin)
        worksheet.merge_cells(start_row=6, start_column=7, end_row=6, end_column=last_column)
        delivery_header = worksheet.cell(row=6, column=7, value='納期')
        delivery_header.font = Font(name='MS PMincho', bold=True, size=12)
        delivery_header.fill = header_fill
        delivery_header.alignment = Alignment(horizontal='center', vertical='center')
        set_range_outline(6, 6, 7, last_column, left_side=medium)
        for column, delivery_date in enumerate(delivery_dates, 7):
            cell = worksheet.cell(row=7, column=column, value=f'{delivery_date.month}/{delivery_date.day}')
            cell.font = Font(name='MS PMincho', bold=True, size=10)
            cell.fill = header_fill
            cell.border = Border(left=medium if column == 7 else thin, right=thin, top=thin, bottom=thin)
            cell.alignment = Alignment(horizontal='center', vertical='center')

        sorted_materials = sorted(by_material.values(), key=lambda items: items[0].material.product_code)
        daily_total_lots = defaultdict(int)
        daily_total_weight = defaultdict(Decimal)
        for index, material_orders in enumerate(sorted_materials, 1):
            material = material_orders[0].material
            parts = material.product_code.split(maxsplit=1)
            order_by_date = {}
            for order in material_orders:
                prev = order_by_date.get(order.delivery_date, (0, 0))
                order_by_date[order.delivery_date] = (prev[0] + order.order_lots, prev[1] + order.order_sheets)
            lot_multiple = material_orders[0].lot_multiple
            sheet_weight_kg = Decimal(0)
            if material.specific_gravity and material.size_length and material.size_width and material.size_thickness:
                sheet_weight_kg = material.specific_gravity * material.size_length * material.size_width * material.size_thickness / Decimal('1000000')
            total_lots_all = sum(order.order_lots for order in material_orders)
            total_sheets_all = sum(order.order_sheets for order in material_orders)
            total_label = str(total_lots_all)
            if total_sheets_all:
                total_label += f'+{total_sheets_all}枚'
            values = [index, 'SO1', parts[0], parts[1] if len(parts) > 1 else '', f'{lot_multiple}枚', total_label]
            for day in delivery_dates:
                lots, sheets = order_by_date.get(day, (0, 0))
                if lots or sheets:
                    cell_val = str(lots) if lots else ''
                    if sheets:
                        cell_val += f'+{sheets}枚' if cell_val else f'{sheets}枚'
                    values.append(cell_val)
                else:
                    values.append('')
            for column, value in enumerate(values, 1):
                cell = worksheet.cell(row=7 + index, column=column, value=value)
                cell.font = Font(name='MS PMincho', size=11)
                cell.border = Border(
                    left=medium if column == 7 else thin,
                    right=medium if column == 6 else thin,
                    top=thin,
                    bottom=thin,
                )
                cell.alignment = Alignment(horizontal='center' if column != 4 else 'left', vertical='center')
            worksheet.row_dimensions[7 + index].height = 24
            for day in delivery_dates:
                lots, sheets = order_by_date.get(day, (0, 0))
                total_day_sheets = lots * lot_multiple + sheets
                if total_day_sheets:
                    daily_total_lots[day] += lots
                    daily_total_weight[day] += Decimal(total_day_sheets) * sheet_weight_kg / Decimal('1000')
        summary_start = 7 + len(sorted_materials) + 1
        for label_row, label, get_value in [
            (summary_start, '発注量', lambda d: daily_total_lots.get(d, '')),
            (summary_start + 1, '目安重量t', lambda d: float(daily_total_weight.get(d, Decimal(0)).quantize(Decimal('0.01'))) if daily_total_weight.get(d) else ''),
        ]:
            worksheet.merge_cells(start_row=label_row, start_column=5, end_row=label_row, end_column=6)
            label_cell = worksheet.cell(row=label_row, column=5, value=label)
            label_cell.font = Font(name='MS PMincho', bold=True, size=10)
            label_cell.border = Border(left=thin, right=medium, top=thin, bottom=thin)
            label_cell.alignment = Alignment(horizontal='center', vertical='center')
            worksheet.cell(row=label_row, column=6).border = Border(right=medium, top=thin, bottom=thin)
            for col_idx, day in enumerate(delivery_dates, 7):
                val = get_value(day)
                cell = worksheet.cell(row=label_row, column=col_idx, value=val)
                cell.font = Font(name='MS PMincho', size=10)
                cell.border = Border(left=medium if col_idx == 7 else thin, right=thin, top=thin, bottom=thin)
                cell.alignment = Alignment(horizontal='center', vertical='center')
            worksheet.row_dimensions[label_row].height = 24
        widths = [6, 12, 14, 24, 12, 10] + [9] * len(delivery_dates)
        for column, width in enumerate(widths, 1):
            worksheet.column_dimensions[get_column_letter(column)].width = width
        worksheet.row_dimensions[1].height = 26
        worksheet.row_dimensions[3].height = 19
        worksheet.row_dimensions[4].height = 22
        worksheet.row_dimensions[6].height = 19
        worksheet.row_dimensions[7].height = 18
        worksheet.freeze_panes = 'A8'
        output = BytesIO()
        workbook.save(output)
        output.seek(0)
        filename = f'材料注文書_{supplier_name}_{plan_start_date.isoformat()}.xlsx'
        return FileResponse(output, as_attachment=True, filename=filename)

    @action(detail=False, methods=['get'], url_path='material-order-pdf')
    def material_order_pdf(self, request):
        try:
            plan_start_date = datetime.strptime(request.query_params['plan_start_date'], '%Y-%m-%d').date()
            export_start_date = datetime.strptime(request.query_params['start_date'], '%Y-%m-%d').date()
            export_end_date = datetime.strptime(request.query_params['end_date'], '%Y-%m-%d').date()
            supplier = request.query_params['supplier']
            if export_end_date < export_start_date or supplier not in MATERIAL_ORDER_SUPPLIER_CODES:
                raise ValueError
        except (KeyError, ValueError):
            return Response({'detail': '出力条件が不正です。'}, status=status.HTTP_400_BAD_REQUEST)

        approval = ApprovalRequest.objects.filter(
            route_config__item_key='laser_material_order',
            context__start_date=plan_start_date.isoformat(),
            context__lock_start_date=export_start_date.isoformat(),
            context__lock_end_date=export_end_date.isoformat(),
            context__supplier=supplier,
        ).order_by('-updated_at').first()
        if not approval:
            # BOSS承認済フォールバック: 承認履歴がなくても、保存済み注文書は固定命名規則で参照できる。
            filename = (
                f'laser_material_order_{export_start_date:%Y%m%d}_'
                f'{export_end_date:%Y%m%d}_{supplier.lower()}.pdf'
            )
            media_root = Path(settings.MEDIA_ROOT).resolve()
            file_path = (media_root / 'approval_material_orders' / filename).resolve()
            if not str(file_path).startswith(str(media_root)) or not file_path.exists():
                return Response({'detail': '指定期間の保存済み注文書が見つかりません。'}, status=status.HTTP_400_BAD_REQUEST)
            response = FileResponse(file_path.open('rb'), content_type='application/pdf')
            response['Content-Disposition'] = f"inline; filename*=UTF-8''{quote(filename)}"
            return response

        saved_files = (approval.context or {}).get('material_order_pdf_files') or {}
        file_info = saved_files.get(supplier)
        if not isinstance(file_info, dict) or not file_info.get('path'):
            return Response({'detail': '保存済みPDFがありません。注文書作成を先に実行してください。'}, status=status.HTTP_400_BAD_REQUEST)

        latest_step_at = approval.steps.filter(action__in=['confirmed', 'approved']).order_by('-acted_at').values_list('acted_at', flat=True).first()
        try:
            saved_at = datetime.fromisoformat(file_info.get('saved_at')) if file_info.get('saved_at') else None
        except (TypeError, ValueError):
            saved_at = None
        if approval.status in ('created', 'reviewing', 'approved', 'rejected') and latest_step_at and (not saved_at or latest_step_at > saved_at):
            saved_file = self._save_material_order_pdf_file(plan_start_date, export_start_date, export_end_date, supplier)
            saved_files = {**saved_files, supplier: saved_file}
            approval.context = {
                **(approval.context or {}),
                'material_order_pdf_files': saved_files,
                'material_order_pdf_saved_at': datetime.now().isoformat(timespec='seconds'),
            }
            approval.save(update_fields=['context', 'updated_at'])
            file_info = saved_file

        media_root = Path(settings.MEDIA_ROOT).resolve()
        file_path = (media_root / file_info['path']).resolve()
        if not str(file_path).startswith(str(media_root)) or not file_path.exists():
            return Response({'detail': '保存済みPDFファイルが見つかりません。注文書を再作成してください。'}, status=status.HTTP_400_BAD_REQUEST)

        filename = file_info.get('stored_filename') or file_path.name
        response = FileResponse(file_path.open('rb'), content_type='application/pdf')
        response['Content-Disposition'] = f"inline; filename*=UTF-8''{quote(filename)}"
        return response

    def _save_material_order_pdf_file(
        self,
        plan_start_date,
        export_start_date,
        export_end_date,
        supplier,
        filename_prefix='laser_material_order',
        delete_old=True,
    ):
        target_dir = Path(settings.MEDIA_ROOT) / 'approval_material_orders'
        target_dir.mkdir(parents=True, exist_ok=True)
        pdf_bytes, generated_filename = self._build_material_order_pdf(plan_start_date, export_start_date, export_end_date, supplier)
        filename = f'{filename_prefix}_{export_start_date:%Y%m%d}_{export_end_date:%Y%m%d}_{supplier.lower()}.pdf'
        old_filename = f'{filename_prefix}_{plan_start_date:%Y%m%d}_{export_start_date:%Y%m%d}_{export_end_date:%Y%m%d}_{supplier.lower()}.pdf'
        old_path = target_dir / old_filename
        if delete_old and old_path.exists() and old_path.name != filename:
            old_path.unlink()
        target_path = target_dir / filename
        target_path.write_bytes(pdf_bytes)
        relative_path = target_path.relative_to(Path(settings.MEDIA_ROOT)).as_posix()
        return {
            'filename': generated_filename,
            'stored_filename': filename,
            'path': relative_path,
            'url': f"{settings.MEDIA_URL.rstrip('/')}/{relative_path}",
            'saved_at': datetime.now().isoformat(timespec='seconds'),
        }

    def _build_material_order_pdf(self, plan_start_date, export_start_date, export_end_date, supplier):
        try:
            supplier_code = MATERIAL_ORDER_SUPPLIER_CODES[supplier]
        except KeyError:
            raise ValueError('出力条件が不正です。')
        try:
            order_supplier = Supplier.objects.get(supplier_code=supplier_code)
        except Supplier.DoesNotExist:
            raise ValueError(f'仕入先マスタに発注先コード {supplier_code} を登録してください。')

        approval = ApprovalRequest.objects.filter(
            route_config__item_key='laser_material_order',
            context__start_date=plan_start_date.isoformat(),
            context__lock_start_date=export_start_date.isoformat(),
            context__lock_end_date=export_end_date.isoformat(),
            context__supplier=supplier,
        ).prefetch_related('steps__user', 'route_config__creator_proxy_users', 'route_config__reviewer1_proxy_users', 'route_config__reviewer2_proxy_users', 'route_config__approver_proxy_users').order_by('-updated_at').first()
        if not approval or approval.status not in ('created', 'reviewing', 'approved', 'rejected', 'sent'):
            raise ValueError('作成済み、差戻し、承認中または承認済みの材料発注のみPDF出力できます。')
        proxy_user_ids_by_stage = {
            stage: set(getattr(approval.route_config, f'{stage}_proxy_users').values_list('id', flat=True))
            for stage in ('creator', 'reviewer1', 'reviewer2', 'approver')
        }

        def stamp_label(user, acted_at=None, is_proxy=False):
            name = user.last_name or user.username
            if is_proxy:
                name = f'{name}（代）'
            date_str = f'{acted_at.month}/{acted_at.day}' if acted_at else ''
            return f'{name}\n{date_str}' if date_str else name

        def approval_step_label(step):
            return stamp_label(
                step.user,
                step.acted_at,
                step.user_id in proxy_user_ids_by_stage.get(step.stage, set()),
            )

        approval_steps = {
            step.stage: approval_step_label(step)
            for step in approval.steps.all()
            if step.action in ('confirmed', 'approved')
        }
        if 'creator' not in approval_steps and approval.creator_id:
            approval_steps['creator'] = stamp_label(approval.creator, approval.created_at)

        orders = list(LaserWeeklyMaterialOrderProgress.objects.filter(
            supplier=supplier, delivery_date__range=(export_start_date, export_end_date),
        ).filter(
            Q(plan_start_date=plan_start_date, is_manual=False) | Q(is_manual=True),
        ).filter(
            Q(order_lots__gt=0) | Q(order_sheets__gt=0),
        ).select_related('material').order_by('delivery_date', 'material__product_code'))
        if not orders:
            raise ValueError('出力対象の発注がありません。')

        delivery_dates = []
        current_date = export_start_date
        while current_date <= export_end_date:
            delivery_dates.append(current_date)
            current_date += timedelta(days=1)

        by_material = defaultdict(list)
        for order in orders:
            by_material[order.material_id].append(order)

        try:
            pdfmetrics.registerFont(UnicodeCIDFont('HeiseiMin-W3'))
            font_name = 'HeiseiMin-W3'
        except Exception:
            font_name = 'Helvetica'

        page_size = landscape(A4)
        page_width, page_height = page_size
        margin = 15 * mm
        output = BytesIO()
        pdf = canvas.Canvas(output, pagesize=page_size)

        def draw_text(x, y, text, size=9, align='left'):
            pdf.setFont(font_name, size)
            value = str(text or '')
            if align == 'center':
                pdf.drawCentredString(x, y, value)
            elif align == 'right':
                pdf.drawRightString(x, y, value)
            else:
                pdf.drawString(x, y, value)

        def draw_cell(x, y, w, h, text='', size=8, align='center', fill=None):
            if fill:
                pdf.setFillColor(fill)
                pdf.rect(x, y - h, w, h, fill=1, stroke=0)
                pdf.setFillColor(colors.black)
            pdf.setLineWidth(0.45)
            pdf.rect(x, y - h, w, h, fill=0, stroke=1)
            if text not in (None, ''):
                lines = str(text).split('\n')
                line_height = size * 1.15
                start_y = y - (h / 2) + ((len(lines) - 1) * line_height / 2) - (size * 0.35)
                for line_index, line in enumerate(lines):
                    draw_text(
                        x + (w / 2 if align == 'center' else w - 2 if align == 'right' else 2),
                        start_y - line_index * line_height,
                        line,
                        size=size,
                        align=align,
                    )

        def order_label(lots, sheets):
            if lots and sheets:
                return f'{lots}+{sheets}枚'
            if lots:
                return str(lots)
            if sheets:
                return f'{sheets}枚'
            return ''

        rows = []
        daily_total_lots = defaultdict(int)
        daily_total_weight = defaultdict(Decimal)
        sorted_materials = sorted(by_material.values(), key=lambda items: items[0].material.product_code)
        for index, material_orders in enumerate(sorted_materials, 1):
            material = material_orders[0].material
            parts = material.product_code.split(maxsplit=1)
            order_by_date = {}
            for order in material_orders:
                prev = order_by_date.get(order.delivery_date, (0, 0))
                order_by_date[order.delivery_date] = (prev[0] + order.order_lots, prev[1] + order.order_sheets)
            lot_multiple = material_orders[0].lot_multiple
            total_lots = sum(order.order_lots for order in material_orders)
            total_sheets = sum(order.order_sheets for order in material_orders)
            sheet_weight_kg = Decimal(0)
            if material.specific_gravity and material.size_length and material.size_width and material.size_thickness:
                sheet_weight_kg = material.specific_gravity * material.size_length * material.size_width * material.size_thickness / Decimal('1000000')
            daily_values = []
            for day in delivery_dates:
                lots, sheets = order_by_date.get(day, (0, 0))
                daily_values.append(order_label(lots, sheets))
                total_day_sheets = lots * lot_multiple + sheets
                if total_day_sheets:
                    daily_total_lots[day] += lots
                    daily_total_weight[day] += Decimal(total_day_sheets) * sheet_weight_kg / Decimal('1000')
            rows.append([
                index,
                'SO1',
                parts[0],
                parts[1] if len(parts) > 1 else '',
                f'{lot_multiple}枚',
                order_label(total_lots, total_sheets),
                *daily_values,
            ])

        fixed_widths = [10 * mm, 28 * mm, 32 * mm, 55 * mm, 28 * mm, 23 * mm]
        daily_width = (page_width - margin * 2 - sum(fixed_widths)) / max(len(delivery_dates), 1)
        widths = fixed_widths + [daily_width] * len(delivery_dates)
        row_height = 8 * mm
        header_top_height = 6 * mm
        header_date_height = 8 * mm
        table_top = page_height - margin - 50 * mm
        rows_per_page = 13

        def draw_header():
            draw_text(page_width / 2, page_height - margin - 5 * mm, '材 料 注 文 書', size=27, align='center')
            draw_text(page_width - margin, page_height - margin - 13 * mm, f'{datetime.now():%Y/%m/%d}', size=13, align='right')
            draw_text(margin, page_height - margin - 22 * mm, f'{order_supplier.supplier_name} 御中', size=19)
            contact = []
            if order_supplier.contact_person:
                contact.append(f'{order_supplier.contact_person} 様')
            if order_supplier.phone_number:
                contact.append(f'TEL: {order_supplier.phone_number}')
            draw_text(margin + 26 * mm, page_height - margin - 31 * mm, '  '.join(contact), size=15)
            stamp_items = [('承認', 'approver')]
            if approval.route_config.reviewer2_enabled:
                stamp_items.extend([('確認②', 'reviewer2'), ('確認①', 'reviewer1')])
            else:
                stamp_items.append(('確認', 'reviewer1'))
            stamp_items.append(('作成', 'creator'))
            stamp_cell_width = 23 * mm
            stamp_x = page_width - margin - stamp_cell_width * len(stamp_items)
            stamp_top = page_height - margin - 18 * mm
            stamp_body_top = page_height - margin - 26 * mm
            for idx, (label, stage) in enumerate(stamp_items):
                x = stamp_x + idx * stamp_cell_width
                draw_cell(x, stamp_top, stamp_cell_width, 8 * mm, label, size=11)
                draw_cell(x, stamp_body_top, stamp_cell_width, 11 * mm, approval_steps.get(stage, ''), size=8)
            draw_text(stamp_x + stamp_cell_width * len(stamp_items), page_height - margin - 43 * mm, 'ダイソウ工業株式会社', size=13, align='right')
            x = margin
            y = table_top
            headers = ['№', '発注コード', '材質', '材寸', '発注単位', '発注量\n（合計）']
            for idx, (width, header) in enumerate(zip(fixed_widths, headers)):
                draw_cell(x, y, width, header_top_height + header_date_height, header, size=13 if idx != 5 else 12, fill=None)
                x += width
            draw_cell(x, y, daily_width * len(delivery_dates), header_top_height, '納期', size=16, fill=None)
            for delivery_date in delivery_dates:
                draw_cell(x, y - header_top_height, daily_width, header_date_height, f'{delivery_date.month}/{delivery_date.day}', size=13, fill=None)
                x += daily_width
            return y - header_top_height - header_date_height

        for page_index, start in enumerate(range(0, len(rows), rows_per_page)):
            if page_index:
                pdf.showPage()
            y = draw_header()
            for row in rows[start:start + rows_per_page]:
                x = margin
                for idx, (width, value) in enumerate(zip(widths, row)):
                    draw_cell(x, y, width, row_height, value, size=12 if idx != 3 else 11, align='left' if idx in (2, 3) else 'center')
                    x += width
                y -= row_height
            if start + rows_per_page >= len(rows):
                for label, values in [
                    ('発注量', [daily_total_lots.get(day, '') for day in delivery_dates]),
                    ('目安重量t', [daily_total_weight.get(day, Decimal(0)).quantize(Decimal('0.01')) if daily_total_weight.get(day) else '' for day in delivery_dates]),
                ]:
                    x = margin + sum(fixed_widths[:4])
                    draw_cell(x, y, sum(fixed_widths[4:6]), row_height, label, size=13, align='center', fill=None)
                    x += sum(fixed_widths[4:6])
                    for width, value in zip(widths[6:], values):
                        draw_cell(x, y, width, row_height, value, size=12)
                        x += width
                    y -= row_height

        pdf.save()
        output.seek(0)
        filename = f'材料注文書_{order_supplier.supplier_name}_{plan_start_date:%Y%m%d}.pdf'
        return output.read(), filename

    @action(detail=False, methods=['get'], url_path='downstream-products')
    def downstream_products(self, request):
        try:
            line_id = int(request.query_params['line_id'])
        except (KeyError, TypeError, ValueError):
            return Response({'detail': 'line_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        backlog_product_ids = LineBacklog.objects.filter(line_id=line_id).values('product_id')
        products = Product.objects.filter(is_line_final_product=True).filter(
            Q(line_id=line_id) | Q(id__in=backlog_product_ids),
        ).order_by('product_code').values('id', 'product_code', 'product_name')
        return Response(list(products))

    @action(detail=False, methods=['post'], url_path='manual-quantities')
    def save_manual_quantities(self, request):
        quantities = request.data.get('quantities', [])
        if not isinstance(quantities, list):
            return Response({'detail': 'quantities must be a list'}, status=status.HTTP_400_BAD_REQUEST)

        target_ids = {item.get('target_id') for item in quantities if item.get('target_id')}
        targets = {target.id: target for target in LaserWeeklyPlanTarget.objects.filter(id__in=target_ids)}
        for item in quantities:
            try:
                target = targets[int(item['target_id'])]
                plan_date = datetime.strptime(item['plan_date'], '%Y-%m-%d').date()
                sheets_decimal = Decimal(str(item['sheets']))
                if sheets_decimal < 0 or sheets_decimal != sheets_decimal.to_integral_value():
                    raise ValueError
                sheets = int(sheets_decimal)
            except (InvalidOperation, KeyError, TypeError, ValueError):
                return Response({'detail': '手動回数の値が不正です。'}, status=status.HTTP_400_BAD_REQUEST)
            LaserWeeklyPlanManualQuantity.objects.update_or_create(
                target=target, plan_date=plan_date, defaults={'sheets': sheets},
            )
        return Response({'saved_count': len(quantities)})

    @action(detail=False, methods=['post'], url_path='pattern-manual-quantities')
    def save_pattern_manual_quantities(self, request):
        quantities = request.data.get('quantities', [])
        if not isinstance(quantities, list):
            return Response({'detail': 'quantities must be a list'}, status=status.HTTP_400_BAD_REQUEST)

        pattern_ids = {item.get('laser_pattern_id') for item in quantities if item.get('laser_pattern_id')}
        patterns = {pattern.id: pattern for pattern in LaserPattern.objects.filter(id__in=pattern_ids)}
        for item in quantities:
            try:
                pattern = patterns[int(item['laser_pattern_id'])]
                plan_date = datetime.strptime(item['plan_date'], '%Y-%m-%d').date()
                sheets_decimal = Decimal(str(item['sheets']))
                if sheets_decimal < 0 or sheets_decimal != sheets_decimal.to_integral_value():
                    raise ValueError
                sheets = int(sheets_decimal)
            except (InvalidOperation, KeyError, TypeError, ValueError):
                return Response({'detail': '手動回数の値が不正です。'}, status=status.HTTP_400_BAD_REQUEST)
            LaserWeeklyPatternManualQuantity.objects.update_or_create(
                laser_pattern=pattern, plan_date=plan_date, defaults={'sheets': sheets},
            )
        progress_values = request.data.get('progress_values', [])
        if progress_values:
            for pv in progress_values:
                try:
                    pattern = patterns.get(int(pv['laser_pattern_id']))
                    if not pattern:
                        continue
                    progress_date = datetime.strptime(pv['progress_date'], '%Y-%m-%d').date()
                    progress = Decimal(str(pv['progress']))
                except (InvalidOperation, KeyError, TypeError, ValueError):
                    continue
                LaserWeeklyPatternDailyProgress.objects.update_or_create(
                    laser_pattern=pattern, progress_date=progress_date,
                    defaults={'progress': progress},
                )

        return Response({'saved_count': len(quantities)})

    @action(detail=False, methods=['post'], url_path='pattern-manual-reset')
    def reset_pattern_manual_quantities(self, request):
        try:
            start_date = datetime.strptime(request.data['start_date'], '%Y-%m-%d').date()
            end_date = datetime.strptime(request.data['end_date'], '%Y-%m-%d').date()
        except (KeyError, ValueError):
            return Response({'detail': 'start_date, end_date (YYYY-MM-DD) が必要です'}, status=status.HTTP_400_BAD_REQUEST)
        if end_date < start_date:
            return Response({'detail': 'end_date は start_date 以降にしてください'}, status=status.HTTP_400_BAD_REQUEST)
        deleted, _ = LaserWeeklyPatternManualQuantity.objects.filter(plan_date__range=(start_date, end_date)).delete()
        return Response({'deleted_count': deleted})

    @action(detail=False, methods=['post'], url_path='save-initial-progress')
    def save_initial_progress(self, request):
        items = request.data.get('items', [])
        if not isinstance(items, list):
            return Response({'detail': 'items must be a list'}, status=status.HTTP_400_BAD_REQUEST)
        for item in items:
            try:
                laser_pattern_id = int(item['laser_pattern_id'])
                week_start_date = datetime.strptime(item['week_start_date'], '%Y-%m-%d').date()
                initial_progress = round(float(item['initial_progress']), 2)
                is_locked = bool(item.get('is_locked', True))
            except (KeyError, TypeError, ValueError):
                return Response({'detail': '期首進度の値が不正です。'}, status=status.HTTP_400_BAD_REQUEST)
            LaserWeeklyPatternInitialProgress.objects.update_or_create(
                laser_pattern_id=laser_pattern_id, week_start_date=week_start_date,
                defaults={'initial_progress': initial_progress, 'is_locked': is_locked},
            )
        return Response({'saved_count': len(items)})

    def _calc_freq_sheets(self, pattern_row, automatic_daily, dates, is_workday_fn=None, field='manual_sheets'):
        freq_type = pattern_row.get('freq_type', 'DAILY')
        if freq_type == 'DAILY':
            return {day: daily[field] for day, daily in automatic_daily.items()}

        sorted_days = [d.isoformat() for d in dates]
        result = {day: 0 for day in sorted_days}

        def _is_biz(d):
            return is_workday_fn(d) if is_workday_fn else d.weekday() < 5

        if freq_type == 'WEEKLY':
            dow = pattern_row.get('freq_day_of_week')
            if dow is None:
                return {day: daily[field] for day, daily in automatic_daily.items()}
            processing_days = [d for d in sorted_days if datetime.strptime(d, '%Y-%m-%d').date().weekday() == dow]
            if not processing_days:
                return result
            for i, proc_day in enumerate(processing_days):
                if i + 1 < len(processing_days):
                    next_proc = processing_days[i + 1]
                    covered = [d for d in sorted_days if proc_day <= d < next_proc]
                else:
                    covered = [d for d in sorted_days if d >= proc_day]
                total = sum(automatic_daily.get(d, {}).get(field, 0) for d in covered)
                result[proc_day] = total

        elif freq_type == 'EVERY_N_DAYS':
            interval = pattern_row.get('freq_interval_days') or 2
            start_date = pattern_row.get('freq_start_date')
            if not start_date:
                return {day: daily[field] for day, daily in automatic_daily.items()}
            for day_str in sorted_days:
                day_date = datetime.strptime(day_str, '%Y-%m-%d').date()
                if day_date < start_date:
                    result[day_str] = automatic_daily.get(day_str, {}).get(field, 0)
            biz_days_from_start = 0
            scan_date = start_date
            first_day = dates[0] if dates else None
            if first_day and scan_date < first_day:
                while scan_date < first_day:
                    scan_date += timedelta(days=1)
                    if _is_biz(scan_date):
                        biz_days_from_start += 1
            processing_indices = set()
            for idx, day_str in enumerate(sorted_days):
                day_date = datetime.strptime(day_str, '%Y-%m-%d').date()
                if day_date < start_date:
                    continue
                if day_date == start_date or (biz_days_from_start % interval == 0):
                    processing_indices.add(idx)
                biz_days_from_start += 1
            proc_list = sorted(processing_indices)
            for pi, idx in enumerate(proc_list):
                if pi + 1 < len(proc_list):
                    next_idx = proc_list[pi + 1]
                else:
                    next_idx = len(sorted_days)
                covered = sorted_days[idx:next_idx]
                total = sum(automatic_daily.get(d, {}).get(field, 0) for d in covered)
                result[sorted_days[idx]] = total

        return result

    def _calc_auto_initial_progress(self, pattern_id, week_start_date):
        prev_start = week_start_date - timedelta(days=7)
        last_day = LaserWeeklyPatternDailyProgress.objects.filter(
            laser_pattern_id=pattern_id,
            progress_date__gte=prev_start,
            progress_date__lt=week_start_date,
        ).order_by('-progress_date').first()
        return float(last_day.progress) if last_day else 0

    def list(self, request):
        try:
            requested_start_date = datetime.strptime(request.query_params['start_date'], '%Y-%m-%d').date()
        except (KeyError, ValueError):
            return Response({'detail': 'start_date is required (YYYY-MM-DD)'}, status=status.HTTP_400_BAD_REQUEST)
        end_date_param = request.query_params.get('end_date')
        if end_date_param:
            try:
                end_date = datetime.strptime(end_date_param, '%Y-%m-%d').date()
            except ValueError:
                return Response({'detail': 'end_date must be YYYY-MM-DD'}, status=status.HTTP_400_BAD_REQUEST)
            if end_date < requested_start_date:
                return Response({'detail': 'end_date must be on or after start_date'}, status=status.HTTP_400_BAD_REQUEST)
            start_date = requested_start_date
            from masters.models import Calendar
            laser_cal = Calendar.objects.filter(calendar_code='reza').first()
            grid_calendar_id = laser_cal.id if laser_cal else _resolve_calendar_id(None)
            grid_is_working = _build_workday_helpers(grid_calendar_id)[0]
            dates = [start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1) if grid_is_working(start_date + timedelta(days=i))]
        else:
            start_date = requested_start_date - timedelta(days=requested_start_date.weekday())
            from masters.models import Calendar
            laser_cal = Calendar.objects.filter(calendar_code='reza').first()
            grid_calendar_id = laser_cal.id if laser_cal else _resolve_calendar_id(None)
            grid_is_working = _build_workday_helpers(grid_calendar_id)[0]
            dates = [start_date + timedelta(days=i) for i in range(28) if grid_is_working(start_date + timedelta(days=i))]
        if not dates:
            return Response({'detail': '稼働日の範囲を指定してください。'}, status=status.HTTP_400_BAD_REQUEST)
        targets = list(LaserWeeklyPlanTarget.objects.filter(is_active=True).select_related('downstream_line', 'product', 'finished_product', 'laser_pattern__equipment__process__line', 'laser_pattern__material', 'laser_pattern__processing_freq_pattern').prefetch_related('laser_pattern__finished_items'))
        manual_map = {
            (item.target_id, item.plan_date): item.sheets
            for item in LaserWeeklyPlanManualQuantity.objects.filter(
                target_id__in=[target.id for target in targets],
                plan_date__range=(dates[0], dates[-1]),
            )
        }
        prev_week_start = start_date - timedelta(days=7)
        pattern_manual_map = {
            (item.laser_pattern_id, item.plan_date): item.sheets
            for item in LaserWeeklyPatternManualQuantity.objects.filter(
                laser_pattern_id__in=[target.laser_pattern_id for target in targets],
                plan_date__range=(prev_week_start, dates[-1]),
            )
        }
        target_demand_dates = {}
        workday_helpers = {}
        for target in targets:
            laser_process = target.laser_pattern.equipment.process
            laser_line_id = laser_process.line_id if laser_process else None
            calendar_id = _resolve_calendar_id(laser_line_id)
            shift_working_days = workday_helpers.setdefault(
                calendar_id,
                _build_workday_helpers(calendar_id),
            )[2]
            prev_dates = [prev_week_start + timedelta(days=i) for i in range(7) if (prev_week_start + timedelta(days=i)).weekday() < 5]
            for day in prev_dates + dates:
                target_demand_dates[(target.id, day)] = shift_working_days(day, target.lead_time_days)

        plan_map, order_map = defaultdict(Decimal), defaultdict(Decimal)
        if targets:
            demand_dates = set(target_demand_dates.values())
            for plan in LinePlan.objects.filter(line_id__in={t.downstream_line_id for t in targets}, product_id__in={t.product_id for t in targets}, plan_date__in=demand_dates):
                plan_map[(plan.line_id, plan.product_id, plan.plan_date)] += Decimal(plan.plan_qty or 0)
            for backlog in LineBacklog.objects.filter(line_id__in={t.downstream_line_id for t in targets}, product_id__in={t.product_id for t in targets}, plan_date__in=demand_dates, sequence_no=0):
                order_map[(backlog.line_id, backlog.product_id, backlog.plan_date)] += Decimal(backlog.order_qty or 0)
        rows, totals, pattern_totals, material_totals = [], defaultdict(Decimal), {}, {}
        for target in targets:
            take = next((x.units_per_shot for x in target.laser_pattern.finished_items.all() if x.finished_product_id == target.finished_product_id), None)
            name = target.laser_pattern.equipment.equipment_name or ''
            machine = 'TK' if '1' in name or '１' in name else 'AJ' if '2' in name or '２' in name else ''
            if not take or take <= 0 or not machine:
                continue
            hours = Decimal(target.laser_pattern.process_time_min or 0) / Decimal(60)
            daily = {}
            for day in dates:
                key = (target.downstream_line_id, target.product_id, target_demand_dates[(target.id, day)])
                qty = plan_map[key] if target.quantity_source == 'PLAN_QTY' else order_map[key]
                raw = (qty / take) if qty > 0 else Decimal(0)
                auto_sheets = float(raw.quantize(Decimal('0.01'), rounding=ROUND_CEILING)) if qty > 0 else 0.0
                manual_sheets = int(raw.to_integral_value(rounding=ROUND_CEILING)) if qty > 0 else 0
                daily[day.isoformat()] = {
                    'demand_qty': str(qty),
                    'automatic_sheets': auto_sheets,
                    'manual_sheets': manual_sheets,
                }
                freq = target.laser_pattern.processing_freq_pattern
                pattern_row = pattern_totals.setdefault(target.laser_pattern_id, {
                    'laser_pattern_id': target.laser_pattern_id,
                    'pattern_no': target.laser_pattern.pattern_no,
                    'thickness': str(target.laser_pattern.material.size_thickness or ''),
                    'machine': machine,
                    'hours_per_sheet': str(hours),
                    'material_id': target.laser_pattern.material_id,
                    'material_code': target.laser_pattern.material.product_code,
                    'material_name': target.laser_pattern.material.product_name,
                    'order_lot_min': target.laser_pattern.material.order_lot_min or 1,
                    'order_lot_multiple': target.laser_pattern.material.order_lot_multiple or 1,
                    'freq_type': freq.frequency_type if freq else 'DAILY',
                    'freq_day_of_week': freq.day_of_week if freq else None,
                    'freq_interval_days': freq.interval_days if freq else None,
                    'freq_start_date': target.laser_pattern.processing_start_date,
                    'calendar_id': calendar_id,
                    'product_codes': set(),
                    'downstream_line_names': set(),
                    'take_qtys': set(),
                    'lead_time_days': set(),
                    'daily': defaultdict(lambda: {
                        'demand_qty': Decimal('0'),
                        'automatic_sheets': 0,
                        'manual_sheets': 0,
                    }),
                })
                pattern_row['downstream_line_names'].add(target.downstream_line.line_name)
                pattern_row['product_codes'].add(target.product.product_code)
                pattern_row['take_qtys'].add(str(take))
                pattern_row['lead_time_days'].add(target.lead_time_days)
                pattern_daily = pattern_row['daily'][day.isoformat()]
                pattern_daily['demand_qty'] += qty
                pattern_daily['automatic_sheets'] += auto_sheets
                pattern_daily['manual_sheets'] += manual_sheets
            rows.append({'id': target.id, 'downstream_line_name': target.downstream_line.line_name, 'product_code': target.product.product_code, 'product_name': target.product.product_name, 'pattern_no': target.laser_pattern.pattern_no, 'take_qty': str(take), 'thickness': str(target.laser_pattern.material.size_thickness or ''), 'machine': machine, 'hours_per_sheet': str(hours), 'lead_time_days': target.lead_time_days, 'quantity_source': target.quantity_source, 'daily': daily})
        pattern_rows = []
        for pattern_row in sorted(pattern_totals.values(), key=lambda item: item['pattern_no']):
            pattern_row['downstream_line_names'] = sorted(pattern_row['downstream_line_names'])
            pattern_row['representative_product_code'] = sorted(pattern_row.pop('product_codes'))[0]
            pattern_row['take_qtys'] = sorted(pattern_row['take_qtys'], key=Decimal)
            pattern_row['lead_time_days'] = sorted(pattern_row['lead_time_days'])
            automatic_daily = pattern_row['daily']
            pattern_row['daily'] = {}
            material_row = material_totals.setdefault(pattern_row['material_id'], {
                'material_id': pattern_row['material_id'],
                'material_code': pattern_row['material_code'],
                'material_name': pattern_row['material_name'],
                'thickness': pattern_row['thickness'],
                'order_lot_min': pattern_row.get('order_lot_min', 1),
                'order_lot_multiple': pattern_row.get('order_lot_multiple', 1),
                'daily': defaultdict(Decimal),
            })
            cal_id = pattern_row.get('calendar_id')
            is_workday_fn = workday_helpers[cal_id][0] if cal_id in workday_helpers else None
            freq_auto = self._calc_freq_sheets(
                pattern_row, automatic_daily, dates, is_workday_fn, field='automatic_sheets',
            )
            for day, daily in automatic_daily.items():
                day_date = datetime.strptime(day, '%Y-%m-%d').date()
                automatic_sheets = freq_auto.get(day, daily['automatic_sheets'])
                saved = pattern_manual_map.get((pattern_row['laser_pattern_id'], day_date))
                if saved is not None:
                    manual_sheets = saved
                else:
                    manual_sheets = int(Decimal(str(automatic_sheets)).to_integral_value(rounding=ROUND_CEILING)) if automatic_sheets > 0 else 0
                pattern_row['daily'][day] = {
                    'demand_qty': str(daily['demand_qty']),
                    'automatic_sheets': automatic_sheets,
                    'manual_sheets': manual_sheets,
                }
                totals[(pattern_row['laser_pattern_id'], day, pattern_row['machine'])] += manual_sheets
                material_row['daily'][day] += Decimal(manual_sheets)
            pattern_rows.append(pattern_row)

        initial_progress_map = {
            item.laser_pattern_id: item
            for item in LaserWeeklyPatternInitialProgress.objects.filter(
                laser_pattern_id__in=[pr['laser_pattern_id'] for pr in pattern_rows],
                week_start_date=start_date,
            )
        }
        for pattern_row in pattern_rows:
            pid = pattern_row['laser_pattern_id']
            saved = initial_progress_map.get(pid)
            if saved and saved.is_locked:
                pattern_row['initial_progress'] = float(saved.initial_progress)
                pattern_row['initial_progress_locked'] = True
            else:
                auto_val = self._calc_auto_initial_progress(pid, start_date)
                pattern_row['initial_progress'] = auto_val
                pattern_row['initial_progress_locked'] = False

        saved_daily_progress = defaultdict(dict)
        for dp in LaserWeeklyPatternDailyProgress.objects.filter(
            laser_pattern_id__in=[pr['laser_pattern_id'] for pr in pattern_rows],
            progress_date__in=dates,
        ):
            saved_daily_progress[dp.laser_pattern_id][dp.progress_date.isoformat()] = float(dp.progress)
        for pattern_row in pattern_rows:
            pattern_row['saved_progress'] = saved_daily_progress.get(pattern_row['laser_pattern_id'], {})

        material_rows = []
        for material_row in sorted(material_totals.values(), key=lambda item: item['material_code']):
            material_row['daily'] = {
                day: int(sheets.to_integral_value(rounding=ROUND_CEILING))
                for day, sheets in material_row['daily'].items()
            }
            material_rows.append(material_row)
        return Response({
            'start_date': start_date.isoformat(),
            'dates': [d.isoformat() for d in dates],
            'rows': rows,
            'pattern_rows': pattern_rows,
            'material_rows': material_rows,
            'pattern_totals': {':'.join(map(str, key)): str(value) for key, value in totals.items()},
        })

    @action(detail=False, methods=['get'], url_path='material-order-summary')
    def material_order_summary(self, request):
        try:
            start_date = datetime.strptime(request.query_params['start_date'], '%Y-%m-%d').date()
            end_date = datetime.strptime(request.query_params['end_date'], '%Y-%m-%d').date()
            if end_date < start_date:
                raise ValueError
        except (KeyError, ValueError):
            return Response({'detail': 'start_date, end_date が必要です (YYYY-MM-DD)'}, status=status.HTTP_400_BAD_REQUEST)

        rows = (
            LaserWeeklyMaterialOrderProgress.objects
            .filter(delivery_date__range=(start_date, end_date))
            .select_related('material')
            .order_by('material__product_code', 'supplier', 'delivery_date')
        )

        dates = []
        d = start_date
        while d <= end_date:
            dates.append(d.isoformat())
            d += timedelta(days=1)

        grouped = defaultdict(lambda: {'daily': defaultdict(lambda: {'order_lots': 0, 'order_sheets': 0, 'total_sheets': 0}), 'ids': defaultdict(list)})
        for row in rows:
            key = (row.material_id, row.supplier)
            day = row.delivery_date.isoformat()
            entry = grouped[key]['daily'][day]
            entry['order_lots'] += row.order_lots
            entry['order_sheets'] += row.order_sheets
            lot_sheets = row.order_lots * row.lot_multiple if row.lot_multiple else 0
            entry['total_sheets'] += lot_sheets + row.order_sheets
            if row.is_manual:
                grouped[key]['ids'][day].append(row.id)
            if 'material_code' not in grouped[key]:
                grouped[key]['material_code'] = row.material.product_code
                grouped[key]['material_name'] = row.material.product_name
                sg = row.material.specific_gravity
                l = row.material.size_length
                w = row.material.size_width
                t = row.material.size_thickness
                if sg and l and w and t:
                    grouped[key]['sheet_weight_kg'] = float(Decimal(str(sg)) * Decimal(str(l)) * Decimal(str(w)) * Decimal(str(t)) / Decimal('1000000'))
                else:
                    grouped[key]['sheet_weight_kg'] = None
                grouped[key]['lot_multiple'] = row.lot_multiple
                grouped[key]['supplier'] = row.supplier
                grouped[key]['supplier_label'] = row.get_supplier_display()

        result_rows = []
        for (material_id, supplier), data in sorted(grouped.items(), key=lambda x: (x[1].get('material_code', ''), x[1].get('supplier', ''))):
            daily = {}
            for day in dates:
                d_entry = data['daily'].get(day)
                if d_entry:
                    daily[day] = {
                        'order_lots': d_entry['order_lots'],
                        'order_sheets': d_entry['order_sheets'],
                        'total_sheets': d_entry['total_sheets'],
                        'weight_kg': round(d_entry['total_sheets'] * data['sheet_weight_kg'], 3) if data['sheet_weight_kg'] else None,
                        'manual_ids': data['ids'].get(day, []),
                    }
                else:
                    daily[day] = {'order_lots': 0, 'order_sheets': 0, 'total_sheets': 0, 'weight_kg': None, 'manual_ids': []}
            result_rows.append({
                'material_id': material_id,
                'material_code': data['material_code'],
                'material_name': data['material_name'],
                'supplier': data['supplier'],
                'supplier_label': data['supplier_label'],
                'lot_multiple': data.get('lot_multiple', 0),
                'sheet_weight_kg': data['sheet_weight_kg'],
                'daily': daily,
            })

        return Response({'dates': dates, 'rows': result_rows})

    @action(detail=False, methods=['post'], url_path='material-order-manual')
    def material_order_manual_create(self, request):
        try:
            material_id = int(request.data['material_id'])
            supplier = request.data['supplier']
            delivery_date = datetime.strptime(request.data['delivery_date'], '%Y-%m-%d').date()
            order_lots = int(request.data.get('order_lots', 0))
            lot_multiple = int(request.data.get('lot_multiple', 0))
            order_sheets = int(request.data.get('order_sheets', 0))
            if order_lots < 0 or lot_multiple < 0 or order_sheets < 0:
                raise ValueError
            if order_lots == 0 and order_sheets == 0:
                return Response({'detail': '発注ロット数または端数枚数を入力してください。'}, status=status.HTTP_400_BAD_REQUEST)
            if supplier not in dict(LaserWeeklyMaterialOrderProgress.SUPPLIER_CHOICES):
                raise ValueError
        except (KeyError, TypeError, ValueError):
            return Response({'detail': '入力値が不正です。'}, status=status.HTTP_400_BAD_REQUEST)

        material = Product.objects.filter(id=material_id).first()
        if not material:
            return Response({'detail': '材料が見つかりません。'}, status=status.HTTP_400_BAD_REQUEST)

        obj, created = LaserWeeklyMaterialOrderProgress.objects.update_or_create(
            material=material, delivery_date=delivery_date, supplier=supplier, is_manual=True,
            defaults={
                'order_lots': order_lots,
                'lot_multiple': lot_multiple,
                'order_sheets': order_sheets,
                'required_sheets': 0,
                'required_lots': 0,
            },
        )
        return Response({'id': obj.id, 'created': created})

    @action(detail=False, methods=['delete'], url_path='material-order-manual/(?P<pk>[0-9]+)')
    def material_order_manual_delete(self, request, pk=None):
        try:
            obj = LaserWeeklyMaterialOrderProgress.objects.get(pk=pk, is_manual=True)
        except LaserWeeklyMaterialOrderProgress.DoesNotExist:
            return Response({'detail': '手動行が見つかりません。'}, status=status.HTTP_404_NOT_FOUND)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
