# apps/shipping/views_hirakata_pickup.py
"""枚方集荷依頼書API Views"""

from datetime import date, datetime
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from .services.hirakata_pickup_pdf_service import HirakataPickupPDFService


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
@authentication_classes([])
def generate_hirakata_pickup_pdf(request):
    """
    枚方集荷依頼書PDF生成API

    Request Body:
        {
            "start_date": "2024-01-01",
            "end_date": "2024-01-31"
        }

    Returns:
        PDF file as attachment
    """
    try:
        # リクエストパラメータ取得
        start_date_str = request.data.get('start_date')
        end_date_str = request.data.get('end_date')

        if not start_date_str or not end_date_str:
            return Response(
                {'error': '開始日と終了日を指定してください'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 日付変換
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {'error': '日付形式が正しくありません（YYYY-MM-DD形式で指定してください）'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 日付バリデーション
        if start_date > end_date:
            return Response(
                {'error': '開始日は終了日より前である必要があります'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # PDFサービス生成
        service = HirakataPickupPDFService()

        # PDF生成
        pdf_buffer = service.generate_pickup_request_pdf(start_date, end_date)

        # ファイル名生成
        pickup_range = service.get_pickup_date_range(start_date, end_date)
        if pickup_range:
            pickup_start_date, pickup_end_date = pickup_range
        else:
            pickup_start_date, pickup_end_date = start_date, end_date

        filename = f"枚方集荷依頼書_{pickup_start_date.strftime('%Y%m%d')}_{pickup_end_date.strftime('%Y%m%d')}.pdf"

        # HTTPレスポンス作成
        response = HttpResponse(pdf_buffer.read(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        return response

    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"PDF生成エラー: {error_detail}")
        return Response(
            {'error': f'PDF生成中にエラーが発生しました: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
@authentication_classes([])
def generate_hirakata_pickup_excel(request):
    """
    枚方集荷製品詳細Excel生成API

    Request Body:
        {
            "start_date": "2024-01-01",
            "end_date": "2024-01-31"
        }

    Returns:
        Excel file as attachment
    """
    try:
        # リクエストパラメータ取得
        start_date_str = request.data.get('start_date')
        end_date_str = request.data.get('end_date')

        if not start_date_str or not end_date_str:
            return Response(
                {'error': '開始日と終了日を指定してください'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 日付変換
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {'error': '日付形式が正しくありません（YYYY-MM-DD形式で指定してください）'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 日付バリデーション
        if start_date > end_date:
            return Response(
                {'error': '開始日は終了日より前である必要があります'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # PDFサービス生成
        service = HirakataPickupPDFService()

        # 日別製品リスト取得
        daily_products = service.get_daily_product_list(start_date, end_date)

        if not daily_products:
            return Response(
                {'error': '対象期間に出荷予定の製品がありません'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Excel生成
        excel_buffer = service.generate_product_details_excel(
            start_date,
            end_date,
            daily_products
        )

        # ファイル名生成
        filename = f"枚方集荷製品詳細_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.xlsx"

        # HTTPレスポンス作成
        response = HttpResponse(
            excel_buffer.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        return response

    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"Excel生成エラー: {error_detail}")
        return Response(
            {'error': f'Excel生成中にエラーが発生しました: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def get_hirakata_pickup_date_range(request):
    """
    枚方集荷日期間取得API

    Query Parameters:
        start_date: 開始日 (YYYY-MM-DD)
        end_date: 終了日 (YYYY-MM-DD)

    Returns:
        {
            "pickup_start_date": "2024-01-01",
            "pickup_end_date": "2024-01-31",
            "delivery_start_date": "2024-01-01",
            "delivery_end_date": "2024-01-31"
        }
    """
    try:
        # クエリパラメータ取得
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')

        if not start_date_str or not end_date_str:
            return Response(
                {'error': '開始日と終了日を指定してください'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 日付変換
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {'error': '日付形式が正しくありません（YYYY-MM-DD形式で指定してください）'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 日付バリデーション
        if start_date > end_date:
            return Response(
                {'error': '開始日は終了日より前である必要があります'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # PDFサービス生成
        service = HirakataPickupPDFService()

        # 集荷日レンジ取得
        pickup_range = service.get_pickup_date_range(start_date, end_date)

        if not pickup_range:
            return Response(
                {
                    'pickup_start_date': None,
                    'pickup_end_date': None,
                    'delivery_start_date': start_date.strftime('%Y-%m-%d'),
                    'delivery_end_date': end_date.strftime('%Y-%m-%d'),
                    'message': '対象期間に出荷予定の製品がありません'
                },
                status=status.HTTP_200_OK
            )

        pickup_start_date, pickup_end_date = pickup_range

        return Response({
            'pickup_start_date': pickup_start_date.strftime('%Y-%m-%d'),
            'pickup_end_date': pickup_end_date.strftime('%Y-%m-%d'),
            'delivery_start_date': start_date.strftime('%Y-%m-%d'),
            'delivery_end_date': end_date.strftime('%Y-%m-%d')
        })

    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"集荷日レンジ取得エラー: {error_detail}")
        return Response(
            {'error': f'集荷日レンジ取得中にエラーが発生しました: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def get_hirakata_daily_products(request):
    """
    枚方日別製品リスト取得API

    Query Parameters:
        start_date: 開始日 (YYYY-MM-DD)
        end_date: 終了日 (YYYY-MM-DD)

    Returns:
        {
            "2024-01-01": [
                {
                    "product_code": "PROD001",
                    "product_name": "製品名",
                    "quantity": 100,
                    "container_code": "AMI",
                    "container_name": "アミ容器",
                    "containers_needed": 5
                }
            ]
        }
    """
    try:
        # クエリパラメータ取得
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')

        if not start_date_str or not end_date_str:
            return Response(
                {'error': '開始日と終了日を指定してください'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 日付変換
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {'error': '日付形式が正しくありません（YYYY-MM-DD形式で指定してください）'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 日付バリデーション
        if start_date > end_date:
            return Response(
                {'error': '開始日は終了日より前である必要があります'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # PDFサービス生成
        service = HirakataPickupPDFService()

        # 日別製品リスト取得
        daily_products = service.get_daily_product_list(start_date, end_date)

        # 日付をキーにした辞書に変換（JSON シリアライズ用）
        result = {}
        for delivery_date, products in daily_products.items():
            result[delivery_date.strftime('%Y-%m-%d')] = products

        return Response(result)

    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"日別製品リスト取得エラー: {error_detail}")
        return Response(
            {'error': f'日別製品リスト取得中にエラーが発生しました: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
