"""注文書の共通処理（PDF保存・承認申請連携）"""
from django.core.files.base import ContentFile

from .pdf import build_dispatch_order_pdf, dispatch_order_pdf_filename

APPROVAL_ITEM_KEY = 'consumable_dispatch_order'


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
    """注文書送付メールの件名・本文（syomohin と同じ文面）"""
    contact_person = dispatch_order.supplier.contact_person
    greeting = f'{contact_person} 様' if contact_person else 'ご担当者様'
    subject = f'【注文書送付】{dispatch_order.order_number} - {dispatch_order.supplier_name}'
    body = f"""{dispatch_order.supplier_name}
{greeting}

いつもお世話になっております。
ダイソウ工業株式会社 製缶事業部です。

下記の通り、注文書を送付いたします。
添付のPDFファイルをご確認ください。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
注文書番号: {dispatch_order.order_number}
購入先: {dispatch_order.supplier_name}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ご不明な点がございましたら、お気軽にお問い合わせください。

何卒よろしくお願い申し上げます。

――――――――――――――――――――――――――
ダイソウ工業株式会社
製缶事業部
――――――――――――――――――――――――――"""
    return subject, body
