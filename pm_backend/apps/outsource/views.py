from io import BytesIO
from datetime import timedelta
from decimal import Decimal

from django.http import HttpResponse
from django.db import models
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, JSONParser
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from masters.models import Calendar
from orders.utils.calendar_utils import subtract_working_days

from .models import (
    Subcontractor, OutsourceItem, OutsourceBOM, OutsourceMaterial,
    OutsourceOrder, OutsourceSplit, MaterialRequirement,
    SubcontractorDelivery, CustomerShipment,
    MaterialStockTransaction, ProductStockTransaction,
    SplitImportLog,
)
from .serializers import (
    SubcontractorSerializer,
    OutsourceMaterialSerializer,
    OutsourceItemSerializer, OutsourceItemListSerializer,
    OutsourceBOMSerializer,
    OutsourceOrderSerializer, OutsourceOrderListSerializer,
    OutsourceSplitSerializer,
    MaterialRequirementSerializer,
    SubcontractorDeliverySerializer,
    CustomerShipmentSerializer,
    MaterialStockTransactionSerializer,
    ProductStockTransactionSerializer,
    SplitImportLogSerializer,
)
from .services.csv_import import import_fb_csv
from .services.excel_export import generate_split_plan_excel
from .services.excel_import import import_split_plan_excel
from .services.bom_explosion import explode_materials_for_order, explode_materials_for_orders
from .services.purchase_order import generate_purchase_orders


def _to_int_qty(value):
    try:
        return int(Decimal(str(value)))
    except Exception:
        return 0


def _record_material_stock_issue(material, qty, reason, ref_type, ref_id):
    if qty == 0:
        return
    MaterialStockTransaction.objects.create(
        material_code=material.material_code,
        material_name=material.material_name,
        qty_change=-abs(int(qty)),
        tx_type='ISSUE',
        tx_date=material.supply_date,
        reason=reason,
        ref_type=ref_type,
        ref_id=ref_id,
    )


def _record_product_stock(item_code, item_name, qty_change, tx_type, tx_date, reason, ref_type, ref_id):
    if qty_change == 0:
        return
    ProductStockTransaction.objects.create(
        item_code=item_code,
        item_name=item_name,
        qty_change=int(qty_change),
        tx_type=tx_type,
        tx_date=tx_date,
        reason=reason,
        ref_type=ref_type,
        ref_id=ref_id,
    )


def _calc_material_due_date(supply_date, supplier=None):
    daiso_calendar = Calendar.objects.filter(calendar_code__iexact='daiso').first()
    supplier_calendar = getattr(supplier, 'calendar', None)
    calc_calendar = supplier_calendar or daiso_calendar
    return subtract_working_days(supply_date, 1, calc_calendar)


class SubcontractorViewSet(viewsets.ModelViewSet):
    queryset = Subcontractor.objects.all()
    serializer_class = SubcontractorSerializer


class OutsourceMaterialViewSet(viewsets.ModelViewSet):
    queryset = OutsourceMaterial.objects.select_related('supplier')
    serializer_class = OutsourceMaterialSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['is_active', 'supplier']
    search_fields = ['material_code', 'material_name']


class OutsourceItemViewSet(viewsets.ModelViewSet):
    queryset = OutsourceItem.objects.select_related('subcontractor').prefetch_related('bom_lines')
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['is_active', 'subcontractor']
    search_fields = ['item_code', 'item_name']

    def get_serializer_class(self):
        if self.action == 'list':
            return OutsourceItemListSerializer
        return OutsourceItemSerializer


class OutsourceBOMViewSet(viewsets.ModelViewSet):
    queryset = OutsourceBOM.objects.select_related('item')
    serializer_class = OutsourceBOMSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['item']


