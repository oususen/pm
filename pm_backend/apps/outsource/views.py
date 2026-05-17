from io import BytesIO

from django.http import HttpResponse
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, JSONParser
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import (
    Subcontractor, OutsourceItem, OutsourceBOM,
    OutsourceOrder, OutsourceSplit, MaterialRequirement,
    SubcontractorDelivery, CustomerShipment,
)
from .serializers import (
    SubcontractorSerializer,
    OutsourceItemSerializer, OutsourceItemListSerializer,
    OutsourceBOMSerializer,
    OutsourceOrderSerializer, OutsourceOrderListSerializer,
    OutsourceSplitSerializer,
    MaterialRequirementSerializer,
    SubcontractorDeliverySerializer,
    CustomerShipmentSerializer,
)
from .services.csv_import import import_fb_csv
from .services.excel_export import generate_split_plan_excel
from .services.excel_import import import_split_plan_excel
from .services.bom_explosion import explode_materials_for_order, explode_materials_for_orders
from .services.purchase_order import generate_purchase_orders


class SubcontractorViewSet(viewsets.ModelViewSet):
    queryset = Subcontractor.objects.all()
    serializer_class = SubcontractorSerializer


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
    queryset = OutsourceOrder.objects.prefetch_related('splits')
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
        results = import_fb_csv(content, encoding=encoding)

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
        if not order.item:
            return Response({'error': '品目マスタが未紐付けです'}, status=status.HTTP_400_BAD_REQUEST)
        order.calculate_constraints()
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
        """分割計画Excel取込"""
        file = request.FILES.get('file')
        if not file:
            return Response({'error': 'ファイルが指定されていません'}, status=status.HTTP_400_BAD_REQUEST)

        import traceback
        try:
            results = import_split_plan_excel(BytesIO(file.read()))
        except Exception as e:
            traceback.print_exc()
            return Response({'error': f'{type(e).__name__}: {e}'}, status=status.HTTP_400_BAD_REQUEST)

        # 分割計画登録済みの案件に対してBOM展開を実行
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


class MaterialRequirementViewSet(viewsets.ModelViewSet):
    queryset = MaterialRequirement.objects.select_related('split', 'split__order')
    serializer_class = MaterialRequirementSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['supplied', 'material_code']
    ordering_fields = ['supply_date', 'material_code']

    def get_queryset(self):
        qs = super().get_queryset()
        painting_from = self.request.query_params.get('painting_date_from')
        painting_to = self.request.query_params.get('painting_date_to')
        if painting_from:
            qs = qs.filter(split__order__painting_date__gte=painting_from)
        if painting_to:
            qs = qs.filter(split__order__painting_date__lte=painting_to)
        return qs

    @action(detail=True, methods=['post'], url_path='supply')
    def supply(self, request, pk=None):
        """支給実績登録"""
        material = self.get_object()
        supplied_qty = request.data.get('supplied_qty', material.required_qty)
        material.supplied_qty = supplied_qty
        material.supplied = True
        material.save()
        return Response(MaterialRequirementSerializer(material).data)

    @action(detail=False, methods=['post'], url_path='purchase-order')
    def purchase_order(self, request):
        """メーカ別注文書Excel出力"""
        material_ids = request.data.get('material_ids', [])
        unsupplied_only = request.data.get('unsupplied_only', True)

        output, supplier_list = generate_purchase_orders(
            material_ids=material_ids or None,
            unsupplied_only=unsupplied_only,
        )
        if not output:
            return Response({'error': '対象材料がありません'}, status=status.HTTP_400_BAD_REQUEST)

        response = HttpResponse(
            output.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="purchase_order.xlsx"'
        return response


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
        total_delivered = sum(d.qty for d in split.deliveries.all())
        if total_delivered >= split.qty:
            split.process_completed = True
            split.save(update_fields=['process_completed', 'updated_at'])

    def perform_destroy(self, instance):
        split = instance.split
        instance.delete()
        total_delivered = sum(d.qty for d in split.deliveries.all())
        if total_delivered < split.qty:
            split.process_completed = False
            split.save(update_fields=['process_completed', 'updated_at'])


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
        total_shipped = sum(s.qty for s in split.shipments.all())
        if total_shipped >= split.qty:
            split.shipped = True
            split.save(update_fields=['shipped', 'updated_at'])
