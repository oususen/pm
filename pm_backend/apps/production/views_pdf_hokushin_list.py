import logging
from datetime import datetime

from django.http import HttpResponse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from production.services.hokushin_delivery_list_pdf import (
    generate_hokushin_delivery_list_lap_pdf,
    generate_hokushin_delivery_list_new_pdf,
    generate_hokushin_delivery_list_pdf,
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


def _resolve_creator_name(request) -> str:
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return 'システム'

    last_name = (getattr(user, 'last_name', '') or '').strip()
    if last_name:
        return last_name

    username = (user.get_username() or '').strip()
    if username:
        return username

    email = (getattr(user, 'email', '') or '').strip()
    return email or 'システム'


def _build_pdf_response(pdf_bytes, filename):
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    return response


class HokushinDeliveryListPDFView(APIView):
    """北進納入リストPDF生成"""

    def get(self, request):
        parsed, error_response = _parse_line_and_range(request)
        if error_response is not None:
            return error_response

        line_id, start, end, start_date, end_date = parsed
        try:
            pdf_bytes = generate_hokushin_delivery_list_pdf(
                line_id,
                start_date,
                end_date,
                creator_name=_resolve_creator_name(request),
            )
        except Exception as e:
            logger.exception('北進納入リストPDF生成エラー')
            return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return _build_pdf_response(pdf_bytes, f'北進納入リスト_{start}_{end}.pdf')


class HokushinDeliveryListNewPDFView(APIView):
    """新品番ベースの北進納入リストPDF"""

    def get(self, request):
        parsed, error_response = _parse_line_and_range(request)
        if error_response is not None:
            return error_response

        line_id, start, end, start_date, end_date = parsed
        try:
            pdf_bytes = generate_hokushin_delivery_list_new_pdf(
                line_id,
                start_date,
                end_date,
                creator_name=_resolve_creator_name(request),
            )
        except Exception as e:
            logger.exception('新北進納入リストPDF生成エラー')
            return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return _build_pdf_response(pdf_bytes, f'北進納入リスト_新_{start}_{end}.pdf')


class HokushinDeliveryListLapPDFView(APIView):
    """北進納入リスト ラップ期間用PDF（新旧品番併記、午前/午後各1ページ）"""

    def get(self, request):
        parsed, error_response = _parse_line_and_range(request)
        if error_response is not None:
            return error_response

        line_id, start, end, start_date, end_date = parsed
        try:
            pdf_bytes = generate_hokushin_delivery_list_lap_pdf(
                line_id,
                start_date,
                end_date,
                creator_name=_resolve_creator_name(request),
            )
        except Exception as e:
            logger.exception('北進納入リストラップPDF生成エラー')
            return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return _build_pdf_response(pdf_bytes, f'北進納入リスト_ラップ_{start}_{end}.pdf')
