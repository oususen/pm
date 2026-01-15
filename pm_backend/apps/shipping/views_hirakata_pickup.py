# apps/shipping/views_hirakata_pickup.py
"""枚方集荷依頼書API Views"""

from datetime import date, datetime
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .services.hirakata_pickup_pdf_service import HirakataPickupPDFService
from .services.email_service import EmailService
from accounts.permissions import HasResourcePermission


def _normalize_email_list(raw_value):
    if not raw_value:
        return []
    if isinstance(raw_value, str):
        candidates = [item.strip() for item in raw_value.split(',')]
    elif isinstance(raw_value, list):
        candidates = [str(item).strip() for item in raw_value]
    else:
        return []

    unique = []
    seen = set()
    for item in candidates:
        if not item or item in seen:
            continue
        unique.append(item)
        seen.add(item)
    return unique


@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated, HasResourcePermission])
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

        # 転送用ディレクトリに保存（レスポンス送信と別に保管）
        try:
            from pathlib import Path
            from django.conf import settings
            base_dir = Path(settings.BASE_DIR).parent
            transfer_dir = base_dir / "output" / "transfer_queue"
            transfer_dir.mkdir(parents=True, exist_ok=True)
            transfer_path = transfer_dir / filename
            pdf_buffer.seek(0)
            transfer_path.write_bytes(pdf_buffer.read())
            pdf_buffer.seek(0)
        except Exception as e:
            print(f"転送用保存エラー: {e}")

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
@permission_classes([IsAuthenticated, HasResourcePermission])
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
@permission_classes([IsAuthenticated, HasResourcePermission])
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
@permission_classes([IsAuthenticated, HasResourcePermission])
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


@api_view(['GET'])
@permission_classes([IsAuthenticated, HasResourcePermission])
def get_hirakata_pickup_contacts(request):
    """
    枚方集荷依頼用の連絡先取得API

    Query Parameters:
        contact_type: 連絡先種別（任意）
    """
    try:
        contact_type = request.query_params.get('contact_type')
        service = EmailService()
        contacts = service.get_contacts(contact_type)
        return Response(contacts)

    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"連絡先取得エラー: {error_detail}")
        return Response(
            {'error': f'連絡先取得中にエラーが発生しました: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated, HasResourcePermission])
def send_hirakata_pickup_email(request):
    """
    枚方集荷依頼書メール送信API

    Request Body:
        {
            "start_date": "2024-01-01",
            "end_date": "2024-01-31",
            "to_emails": ["a@example.com"],
            "cc_emails": ["b@example.com"],
            "subject": "件名",
            "body": "本文"
        }
    """
    try:
        start_date_str = request.data.get('start_date')
        end_date_str = request.data.get('end_date')
        subject = (request.data.get('subject') or '').strip()
        body = (request.data.get('body') or '').strip()
        user_id = request.user.id if request.user.is_authenticated else None

        if not start_date_str or not end_date_str:
            return Response(
                {'error': '開始日と終了日を指定してください'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {'error': '日付形式が正しくありません（YYYY-MM-DD形式で指定してください）'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if start_date > end_date:
            return Response(
                {'error': '開始日は終了日より前である必要があります'},
                status=status.HTTP_400_BAD_REQUEST
            )

        to_emails = _normalize_email_list(request.data.get('to_emails'))
        cc_emails = _normalize_email_list(request.data.get('cc_emails'))

        if not to_emails:
            return Response(
                {'error': '送信先メールアドレスを指定してください'},
                status=status.HTTP_400_BAD_REQUEST
            )

        pdf_service = HirakataPickupPDFService()
        pickup_range = pdf_service.get_pickup_date_range(start_date, end_date)
        if pickup_range:
            pickup_start_date, pickup_end_date = pickup_range
        else:
            pickup_start_date, pickup_end_date = start_date, end_date

        if not subject:
            subject = f"【枚方集荷依頼】{pickup_start_date.strftime('%Y/%m/%d')}～{pickup_end_date.strftime('%Y/%m/%d')}"

        if not body:
            body = (
                "お世話になっております。\n"
                "ダイソウ工業株式会社の辻岡です。\n\n"
                f"{pickup_start_date.strftime('%Y年%m月%d日')}～{pickup_end_date.strftime('%Y年%m月%d日')}の期間における枚方製造所向けの集荷依頼書を送付いたします。\n\n"
                "添付のPDFをご確認の上、集荷手配をお願いいたします。\n\n"
                "よろしくお願いいたします。\n\n"
                "---\n"
                "ダイソウ工業株式会社\n"
                "辻岡(ツジオカ)\n\n"
                "ご不明な点がございましたら下記までご連絡ください。\n"
                "Email:gyomu4@daiso-ind.co.jp\n"
            )

        pdf_buffer = pdf_service.generate_pickup_request_pdf(start_date, end_date)
        filename = f"枚方集荷依頼書_{pickup_start_date.strftime('%Y%m%d')}_{pickup_end_date.strftime('%Y%m%d')}.pdf"

        email_service = EmailService()
        result = email_service.send_email_with_attachment(
            to_emails=to_emails,
            subject=subject,
            body=body,
            attachment_data=pdf_buffer,
            attachment_filename=filename,
            cc_emails=cc_emails if cc_emails else None,
            user_id=user_id,
        )

        if result.get('success'):
            return Response(result, status=status.HTTP_200_OK)

        return Response(result, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"メール送信エラー: {error_detail}")
        return Response(
            {'error': f'メール送信中にエラーが発生しました: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


generate_hirakata_pickup_pdf.permission_resource = 'shipping'
generate_hirakata_pickup_excel.permission_resource = 'shipping'
get_hirakata_pickup_date_range.permission_resource = 'shipping'
get_hirakata_daily_products.permission_resource = 'shipping'
get_hirakata_pickup_contacts.permission_resource = 'shipping'
send_hirakata_pickup_email.permission_resource = 'shipping'
