"""分析案の作成に使う外部AI呼出し。

検索AI（chat_service）の処理は変更せず、接続先・APIキー・モデル許可リストだけを共用する。
外部へ送るのは、呼出し側で組み立てた分析目的・期間・公開ビューの説明だけで、DBの明細は渡さない。
"""
import json
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from ai.services import chat_service

# 既存の分析案作成（チャット補助の_chat既定）と同じ値。外部AIでの所要時間を実測してからBOSSが確定する。
REQUEST_TIMEOUT_SECONDS = 90

_CODE_FENCE_PATTERN = re.compile(r'^\s*```(?:json)?\s*(.*?)\s*```\s*$', re.DOTALL | re.IGNORECASE)


def external_provider(provider):
    """外部AIの接続設定を返す。許可リスト外のプロバイダは受け付けない。"""
    return chat_service.EXTERNAL_AGENT_PROVIDERS[provider]


def _strip_code_fence(text):
    """モデルがJSONをコードブロックで囲んで返した場合だけ、囲みを外す。中身の検証は呼出し側で厳密に行う。"""
    match = _CODE_FENCE_PATTERN.match(text)
    return match.group(1) if match else text


def request_external_json(provider, model, messages, redactor):
    """OpenAI互換APIへ分析案の作成を依頼し、JSON文字列を返す。

    送信前に伏字化し、応答はそのまま返す（元の名前への復元は、JSONを解析した後に呼出し側で行う）。
    """
    agent = external_provider(provider)
    label = agent['label']
    if not agent['api_key']:
        raise chat_service.LocalAIError(f'{label} APIキーが未設定です。サーバーの環境変数を設定してください。')
    body = {
        'model': model,
        'stream': False,
        'messages': redactor.redact_messages(messages),
        'temperature': 0.3,
        'max_tokens': chat_service.AGENT_MAX_TOKENS,
    }
    if provider == 'deepseek':
        body['response_format'] = {'type': 'json_object'}
        # 分析案はJSONだけが必要なため、思考モードを無効にして空応答・生成上限切れを抑える。
        body['thinking'] = {'type': 'disabled'}
    elif provider == 'openrouter':
        # 無料枠が混雑する場合は他の提供元へ振り分ける（検索AIと同じ設定）。
        # response_formatは、対応しないモデルが拒否するため送らず、プロンプトでJSONを指示する。
        body['provider'] = {'allow_fallbacks': True}
        body['reasoning'] = {'enabled': False}
    request = Request(
        f"{agent['base_url']}/chat/completions",
        data=json.dumps(body, ensure_ascii=False).encode('utf-8'),
        headers={'Content-Type': 'application/json', 'Authorization': f"Bearer {agent['api_key']}"},
        method='POST',
    )
    try:
        with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read().decode('utf-8'))
    except TimeoutError as exc:
        raise chat_service.LocalAIError(f'{label} APIから制限時間内に回答を受信できませんでした。接続状態を確認してください。') from exc
    except HTTPError as exc:
        if exc.code in {401, 403}:
            raise chat_service.LocalAIError(f'{label} APIキーを確認してください。') from exc
        raise chat_service.LocalAIError(f'{label} APIの呼び出しに失敗しました。残高・利用制限・接続状態を確認してください。') from exc
    except (URLError, OSError, ValueError) as exc:
        raise chat_service.LocalAIError(f'{label} APIに接続できません。接続設定を確認してください。') from exc
    choice = (payload.get('choices') or [{}])[0]
    answer = ((choice.get('message') or {}).get('content') or '').strip()
    if not answer:
        raise chat_service.LocalAIError(f'{label} APIから空の応答が返りました。時間をおいて再度お試しください。')
    if choice.get('finish_reason') == 'length':
        raise chat_service.LocalAIError('分析案が生成上限で中断しました。目的を短くするか、別のモデルでお試しください。')
    return _strip_code_fence(answer)
