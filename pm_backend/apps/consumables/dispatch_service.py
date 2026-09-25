"""注文書の共通処理（PDF保存・承認申請連携）"""
from django.core.files.base import ContentFile

from .pdf import build_dispatch_order_pdf, dispatch_order_pdf_filename

APPROVAL_ITEM_KEY = 'consumable_dispatch_order'
CONSUMABLE_ORDER_EMAIL_DEFAULT_BODY = """いつもお世話になっております。
ダイソウ工業株式会社 製缶事業部です。

下記の通り、注文書を送付いたします。
添付のPDFファイルをご確認ください。
ダイソウ工業株式会社
{created_by_name}

ご不明な点がございましたら下記までご連絡ください。
Email:{created_by_email}

このメールは送信専用です。ご返信はCC宛先へお願いします。"""


def save_dispatch_order_pdf(dispatch_order):
    """注文書PDFを生成して保存する（承認欄は現時点の承認状況）"""
    content = build_dispatch_order_pdf(dispatch_order)
    if dispatch_order.pdf_file:
        dispatch_order.pdf_file.delete(save=False)
    dispatch_order.pdf_file.save(dispatch_order_pdf_filename(dispatch_order), ContentFile(content), save=False)
    dispatch_order.save(update_fields=['pdf_file'])
    return content


def refresh_dispatch_pdf_for_approval(approval_request):
    """承認申請の段階が進んだ・却下されたときに、注文書PDFの承認欄を更新する（approval_views から呼ぶ）"""
    if approval_request.route_config.item_key != APPROVAL_ITEM_KEY:
        return
    from .models import ConsumableDispatchOrder

    dispatch_order = (
        ConsumableDispatchOrder.objects.select_related('supplier', 'created_by', 'approval_request__route_config')
        .filter(approval_request=approval_request)
        .first()
    )
    if dispatch_order:
        save_dispatch_order_pdf(dispatch_order)


def build_order_email(dispatch_order):
    """消耗品注文書送付メールの件名・本文"""
    subject = f'【注文書送付】{dispatch_order.order_number} - {dispatch_order.supplier_name}'
    return subject, CONSUMABLE_ORDER_EMAIL_DEFAULT_BODY


def render_order_email_body(body, dispatch_order):
    """本文テンプレートの作成者プレースホルダーを置換する"""
    from .services import display_user_name

    values = {
        '{created_by_name}': display_user_name(dispatch_order.created_by),
        '{created_by_email}': dispatch_order.created_by.email or '',
    }
    for placeholder, value in values.items():
        body = body.replace(placeholder, value)
    return body
