# apps/shipping/services/email_service.py
"""メール送信サービス"""

import os
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from io import BytesIO
from typing import Dict, List, Optional

from django.db import connection

try:
    from accounts.models import UserSmtpConfig
except Exception:
    UserSmtpConfig = None


class EmailService:
    """メール送信サービス"""

    def get_smtp_config(self, user_id: Optional[int] = None) -> Optional[Dict]:
        """
        SMTP設定を取得

        Args:
            user_id: ユーザーID（Noneの場合はデフォルト設定を取得）

        Returns:
            Dict: SMTP設定（host, port, user, password）
        """
        config = self._get_smtp_config_from_profile(user_id)
        if config:
            return config

        return None

    def _get_smtp_config_from_profile(self, user_id: Optional[int]) -> Optional[Dict]:
        if not UserSmtpConfig:
            return None

        try:
            queryset = UserSmtpConfig.objects.filter(is_active=True)
            profile = None

            # まず、指定されたユーザーの設定を探す
            if user_id:
                profile = queryset.filter(user_id=user_id).first()

            # ユーザー個別の設定がない場合、デフォルト設定を探す
            if not profile:
                profile = queryset.filter(is_admin=True).order_by('id').first()

        except Exception as e:
            print(f"SMTP設定取得エラー: {e}")
            return None

        if not profile or not profile.smtp_host:
            return None

        return {
            'host': profile.smtp_host,
            'port': profile.smtp_port or 587,
            'user': profile.smtp_user,
            'password': profile.smtp_password,
        }


    def get_contacts(self, contact_type: Optional[str] = None) -> List[Dict]:
        """
        連絡先一覧を取得

        Args:
            contact_type: 連絡先種別（指定がある場合のみフィルタ）

        Returns:
            List[Dict]: 連絡先リスト
        """
        with connection.cursor() as cursor:
            if contact_type:
                cursor.execute(
                    """
                    SELECT
                        id,
                        contact_type,
                        company_name,
                        department,
                        contact_person,
                        email,
                        phone,
                        notes
                    FROM m_contacts
                    WHERE contact_type = %s
                      AND is_active = 1
                    ORDER BY display_order, company_name
                    """,
                    [contact_type],
                )
            else:
                cursor.execute(
                    """
                    SELECT
                        id,
                        contact_type,
                        company_name,
                        department,
                        contact_person,
                        email,
                        phone,
                        notes
                    FROM m_contacts
                    WHERE is_active = 1
                    ORDER BY contact_type, display_order, company_name
                    """
                )

            results = cursor.fetchall()

        contacts = []
        for row in results:
            contact_name = row[2] or ''  # company_name
            if row[3]:
                contact_name += f" {row[3]}"
            if row[4]:
                contact_name += f" {row[4]}"

            contacts.append({
                'id': row[0],
                'contact_type': row[1],
                'display_name': contact_name.strip(),
                'email': row[5],
                'phone': row[6],
                'notes': row[7],
            })

        return contacts

    def send_email_with_attachment(
        self,
        to_emails: List[str],
        subject: str,
        body: str,
        attachment_data: BytesIO,
        attachment_filename: str,
        cc_emails: Optional[List[str]] = None,
        user_id: Optional[int] = None,
        extra_attachments: Optional[List[Dict]] = None,
        reply_to: Optional[str] = None,
    ) -> Dict:
        """
        添付ファイル付きメールを送信

        Args:
            to_emails: 宛先メールアドレスリスト
            subject: 件名
            body: 本文
            attachment_data: 添付ファイルデータ（BytesIO）
            attachment_filename: 添付ファイル名
            cc_emails: CCメールアドレスリスト
            user_id: 送信者ユーザーID

        Returns:
            Dict: 送信結果 {'success': bool, 'message': str}
        """
        smtp_config = self.get_smtp_config(user_id)
        if not smtp_config:
            return {
                'success': False,
                'message': 'SMTP設定が見つかりません。管理者に連絡してください。',
            }

        try:
            msg = MIMEMultipart()
            msg['From'] = smtp_config['user']
            msg['To'] = ', '.join(to_emails)
            msg['Subject'] = subject
            if cc_emails:
                msg['Cc'] = ', '.join(cc_emails)
            if reply_to:
                msg['Reply-To'] = reply_to

            msg.attach(MIMEText(body, 'plain', 'utf-8'))

            attachment_data.seek(0)
            ext = os.path.splitext(attachment_filename)[1].lower()
            mime_subtypes = {
                '.xlsx': 'vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                '.xls': 'vnd.ms-excel',
                '.pdf': 'pdf',
            }
            subtype = mime_subtypes.get(ext, 'octet-stream')
            attachment = MIMEApplication(attachment_data.read(), _subtype=subtype)
            attachment.add_header(
                'Content-Disposition',
                'attachment',
                filename=attachment_filename,
            )
            msg.attach(attachment)

            if extra_attachments:
                for ea in extra_attachments:
                    ea_data = ea['data']
                    ea_filename = ea['filename']
                    ea_data.seek(0)
                    ea_ext = os.path.splitext(ea_filename)[1].lower()
                    ea_subtype = mime_subtypes.get(ea_ext, 'octet-stream')
                    ea_attach = MIMEApplication(ea_data.read(), _subtype=ea_subtype)
                    ea_attach.add_header('Content-Disposition', 'attachment', filename=ea_filename)
                    msg.attach(ea_attach)

            recipients = list(to_emails)
            if cc_emails:
                recipients.extend(cc_emails)

            with smtplib.SMTP(smtp_config['host'], smtp_config['port']) as server:
                server.starttls()
                server.login(smtp_config['user'], smtp_config['password'])
                refused_recipients = server.send_message(msg, to_addrs=recipients)

            if refused_recipients:
                refused_list = ', '.join(refused_recipients.keys())
                return {
                    'success': False,
                    'message': f'一部の宛先で送信に失敗しました: {refused_list}',
                }

            return {
                'success': True,
                'message': f'メールを送信しました（宛先: {len(to_emails)}件）',
            }

        except smtplib.SMTPAuthenticationError:
            return {
                'success': False,
                'message': 'SMTP認証エラー: ユーザー名またはパスワードが正しくありません',
            }
        except smtplib.SMTPException as exc:
            return {
                'success': False,
                'message': f'メール送信エラー: {str(exc)}',
            }
        except Exception as exc:
            return {
                'success': False,
                'message': f'予期しないエラー: {str(exc)}',
            }