class OutsourceOrderViewSet(viewsets.ModelViewSet):
    queryset = OutsourceOrder.objects.select_related('item').prefetch_related('splits')
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'painting_name']
    search_fields = ['case_no', 'item_code', 'item_name']
    ordering_fields = ['painting_date', 'imported_at', 'status']

    def get_queryset(self):
        qs = super().get_queryset()
        painting_from = self.request.query_params.get('painting_date_from')
        painting_to = self.request.query_params.get('painting_date_to')
        if painting_from:
            qs = qs.filter(painting_date__gte=painting_from)
        if painting_to:
            qs = qs.filter(painting_date__lte=painting_to)
        return qs

    def get_serializer_class(self):
        if self.action == 'list':
            return OutsourceOrderListSerializer
        return OutsourceOrderSerializer

    @action(detail=False, methods=['post'], url_path='import-csv', parser_classes=[MultiPartParser])
    def import_csv(self, request):
        """FB受注CSV取込"""
        file = request.FILES.get('file')
        if not file:
            return Response({'error': 'ファイルが指定されていません'}, status=status.HTTP_400_BAD_REQUEST)

        encoding = request.data.get('encoding', 'shift_jis')
        content = file.read()
        try:
            results = import_fb_csv(content, encoding=encoding)
        except Exception as e:
            return Response(
                {'error': f'CSV取込でエラーが発生しました: {type(e).__name__}: {e}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response({
            'created_count': len(results['created']),
            'skipped_count': len(results['skipped']),
            'error_count': len(results['errors']),
            **results,
        })

    @action(detail=True, methods=['post'], url_path='calculate-constraints')
    def calculate_constraints(self, request, pk=None):
        """制約条件を再計算"""
        order = self.get_object()
        if not order.item and order.item_code:
            matched_item = OutsourceItem.objects.filter(item_code=order.item_code).first()
            if matched_item:
                order.item = matched_item
                order.save(update_fields=['item'])
        if not order.item:
            return Response({'error': '品目マスタが未紐付けです'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            outsource_expand_days = int(request.data.get('outsource_expand_days') or 0)
            internal_approval_days = int(request.data.get('internal_approval_days') or 0)
            business_process_days = int(request.data.get('business_process_days') or 0)
        except (TypeError, ValueError):
            return Response({'error': '発注LT入力は整数で指定してください'}, status=status.HTTP_400_BAD_REQUEST)
        extra_order_lt = outsource_expand_days + internal_approval_days + business_process_days
        order.calculate_constraints(extra_order_lt=extra_order_lt)
        order.save()
        return Response(OutsourceOrderSerializer(order).data)

    @action(detail=False, methods=['post'], url_path='export-excel')
    def export_excel(self, request):
        """外作先展開Excel出力"""
        order_ids = request.data.get('order_ids', [])
        if not order_ids:
            return Response({'error': '案件を選択してください'}, status=status.HTTP_400_BAD_REQUEST)

        output = generate_split_plan_excel(order_ids)

        # ステータス更新
        OutsourceOrder.objects.filter(id__in=order_ids, status='IMPORTED').update(status='SENT_TO_SUB')

        response = HttpResponse(
            output.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="split_plan_template.xlsx"'
        return response

    @action(detail=False, methods=['post'], url_path='import-split-excel', parser_classes=[MultiPartParser])
    def import_split_excel(self, request):
        """分割計画Excel取込（上書き対象がある場合はconfirm必須）"""
        file = request.FILES.get('file')
        if not file:
            return Response({'error': 'ファイルが指定されていません'}, status=status.HTTP_400_BAD_REQUEST)

        confirm = request.data.get('confirm', '') == 'true'
        file_bytes = BytesIO(file.read())

        import traceback
        try:
            if not confirm:
                preview = import_split_plan_excel(file_bytes, dry_run=True)
                if preview.get('has_overwrite'):
                    return Response({
                        'needs_confirm': True,
                        'updated_count': len(preview['updated']),
                        'error_count': len(preview['errors']),
                        'warning_count': len(preview['warnings']),
                        **preview,
                    })
                file_bytes.seek(0)

            results = import_split_plan_excel(file_bytes, dry_run=False)
            if confirm:
                for w in results.get('warnings', []):
                    msg = w.get('message') or ''
                    if '上書きしますか？' in msg:
                        w['message'] = msg.replace('上書きしますか？', '上書きしました')
        except Exception as e:
            traceback.print_exc()
            return Response({'error': f'{type(e).__name__}: {e}'}, status=status.HTTP_400_BAD_REQUEST)

        for item in results['updated']:
            try:
                order = OutsourceOrder.objects.get(case_no=item['case_no'])
                if order.item:
                    bom_result = explode_materials_for_order(order.id)
                    item['material_count'] = bom_result['created_count']
                    if bom_result['errors']:
                        item['bom_errors'] = bom_result['errors']
            except OutsourceOrder.DoesNotExist:
                pass

        username = ''
        if request.user and request.user.is_authenticated:
            username = f'{request.user.last_name} {request.user.first_name}'.strip() or request.user.username

        SplitImportLog.objects.create(
            file_name=file.name or '',
            updated_count=len(results['updated']),
            warning_count=len(results['warnings']),
            error_count=len(results['errors']),
            detail=results,
            imported_by=username,
        )

        return Response({
            'updated_count': len(results['updated']),
            'error_count': len(results['errors']),
            'warning_count': len(results['warnings']),
            **results,
        })

    @action(detail=True, methods=['post'], url_path='explode-materials')
    def explode_materials(self, request, pk=None):
        """BOM展開（材料所要量生成）"""
        order = self.get_object()
        result = explode_materials_for_order(order.id)
        if result['errors']:
            return Response({'errors': result['errors']}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'created_count': result['created_count']})


class OutsourceSplitViewSet(viewsets.ModelViewSet):
    queryset = OutsourceSplit.objects.select_related('order')
    serializer_class = OutsourceSplitSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['order', 'material_supplied', 'process_completed', 'shipped']

    def get_queryset(self):
        qs = super().get_queryset()
        painting_from = self.request.query_params.get('painting_date_from')
        painting_to = self.request.query_params.get('painting_date_to')
        if painting_from:
            qs = qs.filter(order__painting_date__gte=painting_from)
        if painting_to:
            qs = qs.filter(order__painting_date__lte=painting_to)
        return qs

    def perform_update(self, serializer):
        before = serializer.instance
        old_process_date = before.process_date
        old_qty = before.qty

        split = serializer.save()
        # 分割の加工日・数量変更時は、未出庫分の材料所要量を再計算して追従
        if split.process_date != old_process_date or split.qty != old_qty:
            _sync_material_requirements_for_split(split)
        _sync_order_status(split.order)

    def perform_create(self, serializer):
        split = serializer.save()
        _sync_order_status(split.order)


def _sync_material_requirements_for_split(split):
    order = split.order
    if not order.item:
        return
    supply_transport_lt = order.item.subcontractor.transport_lt_supply
    bom_lines = OutsourceBOM.objects.select_related('supplier').filter(item=order.item)
    if not bom_lines.exists():
        return

    for bom in bom_lines:
        required_qty = Decimal(str(split.qty)) * bom.quantity_per
        supply_date = split.process_date - timedelta(days=supply_transport_lt)
        material_due_date_default = _calc_material_due_date(supply_date, getattr(bom, 'supplier', None))

        mat = MaterialRequirement.objects.filter(
            split=split,
            material_code=bom.material_code,
        ).first()
        if not mat:
            MaterialRequirement.objects.create(
                split=split,
                material_code=bom.material_code,
                material_name=bom.material_name,
                supplier_name=bom.supplier_name,
                required_qty=required_qty,
                order_qty=required_qty,
                material_due_date=material_due_date_default,
                supply_date=supply_date,
            )
            continue

        # 出庫済みは履歴保護のため更新しない
        if mat.issued:
            continue

        mat.material_name = bom.material_name
        mat.supplier_name = bom.supplier_name
        mat.required_qty = required_qty
        if not mat.material_due_date:
            mat.material_due_date = material_due_date_default
        mat.supply_date = supply_date
        mat.save(update_fields=['material_name', 'supplier_name', 'required_qty', 'material_due_date', 'supply_date', 'updated_at'])


def _sync_order_status(order):
    """分割の進捗状況からorderステータスを自動更新"""
    splits = order.splits.all()
    if not splits.exists():
        return

    from django.db.models import Sum
    all_shipped = True
    any_active = False
    for s in splits:
        delivered = s.deliveries.aggregate(t=Sum('qty'))['t'] or 0
        shipped = s.shipments.aggregate(t=Sum('qty'))['t'] or 0
        has_ordered = s.material_requirements.filter(ordered=True).exists()
        has_supplied = s.material_requirements.filter(supplied=True).exists()
        if shipped < s.qty:
            all_shipped = False
        if (s.material_supplied or s.process_completed or s.shipped
                or delivered > 0 or shipped > 0
                or has_ordered or has_supplied):
            any_active = True

    new_status = order.status
    if all_shipped:
        new_status = 'COMPLETED'
    elif any_active:
        new_status = 'IN_PROGRESS'

    if new_status != order.status and order.status in ('SPLIT_REGISTERED', 'IN_PROGRESS'):
        order.status = new_status
        order.save(update_fields=['status'])


class MaterialRequirementViewSet(viewsets.ModelViewSet):
    queryset = MaterialRequirement.objects.select_related('split', 'split__order')
    serializer_class = MaterialRequirementSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['supplied', 'ordered', 'shipment_planned', 'issued', 'material_code']
    search_fields = ['material_code', 'material_name', 'split__order__case_no', 'split__order__item_name']
    ordering_fields = ['material_due_date', 'supply_date', 'material_code']

    def get_queryset(self):
        qs = super().get_queryset()
        painting_from = self.request.query_params.get('painting_date_from')
        painting_to = self.request.query_params.get('painting_date_to')
        if painting_from:
            qs = qs.filter(split__order__painting_date__gte=painting_from)
        if painting_to:
            qs = qs.filter(split__order__painting_date__lte=painting_to)
        return qs

    def perform_update(self, serializer):
        before = serializer.instance
        was_issued = before.issued
        before_qty = _to_int_qty(before.supplied_qty or before.required_qty)
        material = serializer.save()
        if material.issued and not material.supplied:
            material.supplied = True
            if not material.supplied_qty:
                material.supplied_qty = material.required_qty
            material.save(update_fields=['supplied', 'supplied_qty', 'updated_at'])
        elif not material.issued and material.supplied:
            material.supplied = False
            material.supplied_qty = 0
            material.save(update_fields=['supplied', 'supplied_qty', 'updated_at'])

        now_issued = material.issued
        if not was_issued and now_issued:
            issue_qty = _to_int_qty(material.supplied_qty or material.required_qty)
            _record_material_stock_issue(
                material,
                issue_qty,
                '材料支給画面で出庫済み',
                'material_requirement_issue',
                material.id,
            )
        elif was_issued and not now_issued:
            # 出庫取消は逆仕訳（在庫戻し）
            MaterialStockTransaction.objects.create(
                material_code=material.material_code,
                material_name=material.material_name,
                qty_change=abs(before_qty),
                tx_type='ADJUST',
                tx_date=material.supply_date,
                reason='出庫取消',
                ref_type='material_requirement_issue_cancel',
                ref_id=material.id,
            )
        _sync_order_status(material.split.order)

    @action(detail=True, methods=['post'], url_path='supply')
    def supply(self, request, pk=None):
        """支給実績登録"""
        material = self.get_object()
        supplied_qty = request.data.get('supplied_qty', material.required_qty)
        material.supplied_qty = supplied_qty
        material.shipment_planned = True
        material.issued = True
        material.supplied = True
        material.save()
        issue_qty = _to_int_qty(material.supplied_qty or material.required_qty)
        _record_material_stock_issue(
            material,
            issue_qty,
            '材料支給画面で出庫済み',
            'material_requirement_supply',
            material.id,
        )
        _sync_order_status(material.split.order)
        return Response(MaterialRequirementSerializer(material).data)

    @action(detail=False, methods=['post'], url_path='purchase-order')
    def purchase_order(self, request):
        """メーカ別注文書Excel出力"""
        material_ids = request.data.get('material_ids', [])
        unsupplied_only = request.data.get('unsupplied_only', False)
        unordered_only = request.data.get('unordered_only', True)

        output, supplier_list = generate_purchase_orders(
            material_ids=material_ids or None,
            unsupplied_only=unsupplied_only,
            unordered_only=unordered_only,
        )
        if not output:
            return Response({'error': '対象材料がありません'}, status=status.HTTP_400_BAD_REQUEST)

        response = HttpResponse(
            output.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="purchase_order.xlsx"'
        return response

    @action(detail=True, methods=['post'], url_path='receive')
    def receive(self, request, pk=None):
        """材料検収（入庫）"""
        material = self.get_object()
        qty = _to_int_qty(request.data.get('received_qty', 0))
        tx_date = request.data.get('tx_date') or material.supply_date
        reason = str(request.data.get('reason', '')).strip() or '材料検収'
        if qty <= 0:
            return Response({'error': '検収数量は1以上を指定してください'}, status=status.HTTP_400_BAD_REQUEST)

        MaterialStockTransaction.objects.create(
            material_code=material.material_code,
            material_name=material.material_name,
            qty_change=qty,
            tx_type='RECEIPT',
            tx_date=tx_date,
            reason=reason,
            ref_type='material_requirement_receipt',
            ref_id=material.id,
        )
        return Response({'ok': True})


class SubcontractorDeliveryViewSet(viewsets.ModelViewSet):
    queryset = SubcontractorDelivery.objects.select_related('split', 'split__order')
    serializer_class = SubcontractorDeliverySerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['split', 'split__order']
    ordering_fields = ['delivery_date']

    def get_queryset(self):
        qs = super().get_queryset()
        painting_from = self.request.query_params.get('painting_date_from')
        painting_to = self.request.query_params.get('painting_date_to')
        if painting_from:
            qs = qs.filter(split__order__painting_date__gte=painting_from)
        if painting_to:
            qs = qs.filter(split__order__painting_date__lte=painting_to)
        return qs

    def perform_create(self, serializer):
        delivery = serializer.save()
        split = delivery.split
        _record_product_stock(
            split.order.item_code,
            split.order.item_name,
            delivery.qty,
            'RECEIPT',
            delivery.delivery_date,
            '外作先納入による入庫',
            'subcontractor_delivery',
            delivery.id,
        )
        total_delivered = sum(d.qty for d in split.deliveries.all())
        if total_delivered >= split.qty:
            split.process_completed = True
            split.save(update_fields=['process_completed', 'updated_at'])
        _sync_order_status(split.order)

    def perform_update(self, serializer):
        before = serializer.instance
        old_qty = before.qty
        old_date = before.delivery_date
        delivery = serializer.save()
        split = delivery.split
        qty_diff = delivery.qty - old_qty
        if qty_diff != 0:
            _record_product_stock(
                split.order.item_code,
                split.order.item_name,
                qty_diff,
                'RECEIPT',
                delivery.delivery_date,
                '外作先納入修正',
                'subcontractor_delivery_update',
                delivery.id,
            )
        elif delivery.delivery_date != old_date:
            _record_product_stock(
                split.order.item_code,
                split.order.item_name,
                0,
                'RECEIPT',
                delivery.delivery_date,
                '外作先納入日修正',
                'subcontractor_delivery_update',
                delivery.id,
            )
        _sync_order_status(split.order)

    def perform_destroy(self, instance):
        split = instance.split
        _record_product_stock(
            split.order.item_code,
            split.order.item_name,
            -instance.qty,
            'ADJUST',
            instance.delivery_date,
            '外作先納入削除',
            'subcontractor_delivery_delete',
            instance.id,
        )
        instance.delete()
        total_delivered = sum(d.qty for d in split.deliveries.all())
        if total_delivered < split.qty:
            split.process_completed = False
            split.save(update_fields=['process_completed', 'updated_at'])
        _sync_order_status(split.order)


class CustomerShipmentViewSet(viewsets.ModelViewSet):
    queryset = CustomerShipment.objects.select_related('split', 'split__order')
    serializer_class = CustomerShipmentSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['split', 'split__order']
    ordering_fields = ['shipment_date']

    def get_queryset(self):
        qs = super().get_queryset()
        painting_from = self.request.query_params.get('painting_date_from')
        painting_to = self.request.query_params.get('painting_date_to')
        if painting_from:
            qs = qs.filter(split__order__painting_date__gte=painting_from)
        if painting_to:
            qs = qs.filter(split__order__painting_date__lte=painting_to)
        return qs

    def perform_create(self, serializer):
        shipment = serializer.save()
        split = shipment.split
        _record_product_stock(
            split.order.item_code,
            split.order.item_name,
            -shipment.qty,
            'SHIP',
            shipment.shipment_date,
            '顧客出荷による出庫',
            'customer_shipment',
            shipment.id,
        )
        total_shipped = sum(s.qty for s in split.shipments.all())
        if total_shipped >= split.qty:
            split.shipped = True
            split.save(update_fields=['shipped', 'updated_at'])
        _sync_order_status(split.order)

    def perform_update(self, serializer):
        before = serializer.instance
        old_qty = before.qty
        shipment = serializer.save()
        split = shipment.split
        qty_diff = shipment.qty - old_qty
        if qty_diff != 0:
            _record_product_stock(
                split.order.item_code,
                split.order.item_name,
                -qty_diff,
                'SHIP',
                shipment.shipment_date,
                '顧客出荷修正',
                'customer_shipment_update',
                shipment.id,
            )
        _sync_order_status(split.order)

    def perform_destroy(self, instance):
        split = instance.split
        _record_product_stock(
            split.order.item_code,
            split.order.item_name,
            instance.qty,
            'ADJUST',
            instance.shipment_date,
            '顧客出荷削除',
            'customer_shipment_delete',
            instance.id,
        )
        instance.delete()
        total_shipped = sum(s.qty for s in split.shipments.all())
        if total_shipped < split.qty:
            split.shipped = False
            split.save(update_fields=['shipped', 'updated_at'])
        _sync_order_status(split.order)


class MaterialStockTransactionViewSet(viewsets.ModelViewSet):
    queryset = MaterialStockTransaction.objects.all()
    serializer_class = MaterialStockTransactionSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['material_code', 'tx_type']
    search_fields = ['material_code', 'material_name', 'reason']
    ordering_fields = ['tx_date', 'created_at', 'material_code']
    http_method_names = ['get', 'post', 'head', 'options']

    @action(detail=False, methods=['get'], url_path='summary')
    def summary(self, request):
        rows = (
            MaterialStockTransaction.objects
            .values('material_code', 'material_name')
            .annotate(stock_qty=models.Sum('qty_change'))
            .order_by('material_code')
        )
        return Response(list(rows))

    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        qty_change = int(data.get('qty_change', 0))
        reason = str(data.get('reason', '')).strip()
        if qty_change == 0:
            return Response({'error': '数量は0以外を指定してください'}, status=status.HTTP_400_BAD_REQUEST)
        if not reason:
            return Response({'error': '棚卸調整理由は必須です'}, status=status.HTTP_400_BAD_REQUEST)
        data['tx_type'] = 'ADJUST'
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ProductStockTransactionViewSet(viewsets.ModelViewSet):
    queryset = ProductStockTransaction.objects.all()
    serializer_class = ProductStockTransactionSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['item_code', 'tx_type']
    search_fields = ['item_code', 'item_name', 'reason']
    ordering_fields = ['tx_date', 'created_at', 'item_code']
    http_method_names = ['get', 'post', 'head', 'options']

    @action(detail=False, methods=['get'], url_path='summary')
    def summary(self, request):
        rows = (
            ProductStockTransaction.objects
            .values('item_code', 'item_name')
            .annotate(stock_qty=models.Sum('qty_change'))
            .order_by('item_code')
        )
        return Response(list(rows))

    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        qty_change = int(data.get('qty_change', 0))
        reason = str(data.get('reason', '')).strip()
        if qty_change == 0:
            return Response({'error': '数量は0以外を指定してください'}, status=status.HTTP_400_BAD_REQUEST)
        if not reason:
            return Response({'error': '棚卸調整理由は必須です'}, status=status.HTTP_400_BAD_REQUEST)
        data['tx_type'] = 'ADJUST'
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class SplitImportLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SplitImportLog.objects.all()
    serializer_class = SplitImportLogSerializer
    filter_backends = [OrderingFilter]
    ordering_fields = ['created_at']
