import logging
from datetime import datetime

from django.http import HttpResponse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from orders.utils.calendar_utils import get_business_today
from production.services.hokushin_delivery_pdf import (
    EmptyDeliveryError,
    generate_hokushin_delivery_all_pdf,
    generate_hokushin_delivery_pdf,
    preview_hokushin_delivery,
    preview_hokushin_delivery_all,
)


logger = logging.getLogger(__name__)


def _parse_line_id(request):
    line_id = request.query_params.get('line')
    if not line_id:
        return None, Response(
            {'detail': 'line は必須です'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    return int(line_id), None


def _parse_delivery_date(request, key):
    raw = request.query_params.get(key)
    if not raw:
        return None
    try:
        return datetime.strptime(raw, '%Y-%m-%d').date()
    except ValueError:
        raise ValueError(f'{key} の日付形式が不正です (YYYY-MM-DD)')


def _parse_delivery_dates(request):
    try:
        return (
            _parse_delivery_date(request, 'am_delivery_date'),
            _parse_delivery_date(request, 'yoi_delivery_date'),
        ), None
    except ValueError as e:
        return None, Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)


def _build_pdf_response(pdf_bytes, filename):
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    return response


class HokushinDeliveryPDFView(APIView):
    """㈱北進塗装様向け 納品書PDF生成（AM便 + 宵積み 2ページ）"""

    def get(self, request):
        line_id, error_response = _parse_line_id(request)
        if error_response is not None:
            return error_response

        parsed_dates, error_response = _parse_delivery_dates(request)
        if error_response is not None:
            return error_response
        am_date, yoi_date = parsed_dates

        if request.query_params.get('preview') == '1':
            try:
                data = preview_hokushin_delivery(line_id)
            except Exception as e:
                logger.exception('北進塗装納品書プレビューエラー')
                return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            return Response(data)

        try:
            pdf_bytes = generate_hokushin_delivery_pdf(
                line_id,
                am_delivery_date=am_date,
                yoi_delivery_date=yoi_date,
            )
        except EmptyDeliveryError as e:
            return Response(
                {'detail': str(e), 'code': 'EMPTY_DELIVERY'},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            logger.exception('北進塗装納品書PDF生成エラー')
            return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        today = get_business_today()
        return _build_pdf_response(pdf_bytes, f'北進塗装納品書_{today.strftime("%Y%m%d")}.pdf')


class HokushinDeliveryAllPDFView(APIView):
    """㈱北進塗装様向け 納品書PDF（全製品版）"""

    def get(self, request):
        line_id, error_response = _parse_line_id(request)
        if error_response is not None:
            return error_response

        parsed_dates, error_response = _parse_delivery_dates(request)
        if error_response is not None:
            return error_response
        am_date, yoi_date = parsed_dates

        if request.query_params.get('preview') == '1':
            try:
                data = preview_hokushin_delivery_all(line_id)
            except Exception as e:
                logger.exception('北進塗装納品書（全製品）プレビューエラー')
                return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            return Response(data)

        try:
            pdf_bytes = generate_hokushin_delivery_all_pdf(
                line_id,
                am_delivery_date=am_date,
                yoi_delivery_date=yoi_date,
            )
        except Exception as e:
            logger.exception('北進塗装納品書（全製品）PDF生成エラー')
            return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        today = get_business_today()
        return _build_pdf_response(pdf_bytes, f'北進塗装納品書（全製品）_{today.strftime("%Y%m%d")}.pdf')
