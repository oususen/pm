"""
工程実時間記録API
"""
from rest_framework import viewsets, status
from rest_framework.response import Response

from .models_process_realtime import ProcessRealtimeRecord
from .serializers_process_realtime import (
    ProcessRealtimeRecordSerializer,
    ProcessRealtimeCreateSerializer,
)


class ProcessRealtimeRecordViewSet(viewsets.ModelViewSet):
    """工程実時間記録ViewSet"""

    queryset = ProcessRealtimeRecord.objects.all()
    serializer_class = ProcessRealtimeRecordSerializer

    def get_queryset(self):
        queryset = ProcessRealtimeRecord.objects.select_related('process', 'product')

        process_id = self.request.query_params.get('process_id')
        if process_id:
            queryset = queryset.filter(process_id=process_id)

        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(timestamp__gte=start_date)
        if end_date:
            queryset = queryset.filter(timestamp__lte=end_date)

        record_type = self.request.query_params.get('record_type')
        if record_type:
            queryset = queryset.filter(record_type=record_type)

        product_id = self.request.query_params.get('product_id')
        if product_id:
            queryset = queryset.filter(product_id=product_id)
        product_code = self.request.query_params.get('product_code')
        if product_code:
            queryset = queryset.filter(product_code=product_code)

        return queryset.order_by('-timestamp')

    def create(self, request, *args, **kwargs):
        serializer = ProcessRealtimeCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        record = serializer.save()
        return Response(ProcessRealtimeRecordSerializer(record).data, status=status.HTTP_201_CREATED)

