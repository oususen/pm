# -*- coding: utf-8 -*-
"""
出荷指示書API
"""

from datetime import datetime, date
from django.http import JsonResponse, FileResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import json
import tempfile
import os

from shipping.services.shipping_order_service import ShippingOrderService
from shipping.services.shipping_pdf_generator import generate_shipping_order_pdf


@require_http_methods(["GET"])
def get_available_dates(request):
    """
    出荷指示書を作成可能な日付一覧を取得

    Returns:
        JSON: {
            "dates": ["2026-01-08", "2026-01-07", ...]
        }
    """
    try:
        service = ShippingOrderService()
        dates = service.get_available_dates()

        # date型をstr型に変換
        date_strings = [d.isoformat() for d in dates]

        return JsonResponse({
            "dates": date_strings,
            "count": len(date_strings)
        })

    except Exception as e:
        return JsonResponse({
            "error": str(e)
        }, status=500)


@require_http_methods(["GET"])
def get_shipping_order_data(request, target_date_str):
    """
    指定日の出荷指示書データを取得

    Args:
        target_date_str: YYYY-MM-DD形式の日付文字列

    Returns:
        JSON: {
            "date": "2026-01-08",
            "trip1": [...],
            "trip2": [...],
            "trip3": [...],
            "trip4": [...],
            "trip2_special_annotations": [...],
            "attachment_note": "..."
        }
    """
    try:
        # 日付をパース
        target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()

        # サービスを使用してデータを取得
        service = ShippingOrderService()
        shipping_data = service.get_shipping_data_by_date(target_date)

        # date型をstr型に変換
        shipping_data['date'] = shipping_data['date'].isoformat()

        return JsonResponse(shipping_data)

    except ValueError as e:
        return JsonResponse({
            "error": f"日付形式が不正です: {str(e)}"
        }, status=400)
    except Exception as e:
        return JsonResponse({
            "error": str(e)
        }, status=500)


@require_http_methods(["POST"])
@csrf_exempt
def generate_shipping_order_pdf_api(request):
    """
    出荷指示書PDFを生成してダウンロード

    Request Body:
        {
            "target_date": "2026-01-08",
            "creator_name": "山田太郎"
        }

    Returns:
        PDF file
    """
    try:
        # リクエストボディをパース
        body = json.loads(request.body)
        target_date_str = body.get('target_date')
        creator_name = body.get('creator_name', 'システム')

        if not target_date_str:
            return JsonResponse({
                "error": "target_dateは必須です"
            }, status=400)

        # 日付をパース
        target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()

        # サービスを使用してデータを取得
        service = ShippingOrderService()
        shipping_data = service.get_shipping_data_by_date(target_date)

        # 一時ファイルを作成
        with tempfile.NamedTemporaryFile(
            suffix='.pdf',
            delete=False,
            mode='wb'
        ) as tmp_file:
            temp_path = tmp_file.name

        # PDFを生成
        try:
            pdf_path = generate_shipping_order_pdf(
                shipping_data=shipping_data,
                output_path=temp_path,
                creator_name=creator_name,
                service=service
            )

            # PDFファイルを読み込んでレスポンスとして返す
            with open(pdf_path, 'rb') as pdf_file:
                response = HttpResponse(pdf_file.read(), content_type='application/pdf')
                filename = f"出荷指示書_{target_date_str}.pdf"
                response['Content-Disposition'] = f'attachment; filename="{filename}"'
                return response

        finally:
            # 一時ファイルを削除
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    except ValueError as e:
        return JsonResponse({
            "error": f"日付形式が不正です: {str(e)}"
        }, status=400)
    except json.JSONDecodeError:
        return JsonResponse({
            "error": "JSONの形式が不正です"
        }, status=400)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({
            "error": str(e)
        }, status=500)
