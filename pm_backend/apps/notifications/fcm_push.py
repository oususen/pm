import json
import logging
from typing import Any

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

FCM_SCOPE = ['https://www.googleapis.com/auth/firebase.messaging']


def _load_service_account_info():
    raw_json = (getattr(settings, 'FCM_SERVICE_ACCOUNT_JSON', '') or '').strip()
    if raw_json:
        try:
            return json.loads(raw_json)
        except json.JSONDecodeError:
            logger.warning('FCM_SERVICE_ACCOUNT_JSON の JSON 解析に失敗しました。')
            return None

    file_path = (getattr(settings, 'FCM_SERVICE_ACCOUNT_FILE', '') or '').strip()
    if not file_path:
        return None

    try:
        with open(file_path, 'r', encoding='utf-8') as fh:
            return json.load(fh)
    except OSError:
        logger.warning('FCM_SERVICE_ACCOUNT_FILE を読み込めませんでした。 path=%s', file_path)
    except json.JSONDecodeError:
        logger.warning('FCM_SERVICE_ACCOUNT_FILE の JSON 解析に失敗しました。 path=%s', file_path)
    return None


def get_fcm_config():
    service_account = _load_service_account_info()
    project_id = (getattr(settings, 'FCM_PROJECT_ID', '') or '').strip()
    if not project_id and service_account:
        project_id = str(service_account.get('project_id') or '').strip()
    return {
        'enabled': bool(project_id and service_account),
        'project_id': project_id,
        'service_account': service_account,
    }


def _get_access_token(service_account: dict[str, Any]):
    try:
        from google.auth.transport.requests import Request
        from google.oauth2 import service_account as google_service_account
    except ImportError:
        logger.warning('google-auth が未インストールのため FCM を送信できません。')
        return ''

    credentials = google_service_account.Credentials.from_service_account_info(
        service_account,
        scopes=FCM_SCOPE,
    )
    credentials.refresh(Request())
    return credentials.token or ''


def _build_data_payload(payload: dict[str, Any]):
    data = {}
    for key, value in (payload.get('data') or {}).items():
        data[str(key)] = '' if value is None else str(value)
    if payload.get('url') and 'url' not in data:
        data['url'] = str(payload['url'])
    if payload.get('tag') and 'tag' not in data:
        data['tag'] = str(payload['tag'])
    return data


def _is_invalid_token_response(response_json: dict[str, Any]):
    error = response_json.get('error') or {}
    status = str(error.get('status') or '').upper()
    if status in {'UNREGISTERED', 'NOT_FOUND'}:
        return True

    for detail in error.get('details') or []:
        code = str(detail.get('errorCode') or '').upper()
        if code in {'UNREGISTERED', 'INVALID_ARGUMENT'}:
            return True
    return False


def send_fcm_push(device, payload):
    config = get_fcm_config()
    if not config['enabled']:
        return False

    access_token = _get_access_token(config['service_account'])
    if not access_token:
        return False

    url = f"https://fcm.googleapis.com/v1/projects/{config['project_id']}/messages:send"
    data = _build_data_payload(payload)
    data['title'] = payload.get('title') or ''
    data['body'] = payload.get('body') or ''
    body = {
        'message': {
            'token': device.token,
            'data': data,
            'android': {
                'priority': 'high',
                'ttl': '30s',
            },
        },
    }

    try:
        response = requests.post(
            url,
            headers={
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json; charset=utf-8',
            },
            json=body,
            timeout=10,
        )
    except requests.RequestException:
        logger.exception('FCM 送信中に通信エラーが発生しました。 token=%s', device.token[:24])
        return False

    if response.ok:
        return True

    try:
        response_json = response.json()
    except ValueError:
        response_json = {}

    if _is_invalid_token_response(response_json):
        logger.info('無効な FCM トークンを削除します。 token=%s', device.token[:24])
        device.delete()
        return False

    logger.warning(
        'FCM 送信に失敗しました。 status=%s body=%s',
        response.status_code,
        response.text[:500],
    )
    return False
