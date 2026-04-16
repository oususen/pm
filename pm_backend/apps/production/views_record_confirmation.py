"""
生産実績確認済みAPI
- POST: 確認済みフラグを登録
- GET: 確認済みフラグを取得（日付範囲・ライン・工程で検索）
"""
from datetime import date

from rest_framework.response import Response
from rest_framework.views import APIView

from production.models_record_confirmation import ProductionRecordConfirmation


class ProductionRecordConfirmationView(APIView):
    """
    GET  /api/production/record-confirmations/?date=YYYY-MM-DD&line_id=X&process_id=Y
         日付範囲: date_from / date_to
    POST /api/production/record-confirmations/
         { work_date, line_id, process_id }
    """

    def get(self, request):
        qs = ProductionRecordConfirmation.objects.select_related(
            'line', 'process', 'confirmed_by'
        )

        # 単一日付
        date_str = request.query_params.get('date')
        if date_str:
            try:
                qs = qs.filter(work_date=date.fromisoformat(date_str))
            except ValueError:
                pass

        # 日付範囲
        date_from = request.query_params.get('date_from')
        if date_from:
            try:
                qs = qs.filter(work_date__gte=date.fromisoformat(date_from))
            except ValueError:
                pass
        date_to = request.query_params.get('date_to')
        if date_to:
            try:
                qs = qs.filter(work_date__lte=date.fromisoformat(date_to))
            except ValueError:
                pass

        line_id = request.query_params.get('line_id')
        if line_id:
            qs = qs.filter(line_id=line_id)

        process_id = request.query_params.get('process_id')
        if process_id:
            qs = qs.filter(process_id=process_id)

        items = []
        for row in qs.order_by('-work_date', 'line_id', 'process_id'):
            items.append({
                'id': row.id,
                'work_date': str(row.work_date),
                'line_id': row.line_id,
                'line_code': row.line.line_code if row.line else '',
                'process_id': row.process_id,
                'process_code': row.process.process_code if row.process else '',
                'process_name': row.process.process_name if row.process else '',
                'confirmed_by': row.confirmed_by_id,
                'confirmed_by_name': (
                    row.confirmed_by.get_full_name() or row.confirmed_by.username
                ) if row.confirmed_by else '',
                'confirmed_at': row.confirmed_at.isoformat() if row.confirmed_at else None,
            })

        return Response({'items': items})

    def post(self, request):
        work_date_str = request.data.get('work_date')
        line_id = request.data.get('line_id')
        process_id = request.data.get('process_id')

        if not work_date_str or not line_id or not process_id:
            return Response(
                {'detail': 'work_date, line_id, process_id は必須です。'},
                status=400,
            )

        try:
            work_date = date.fromisoformat(work_date_str)
        except ValueError:
            return Response({'detail': '日付形式が不正です。'}, status=400)

        obj, created = ProductionRecordConfirmation.objects.update_or_create(
            work_date=work_date,
            line_id=line_id,
            process_id=process_id,
            defaults={'confirmed_by': request.user if request.user.is_authenticated else None},
        )

        return Response({
            'id': obj.id,
            'work_date': str(obj.work_date),
            'line_id': obj.line_id,
            'process_id': obj.process_id,
            'confirmed_at': obj.confirmed_at.isoformat() if obj.confirmed_at else None,
            'created': created,
        })
