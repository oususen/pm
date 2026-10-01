"""利用者からシステム管理者へのリクエスト（メール送信のみ・DB保存なし）"""

import os

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
MAX_FILES = 5
MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_TOTAL_BYTES = 20 * 1024 * 1024

# 画像: 拡張子 -> MIMEサブタイプ（スクリーンショット貼り付けを含む）
IMAGE_SUBTYPES = {'.png': 'png', '.jpg': 'jpeg', '.jpeg': 'jpeg', '.gif': 'gif', '.webp': 'webp'}
# 書類: 拡張子 -> (MIMEメインタイプ, サブタイプ)。ここにない拡張子（実行ファイル・スクリプト・ZIP等）は受け付けない。
DOCUMENT_TYPES = {
    '.xlsx': ('application', 'vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
    '.xlsm': ('application', 'vnd.ms-excel.sheet.macroEnabled.12'),
    '.xls': ('application', 'vnd.ms-excel'),
    '.docx': ('application', 'vnd.openxmlformats-officedocument.wordprocessingml.document'),
    '.doc': ('application', 'msword'),
    '.pdf': ('application', 'pdf'),
    '.csv': ('text', 'csv'),
    '.txt': ('text', 'plain'),
}


def _safe_filename(name, index):
    """ヘッダ注入を防ぐため、制御文字とパス区切りを除いたファイル名にする"""
    base = os.path.basename((name or '').replace('\\', '/'))
    base = ''.join(ch for ch in base if ch >= ' ' and ch != '\x7f').strip()
    return base or f'file{index}'


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

        attachments = []
        files = request.FILES.getlist('files')
        if len(files) > MAX_FILES:
            return Response({'detail': f'添付ファイルは最大{MAX_FILES}個までです。'}, status=400)
        total_bytes = 0
        for index, f in enumerate(files, start=1):
            filename = _safe_filename(f.name, index)
            ext = os.path.splitext(filename)[1].lower()
            if f.size > MAX_FILE_BYTES:
                return Response({'detail': f'{filename}: 1ファイル{MAX_FILE_BYTES // 1024 // 1024}MBまでです。'}, status=400)
            total_bytes += f.size
            if total_bytes > MAX_TOTAL_BYTES:
                return Response({'detail': f'添付ファイルの合計は{MAX_TOTAL_BYTES // 1024 // 1024}MBまでです。'}, status=400)
            if ext in IMAGE_SUBTYPES:
                attachments.append({'filename': filename, 'data': f.read(), 'maintype': 'image', 'subtype': IMAGE_SUBTYPES[ext]})
            elif ext in DOCUMENT_TYPES:
                maintype, subtype = DOCUMENT_TYPES[ext]
                attachments.append({'filename': filename, 'data': f.read(), 'maintype': maintype, 'subtype': subtype})
            else:
                return Response({'detail': f'{filename}: 対応していない形式です（画像・Excel・Word・PDF・CSV・テキストのみ）。'}, status=400)

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
        file_names = '、'.join(a['filename'] for a in attachments) or 'なし'
        mail_body = (
            f'種別: {REQUEST_TYPES[type_key]}\n'
            f'依頼者: {full_name or user.username}（ユーザー名: {user.username} / 社員コード: {employee_code or "-"}）\n'
            f'依頼者メール: {user.email or "-"}\n'
            f'画面: {page_url or "-"}\n'
            f'添付ファイル: {len(attachments)}個（{file_names}）\n'
            '----------------------------------------\n'
            f'{body}\n'
        )

        result = EmailService().send_plain_email(
            to_emails=admin_emails,
            subject=f'[PMリクエスト] {REQUEST_TYPES[type_key]}: {subject}',
            body=mail_body,
            user_id=user.id,
            reply_to=user.email or None,
            file_attachments=attachments,
        )
        if not result.get('success'):
            return Response({'detail': result.get('message') or '送信に失敗しました。'}, status=502)
        return Response({'detail': 'システム管理者へ送信しました。'})
