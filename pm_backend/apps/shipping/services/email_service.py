# apps/shipping/services/email_service.py
"""メール送信サービス"""

import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from io import BytesIO
from typing import Dict, List, Optional

from django.contrib.auth import get_user_model
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
            user_id: ユーザーID（Noneの場合は管理者の設定を取得）

        Returns:
            Dict: SMTP設定（host, port, user, password）
        """
        config = self._get_smtp_config_from_profile(user_id)
        if config:
            return config

        config = self._get_legacy_config_for_auth_user(user_id)
        if config:
            return config

        with connection.cursor() as cursor:
            if user_id:
                cursor.execute(
                    """
                    SELECT smtp_host, smtp_port, smtp_user, smtp_password
                    FROM users
                    WHERE id = %s AND is_active = 1
                    """,
                    [user_id],
                )
            else:
                cursor.execute(
                    """
                    SELECT smtp_host, smtp_port, smtp_user, smtp_password
                    FROM users
                    WHERE is_admin = 1 AND is_active = 1
                    ORDER BY id
                    LIMIT 1
                    """
                )

            result = cursor.fetchone()

        if result and result[0]:
            return {
                'host': result[0],
                'port': result[1] or 587,
                'user': result[2],
                'password': result[3],
            }

        return None

    def _get_smtp_config_from_profile(self, user_id: Optional[int]) -> Optional[Dict]:
        if not UserSmtpConfig:
            return None

        try:
            queryset = UserSmtpConfig.objects.filter(is_active=True)
            if user_id:
                profile = queryset.filter(user_id=user_id).first()
            else:
                profile = queryset.filter(is_admin=True).order_by('id').first()
        except Exception:
            return None

        if not profile or not profile.smtp_host:
            return None

        return {
            'host': profile.smtp_host,
            'port': profile.smtp_port or 587,
            'user': profile.smtp_user,
            'password': profile.smtp_password,
        }

    def _get_legacy_config_for_auth_user(self, user_id: Optional[int]) -> Optional[Dict]:
        if not user_id:
            return None

        try:
            user = get_user_model().objects.filter(id=user_id).first()
        except Exception:
            return None

        if not user:
            return None

        identifiers = [user.email, user.username]
        for identifier in identifiers:
            if not identifier:
                continue
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT smtp_host, smtp_port, smtp_user, smtp_password
                    FROM users
                    WHERE smtp_user = %s AND is_active = 1
                    """,
                    [identifier],
                )
                result = cursor.fetchone()
            if result and result[0]:
                return {
                    'host': result[0],
                    'port': result[1] or 587,
                    'user': result[2],
                    'password': result[3],
                }

        return None

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
                    FROM contacts
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
                    FROM contacts
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

            msg.attach(MIMEText(body, 'plain', 'utf-8'))

            attachment_data.seek(0)
            attachment = MIMEApplication(attachment_data.read(), _subtype='pdf')
            attachment.add_header(
                'Content-Disposition',
                'attachment',
                filename=attachment_filename,
            )
            msg.attach(attachment)

            recipients = list(to_emails)
            if cc_emails:
                recipients.extend(cc_emails)

            with smtplib.SMTP(smtp_config['host'], smtp_config['port']) as server:
                server.starttls()
                server.login(smtp_config['user'], smtp_config['password'])
                server.send_message(msg, to_addrs=recipients)

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
