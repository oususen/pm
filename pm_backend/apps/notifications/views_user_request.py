"""利用者からシステム管理者へのリクエスト（メール送信のみ・DB保存なし）"""

from django.contrib.auth import get_user_model
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from shipping.services.email_service import EmailService

REQUEST_TYPES = {
    'request': '要望',
    'bug': '不具合',
    'question': '問い合わせ',
    'other': 'その他',
}
MAX_IMAGES = 5
MAX_IMAGE_BYTES = 5 * 1024 * 1024
IMAGE_SUBTYPES = {
    'image/png': 'png',
    'image/jpeg': 'jpeg',
    'image/gif': 'gif',
    'image/webp': 'webp',
}
IMAGE_EXTENSIONS = {'png': 'png', 'jpeg': 'jpg', 'gif': 'gif', 'webp': 'webp'}


class UserRequestView(APIView):
    """POST /api/user-requests/ : システム管理者へリクエストをメール送信する"""

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        type_key = (request.data.get('request_type') or '').strip()
        subject = ' '.join((request.data.get('subject') or '').split())
        body = (request.data.get('body') or '').strip()
        page_url = (request.data.get('page_url') or '').strip()

        if type_key not in REQUEST_TYPES:
            return Response({'detail': '種別を選択してください。'}, status=400)
        if not subject:
            return Response({'detail': '件名を入力してください。'}, status=400)
        if not body:
            return Response({'detail': '内容を入力してください。'}, status=400)

        images = []
        files = request.FILES.getlist('images')
        if len(files) > MAX_IMAGES:
            return Response({'detail': f'画像は最大{MAX_IMAGES}枚までです。'}, status=400)
        for index, f in enumerate(files, start=1):
            subtype = IMAGE_SUBTYPES.get(f.content_type)
            if not subtype:
                return Response({'detail': f'{f.name}: 対応していない画像形式です（png/jpeg/gif/webp）。'}, status=400)
            if f.size > MAX_IMAGE_BYTES:
                return Response({'detail': f'{f.name}: 画像は1枚{MAX_IMAGE_BYTES // 1024 // 1024}MBまでです。'}, status=400)
            images.append({
                'filename': f'image{index}.{IMAGE_EXTENSIONS[subtype]}',
                'data': f.read(),
                'subtype': subtype,
            })

        # 送信先: システム管理者フラグが付いた有効ユーザー全員（メールアドレス登録済みのみ）
        admin_emails = list(
            get_user_model().objects.filter(profile__is_system_admin=True, is_active=True)
            .exclude(email='')
            .values_list('email', flat=True)
            .distinct()
        )
        if not admin_emails:
            return Response({'detail': 'システム管理者（メールアドレス登録済み）が設定されていません。'}, status=400)

        user = request.user
        full_name = f'{user.last_name} {user.first_name}'.strip()
        profile = getattr(user, 'profile', None)
        employee_code = getattr(profile, 'employee_code', '') or ''
        mail_body = (
            f'種別: {REQUEST_TYPES[type_key]}\n'
            f'依頼者: {full_name or user.username}（ユーザー名: {user.username} / 社員コード: {employee_code or "-"}）\n'
            f'依頼者メール: {user.email or "-"}\n'
            f'画面: {page_url or "-"}\n'
            f'添付画像: {len(images)}枚\n'
            '----------------------------------------\n'
            f'{body}\n'
        )

        result = EmailService().send_plain_email(
            to_emails=admin_emails,
            subject=f'[PMリクエスト] {REQUEST_TYPES[type_key]}: {subject}',
            body=mail_body,
            user_id=user.id,
            reply_to=user.email or None,
            image_attachments=images,
        )
        if not result.get('success'):
            return Response({'detail': result.get('message') or '送信に失敗しました。'}, status=502)
        return Response({'detail': 'システム管理者へ送信しました。'})
