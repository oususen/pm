"""Anthropic Claude(Messages API)への直接接続。分析案の作成など、JSONを1回で得る呼出し用。

OpenAI互換の経路(analysis_llm.request_external_json の deepseek/openrouter)とは送受信の形が違うため、別ファイルにする。
公式docsで確認した制約(2026-10-13):
- temperature / top_p / top_k は送らない(Haiku 5.5は1以外で400)。
- 末尾がassistantのプレフィルは400のため使わない。
- thinkingは既定オンでトークンを消費するため、{"type": "disabled"} を送る。
- JSONは構造化出力 output_config.format(json_schema)で得る。スキーマが通らない(400)場合も、プロンプトだけには落とさず停止する(フォールバックしない)。
- ヘッダは x-api-key と anthropic-version(Authorization は付けない)。systemはトップレベル、max_tokensは必須。
- 応答は content[] のうち type == 'text' のブロックを連結して読む。
HTTP本文・APIキー・リクエストの全文は、例外・ログ・応答に出さない(固定文のみ)。再送・別モデルへの切替もしない。
"""
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from ai.services import chat_service

ANTHROPIC_VERSION = '2023-06-01'

# 不完全・拒否の応答は、JSONが一見正しく見えても成功として返さない
STOP_REASON_MESSAGES = {
    'max_tokens': '分析案が生成上限で中断しました。目的を短くするか、別のモデルでお試しください。',
    'refusal': 'AIが応答を拒否しました。目的の表現を見直してください。',
    'model_context_window_exceeded': '入力が長すぎてAIが処理できませんでした。目的を短くしてください。',
}


def _error(message, code=''):
    return chat_service.LocalAIError(message, code=code)


def split_messages(messages):
    """OpenAI形(role/content)のmessagesを、Anthropic形(トップレベルsystem + user/assistantのmessages)へ変換する。"""
    system_parts = []
    converted = []
    for item in messages:
        role, content = item.get('role'), item.get('content')
        if not isinstance(content, str):
            raise _error('Claudeへ送る文面の形式が不正です。')
        if role == 'system':
            system_parts.append(content)
        elif role in ('user', 'assistant'):
            converted.append({'role': role, 'content': content})
        else:
            raise _error('Claudeへ送る文面の形式が不正です。')
    if not converted or converted[0]['role'] != 'user':
        raise _error('Claudeへ送る文面の先頭はユーザーの発言にしてください。')
    if converted[-1]['role'] != 'user':
        # 末尾assistant(プレフィル)は400になるため、送らない
        raise _error('Claudeへ送る文面の末尾はユーザーの発言にしてください。')
    return '\n\n'.join(system_parts), converted


def build_body(model, messages, json_schema):
    system, converted = split_messages(messages)
    body = {
        'model': model,
        'max_tokens': chat_service.AGENT_MAX_TOKENS,
        'messages': converted,
        'thinking': {'type': 'disabled'},
        'output_config': {'format': {'type': 'json_schema', 'schema': json_schema}},
    }
    if system:
        body['system'] = system
    return body


def _http_error(label, code):
    """HTTPステータス別の固定文。応答本文は読まない・出さない。"""
    if code in (401, 403):
        return _error(f'{label} APIキーを確認してください。', 'ai_auth')
    if code == 402:
        text = f'{label} APIの請求エラーです。クレジット残高・支払い設定を確認してください。'
    elif code == 429:
        text = f'{label} APIのレート制限または月間上限に達しました。時間をおくか、利用上限を確認してください。'
    elif code == 400:
        text = f'{label} APIがリクエストを受け付けませんでした。残高・上限・リクエスト内容を確認してください。'
    else:
        text = f'{label} APIの呼び出しに失敗しました。残高・利用制限・接続状態を確認してください。'
    return _error(text, 'ai_http')


def request_json(provider, model, messages, json_schema=None, timeout=None):
    """Messages APIへ依頼し、構造化出力のJSON文字列を返す。json_schemaが無いときは、HTTPリクエストを発生させず停止する。"""
    agent = chat_service.EXTERNAL_AGENT_PROVIDERS[provider]
    label = agent['label']
    if json_schema is None:
        raise _error('Claudeの呼出しにはJSONスキーマが必要です。プロンプトだけでは続行しません。')
    if not agent['api_key']:
        raise _error(f'{label} APIキーが未設定です。サーバーの環境変数を設定してください。', 'ai_auth')
    body = build_body(model, messages, json_schema)
    request = Request(
        f"{agent['base_url']}/v1/messages",
        data=json.dumps(body, ensure_ascii=False).encode('utf-8'),
        headers={'Content-Type': 'application/json', 'x-api-key': agent['api_key'], 'anthropic-version': ANTHROPIC_VERSION},
        method='POST',
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode('utf-8'))
    except TimeoutError:
        raise _error(f'{label} APIから制限時間内に回答を受信できませんでした。接続状態を確認してください。', 'ai_timeout') from None
    except HTTPError as exc:
        raise _http_error(label, exc.code) from None
    # HTTPErrorは、URLErrorの下位の型のため、上の except HTTPError を先に置く(この順序を変えない)
    except URLError as exc:
        if isinstance(exc.reason, TimeoutError):
            raise _error(f'{label} APIから制限時間内に回答を受信できませんでした。接続状態を確認してください。', 'ai_timeout') from None
        raise _error(f'{label} APIに接続できません。接続設定を確認してください。', 'ai_connect') from None
    except (OSError, ValueError):
        raise _error(f'{label} APIに接続できません。接続設定を確認してください。', 'ai_connect') from None
    if not isinstance(payload, dict):
        raise _error(f'{label} APIから空の応答が返りました。時間をおいて再度お試しください。', 'ai_empty')
    stop_message = STOP_REASON_MESSAGES.get(payload.get('stop_reason'))
    if stop_message:
        raise _error(stop_message)
    blocks = payload.get('content')
    text = ''.join(
        block.get('text') or '' for block in (blocks if isinstance(blocks, list) else [])
        if isinstance(block, dict) and block.get('type') == 'text'
    ).strip()
    if not text:
        raise _error(f'{label} APIから空の応答が返りました。時間をおいて再度お試しください。', 'ai_empty')
    return text
