import logging
from datetime import datetime

from django.http import HttpResponse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from production.services.floor_shipping_pdf import (
    generate_floor_shipping_lap_pdf,
    generate_floor_shipping_new_pdf,
    generate_floor_shipping_pdf,
)


logger = logging.getLogger(__name__)


def _parse_line_and_range(request):
    line_id = request.query_params.get('line')
    start = request.query_params.get('start_date')
    end = request.query_params.get('end_date')
    if not line_id or not start or not end:
        return None, Response(
            {'detail': 'line, start_date, end_date は必須です'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        start_date = datetime.strptime(start, '%Y-%m-%d').date()
        end_date = datetime.strptime(end, '%Y-%m-%d').date()
        return (int(line_id), start, end, start_date, end_date), None
    except ValueError:
        return None, Response(
            {'detail': '日付形式が不正です (YYYY-MM-DD)'},
            status=status.HTTP_400_BAD_REQUEST,
        )


def _build_pdf_response(pdf_bytes, filename):
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    return response


class FloorShippingPDFView(APIView):
    """フロア配送 8時着/15時着 明細PDF生成"""

    def get(self, request):
        parsed, error_response = _parse_line_and_range(request)
        if error_response is not None:
            return error_response

        line_id, start, end, start_date, end_date = parsed
        try:
            pdf_bytes = generate_floor_shipping_pdf(line_id, start_date, end_date)
        except Exception as e:
            logger.exception('フロア配送PDF生成エラー')
            return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return _build_pdf_response(pdf_bytes, f'フロア配送明細_{start}_{end}.pdf')


class FloorShippingNewPDFView(APIView):
    """新品番ベースのフロア配送明細PDF"""

    def get(self, request):
        parsed, error_response = _parse_line_and_range(request)
        if error_response is not None:
            return error_response

        line_id, start, end, start_date, end_date = parsed
        try:
            pdf_bytes = generate_floor_shipping_new_pdf(line_id, start_date, end_date)
        except Exception as e:
            logger.exception('新配送明細PDF生成エラー')
            return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return _build_pdf_response(pdf_bytes, f'フロア配送明細_新_{start}_{end}.pdf')


class FloorShippingLapPDFView(APIView):
    """フロア配送 ラップ期間用PDF（新旧品番併記、午前/午後各1ページ）"""

    def get(self, request):
        parsed, error_response = _parse_line_and_range(request)
        if error_response is not None:
            return error_response

        line_id, start, end, start_date, end_date = parsed
        try:
            pdf_bytes = generate_floor_shipping_lap_pdf(line_id, start_date, end_date)
        except Exception as e:
            logger.exception('フロア配送ラップPDF生成エラー')
            return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return _build_pdf_response(pdf_bytes, f'フロア配送明細_ラップ_{start}_{end}.pdf')
