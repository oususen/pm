"""社内AIチャットのアプリケーションサービス。"""
import json
import os
import re
import unicodedata
from difflib import SequenceMatcher
from calendar import monthrange
from datetime import date
from decimal import Decimal, InvalidOperation
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from django.db.models import Count, DecimalField, ExpressionWrapper, F, Q, Sum, Value
from django.db.models.functions import Coalesce, TruncDate
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ai.context.screen_context import COMMON_COVERAGE, resolve_screen_context
from ai.config.models import AIProviderConfig
from ai.config.service import (
    apply_tool_policy,
    authorized_personal_data_allowed,
    external_aggregate_transfer_allowed,
    external_image_transfer_allowed,
    limit_external_result_rows,
)
from accounts.models import Department
from masters.models import Product
from production.models_brake_line_record import BrakeLineRecord
from production.models_laser_actual import LaserActual, LaserActualDetail
from production.models_process_realtime import ProcessRealtimeRecord
from quality.models_scrap import ScrapRecord
from overtime.models import OvertimeApplication
from ai.services.order_queries import get_missing_routing_orders
from ai.services.knowledge_retriever import knowledge_prompt, knowledge_source_label, retrieve_knowledge
from ai.services.query_common import AI_DB_ALIAS
from ai.services.sql_queries import execute_readonly_sql, schema_text
from ai.services.vision import selected_visual_attachment


MODEL = os.environ.get('OLLAMA_MODEL', 'qwen3:4b-instruct')
OLLAMA_URL = os.environ.get('OLLAMA_BASE_URL', 'http://127.0.0.1:11434').rstrip('/')
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')
DEEPSEEK_MODEL = os.environ.get('DEEPSEEK_MODEL', 'deepseek-v4-pro')
DEEPSEEK_BASE_URL = os.environ.get('DEEPSEEK_BASE_URL', 'https://api.deepseek.com').rstrip('/')
DEEPSEEK_MODELS = {
    'deepseek-v4-pro': 'DeepSeek V4 Pro（高精度）',
    'deepseek-flash': 'DeepSeek Flash（高速）',
}
# ローカルLLM(Qwen)導入前の評価用。OpenRouter経由でQwen3.8 27B相当のモデルを試す。
OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY', '')
OPENROUTER_MODEL = os.environ.get('OPENROUTER_MODEL', 'qwen/qwen3.8-27b:free')
OPENROUTER_BASE_URL = os.environ.get('OPENROUTER_BASE_URL', 'https://openrouter.ai/api/v1').rstrip('/')
OPENROUTER_MODELS = {
    'qwen/qwen3.8-27b:free': 'Qwen3.8 27B（OpenRouter・無料枠）',
    'google/gemma-4-26b-a4b-it:free': 'Gemma 4 26B A4B（OpenRouter・無料枠）',
    'google/gemma-4-26b-a4b-it': 'Gemma 4 26B A4B（OpenRouter・有料/要クレジット）',
}
# 外部AI(DeepSeek互換のOpenAI形式API)。エージェント方式のツール呼び出しはこれらすべてで共通ロジックを使う。
EXTERNAL_AGENT_PROVIDERS = {
    'deepseek': {
        'base_url': DEEPSEEK_BASE_URL, 'api_key': DEEPSEEK_API_KEY,
        'models': DEEPSEEK_MODELS, 'default_model': DEEPSEEK_MODEL, 'label': 'DeepSeek',
    },
    'openrouter': {
        'base_url': OPENROUTER_BASE_URL, 'api_key': OPENROUTER_API_KEY,
        'models': OPENROUTER_MODELS, 'default_model': OPENROUTER_MODEL, 'label': 'OpenRouter',
    },
}
MAX_RANGE_DAYS = 93
AGENT_MAX_ROUNDS = 8
AGENT_MAX_TOKENS = 4096
PRODUCT_CODE_PATTERN = re.compile(r'(?<![A-Za-z0-9])([A-Za-z]{1,10}\d{3,}(?:-[A-Za-z0-9]+)+)(?![A-Za-z0-9])')
PRODUCT_CODE_LOOSE_PATTERN = re.compile(r'(?<![A-Za-z0-9])([A-Za-z](?:[A-Za-z0-9\s-]{4,49}))(?![A-Za-z0-9])')
PRODUCT_CODE_JA_SUFFIX_PATTERN = re.compile(r'(?<![A-Za-z0-9])([A-Za-z][A-Za-z0-9-]{4,49})\s*の\s*([0-9]{1,3}[A-Za-z]?)(?![A-Za-z0-9])')
REDACTION_PLACEHOLDER_PATTERN = re.compile(r'(?:実績作業者|作業者|得意先|仕入先|照会情報)\d+')
FORCE_TOOL_CALL_TERMS = ('グラフ', 'ぐらふ', 'チャート', '図表', 'もう一回', 'もう一度', '再集計', '再度', '再表示')
DATA_OPTION_SELECTIONS = {
    '1': {'intent': 'production', 'label': '生産数の日別推移', 'terms': ('生産数', '日別推移')},
    '2': {'intent': 'scrap', 'label': '仕損の理由別集計', 'terms': ('仕損', '理由別')},
    '3': {'intent': 'overtime', 'label': '残業申請時間の照会', 'terms': ('残業',)},
}

AI_DB_ACCESS = [
    {
        'model': 'masters.Supplier',
        'label': '仕入先',
        'search_fields': ['supplier_name'],
        'display_fields': ['supplier_name', 'supplier_code', 'supplier_type'],
        'display': '{supplier_name}（コード: {supplier_code}、区分: {supplier_type}）',
    },
    {
        'model': 'masters.Customer',
        'label': '得意先',
        'search_fields': ['customer_name', 'short_name'],
        'display_fields': ['customer_name', 'customer_code'],
        'display': '{customer_name}（コード: {customer_code}）',
        'filter': {'is_active': True},
    },
    {
        'model': 'masters.Product',
        'label': '製品',
        'search_fields': ['product_code', 'product_name'],
        'display_fields': ['product_name', 'product_code'],
        'display': '{product_name}（品番: {product_code}）',
        'filter': {'is_active': True},
    },
    {
        'model': 'masters.Line',
        'label': 'ライン',
        'search_fields': ['line_code', 'line_name'],
        'display_fields': ['line_name', 'line_code'],
        'display': '{line_name}（コード: {line_code}）',
        'filter': {'is_active': True},
    },
    {
        'model': 'masters.Process',
        'label': '工程',
        'search_fields': ['process_code', 'process_name'],
        'display_fields': ['process_name', 'process_code'],
        'display': '{process_name}（コード: {process_code}）',
        'filter': {'is_active': True},
    },
]


class LocalAIError(Exception):
    """選択したAIモデルと通信できない、または応答形式が不正。"""


class ExternalDataRedactor:
    """外部AIへ送る前に、PM内で管理している識別子を一時IDへ置換する。"""

    def __init__(self):
        self.replacements = []

    def add(self, value, replacement):
        value = str(value or '').strip()
        if value and not any(value == original for original, _ in self.replacements):
            self.replacements.append((value, replacement))

    def redact_text(self, value):
        text = str(value or '')
        for original, replacement in sorted(self.replacements, key=lambda item: len(item[0]), reverse=True):
            text = text.replace(original, replacement)
        # 連絡先はAI回答で復元しないため、外部送信前に常に除去する。
        text = re.sub(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}', '[メールアドレス]', text)
        text = re.sub(r'(?<!\d)(?:0\d{1,4}-?\d{1,4}-?\d{3,4})(?!\d)', '[電話番号]', text)
        return text

    def restore_text(self, value):
        text = str(value or '')
        # 作業者1 と 作業者14 のような一時IDが部分一致しないよう、長いIDから復元する。
        for original, replacement in sorted(self.replacements, key=lambda item: len(item[1]), reverse=True):
            text = text.replace(replacement, original)
        return text

    def redact_messages(self, messages):
        redacted = []
        for message in messages:
            content = message.get('content', '')
            # 画像付きメッセージはOpenAI互換形式の配列になる。文章部分だけを伏字化し、
            # 明示添付された画像データは壊さずそのまま残す。
            if isinstance(content, list):
                content = [
                    {**part, 'text': self.redact_text(part.get('text', ''))}
                    if isinstance(part, dict) and part.get('type') == 'text' else part
                    for part in content
                ]
            else:
                content = self.redact_text(content)
            redacted.append({**message, 'content': content})
        return redacted


def _build_external_data_redactor():
    """外部送信時に伏字化するPM内の識別子を収集する。対応表はリクエスト内だけで使う。"""
    from django.contrib.auth import get_user_model
    from masters.models import Customer, Supplier

    redactor = ExternalDataRedactor()
    for index, user in enumerate(get_user_model().objects.using(AI_DB_ALIAS).filter(is_active=True).only(
        'username', 'first_name', 'last_name'
    ), start=1):
        label = f'作業者{index}'
        redactor.add(f'{user.last_name} {user.first_name}'.strip(), label)
        redactor.add(f'{user.last_name}{user.first_name}'.strip(), label)
        redactor.add(user.username, label)
    for index, name in enumerate(
        ProcessRealtimeRecord.objects.using(AI_DB_ALIAS).exclude(operator_name__isnull=True).exclude(operator_name='')
        .values_list('operator_name', flat=True).distinct(),
        start=1,
    ):
        redactor.add(name, f'実績作業者{index}')
    for index, customer in enumerate(Customer.objects.using(AI_DB_ALIAS).filter(is_active=True).only('customer_name', 'short_name'), start=1):
        redactor.add(customer.customer_name, f'得意先{index}')
        redactor.add(customer.short_name, f'得意先{index}')
    for index, supplier in enumerate(Supplier.objects.using(AI_DB_ALIAS).only('supplier_name'), start=1):
        redactor.add(supplier.supplier_name, f'仕入先{index}')
    return redactor


def _ollama_chat(messages, json_mode=False, num_predict=180, timeout=90, include_metadata=False):
    body = {
        'model': MODEL,
        'stream': False,
        'think': False,
        'keep_alive': '10m',
        'messages': messages,
        'options': {
            'temperature': 0.7, 'top_p': 0.8, 'top_k': 20, 'min_p': 0,
            'num_ctx': 4096, 'num_predict': num_predict,
        },
    }
    if json_mode:
        body['format'] = 'json'
    request = Request(
        f'{OLLAMA_URL}/api/chat',
        data=json.dumps(body, ensure_ascii=False).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='POST',
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode('utf-8'))
        answer = payload.get('message', {}).get('content', '').strip()
        if not answer:
            raise LocalAIError('ローカルAIから空の応答が返りました。')
        if json_mode and payload.get('done_reason') == 'length':
            raise LocalAIError('質問の解析が生成上限で中断しました。アプリの生成上限設定を確認してください。')
        if include_metadata:
            endpoint = urlsplit(OLLAMA_URL)
            # 実行情報は設定上のモデル名ではなく、Ollamaが返した値を使う。
            return answer, {
                'model': payload.get('model', ''),
                'host': endpoint.hostname,
                'port': endpoint.port,
                'created_at': payload.get('created_at', ''),
                'duration_seconds': round(payload.get('total_duration', 0) / 1_000_000_000, 2),
                'output_tokens': payload.get('eval_count'),
                'done_reason': payload.get('done_reason', ''),
                'truncated': payload.get('done_reason') == 'length',
            }
        return answer
    except TimeoutError as exc:
        raise LocalAIError('Ollamaから制限時間内に回答を受信できませんでした。実行状態を確認してください。') from exc
    except (HTTPError, URLError, OSError, ValueError) as exc:
        raise LocalAIError(
            f'Ollamaまたは指定モデルを確認できません。Ollamaの起動とモデル {MODEL} の導入状態を確認してください。'
        ) from exc


def _deepseek_chat(messages, json_mode=False, num_predict=180, timeout=90, include_metadata=False, model=None, redactor=None):
    """DeepSeek Chat Completions APIを呼び出す。APIキーは環境変数だけから取得する。"""
    if not DEEPSEEK_API_KEY:
        raise LocalAIError('DeepSeek APIキーが未設定です。サーバーの DEEPSEEK_API_KEY を設定してください。')
    body = {
        'model': model or DEEPSEEK_MODEL,
        'stream': False,
        'messages': redactor.redact_messages(messages) if redactor else messages,
        'temperature': 0.3 if json_mode else 0.7,
        'max_tokens': num_predict,
    }
    if json_mode:
        body['response_format'] = {'type': 'json_object'}
        # 意図解析は構造化JSONだけが必要なため、思考モードを無効化して空応答を抑える。
        body['thinking'] = {'type': 'disabled'}
    request = Request(
        f'{DEEPSEEK_BASE_URL}/chat/completions',
        data=json.dumps(body, ensure_ascii=False).encode('utf-8'),
        headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {DEEPSEEK_API_KEY}',
        },
        method='POST',
    )
    try:
        answer = ''
        payload = {}
        choice = {}
        # JSON Outputは公式仕様上、まれに空応答になるため1回だけ再試行する。
        for _ in range(2 if json_mode else 1):
            with urlopen(request, timeout=timeout) as response:
                payload = json.loads(response.read().decode('utf-8'))
            choice = (payload.get('choices') or [{}])[0]
            answer = ((choice.get('message') or {}).get('content') or '').strip()
            if answer:
                break
        if redactor and answer:
            answer = redactor.restore_text(answer)
        if not answer:
            raise LocalAIError('DeepSeek APIから空の応答が返りました。時間をおいて再度お試しください。')
        if json_mode and choice.get('finish_reason') == 'length':
            raise LocalAIError('質問の解析が生成上限で中断しました。生成上限設定を確認してください。')
        if include_metadata:
            usage = payload.get('usage') or {}
            return answer, {
                'provider': 'deepseek',
                'model': payload.get('model', model or DEEPSEEK_MODEL),
                'duration_seconds': None,
                'output_tokens': usage.get('completion_tokens'),
                'done_reason': choice.get('finish_reason', ''),
                'truncated': choice.get('finish_reason') == 'length',
            }
        return answer
    except TimeoutError as exc:
        raise LocalAIError('DeepSeek APIから制限時間内に回答を受信できませんでした。接続状態を確認してください。') from exc
    except HTTPError as exc:
        if exc.code in {401, 403}:
            raise LocalAIError('DeepSeek APIキーを確認してください。') from exc
        raise LocalAIError('DeepSeek APIの呼び出しに失敗しました。残高・利用制限・接続状態を確認してください。') from exc
    except (URLError, OSError, ValueError, json.JSONDecodeError) as exc:
        raise LocalAIError('DeepSeek APIに接続できません。接続設定を確認してください。') from exc


def _deepseek_query_intent(messages, model=None, redactor=None):
    """DeepSeekの関数呼び出しで、DB照会条件だけを構造化して取得する。"""
    if not DEEPSEEK_API_KEY:
        raise LocalAIError('DeepSeek APIキーが未設定です。サーバーの DEEPSEEK_API_KEY を設定してください。')
    body = {
        'model': model or DEEPSEEK_MODEL,
        'stream': False,
        'messages': redactor.redact_messages(messages) if redactor else messages,
        'thinking': {'type': 'disabled'},
        'max_tokens': 512,
        'tools': [{
            'type': 'function',
            'function': {
                'name': 'select_production_query',
                'description': 'PMの読み取り専用集計に必要な照会条件を返す。DB操作は行わない。',
                'parameters': {
                    'type': 'object',
                    'properties': {
                        'intent': {'type': 'string', 'enum': ['production', 'operator', 'scrap', 'interruption', 'overtime', 'report', 'help']},
                        'start_date': {'type': 'string', 'description': 'YYYY-MM-DD'},
                        'end_date': {'type': 'string', 'description': 'YYYY-MM-DD'},
                        'operator_name': {'type': 'string'},
                        'group_name': {'type': 'string'},
                        'process_name': {'type': 'string'},
                        'product_code': {'type': 'string'},
                        'document': {'type': 'boolean'},
                        'show_chart': {'type': 'boolean'},
                    },
                    'required': ['intent', 'start_date', 'end_date', 'operator_name', 'group_name', 'process_name', 'product_code', 'document', 'show_chart'],
                },
            },
        }],
        'tool_choice': 'required',
    }
    request = Request(
        f'{DEEPSEEK_BASE_URL}/chat/completions',
        data=json.dumps(body, ensure_ascii=False).encode('utf-8'),
        headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {DEEPSEEK_API_KEY}',
        },
        method='POST',
    )
    try:
        for _ in range(2):
            with urlopen(request, timeout=90) as response:
                payload = json.loads(response.read().decode('utf-8'))
            message = ((payload.get('choices') or [{}])[0].get('message') or {})
            tool_calls = message.get('tool_calls') or []
            if tool_calls:
                arguments = (((tool_calls[0].get('function') or {}).get('arguments')) or '').strip()
                if redactor:
                    arguments = redactor.restore_text(arguments)
                if arguments:
                    return arguments
        raise LocalAIError('DeepSeek APIが照会条件を返しませんでした。時間をおいて再度お試しください。')
    except TimeoutError as exc:
        raise LocalAIError('DeepSeek APIから制限時間内に回答を受信できませんでした。接続状態を確認してください。') from exc
    except HTTPError as exc:
        if exc.code in {401, 403}:
            raise LocalAIError('DeepSeek APIキーを確認してください。') from exc
        raise LocalAIError('DeepSeek APIの呼び出しに失敗しました。残高・利用制限・接続状態を確認してください。') from exc
    except (URLError, OSError, ValueError, json.JSONDecodeError) as exc:
        raise LocalAIError('DeepSeek APIに接続できません。接続設定を確認してください。') from exc


DEEPSEEK_AGENT_TOOLS = [
    {
        'type': 'function',
        'function': {
            'name': 'search_product',
            'description': '品番マスタを検索する。品番を含む生産実績を照会する前に必ず呼び出す。',
            'parameters': {
                'type': 'object',
                'properties': {'product_code': {'type': 'string', 'description': '利用者が入力した品番'}},
                'required': ['product_code'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'count_products',
            'description': (
                '品番マスタの件数を集計する。何も指定しなければカテゴリ別の内訳(件数)を返す。'
                '「最終品」はis_final_product、「ライン最終品」はis_line_final_productで絞り込める。'
                'それ以外の業務用語がどの項目に対応するか自明でない場合は、まず条件指定なしで呼んで'
                '実際に存在するカテゴリと件数を確認し、対応が明確でなければ推測せず利用者に確認すること。'
            ),
            'parameters': {
                'type': 'object',
                'properties': {
                    'category': {
                        'type': 'string',
                        'enum': ['ASSEMBLY', 'SINGLE', 'MATERIAL', 'PURCHASED', 'OUTSOURCED', 'UNKNOWN'],
                        'description': '絞り込むカテゴリコード。不明・未指定なら全カテゴリの内訳を返す。',
                    },
                    'is_final_product': {'type': 'boolean', 'description': '最終製品(「最終品」)かどうかで絞り込む。'},
                    'is_line_final_product': {
                        'type': 'boolean',
                        'description': 'そのラインで最後に出力される「ライン最終品」（次ラインへの中間品）かどうかで絞り込む。',
                    },
                    'is_active': {'type': 'boolean', 'description': '有効な品番だけに絞るか。既定はtrue。'},
                },
                'required': [],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'get_business_data',
            'description': '許可済みの読み取り専用集計を実行する。任意SQL、更新、削除はできない。',
            'parameters': {
                'type': 'object',
                'properties': {
                    'intent': {'type': 'string', 'enum': ['production', 'scrap', 'interruption', 'overtime']},
                    'start_date': {'type': 'string', 'description': 'YYYY-MM-DD'},
                    'end_date': {'type': 'string', 'description': 'YYYY-MM-DD'},
                    'product_code': {'type': 'string', 'description': '利用者が正式に指定した品番。生産数のみ使用する。'},
                    'process_name': {'type': 'string', 'description': '仕損の工程名。不要なら空文字。'},
                    'group_name': {'type': 'string', 'description': '残業の組織名。不要なら空文字。'},
                },
                'required': ['intent', 'start_date', 'end_date', 'product_code', 'process_name', 'group_name'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'get_missing_routing_orders',
            'description': (
                '受注画面の「ルーティング未設定の注文品」を読み取り専用で照会する。'
                'OPEN受注明細のうち、品番マスタがあり有効なルーティングがない品番だけを返す。'
                '画面と同じく品番ごとに1件へ絞り込み、得意先名・受注番号・明細は返さない。'
            ),
            'parameters': {
                'type': 'object',
                'properties': {
                    'due_date_from': {
                        'type': 'string',
                        'description': '納期開始日（YYYY-MM-DD）。省略時は画面既定の90日前から。',
                    },
                },
                'required': [],
            },
        },
    },
]

def _readonly_sql_tool(screen_context, allow_personal_data=False):
    """画面ごとの許可テーブル・列だけをDeepSeekへ提示する。"""
    return {
        'type': 'function',
        'function': {
            'name': 'execute_readonly_sql',
            'description': (
                'AI用DB辞書にある列だけを使い、読み取り専用SQLを実行する。'
                'SELECTのみ、単一文、明示列、最大件数までに限定される。'
                '既存の専用集計ツールで回答できる場合はそちらを優先し、SQLで更新・削除・DDL・個人情報取得はしない。\n'
                f"この画面で使えるテーブルと列:\n{schema_text(screen_context['id'], allow_personal_data)}"
            ),
            'parameters': {
                'type': 'object',
                'properties': {'sql': {'type': 'string', 'description': 'AI用DB辞書の列だけを明示したSELECT文'}},
                'required': ['sql'],
            },
        },
    }


DEEPSEEK_PERSONAL_OVERTIME_TOOL = {
    'type': 'function',
    'function': {
        'name': 'get_personal_overtime_threshold',
        'description': '権限がある画面だけで使える個人別残業時間のしきい値超過者集計。申請明細は返さない。',
        'parameters': {
            'type': 'object',
            'properties': {
                'start_date': {'type': 'string', 'description': 'YYYY-MM-DD'},
                'end_date': {'type': 'string', 'description': 'YYYY-MM-DD'},
                'threshold_hours': {'type': 'number', 'description': '超過判定する時間。例: 42'},
            },
            'required': ['start_date', 'end_date', 'threshold_hours'],
        },
    },
}

DEEPSEEK_EMPLOYEE_SEARCH_TOOL = {
    'type': 'function',
    'function': {
        'name': 'search_employee',
        'description': (
            '権限がある画面だけで使える社員氏名検索。姓だけなど部分一致でも検索できる。'
            '候補を確定するのはAIではなく利用者であり、1件でも利用者に確認してから使うこと。'
        ),
        'parameters': {
            'type': 'object',
            'properties': {'name': {'type': 'string', 'description': '利用者が入力した氏名（姓のみ・部分一致可、敬称は除く）'}},
            'required': ['name'],
        },
    },
}

DEEPSEEK_INDIVIDUAL_OVERTIME_TOOL = {
    'type': 'function',
    'function': {
        'name': 'get_individual_overtime',
        'description': '権限がある画面だけで使える、指定した一人の残業申請時間を承認段階別に集計する。氏名はPM内のユーザーと照合する。',
        'parameters': {
            'type': 'object',
            'properties': {
                'employee_name': {'type': 'string', 'description': '利用者が指定した氏名（敬称は除く）'},
                'start_date': {'type': 'string', 'description': 'YYYY-MM-DD'},
                'end_date': {'type': 'string', 'description': 'YYYY-MM-DD'},
                'show_total_bar': {
                    'type': 'boolean',
                    'description': (
                        '利用者が「合計グラフ」「トータルで」のように合計を含むグラフを求めている場合はtrue。'
                        '内訳(時間外・休日出勤など)だけのグラフで良い場合はfalse。'
                        '合計の数値自体はPM側が実データから計算するため、AIが数値を作る必要はない。'
                    ),
                },
            },
            'required': ['employee_name', 'start_date', 'end_date', 'show_total_bar'],
        },
    },
}


def _confirmed_product_codes(question, history):
    """利用者が正式に入力済みの品番だけを、集計ツールで使用可能にする。"""
    confirmed = set()
    for candidate in _product_code_candidates(question, history):
        code, _ = _resolve_product_code(candidate, [candidate])
        if code:
            confirmed.add(code)
    return confirmed


def _agent_product_lookup(product_code):
    """DeepSeekエージェント向けの品番マスタ照会。候補を勝手に確定しない。"""
    input_code = str(product_code or '').strip()[:50]
    registered_code, candidates = _resolve_product_code(input_code, [input_code])
    if not registered_code:
        return {
            'status': 'not_found' if not candidates else 'ambiguous',
            'input_product_code': input_code,
            'candidates': candidates,
            'instruction': '候補がある場合もAIは選ばず、利用者に正式品番の入力を依頼する。',
        }
    product = Product.objects.using(AI_DB_ALIAS).filter(product_code=registered_code).values('product_code', 'product_name').first()
    return {
        'status': 'found',
        'product_code': registered_code,
        'product_name': (product or {}).get('product_name', ''),
    }


def _agent_product_category_counts(arguments):
    """品番マスタの件数を集計する。category・is_final_product・is_line_final_productで絞り込める。"""
    category_labels = dict(Product.CATEGORY_CHOICES)
    is_active = arguments.get('is_active')
    is_active = True if is_active is None else bool(is_active)
    queryset = Product.objects.using(AI_DB_ALIAS).filter(is_active=is_active)
    filters_applied = {'is_active': is_active}

    category = str(arguments.get('category') or '').strip().upper()
    if category:
        if category not in category_labels:
            return {
                'status': 'invalid_request',
                'detail': f'カテゴリ「{category}」は存在しません。',
                'valid_categories': [{'code': code, 'label': label} for code, label in Product.CATEGORY_CHOICES],
            }
        queryset = queryset.filter(category=category)
        filters_applied['category'] = category

    if arguments.get('is_final_product') is not None:
        value = bool(arguments['is_final_product'])
        queryset = queryset.filter(is_final_product=value)
        filters_applied['is_final_product'] = value

    if arguments.get('is_line_final_product') is not None:
        value = bool(arguments['is_line_final_product'])
        queryset = queryset.filter(is_line_final_product=value)
        filters_applied['is_line_final_product'] = value

    if len(filters_applied) > 1:
        return {
            'status': 'ok',
            'source': '品番マスタ（条件別件数）',
            'filters': filters_applied,
            'count': queryset.count(),
        }
    rows = list(queryset.values('category').annotate(count=Count('id')).order_by('-count'))
    return {
        'status': 'ok',
        'source': '品番マスタ（カテゴリ別件数）',
        'is_active': is_active,
        'total': queryset.count(),
        'breakdown': [
            {
                'category': row['category'] or 'NULL',
                'category_label': category_labels.get(row['category'], 'カテゴリ未設定'),
                'count': row['count'],
            }
            for row in rows
        ],
    }


def _agent_date_range(arguments):
    """エージェントの期間引数を検証し、許可範囲に制限する。"""
    try:
        start = date.fromisoformat(str(arguments.get('start_date') or ''))
        end = date.fromisoformat(str(arguments.get('end_date') or ''))
    except (TypeError, ValueError):
        return None, None, {'status': 'invalid_request', 'detail': '開始日と終了日はYYYY-MM-DDで指定してください。'}
    if start > end or (end - start).days >= MAX_RANGE_DAYS:
        return None, None, {'status': 'invalid_request', 'detail': f'集計期間は{MAX_RANGE_DAYS}日未満で指定してください。'}
    return start, end, None


def _agent_business_data(arguments, confirmed_product_codes, screen_context):
    """許可済み集計関数だけをDeepSeekのツール呼び出しから実行する。"""
    start, end, error = _agent_date_range(arguments)
    if error:
        return error, None, None
    intent = str(arguments.get('intent') or '').strip()
    product_code = str(arguments.get('product_code') or '').strip()[:50]
    process_name = str(arguments.get('process_name') or '').strip()[:100]
    group_name = str(arguments.get('group_name') or '').strip()[:100]

    if intent not in screen_context['allowed_intents']:
        return {
            'status': 'invalid_request',
            'detail': f"{screen_context['label']}画面からは、この集計種別を参照できません。",
        }, None, None

    try:
        if intent == 'production':
            if product_code:
                registered_code, candidates = _resolve_product_code(product_code, [product_code])
                if not registered_code:
                    return {
                        'status': 'product_not_found' if not candidates else 'product_confirmation_required',
                        'input_product_code': product_code,
                        'candidates': candidates,
                        'instruction': '候補をAIが選んで集計してはいけない。利用者に正式品番を確認する。',
                    }, None, None
                if registered_code not in confirmed_product_codes:
                    return {
                        'status': 'product_confirmation_required',
                        'product_code': registered_code,
                        'instruction': 'この品番は利用者が正式に指定していない。利用者に確認する。',
                    }, None, None
                product_code = registered_code
            facts = _production_facts(start, end, product_code=product_code)
            source = f"{facts['source']}（品番: {product_code}）" if product_code else '工程実績（生産数）'
            data = {
                'status': 'ok', 'source': source,
                'period': {'start_date': start.isoformat(), 'end_date': end.isoformat()},
                'product_code': product_code or '全品番',
                'production_quantity': facts['total'], 'record_count': facts['records'],
                'daily': list(zip(facts['labels'], facts['values'])), 'by_process': facts['processes'],
            }
            return data, {'labels': facts['labels'], 'values': facts['values'], 'series_label': '個'}, data['period']
        if intent == 'scrap':
            facts = _scrap_facts(start, end, process_name)
            source = f'{process_name}工程の確定仕損記録' if process_name else '確定仕損記録'
            data = {
                'status': 'ok', 'source': source,
                'period': {'start_date': start.isoformat(), 'end_date': end.isoformat()},
                'scrap_quantity': facts['total'], 'record_count': facts['records'], 'by_reason': facts['items'],
            }
            return data, {'labels': facts['labels'], 'values': facts['values'], 'series_label': '個'}, data['period']
        if intent == 'interruption':
            facts = _interruption_facts(start, end)
            data = {
                'status': 'ok', 'source': 'ブレーキライン作業記録（中断・強制終了）',
                'period': {'start_date': start.isoformat(), 'end_date': end.isoformat()},
                'interruption_count': facts['total'], 'by_reason': facts['items'],
            }
            return data, {'labels': facts['labels'], 'values': facts['values'], 'series_label': '件'}, data['period']
        if intent == 'overtime':
            facts = _overtime_facts(start, end, group_name)
            data = {
                'status': 'ok', 'source': '残業申請時間（承認段階別・グループ集計）',
                'period': {'start_date': start.isoformat(), 'end_date': end.isoformat()},
                'group_name': facts['group_name'],
                'final_approved_hours': facts['final_approved_hours'],
                'pending_final_approval_hours': facts['pending_final_approval_hours'],
            }
            return data, {'labels': facts['labels'], 'values': facts['values'], 'series_label': '時間'}, data['period']
    except LocalAIError as exc:
        return {'status': 'invalid_request', 'detail': str(exc)}, None, None
    return {'status': 'invalid_request', 'detail': 'この集計種別は利用できません。'}, None, None


def _personal_overtime_threshold(arguments):
    """個人別の残業申請時間を、しきい値超過者だけへ最小化して集計する。"""
    start, end, error = _agent_date_range(arguments)
    if error:
        return error, None, None
    try:
        threshold = Decimal(str(arguments.get('threshold_hours')))
    except (InvalidOperation, TypeError, ValueError):
        return {'status': 'invalid_request', 'detail': 'しきい値の時間を数値で指定してください。'}, None, None
    if threshold < 0 or threshold > Decimal('300'):
        return {'status': 'invalid_request', 'detail': 'しきい値は0〜300時間で指定してください。'}, None, None
    queryset = OvertimeApplication.objects.using(AI_DB_ALIAS).filter(
        work_date__gte=start,
        work_date__lte=end,
        application_type__in=['overtime', 'holiday'],
        status__in=['approved_supervisor', 'approved_chief', 'approved_manager'],
    )
    rows = list(queryset.values(
        'applicant_id', 'applicant__last_name', 'applicant__first_name', 'applicant__username'
    ).annotate(
        hours=Sum('hours'), midnight_hours=Sum('midnight_hours'), records=Count('id')
    ))
    exceeders = []
    for row in rows:
        total_hours = (row['hours'] or Decimal('0')) + (row['midnight_hours'] or Decimal('0'))
        if total_hours <= threshold:
            continue
        employee_name = f"{row['applicant__last_name']} {row['applicant__first_name']}".strip()
        exceeders.append({
            'employee_name': employee_name or row['applicant__username'],
            'total_hours': float(total_hours),
            'record_count': row['records'],
        })
    exceeders.sort(key=lambda row: (-row['total_hours'], row['employee_name']))
    period = {'start_date': start.isoformat(), 'end_date': end.isoformat()}
    data = {
        'status': 'ok',
        'source': '残業申請時間（個人別・しきい値超過）',
        'period': period,
        'threshold_hours': float(threshold),
        'exceeders': exceeders,
    }
    chart = {
        'labels': [row['employee_name'] for row in exceeders],
        'values': [row['total_hours'] for row in exceeders],
        'series_label': '時間',
    }
    return data, chart, period


def _agent_employee_lookup(name, redactor):
    """DeepSeekエージェント向けの社員氏名検索。部分一致（姓のみ等）を許可し、候補は確定せず利用者に確認させる。"""
    from django.contrib.auth import get_user_model

    query = str(name or '').strip()[:50]
    if redactor:
        query = redactor.restore_text(query)
    normalized_query = _normalized_text(query).removesuffix('さん').removesuffix('氏')
    if not normalized_query:
        return {'status': 'invalid_request', 'detail': '氏名を指定してください。'}
    matches = []
    for user in get_user_model().objects.using(AI_DB_ALIAS).filter(is_active=True).only('id', 'username', 'first_name', 'last_name'):
        full_name = f'{user.last_name} {user.first_name}'.strip() or user.username
        if normalized_query in _normalized_text(full_name):
            matches.append(full_name)
    matches = sorted(set(matches))
    if not matches:
        return {
            'status': 'not_found', 'input_name': query,
            'instruction': '該当する社員がいない。氏名の誤りがないか利用者に確認する。',
        }
    if len(matches) == 1:
        return {
            'status': 'found', 'employee_name': matches[0],
            'instruction': 'この氏名で良いか必ず利用者に確認してから get_individual_overtime を呼ぶこと。確認なしに断定してはいけない。',
        }
    return {
        'status': 'ambiguous', 'candidates': matches[:5],
        'instruction': '複数該当する。候補を提示し、利用者が選んだ氏名で get_individual_overtime を呼ぶこと。AIが勝手に選んではいけない。',
    }


def _agent_individual_overtime(arguments, redactor):
    """DeepSeekが指定した一人の残業申請時間を、承認段階別に集計する。氏名は伏字→復元してから照合する。"""
    start, end, error = _agent_date_range(arguments)
    if error:
        return error, None, None
    name = str(arguments.get('employee_name') or '').strip()[:50]
    if redactor:
        name = redactor.restore_text(name)
    if not name:
        return {'status': 'invalid_request', 'detail': '氏名を指定してください。'}, None, None
    try:
        facts = _individual_overtime_facts(start, end, name)
    except LocalAIError as exc:
        return {'status': 'invalid_request', 'detail': str(exc)}, None, None
    period = {'start_date': start.isoformat(), 'end_date': end.isoformat()}
    data = {
        'status': 'ok',
        'source': '残業申請時間（指定社員・承認段階別）',
        'period': period,
        'employee_name': facts['employee_name'],
        'total_hours': facts['total_hours'],
        'total_records': facts['total_records'],
        'items': facts['items'],
    }
    labels = list(facts['labels'])
    values = list(facts['values'])
    # 合計棒を含めるかはDeepSeekの判断(show_total_bar)に従う。数値自体はDBから計算した実データのみを使う。
    if arguments.get('show_total_bar') is True and len(facts['items']) > 1:
        labels.append('合計')
        values.append(facts['total_hours'])
    chart = {'labels': labels, 'values': values, 'series_label': '時間'}
    return data, chart, period


def _deepseek_agent_chat(
    question, history, model=None, redactor=None, allow_personal_overtime=False, screen_context=None,
    base_url=None, api_key=None, default_model=None, provider_key='deepseek', provider_label='DeepSeek',
    knowledge_document_ids=None, vision_attachment=None,
):
    """DeepSeek互換のOpenAI形式APIが、読み取り専用ツールを選び、段階的に調査して回答する。"""
    base_url = base_url or DEEPSEEK_BASE_URL
    api_key = api_key or DEEPSEEK_API_KEY
    default_model = default_model or DEEPSEEK_MODEL
    if not api_key:
        raise LocalAIError(f'{provider_label} APIキーが未設定です。サーバーの環境変数を設定してください。')
    recent_period = _recent_data_period(history)
    selected_option = _selected_data_option(question, history)
    screen_context = screen_context or resolve_screen_context(None)
    knowledge_chunks = retrieve_knowledge(question, screen_context, document_ids=knowledge_document_ids)
    retrieved_knowledge = knowledge_prompt(knowledge_chunks)
    knowledge_source = knowledge_source_label(knowledge_chunks)
    allowed_tools = screen_context['allowed_tools']
    available_tools = [
        tool for tool in DEEPSEEK_AGENT_TOOLS
        if tool['function']['name'] in allowed_tools
    ]
    if 'execute_readonly_sql' in allowed_tools:
        available_tools.append(_readonly_sql_tool(screen_context, allow_personal_overtime))
    if allow_personal_overtime:
        available_tools.extend(
            tool for tool in (
                DEEPSEEK_PERSONAL_OVERTIME_TOOL,
                DEEPSEEK_EMPLOYEE_SEARCH_TOOL,
                DEEPSEEK_INDIVIDUAL_OVERTIME_TOOL,
            )
            if tool['function']['name'] in allowed_tools
        )
    order_context_instruction = ''
    if screen_context['id'] == 'orders':
        order_context_instruction = (
            '受注画面では、ルーティング未設定の注文品について質問された場合は、'
            '必ずget_missing_routing_ordersを呼んでください。'
            '返された数量は代表受注明細の数量であり、全受注明細の合計ではないことを守ってください。'
            '得意先名、受注番号、受注明細は結果に含まれないため、推測・要求・回答してはいけません。\n'
        )
    pdf_page_notice = ''
    if vision_attachment and vision_attachment['kind'] == 'PDF':
        sent_pages = len(vision_attachment['data_urls'])
        total_pages = vision_attachment['total_pages']
        if total_pages > sent_pages:
            pdf_page_notice = (
                f'添付PDFは全{total_pages}ページ中、先頭{sent_pages}ページだけを確認しています。'
                f'この回答には「{sent_pages + 1}ページ以降はまだ確認していません」と必ず明記してください。'
                '未確認ページの内容を推測・要約してはいけません。\n'
            )
    messages = [{
        'role': 'system',
        'content': (
            'あなたは本社の生産管理を支援する社内AIです。利用者の質問を自分で調査して回答してください。\n'
            f"今回の起点画面: {screen_context['label']}。この画面に許可されたツール以外を使ってはいけません。\n"
            '利用できるのは品番マスタ検索、許可済みの読み取り専用集計ツール、および許可された場合のAI用DB辞書SQLだけです。'
            'SQLはexecute_readonly_sqlでSELECT一文だけを使えます。更新、削除、DDL、管理SQL、個人情報取得はできません。\n'
            'SQLで「〇〇別」の集計を聞かれたら、そのキーとなるコード列(品番ならproduct_code)でGROUP BYし、回答の表にはコードを先頭列に出してください。'
            '名称は併記にとどめ、名称だけの表にしてはいけません(別のコードに同じ名称がある場合があります)。\n'
            + order_context_instruction +
            '品番を含む質問では、必ず最初にsearch_productを呼び、見つからなければ「現在この品番はありません」と回答してください。候補を勝手に選んではいけません。\n'
            '品番マスタの件数質問ではcount_productsを使ってください。「最終品」はis_final_product、'
            '「ライン最終品」はis_line_final_productで絞り込めます。それ以外の業務用語がDB上の分類'
            '(カテゴリ等)に対応するか自明でない場合は、まず条件指定なしで呼んで実際に存在するカテゴリと'
            '件数を確認してください。用語がどの項目に対応するか自分で判断できない場合は、推測せず'
            '確認した内訳を提示して利用者に確認してください。\n'
            '生産数・仕損・中断・残業の数値を答えるときは、必ずget_business_dataを呼び、ツール結果にない数値を作らないでください。\n'
            '個人別残業は、search_employee・get_individual_overtime・get_personal_overtime_threshold が利用可能な場合だけ使用してください。'
            '注意: 個人名は外部送信前に「作業者1」の形式の識別子に変換されています。これは氏名として'
            'そのまま検索・集計に使える文字列です。質問文に「作業者12」のような表記があれば、'
            'それをsearch_employeeやget_individual_overtimeのemployee_name引数へそのまま渡し、'
            '通常の氏名の質問と同じ手順で処理してください。\n'
            '指定した一人の合計を聞かれたら、氏名(一時IDを含む)が姓だけ・曖昧でも必ず最初にsearch_employeeで検索し、'
            '候補が1件でも「○○さんですか？」のように利用者に確認してから get_individual_overtime を呼んでください。'
            '複数候補がある場合は候補を提示し、利用者が選んだ氏名だけを使ってください。AIが候補を勝手に確定してはいけません。'
            '重要: 氏名はsearch_employeeまたはget_individual_overtimeの結果に実際に含まれる文字列だけを使ってください。'
            'ツールを呼ばずに氏名を記憶・推測・生成することは重大な誤りです。ツールを呼んでいないのに'
            '「検索したところ」「見つかりました」のように述べてはいけません。'
            'しきい値超過者の抽出を聞かれたら get_personal_overtime_threshold を選んでください。'
            'get_individual_overtime の結果を使うときは、必ず最初に合計時間(total_hours)と件数(total_records)を明示し、'
            'その後に時間外・休日出勤などの内訳(items)を説明してください。合計を省略してはいけません。'
            'get_individual_overtime の show_total_bar は、利用者が「合計グラフ」のように合計を含むグラフを'
            '求めているかどうかをあなたが判断して指定してください。合計の数値はPM側が実データから計算するので、'
            'あなたが数値を作る必要はありません。'
            '結果に含まれる氏名・一時ID以外の個人情報を推測してはいけません。\n'
            'tool結果のsourceは画面へ根拠として表示されます。回答では結論を先に短く伝え、必要なら日別傾向を説明してください。\n'
            'グラフはツールを呼んだ回だけ画面側に自動描画されます。ツールを呼ばずに記憶だけで答えた回には'
            'グラフは出ません。「グラフをください」と言われて記憶だけで答える場合は、'
            '「グラフを表示するには、もう一度集計しますか？」のように確認するか、その場でツールを呼び直してください。'
            'ツールを呼んでいないのに「グラフは画面側に表示されます」のように、実際に出ていないグラフを'
            '出たかのように説明してはいけません。「グラフ機能はない」という誤った説明も避けてください。\n'
            'selected_data_option がある場合は、利用者が直前の選択肢を選んだものとして解釈し、必要なツールを自分で選んでください。\n'
            f'本日: {date.today().isoformat()}。直近のDB集計期間: {json.dumps(recent_period, ensure_ascii=False)}。'
            f'選択済みの業務候補: {json.dumps(selected_option, ensure_ascii=False)}。'
            + (
                'このターンには利用者が明示添付した画像またはPDFページがあります。内容・文字・設備・帳票の見た目を確認し、'
                '見えていないことを推測で断定しないでください。\n'
                if vision_attachment else ''
            )
            + pdf_page_notice
            + retrieved_knowledge
        ),
    }]
    messages.extend({'role': row['role'], 'content': row['content']} for row in history[-12:])
    messages.append({
        'role': 'user',
        'content': [
            {'type': 'text', 'text': question},
            *[
                {'type': 'image_url', 'image_url': {'url': data_url}}
                for data_url in vision_attachment['data_urls']
            ],
        ] if vision_attachment else question,
    })
    confirmed_codes = _confirmed_product_codes(question, history)
    source = f'{provider_label} APIとの会話'
    if vision_attachment:
        source += f" / 添付{vision_attachment['kind']}: {vision_attachment['name']}"
        if vision_attachment['kind'] == 'PDF' and vision_attachment['total_pages'] > len(vision_attachment['data_urls']):
            source += f"（先頭{len(vision_attachment['data_urls'])}/{vision_attachment['total_pages']}ページ）"
    period = None
    chart = None
    payload = {}
    # そのターンで実際にDeepSeekへ提示された一時ID(＝根拠あり)だけを復元対象にする。
    # ツールを呼ばず推測した一時IDが実在社員名に化けるのを防ぐ。
    grounded_placeholders = set()

    try:
        for attempt in range(AGENT_MAX_ROUNDS):
            redacted_messages = redactor.redact_messages(messages) if redactor else messages
            if redactor:
                for row in redacted_messages:
                    grounded_placeholders.update(REDACTION_PLACEHOLDER_PATTERN.findall(str(row.get('content', ''))))
            body = {
                'model': model or default_model,
                'stream': False,
                'messages': redacted_messages,
                'temperature': 0.4,
                'max_tokens': AGENT_MAX_TOKENS,
                'tools': available_tools,
            }
            if provider_key == 'deepseek':
                # DeepSeek独自パラメータ。複数ツールを跨ぐ調査・分析のため思考モードを有効にする
                # （OpenAI互換の他プロバイダには送らない）。意図解析のJSON出力は別関数で無効のまま。
                body['thinking'] = {'type': 'enabled'}
            if provider_key == 'openrouter':
                # 無料枠が特定の提供元(例: ModelRun)だけで混雑する場合、他の提供元へ自動振り分けする。
                body['provider'] = {'allow_fallbacks': True}
                # OpenRouter共通の推論パラメータ。DeepSeekの thinking に相当する。
                body['reasoning'] = {'enabled': True}
            # 「グラフ」「もう一回」等は、記憶だけで答えて実データが伴わない誤答が多いため、
            # 最初の1回だけツール呼び出しを必須化する。どのツールを呼ぶかはDeepSeekの判断のまま。
            if attempt == 0 and available_tools and any(term in question for term in FORCE_TOOL_CALL_TERMS):
                body['tool_choice'] = 'required'
            request = Request(
                f'{base_url}/chat/completions',
                data=json.dumps(body, ensure_ascii=False).encode('utf-8'),
                headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {api_key}'},
                method='POST',
            )
            with urlopen(request, timeout=120) as response:
                payload = json.loads(response.read().decode('utf-8'))
            choice = (payload.get('choices') or [{}])[0]
            message = choice.get('message') or {}
            tool_calls = message.get('tool_calls') or []
            if not tool_calls:
                answer = str(message.get('content') or '').strip()
                if redactor:
                    used_placeholders = set(REDACTION_PLACEHOLDER_PATTERN.findall(answer))
                    if used_placeholders - grounded_placeholders:
                        raise LocalAIError(
                            'AIの回答に、ツールで確認していない対象が含まれていたため回答を中止しました。'
                            '氏名を確認のうえ、もう一度お尋ねください。'
                        )
                    answer = redactor.restore_text(answer)
                if not answer:
                    raise LocalAIError(f'{provider_label} APIから回答が返りませんでした。時間をおいて再度お試しください。')
                usage = payload.get('usage') or {}
                display_source = ' / '.join(item for item in (source, knowledge_source) if item)
                return answer, {
                    'provider': provider_key, 'model': payload.get('model', model or default_model),
                    'duration_seconds': None, 'output_tokens': usage.get('completion_tokens'),
                    'done_reason': choice.get('finish_reason', ''), 'truncated': choice.get('finish_reason') == 'length',
                }, display_source, period, chart

            assistant_message = {
                'role': 'assistant', 'content': message.get('content') or '', 'tool_calls': tool_calls,
            }
            # 思考モードのツール呼び出しでは、同一ターン内のreasoning_contentを次の呼び出しへ戻す必要がある。
            if message.get('reasoning_content'):
                assistant_message['reasoning_content'] = message['reasoning_content']
            # OpenRouterは推論をreasoning_detailsで返す。ツール呼び出しの継続時は同じ内容を戻す。
            if message.get('reasoning_details'):
                assistant_message['reasoning_details'] = message['reasoning_details']
            messages.append(assistant_message)
            for tool_call in tool_calls:
                function = tool_call.get('function') or {}
                try:
                    arguments = json.loads(function.get('arguments') or '{}')
                except json.JSONDecodeError:
                    result, tool_chart, tool_period = {'status': 'invalid_request', 'detail': 'ツール引数が不正です。'}, None, None
                else:
                    if function.get('name') == 'search_product' and 'search_product' in allowed_tools:
                        result, tool_chart, tool_period = _agent_product_lookup(arguments.get('product_code')), None, None
                    elif function.get('name') == 'count_products' and 'count_products' in allowed_tools:
                        result, tool_chart, tool_period = _agent_product_category_counts(arguments), None, None
                    elif function.get('name') == 'get_missing_routing_orders' and 'get_missing_routing_orders' in allowed_tools:
                        result, tool_chart, tool_period = get_missing_routing_orders(arguments)
                    elif function.get('name') == 'execute_readonly_sql' and 'execute_readonly_sql' in allowed_tools:
                        result, tool_chart, tool_period = execute_readonly_sql(
                            arguments, screen_context, allow_personal_overtime, redactor,
                        )
                    elif function.get('name') == 'get_business_data' and 'get_business_data' in allowed_tools:
                        result, tool_chart, tool_period = _agent_business_data(arguments, confirmed_codes, screen_context)
                    elif function.get('name') == 'get_personal_overtime_threshold' and allow_personal_overtime and 'get_personal_overtime_threshold' in allowed_tools:
                        result, tool_chart, tool_period = _personal_overtime_threshold(arguments)
                    elif function.get('name') == 'search_employee' and allow_personal_overtime and 'search_employee' in allowed_tools:
                        result, tool_chart, tool_period = _agent_employee_lookup(arguments.get('name'), redactor), None, None
                    elif function.get('name') == 'get_individual_overtime' and allow_personal_overtime and 'get_individual_overtime' in allowed_tools:
                        result, tool_chart, tool_period = _agent_individual_overtime(arguments, redactor)
                    else:
                        result, tool_chart, tool_period = {'status': 'invalid_request', 'detail': '許可されていないツールです。'}, None, None
                if result.get('status') == 'ok':
                    source = result.get('source', source)
                    period = tool_period
                    chart = tool_chart
                messages.append({
                    'role': 'tool', 'tool_call_id': tool_call.get('id', ''),
                    'content': json.dumps(limit_external_result_rows(result), ensure_ascii=False),
                })
        raise LocalAIError(f'{provider_label} APIが調査を完了できませんでした。質問を具体的にして再度お試しください。')
    except TimeoutError as exc:
        raise LocalAIError(f'{provider_label} APIから制限時間内に回答を受信できませんでした。接続状態を確認してください。') from exc
    except HTTPError as exc:
        if exc.code in {401, 403}:
            raise LocalAIError(f'{provider_label} APIキーを確認してください。') from exc
        if exc.code == 429:
            raise LocalAIError(
                f'【レート制限】{provider_label} APIが現在レート制限中です。時間をおいて再試行するか、'
                '無料枠以外のモデル・自分のプロバイダキーの設定を検討してください。'
            ) from exc
        if exc.code == 402:
            raise LocalAIError(
                f'【残高不足】{provider_label} APIの無料枠(トライアル残高)を使い切りました。'
                'クレジットを追加購入するか、無料モデルに切り替えてください。'
            ) from exc
        raise LocalAIError(f'{provider_label} APIの呼び出しに失敗しました。残高・利用制限・接続状態を確認してください。') from exc
    except (URLError, OSError, ValueError, json.JSONDecodeError) as exc:
        raise LocalAIError(f'{provider_label} APIに接続できません。接続設定を確認してください。') from exc


def _chat(messages, provider, json_mode=False, num_predict=180, timeout=90, include_metadata=False, model=None, redactor=None):
    if provider == 'deepseek':
        return _deepseek_chat(messages, json_mode, num_predict, timeout, include_metadata, model, redactor)
    return _ollama_chat(messages, json_mode, num_predict, timeout, include_metadata)


def _product_code_candidates(question, history):
    """ユーザーが明示した品番候補を、空白区切りを含めて会話から集める。"""
    messages = [str(question or '')]
    messages.extend(
        str(row.get('content', ''))
        for row in reversed(history)
        if row.get('role') == 'user'
    )
    candidates = []
    for message in messages:
        normalized_message = unicodedata.normalize('NFKC', message)
        # 音声入力などの「V123 の 03B」を、枝番付きの品番候補として先に扱う。
        for match in PRODUCT_CODE_JA_SUFFIX_PATTERN.finditer(normalized_message):
            code = f'{match.group(1)}-{match.group(2)}'.upper()[:50]
            if code.lower() not in {item.lower() for item in candidates}:
                candidates.append(code)
        for match in PRODUCT_CODE_PATTERN.finditer(normalized_message):
            code = match.group(1)[:50]
            if code.lower() not in {item.lower() for item in candidates}:
                candidates.append(code)
        for match in PRODUCT_CODE_LOOSE_PATTERN.finditer(normalized_message):
            code = match.group(1).strip()[:50]
            normalized_code = re.sub(r'[^A-Za-z0-9]', '', code)
            if (
                len(normalized_code) >= 6
                and any(char.isalpha() for char in normalized_code)
                and any(char.isdigit() for char in normalized_code)
                and code.lower() not in {item.lower() for item in candidates}
            ):
                candidates.append(code)
    return candidates


def _product_code_key(value):
    """品番の照合用に空白・ハイフン・英字の表記揺れだけを吸収する。"""
    return re.sub(r'[^A-Z0-9]', '', unicodedata.normalize('NFKC', str(value or '')).upper())


def _resolve_product_code(product_code, product_candidates):
    """正式品番へ解決し、曖昧な入力時は候補だけを返す。"""
    raw_codes = [str(product_code or '').strip(), *product_candidates]
    raw_codes = [code for code in raw_codes if _product_code_key(code)]
    master_codes = list(Product.objects.using(AI_DB_ALIAS).values_list('product_code', flat=True))
    master_keys = {code: _product_code_key(code) for code in master_codes}
    raw_keys = [_product_code_key(code) for code in raw_codes]
    for raw_code in raw_codes:
        raw_key = _product_code_key(raw_code)
        # 枝番を含む候補がある場合、親品番だけの完全一致を優先してはいけない。
        if any(key.startswith(raw_key) and len(key) > len(raw_key) for key in raw_keys):
            continue
        exact = [code for code, key in master_keys.items() if key == raw_key]
        if len(exact) == 1:
            return exact[0], []

    scored = {}
    for raw_code in raw_codes:
        raw_key = _product_code_key(raw_code)
        if len(raw_key) < 6 or not any(char.isalpha() for char in raw_key) or not any(char.isdigit() for char in raw_key):
            continue
        for master_code, master_key in master_keys.items():
            score = SequenceMatcher(None, raw_key, master_key).ratio()
            if score >= 0.78:
                scored[master_code] = max(scored.get(master_code, 0), score)
    candidates = [code for code, _ in sorted(scored.items(), key=lambda item: (-item[1], item[0]))[:3]]
    return None, candidates


def _is_all_products_request(question):
    """明示的な全品番指定では、以前の品番条件を引き継がない。"""
    return any(term in str(question or '') for term in ('全品番', 'すべての品番', '全ての品番', '全体の生産', '総生産'))


def _selected_data_option(question, history):
    """直前の業務選択肢に対する番号回答だけを、対応する集計質問へ復元する。"""
    selected_number = unicodedata.normalize('NFKC', str(question or '')).strip()
    option = DATA_OPTION_SELECTIONS.get(selected_number)
    if not option:
        return None
    for row in reversed(history):
        if row.get('role') != 'assistant':
            continue
        content = str(row.get('content', ''))
        if all(term in content for term in option['terms']):
            return option
        return None
    return None


def _recent_data_period(history):
    """会話中の直近のDB集計期間だけを、次の照会条件へ引き継ぐ。"""
    for row in reversed(history):
        period = row.get('period') if row.get('role') == 'assistant' else None
        if not isinstance(period, dict):
            continue
        try:
            start = date.fromisoformat(str(period.get('start_date') or ''))
            end = date.fromisoformat(str(period.get('end_date') or ''))
        except ValueError:
            continue
        return {'start_date': start.isoformat(), 'end_date': end.isoformat()}
    return None


def _date_range(question, history, provider, model=None, redactor=None):
    today = date.today()
    start_default = today.replace(day=1)
    product_candidates = _product_code_candidates(question, history)
    selected_option = _selected_data_option(question, history)
    prompt = {
        'today': today.isoformat(),
        'default_start_date': start_default.isoformat(),
        'default_end_date': today.isoformat(),
        'recent_context': history[-4:],
        'current_request': question,
        'user_product_code_candidates': product_candidates,
        'selected_data_option': selected_option,
        'recent_data_period': _recent_data_period(history),
    }
    messages = [
        {
            'role': 'system',
            'content': (
                '社内生産AIのリクエスト分類器です。'
                'このチャットは本社の生産管理を基本対象とする。'
                'intent は production, operator, scrap, interruption, overtime, report, help のいずれか。'
                'production=生産数・出来高、operator=特定作業者の生産数、scrap=仕損・不良、'
                'interruption=ブレーキラインの中断・強制終了、overtime=残業時間、report=複合報告書。'
                '入荷・購買・在庫・受注・出荷・サプライヤーなど上記に該当しない質問は help にすること。'
                '日付範囲は明示がなければ与えられた既定値。operator_name は質問に明記された作業者名だけ。'
                'overtime は残業時間の質問。質問中に「板金の残業」または「板金グループの残業」とあれば group_name は必ず「板金」。'
                '「グループ」という語がなくても組織名をgroup_nameに抽出し、末尾の「グループ」は含めない。'
                'process_name は仕損が起きた工程名だけ。工程指定がなければ空文字。'
                '質問または直近会話でユーザーが品番を明記している場合、product_code にその品番を正確に抽出する。'
                'user_product_code_candidates がある場合は、現在の質問が明示的な全品番集計でない限り、その候補を必ず引き継ぐ。'
                '品番指定がなければ空文字。'
                'selected_data_option がある場合、現在の番号回答はその label の質問を選択したものとして、指定された intent を必ず設定する。'
                'recent_data_period があり、質問で期間を変更していない場合は、その開始日と終了日を引き継ぐ。'
                'document は報告書・文書作成の依頼なら true。show_chart は図表・グラフ表示を頼まれた場合だけ true。'
                '日付・対象が会話中にあれば必ず引き継ぐ。'
            ),
        },
        {'role': 'user', 'content': json.dumps(prompt, ensure_ascii=False)},
    ]
    if provider == 'deepseek':
        raw = _deepseek_query_intent(messages, model=model, redactor=redactor)
    else:
        messages[0]['content'] += (
            '次のJSONだけを返してください。'
            '形式: {"intent":"production","start_date":"YYYY-MM-DD","end_date":"YYYY-MM-DD","operator_name":"","group_name":"","process_name":"","product_code":"","document":false,"show_chart":false}'
        )
        raw = _chat(messages, provider, json_mode=True, num_predict=256, timeout=90, model=model, redactor=redactor)
    try:
        plan = json.loads(raw)
        if plan.get('intent') not in {'production', 'operator', 'scrap', 'interruption', 'overtime', 'report', 'help'}:
            raise ValueError('intent')
        start = date.fromisoformat(plan.get('start_date', ''))
        end = date.fromisoformat(plan.get('end_date', ''))
        if start > end or (end - start).days >= MAX_RANGE_DAYS:
            raise ValueError('range')
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise LocalAIError('質問の期間を読み取れませんでした。開始日と終了日を含めて聞き直してください。') from exc
    plan['start_date'] = start
    plan['end_date'] = end
    plan['operator_name'] = str(plan.get('operator_name') or '').strip()[:50]
    plan['group_name'] = str(plan.get('group_name') or '').strip()[:100]
    plan['process_name'] = str(plan.get('process_name') or '').strip()[:100]
    plan['product_code'] = str(plan.get('product_code') or '').strip()[:50]
    if selected_option:
        plan['intent'] = selected_option['intent']
    # AIの応答漏れで、明示済みの品番が全品番集計に化けないようにする。
    if plan['intent'] in {'production', 'operator'} and product_candidates and not _is_all_products_request(question):
        plan['product_code'] = product_candidates[0]
    if plan['product_code'] or product_candidates:
        registered_code, matched_candidates = _resolve_product_code(plan['product_code'], product_candidates)
        if not registered_code:
            plan['product_not_found'] = plan['product_code'] or product_candidates[0]
            plan['product_match_candidates'] = matched_candidates
        else:
            plan['product_code'] = registered_code
    plan['document'] = plan.get('document') is True
    plan['show_chart'] = plan.get('show_chart') is True
    if plan['intent'] == 'operator' and not plan['operator_name']:
        raise LocalAIError('作業者名を特定できませんでした。例：「作業者Aの今月の生産数を見せて」のように指定してください。')
    if plan['intent'] == 'overtime' and not plan['group_name']:
        raise LocalAIError('残業時間を集計するグループ名を指定してください。')
    return plan


def _normalized_text(value):
    """氏名照合用に全角半角と空白の表記揺れだけを吸収する。"""
    return re.sub(r'\s+', '', unicodedata.normalize('NFKC', str(value or '')))


def _month_period(year_text, month_text):
    year = int(year_text or date.today().year)
    month = int(month_text)
    if not 1 <= month <= 12:
        raise LocalAIError('月の指定を読み取れませんでした。1月〜12月で指定してください。')
    return date(year, month, 1), date(year, month, monthrange(year, month)[1])


def _find_user_by_name(name):
    """氏名完全一致だけを許可し、候補推測による別人の集計を防ぐ。"""
    from django.contrib.auth import get_user_model

    requested = _normalized_text(name).removesuffix('さん').removesuffix('氏')
    matches = []
    for user in get_user_model().objects.using(AI_DB_ALIAS).filter(is_active=True).only(
        'id', 'username', 'first_name', 'last_name'
    ):
        full_name = _normalized_text(f'{user.last_name}{user.first_name}')
        if requested in {full_name, _normalized_text(user.username)}:
            matches.append(user)
    if not matches:
        raise LocalAIError(f'「{name}」に一致する社員を確認できませんでした。氏名を確認してください。')
    if len(matches) > 1:
        raise LocalAIError(f'「{name}」に一致する社員が複数います。フルネームで指定してください。')
    return matches[0]


def _individual_overtime_facts(start, end, name):
    """指定した一人の提出済み時間外・休日出勤申請を、種別・承認段階別に集計する。"""
    user = _find_user_by_name(name)
    statuses = {
        'submitted': '申請中',
        'approved_leader': 'リーダー承認済み',
        'approved_supervisor': '班長承認済み',
        'approved_chief': '係長承認済み',
        'approved_manager': '最終承認済み',
    }
    type_labels = {'overtime': '時間外', 'holiday': '休日出勤'}
    rows = list(
        OvertimeApplication.objects.using(AI_DB_ALIAS).filter(
            applicant=user,
            work_date__gte=start,
            work_date__lte=end,
            application_type__in=type_labels,
            status__in=statuses,
        ).values('application_type', 'status').annotate(
            hours=Sum('hours'), midnight_hours=Sum('midnight_hours'), records=Count('id')
        )
    )
    by_key = {(row['application_type'], row['status']): row for row in rows}
    items = []
    for app_type, type_label in type_labels.items():
        for status, status_label in statuses.items():
            row = by_key.get((app_type, status))
            if not row:
                continue
            hours = (row['hours'] or Decimal('0')) + (row['midnight_hours'] or Decimal('0'))
            records = row['records']
            if records:
                items.append({'label': f'{type_label}・{status_label}', 'hours': float(hours), 'records': records})
    display_name = f'{user.last_name} {user.first_name}'.strip() or user.username
    return {
        'employee_name': display_name,
        'total_hours': sum((item['hours'] for item in items), 0.0),
        'total_records': sum((item['records'] for item in items), 0),
        'items': items,
        'labels': [item['label'] for item in items],
        'values': [item['hours'] for item in items],
    }


def _quick_overtime_response(question, history):
    """氏名・月が明示された残業照会をQwen待ちなしで安全に集計する。"""
    compact_question = _normalized_text(question)
    person_match = re.match(
        r'^(?P<name>.+?)(?:さん|氏)?の(?:(?P<year>\d{4})年)?(?P<month>1[0-2]|[1-9])月(?:の)?残業',
        compact_question,
    )
    if person_match and 'グループ' not in person_match.group('name'):
        start, end = _month_period(person_match.group('year'), person_match.group('month'))
        facts = _individual_overtime_facts(start, end, person_match.group('name'))
        breakdown = '、'.join(
            f"{item['label']} {item['hours']:g}時間（{item['records']}件）" for item in facts['items']
        ) or '対象となる提出済み申請はありません'
        return {
            'answer': (
                f"{start.year}年{start.month}月の{facts['employee_name']}さんの残業申請時間は"
                f"合計 {facts['total_hours']:g}時間（{facts['total_records']}件）です。"
                f"内訳: {breakdown}。\n残業申請時間の集計であり、打刻実績ではありません。"
            ),
            'intent': 'individual_overtime',
            'period': {'start_date': start.isoformat(), 'end_date': end.isoformat()},
            'source': '残業申請時間（指定社員・承認段階別）',
            'chart': None,
            'facts': facts,
        }

    previous_questions = ' '.join(row['content'] for row in history)
    if ('個人の集計' in question or '個人別' in question) and '残業' in previous_questions:
        return {
            'answer': (
                'できます。氏名と対象月を指定すると、指定した一人の提出済み残業申請を承認段階別に集計します。\n'
                '例: 「王 崇栓の2026年8月の残業を教えて」\n'
                '個人間の比較・順位付けは行いません。'
            ),
            'intent': 'individual_overtime_help',
            'source': '残業申請の個人集計機能',
            'chart': None,
            'facts': None,
        }
    return None


def _scrap_facts(start, end, process_name=''):
    net_qty = ExpressionWrapper(
        F('qty') - Coalesce(F('return_qty'), Value(Decimal('0'))),
        output_field=DecimalField(max_digits=14, decimal_places=3),
    )
    queryset = ScrapRecord.objects.using(AI_DB_ALIAS).filter(
            plan_date__gte=start,
            plan_date__lte=end,
            event_type='SCRAP',
            disposition_status__in=['REJECTED', 'PARTIAL'],
        ).annotate(net_qty=net_qty).filter(net_qty__gt=0)
    if process_name:
        queryset = queryset.filter(occurrence_process__process_name__icontains=process_name)
    total = queryset.aggregate(total=Sum('net_qty'), records=Count('id'))
    rows = list(
        queryset
        .values('reason').annotate(quantity=Sum('net_qty'), records=Count('id'))
        .order_by('-quantity')[:8]
    )
    return {
        'total': float(total['total'] or 0),
        'records': total['records'],
        'labels': [row['reason'] or '理由未登録' for row in rows],
        'values': [float(row['quantity'] or 0) for row in rows],
        'items': [{'reason': row['reason'] or '理由未登録', 'quantity': float(row['quantity'] or 0), 'records': row['records']} for row in rows],
    }


def _production_facts(start, end, operator_name='', product_code=''):
    # 仕入の入荷実績は record_type='PURCHASE' で保存されるため、生産数には含まれない。
    queryset = ProcessRealtimeRecord.objects.using(AI_DB_ALIAS).filter(
        timestamp__date__gte=start,
        timestamp__date__lte=end,
        record_type='PRODUCTION',
    )
    if operator_name:
        queryset = queryset.filter(operator_name__iexact=operator_name)
    if product_code:
        queryset = queryset.filter(product_code__iexact=product_code)
    by_day = list(
        queryset.annotate(day=TruncDate('timestamp'))
        .values('day').annotate(quantity=Sum('qty'), records=Count('id'))
        .order_by('day')
    )
    by_process = list(
        queryset.values('process__process_name')
        .annotate(quantity=Sum('qty'), records=Count('id'))
        .order_by('-quantity')[:8]
    )
    laser_by_day = []
    laser_total = Decimal('0')
    laser_records = 0
    brake_by_day = []
    brake_total = Decimal('0')
    brake_records = 0
    # 生産実績照会のレーザータブと同じ定義。終了済みの構成部品明細だけを数量根拠にする。
    if product_code and not operator_name:
        laser_queryset = LaserActualDetail.objects.using(AI_DB_ALIAS).filter(
            actual__work_date__gte=start,
            actual__work_date__lte=end,
            actual__operator_action=LaserActual.OPERATOR_ACTION_END,
            detail_type=LaserActualDetail.DETAIL_TYPE_COMPONENT,
            product_code__iexact=product_code,
        )
        laser_by_day = list(
            laser_queryset.values('actual__work_date')
            .annotate(quantity=Sum('total_qty'), records=Count('id'))
            .order_by('actual__work_date')
        )
        laser_total = sum((row['quantity'] or Decimal('0') for row in laser_by_day), Decimal('0'))
        laser_records = sum(row['records'] for row in laser_by_day)
        if laser_records:
            by_process.append({
                'process__process_name': 'レーザー実績',
                'quantity': laser_total,
                'records': laser_records,
            })

    # 生産実績照会（ProductionRecordInquiry.vue の isCountableProductionRow）・LineBacklog.actual_qty と同じ定義。
    # 作業区間ごとに終了(END)・中断(PAUSE)時点の加工数を登録するため、両方の qty を合計する。
    if product_code and not operator_name:
        brake_queryset = BrakeLineRecord.objects.using(AI_DB_ALIAS).filter(
            plan_date__gte=start,
            plan_date__lte=end,
            operator_action__in=[
                BrakeLineRecord.OPERATOR_ACTION_END,
                BrakeLineRecord.OPERATOR_ACTION_PAUSE,
            ],
        ).filter(
            Q(product_code__iexact=product_code) | Q(product__product_code__iexact=product_code)
        )
        brake_by_day = list(
            brake_queryset.values('plan_date')
            .annotate(quantity=Sum('qty'), records=Count('id'))
            .order_by('plan_date')
        )
        brake_total = sum((row['quantity'] or Decimal('0') for row in brake_by_day), Decimal('0'))
        brake_records = sum(row['records'] for row in brake_by_day)
        if brake_records:
            by_process.append({
                'process__process_name': 'ブレーキ実績',
                'quantity': brake_total,
                'records': brake_records,
            })

    # 同じ生産事実を複数テーブルから二重に足さない。画面別の専用実績を正規根拠とする。
    if brake_records:
        selected_by_day = [
            {'day': row['plan_date'], 'quantity': row['quantity'] or Decimal('0'), 'records': row['records']}
            for row in brake_by_day
        ]
        selected_by_process = [row for row in by_process if row['process__process_name'] == 'ブレーキ実績']
        source = 'ブレーキ実績（終了・中断時の加工数）'
    elif laser_records:
        selected_by_day = [
            {'day': row['actual__work_date'], 'quantity': row['quantity'] or Decimal('0'), 'records': row['records']}
            for row in laser_by_day
        ]
        selected_by_process = [row for row in by_process if row['process__process_name'] == 'レーザー実績']
        source = 'レーザー実績（終了済み構成部品明細）'
    else:
        selected_by_day = by_day
        selected_by_process = by_process
        source = '工程実績'
    total = sum((row['quantity'] or Decimal('0') for row in selected_by_day), Decimal('0'))
    return {
        'total': float(total),
        'records': sum(row['records'] for row in selected_by_day),
        'labels': [row['day'].isoformat() for row in selected_by_day],
        'values': [float(row['quantity'] or 0) for row in selected_by_day],
        'processes': [{'process': row['process__process_name'] or '工程未登録', 'quantity': float(row['quantity'] or 0), 'records': row['records']} for row in selected_by_process],
        'operator_name': operator_name,
        'product_code': product_code,
        'source': source,
        'laser_total': float(laser_total),
        'laser_records': laser_records,
        'brake_total': float(brake_total),
        'brake_records': brake_records,
    }


def _interruption_facts(start, end):
    queryset = BrakeLineRecord.objects.using(AI_DB_ALIAS).filter(
        plan_date__gte=start,
        plan_date__lte=end,
        operator_action__in=['PAUSE', 'TEMP_END'],
    )
    rows = list(
        queryset.values('operator_action_reason', 'operator_action')
        .annotate(records=Count('id')).order_by('-records')[:8]
    )
    return {
        'total': queryset.count(),
        'labels': [row['operator_action_reason'] or '理由未登録' for row in rows],
        'values': [row['records'] for row in rows],
        'items': [
            {'reason': row['operator_action_reason'] or '理由未登録',
             'action': '強制終了' if row['operator_action'] == 'TEMP_END' else '中断',
             'records': row['records']} for row in rows
        ],
    }


def _overtime_facts(start, end, group_name):
    """最終承認済みと最終承認待ちを個人名なしでグループ集計する。"""
    search_name = group_name.removesuffix('グループ').strip()
    groups = list(Department.objects.using(AI_DB_ALIAS).filter(level='unit', name__iexact=search_name).values('id', 'name')[:2])
    if not groups:
        raise LocalAIError(f'「{group_name}」に一致する組織グループがDBにありません。')
    if len(groups) > 1:
        raise LocalAIError(f'「{group_name}」に一致する組織グループが複数あります。正式なグループ名を指定してください。')
    group = groups[0]
    queryset = OvertimeApplication.objects.using(AI_DB_ALIAS).filter(
        work_date__gte=start,
        work_date__lte=end,
        application_type='overtime',
        status__in=['approved_supervisor', 'approved_chief', 'approved_manager'],
        applicant__profile__unit_id=group['id'],
    )
    statuses = list(queryset.values('status').annotate(
        hours=Sum('hours'), midnight_hours=Sum('midnight_hours'), records=Count('id')
    ))
    final_total = Decimal('0')
    pending_total = Decimal('0')
    final_count = 0
    pending_count = 0
    for row in statuses:
        hours = (row['hours'] or Decimal('0')) + (row['midnight_hours'] or Decimal('0'))
        if row['status'] == 'approved_manager':
            final_total += hours
            final_count += row['records']
        else:
            pending_total += hours
            pending_count += row['records']
    return {
        'group_name': group['name'],
        'final_approved_hours': float(final_total),
        'pending_final_approval_hours': float(pending_total),
        'final_approved_records': final_count,
        'pending_final_approval_records': pending_count,
        'labels': ['最終承認済み', '上長承認済み・最終承認待ち'],
        'values': [float(final_total), float(pending_total)],
    }


def _build_facts(plan):
    start, end = plan['start_date'], plan['end_date']
    intent = plan['intent']
    if intent in {'production', 'operator'}:
        production = _production_facts(
            start,
            end,
            plan['operator_name'] if intent == 'operator' else '',
            plan['product_code'],
        )
        source = f"{production['source']}（品番: {plan['product_code']}）" if plan['product_code'] else '工程実績（生産数）'
        return source, production, {
            '生産数量': production['total'], '記録件数': production['records'],
            '作業者': production['operator_name'] or '全体', '日別推移': list(zip(production['labels'], production['values'])),
            '工程別': production['processes'], '品番': production['product_code'] or '全品番',
        }
    if intent == 'scrap':
        scrap = _scrap_facts(start, end, plan['process_name'])
        source = f"{plan['process_name']}工程の確定仕損記録" if plan['process_name'] else '確定仕損記録'
        return source, scrap, {'確定仕損数量': scrap['total'], '記録件数': scrap['records'], '理由別': scrap['items']}
    if intent == 'interruption':
        interruptions = _interruption_facts(start, end)
        return 'ブレーキライン作業記録（中断・強制終了）', interruptions, {'中断・強制終了件数': interruptions['total'], '理由別': interruptions['items']}
    if intent == 'overtime':
        overtime = _overtime_facts(start, end, plan['group_name'])
        chart = {'labels': overtime['labels'], 'values': overtime['values']}
        facts = {
            'グループ': overtime['group_name'],
            '最終承認済み申請時間': overtime['final_approved_hours'],
            '最終承認済み件数': overtime['final_approved_records'],
            '上長承認済み・最終承認待ち申請時間': overtime['pending_final_approval_hours'],
            '上長承認済み・最終承認待ち件数': overtime['pending_final_approval_records'],
        }
        return '残業申請時間（承認段階別・グループ集計）', chart, facts
    if intent == 'report':
        production = _production_facts(start, end)
        scrap = _scrap_facts(start, end)
        interruptions = _interruption_facts(start, end)
        facts = {'production': production, 'scrap': scrap, 'interruptions': interruptions}
        brief = {
            '生産数量': production['total'], '生産記録数': production['records'],
            '確定仕損数量': scrap['total'], '仕損理由': scrap['items'][:5],
            '中断件数': interruptions['total'], '中断理由': interruptions['items'][:5],
        }
        return '生産・仕損・中断の期間集計', {
            'labels': production['labels'], 'values': production['values'],
        }, brief | facts
    return None, None, None


def _has_resource_permission(user, resource, level='view'):
    """フロントエンドの hasPermission と同じ判定をサーバー側でも行う。親権限へフォールバックしない。"""
    if getattr(user, 'is_superuser', False):
        return True
    from accounts.views import _build_effective_permissions

    permissions = _build_effective_permissions(user)
    perm = next((item for item in permissions if item['resource'] == resource), None)
    if not perm:
        return False
    if level == 'edit':
        return bool(perm.get('can_edit'))
    return bool(perm.get('can_view') or perm.get('can_edit'))


class AIChatAPIView(APIView):
    """Qwen・DeepSeek・OpenRouterから選択して使う社内AIチャットAPI。"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """選択可能なAIモデルの準備状態を返す。"""
        try:
            with urlopen(f'{OLLAMA_URL}/api/tags', timeout=3) as response:
                payload = json.loads(response.read().decode('utf-8'))
            models = [item.get('name', '') for item in payload.get('models', [])]
            qwen = {'connected': True, 'model_ready': MODEL in models, 'model': MODEL}
        except (HTTPError, URLError, TimeoutError, OSError, ValueError):
            qwen = {'connected': False, 'model_ready': False, 'model': MODEL}
        provider_configs = {item.provider: item for item in AIProviderConfig.objects.all()}
        qwen_config = provider_configs.get('qwen')
        if qwen_config:
            qwen['is_enabled'] = qwen_config.is_enabled
            qwen['configured_model'] = qwen_config.default_model
        providers = {'qwen': qwen}
        for provider_key, agent_provider in EXTERNAL_AGENT_PROVIDERS.items():
            config = provider_configs.get(provider_key)
            if not config:
                continue
            providers[provider_key] = {
                'connected': bool(agent_provider['api_key']),
                'model_ready': bool(agent_provider['api_key']),
                'model': config.default_model,
                'is_enabled': config.is_enabled,
                'models': [{'id': model_id, 'label': label} for model_id, label in agent_provider['models'].items()],
            }
        # 起点画面の業務データに答えられるかを、管理設定で有効なツールまで含めて判定して画面へ返す。
        screen = apply_tool_policy(resolve_screen_context(request.query_params.get('screen_context')))
        if screen['id'] == 'ai_home':
            supported = bool(screen['allowed_tools'])
        else:
            supported = bool(screen.get('coverage')) and bool(screen['priority_tools'])
        return Response({
            'providers': providers,
            'screen': {
                'id': screen['id'],
                'label': screen['label'],
                'supported': supported,
                'coverage': screen.get('coverage', '') if supported else '',
                'common_coverage': COMMON_COVERAGE,
            },
        })

    def post(self, request):
        if not _has_resource_permission(request.user, 'ai.chat'):
            return Response({'detail': '社内AIチャットを利用する権限がありません。'}, status=403)
        question = str(request.data.get('message') or '').strip()
        if not question or len(question) > 1200:
            return Response({'detail': '質問を入力してください（最大1200文字）。'}, status=400)
        provider = str(request.data.get('provider') or 'openrouter').strip().lower()
        if provider not in {'qwen', *EXTERNAL_AGENT_PROVIDERS}:
            return Response({'detail': 'AIモデルの指定が不正です。'}, status=400)
        provider_config = AIProviderConfig.objects.get(provider=provider)
        if not provider_config.is_enabled:
            return Response({'detail': 'このAIプロバイダは管理設定で無効になっています。'}, status=400)
        model = str(request.data.get('model') or provider_config.default_model).strip()
        is_external_provider = provider in EXTERNAL_AGENT_PROVIDERS
        if is_external_provider and model not in EXTERNAL_AGENT_PROVIDERS[provider]['models']:
            return Response({'detail': f"選択できない{EXTERNAL_AGENT_PROVIDERS[provider]['label']}モデルです。"}, status=400)
        redactor = _build_external_data_redactor() if is_external_provider else None
        # 個人別残業はフロントエンドの申告(allow_personal_overtime)だけでなく、
        # サーバー側でも overtime.personal_summary の閲覧権限を検証する。
        allow_personal_overtime = (
            request.data.get('allow_personal_overtime') is True
            and authorized_personal_data_allowed()
            and _has_resource_permission(request.user, 'overtime.personal_summary')
        )
        screen_context = apply_tool_policy(
            resolve_screen_context(request.data.get('screen_context')),
            is_external_provider=is_external_provider,
        )
        if is_external_provider and not external_aggregate_transfer_allowed():
            screen_context = {**screen_context, 'allowed_tools': frozenset()}
        raw_history = request.data.get('history') or []
        raw_document_ids = request.data.get('knowledge_document_ids') or []
        if not isinstance(raw_document_ids, list):
            return Response({'detail': '参照資料の指定が不正です。'}, status=400)
        knowledge_document_ids = []
        for document_id in raw_document_ids[:3]:
            try:
                normalized_id = int(document_id)
            except (TypeError, ValueError):
                return Response({'detail': '参照資料の指定が不正です。'}, status=400)
            if normalized_id > 0 and normalized_id not in knowledge_document_ids:
                knowledge_document_ids.append(normalized_id)
        vision_attachment = None
        if provider == 'openrouter':
            try:
                vision_attachment = selected_visual_attachment(knowledge_document_ids)
            except ValueError as exc:
                return Response({'detail': str(exc)}, status=400)
            if vision_attachment and not external_image_transfer_allowed():
                return Response({
                    'detail': '添付画像・PDFの外部AI送信はAI設定で無効です。有効にするか、OCRで読める文字だけを質問してください。',
                }, status=400)
        history = [
            {
                'role': row['role'],
                'content': str(row.get('content', ''))[:1200],
                'period': row.get('period') if isinstance(row.get('period'), dict) else None,
            }
            for row in raw_history[-16:]
            if isinstance(row, dict)
            and row.get('role') in {'user', 'assistant'}
            and str(row.get('content', '')).strip()
        ]
        # 外部AI(DeepSeek/OpenRouter)は、固定の分岐結果ではなく読み取り専用ツールを自ら選んで調査する。
        if is_external_provider:
            agent_provider = EXTERNAL_AGENT_PROVIDERS[provider]
            try:
                answer, inference, source, period, chart = _deepseek_agent_chat(
                    question, history, model=model, redactor=redactor,
                    allow_personal_overtime=allow_personal_overtime,
                    screen_context=screen_context,
                    base_url=agent_provider['base_url'], api_key=agent_provider['api_key'],
                    default_model=agent_provider['default_model'],
                    provider_key=provider, provider_label=agent_provider['label'],
                    knowledge_document_ids=knowledge_document_ids,
                    vision_attachment=vision_attachment,
                )
            except LocalAIError as exc:
                return Response({'detail': str(exc)}, status=503)
            return Response({
                'answer': answer,
                'analysis': '',
                'source': source,
                'period': period,
                'chart': chart,
                'document': '',
                'provider': provider,
                'model': inference['model'],
                'inference': inference,
            })
        # 曖昧な品番は、AIの意図解析を待たずに候補を返す。空応答でも全件集計やエラーにしない。
        product_inputs = _product_code_candidates(question, history)
        if product_inputs:
            registered_code, matches = _resolve_product_code('', product_inputs)
            if not registered_code and matches:
                candidate_text = '、'.join(f'「{code}」' for code in matches)
                return Response({
                    'answer': (
                        f'入力された品番「{product_inputs[0]}」は品番マスタに完全一致しません。'
                        f'候補は {candidate_text} です。正式品番を指定してください。'
                    ),
                    'analysis': '',
                    'source': '品番マスタ',
                    'period': None,
                    'chart': None,
                    'document': '',
                    'provider': 'database',
                    'model': '',
                    'inference': None,
                })
        # 1. パターンマッチで即回答（Qwen不要）
        quick = _quick_overtime_response(question, history)
        if quick:
            chart = None
            facts = quick.get('facts')
            if facts and facts.get('values'):
                chart = {
                    'title': f"{facts['employee_name']}の残業申請時間",
                    'labels': facts['labels'],
                    'values': facts['values'],
                    'series_label': '時間',
                }
            return Response({
                'answer': quick['answer'],
                'analysis': '',
                'source': quick.get('source', ''),
                'period': quick.get('period'),
                'chart': chart,
                'document': '',
                'provider': 'database',
                'model': '',
                'inference': None,
            })

        # 2. マスタ検索（サプライヤー・得意先のコード照会）
        lookup = _master_lookup(question)
        if lookup:
            return Response({
                'answer': lookup['answer'],
                'analysis': '',
                'source': lookup['source'],
                'period': None,
                'chart': None,
                'document': '',
                'provider': 'database',
                'model': '',
                'inference': None,
            })

        # 3. 報告書の追質問（前回データを使い、再分類・再集計をスキップ）
        if _is_report_followup(question, history):
            return self._report_from_context(question, history, provider, model, redactor, screen_context, knowledge_document_ids)

        # 4. DB集計が必要な質問
        if _needs_database(question, history):
            return self._data_chat(question, history, provider, model, redactor, screen_context, knowledge_document_ids)

        # 5. 一般会話
        return self._general_chat(question, history, provider, model, redactor, screen_context, knowledge_document_ids)

    def _general_chat(self, question, history, provider, model=None, redactor=None, screen_context=None, knowledge_document_ids=None):
        """システムプロンプトで役割を与え、選択中のモデルで会話を実行する。"""
        knowledge_chunks = retrieve_knowledge(question, screen_context, document_ids=knowledge_document_ids)
        retrieved_knowledge = knowledge_prompt(knowledge_chunks)
        knowledge_source = knowledge_source_label(knowledge_chunks)
        system = {
            'role': 'system',
            'content': (
                'あなたは製造業の社内生産管理システムに組み込まれたAIアシスタント「社内AI」です。'
                'このチャットは本社の生産管理を基本対象とします。'
                'できること:\n'
                '- 生産数の日別推移やチャート表示（例: 「今月の日別生産数をチャートで見せて」）\n'
                '- 仕損の理由別集計（例: 「今月の確定仕損を理由別に教えて」）\n'
                '- ブレーキライン中断・強制終了の分析（例: 「ブレーキラインの中断理由を分析して」）\n'
                '- グループ別残業申請時間の集計（例: 「板金グループの8月の残業時間は？」）\n'
                '- 個人の残業申請時間の照会（例: 「北村さんの8月の残業を教えて」）\n'
                '- 幹部会向け報告書の下書き作成\n\n'
                '重要ルール:\n'
                '- 明確な質問にはすぐ行動してください。何度も聞き返さないこと。\n'
                '- 不明確な場合は1回だけ簡潔に聞き返してください。選択肢は最大3つ。\n'
                '- 対応できない質問には「現在この機能は対応していません」と短く伝えてください。\n'
                '日本語で簡潔に回答してください。'
                + retrieved_knowledge
            ),
        }
        chat_history = (
            [{'role': row['role'], 'content': row['content']} for row in history]
            if _uses_chat_context(question) else []
        )
        try:
            answer, inference = _chat([
                system,
                *chat_history,
                {'role': 'user', 'content': question},
            ], provider, num_predict=512, timeout=180, include_metadata=True, model=model, redactor=redactor)
        except LocalAIError as exc:
            return Response({'detail': str(exc)}, status=503)
        return Response({
            'answer': answer,
            'analysis': '',
            'document': '',
            'source': ' / '.join(item for item in (
                'DeepSeek APIとの会話' if provider == 'deepseek' else 'ローカルQwenの会話', knowledge_source,
            ) if item),
            'chart': None,
            'provider': provider,
            'model': inference['model'],
            'inference': inference,
        })


    def _data_chat(self, question, history, provider, model=None, redactor=None, screen_context=None, knowledge_document_ids=None):
        """DB集計結果を選択中のモデルに渡して自然文で回答する。"""
        try:
            plan = _date_range(question, history, provider, model, redactor)
        except LocalAIError as exc:
            return Response({'detail': str(exc)}, status=400)

        if plan['intent'] == 'help':
            return self._general_chat(question, history, provider, model, redactor, screen_context, knowledge_document_ids)

        if plan.get('product_not_found'):
            matches = plan.get('product_match_candidates') or []
            if matches:
                candidate_text = '、'.join(f'「{code}」' for code in matches)
                answer = (
                    f'入力された品番「{plan["product_not_found"]}」は品番マスタに完全一致しません。'
                    f'候補は {candidate_text} です。正式品番を指定してください。'
                )
            else:
                answer = f'品番「{plan["product_not_found"]}」は、現在の品番マスタにありません。品番を確認してください。'
            return Response({
                'answer': answer,
                'analysis': '',
                'source': '品番マスタ',
                'period': None,
                'chart': None,
                'document': '',
                'provider': 'database',
                'model': '',
                'inference': None,
            })

        source, raw_data, facts = _build_facts(plan)
        if source is None:
            return self._general_chat(question, history, provider, model, redactor, screen_context, knowledge_document_ids)

        start = plan['start_date']
        end = plan['end_date']
        period = {'start_date': start.isoformat(), 'end_date': end.isoformat()}

        chart = None
        if raw_data and raw_data.get('values'):
            series_units = {
                'production': '個', 'operator': '個', 'scrap': '個',
                'interruption': '件', 'overtime': '時間', 'report': '個',
            }
            chart_titles = {
                'production': f"{plan['product_code']} 日別生産数" if plan.get('product_code') else '日別生産数',
                'operator': f"{plan['operator_name']}の日別生産数",
                'scrap': '仕損 理由別数量',
                'interruption': '中断・強制終了 理由別件数',
                'overtime': f"{plan.get('group_name', '')}グループ 残業申請時間",
                'report': '日別生産数',
            }
            chart = {
                'title': chart_titles.get(plan['intent'], 'データ'),
                'labels': raw_data['labels'],
                'values': raw_data['values'],
                'series_label': series_units.get(plan['intent'], ''),
            }

        facts_text = json.dumps(facts, ensure_ascii=False, default=str)
        knowledge_chunks = retrieve_knowledge(question, screen_context, document_ids=knowledge_document_ids)
        retrieved_knowledge = knowledge_prompt(knowledge_chunks)
        knowledge_source = knowledge_source_label(knowledge_chunks)
        try:
            answer, inference = _chat([
                {
                    'role': 'system',
                    'content': (
                        '社内生産AIです。以下のDB集計結果に基づいて質問に日本語で簡潔に回答してください。\n'
                        '厳守事項:\n'
                        '- 数値はDB集計結果から引用し、推測や捏造はしないでください。\n'
                        '- DB集計結果に質問の答えがない場合は「このデータには含まれていません」と正直に伝えてください。\n'
                        '- 無関係なデータを流用して回答を作らないでください。\n'
                        '- 不明確な場合は1回だけ簡潔に聞き返してください。何度も聞き返さないこと。\n'
                        '- サプライヤー名・作業者名・製品名など特定できない情報がある場合は、コードや正式名称を尋ねてください。\n'
                        f'対象期間: {start.isoformat()} ～ {end.isoformat()}'
                        + retrieved_knowledge
                    ),
                },
                {'role': 'user', 'content': f'質問: {question}\n\nDB集計結果:\n{facts_text}'},
            ], provider, num_predict=512, timeout=180, include_metadata=True, model=model, redactor=redactor)
        except LocalAIError as exc:
            return Response({'detail': str(exc)}, status=503)

        document = ''
        if plan.get('document'):
            try:
                document = _chat([
                    {
                        'role': 'system',
                        'content': (
                            '社内の幹部会向け報告書をMarkdown形式で作成してください。'
                            '見出し・箇条書きを使い、データの根拠を明示してください。'
                        ),
                    },
                    {'role': 'user', 'content': f'対象期間: {start.isoformat()} ～ {end.isoformat()}\n\nDB集計結果:\n{facts_text}'},
                ], provider, num_predict=1024, timeout=180, model=model, redactor=redactor)
            except LocalAIError:
                document = ''

        return Response({
            'answer': answer,
            'analysis': '',
            'source': ' / '.join(item for item in (source, knowledge_source) if item),
            'period': period,
            'chart': chart,
            'document': document,
            'provider': provider,
            'model': inference['model'],
            'inference': inference,
        })


    def _report_from_context(self, question, history, provider, model=None, redactor=None, screen_context=None, knowledge_document_ids=None):
        """前回の回答データから報告書を生成する。DB再集計・意図分類をスキップする。"""
        last_data = ''
        for msg in reversed(history):
            if msg['role'] == 'assistant' and msg['content'].strip():
                last_data = msg['content']
                break
        if not last_data:
            return self._general_chat(question, history, provider, model, redactor, screen_context, knowledge_document_ids)
        try:
            document, inference = _chat([
                {
                    'role': 'system',
                    'content': (
                        '社内の幹部会向け報告書をMarkdown形式で作成してください。'
                        '見出し・箇条書きを使い、データの根拠を明示してください。'
                        '提供されたデータだけを使い、推測や捏造はしないでください。'
                    ),
                },
                {'role': 'user', 'content': f'以下のデータを報告書にまとめてください:\n\n{last_data}'},
            ], provider, num_predict=1024, timeout=180, include_metadata=True, model=model, redactor=redactor)
        except LocalAIError as exc:
            return Response({'detail': str(exc)}, status=503)
        return Response({
            'answer': '報告書を作成しました。下のボタンからダウンロードできます。',
            'analysis': '',
            'source': '前回の回答データ',
            'period': None,
            'chart': None,
            'document': document,
            'provider': provider,
            'model': inference['model'],
            'inference': inference,
        })


_LOOKUP_PATTERNS = [
    re.compile(r'(?:それでは|それじゃ|では|じゃあ|じゃ|あと)?(.+?)の(?:サプライヤー|仕入先|得意先)?コード'),
    re.compile(r'(?:それでは|それじゃ|では|じゃあ|じゃ|あと)?(.+?)(?:を|って)(?:調べて|検索して|検索|教えて)'),
]


def _get_search_configs():
    """DB設定を取得し、未登録時はデフォルト設定にフォールバックする。"""
    from ai.models import AISearchConfig
    configs = list(AISearchConfig.objects.using(AI_DB_ALIAS).filter(is_active=True))
    if configs:
        return [
            {
                'model': c.model_path,
                'label': c.label,
                'search_fields': c.search_fields,
                'display_fields': c.display_fields,
                'display': c.display_template,
                'filter': c.filter_json or {},
            }
            for c in configs
        ]
    return AI_DB_ACCESS


def _master_lookup(question):
    """AI検索設定に基づき、マスタのコード照会をDB検索で返す。"""
    lookup_triggers = ('コード', '調べて', '検索して', '検索')
    if not any(trigger in question for trigger in lookup_triggers):
        return None

    search = ''
    for pattern in _LOOKUP_PATTERNS:
        match = pattern.search(question)
        if match:
            search = match.group(1).strip()
            break
    if not search or len(search) < 2:
        return None

    from django.apps import apps

    results = []
    for config in _get_search_configs():
        try:
            app_label, model_name = config['model'].split('.')
            model = apps.get_model(app_label, model_name)
        except (ValueError, LookupError):
            continue

        q = Q()
        for field in config['search_fields']:
            q |= Q(**{f'{field}__icontains': search})

        queryset = model.objects.using(AI_DB_ALIAS).filter(q)
        if config.get('filter'):
            queryset = queryset.filter(**config['filter'])

        for instance in queryset[:3]:
            values = {}
            for field in config['display_fields']:
                display_method = getattr(instance, f'get_{field}_display', None)
                if callable(display_method):
                    values[field] = display_method()
                else:
                    values[field] = getattr(instance, field, '')
            results.append(f"{config['label']}: {config['display'].format(**values)}")

    if not results:
        return {
            'answer': f'「{search}」に一致するマスタデータは見つかりませんでした。',
            'source': 'マスタ検索',
        }
    return {
        'answer': '\n'.join(results),
        'source': 'マスタ検索',
    }


def _is_report_followup(question, history):
    """「これを報告書にまとめて」のような追質問を検出する。"""
    if not history:
        return False
    report_terms = ('報告書', 'レポート', 'まとめて', 'まとめ')
    if not any(term in question for term in report_terms):
        return False
    context_refs = ('これ', 'それ', 'この', 'その', '今の', '上記')
    return any(ref in question for ref in context_refs) or len(question) < 20


def _needs_database(question, history):
    """生産・残業・仕損などDB根拠を要する話題だけ固定集計へ回す。"""
    if _selected_data_option(question, history):
        return True
    data_terms = (
        '生産', '出来高', '実績', '作業者', '担当', '残業', '仕損', '不良', 'スクラップ',
        '中断', '強制終了', '停止', 'ブレーキ', 'ライン', '工程', '品番', '製品', '数量',
        '何時間', '何個', '何件', '集計', '分析', 'データ', 'DB', 'グラフ', 'チャート',
        '今月', '先月', '今年', '昨年', '報告書', '幹部会',
    )
    if any(term in question for term in data_terms) or re.search(r'\d{1,2}月', question):
        return True
    # 「それをグラフで」など、DB質問への短い追質問だけ履歴を使う。
    refers_to_context = any(term in question for term in ('それ', 'その', '先ほど', 'さっき', '上記', '続けて'))
    if not refers_to_context:
        return False
    context = ' '.join(item['content'] for item in history)
    return any(term in context for term in data_terms) or bool(re.search(r'\d{1,2}月', context))


def _uses_chat_context(question):
    """独立した質問に無関係な履歴を混ぜず、明示的な追質問だけ文脈を使う。"""
    references = (
        'それ', 'その', '先ほど', 'さっき', '上記', '続けて', 'もっと', '詳しく',
        '同じ条件', '今の', 'この結果', '月別で', 'グラフに', '表にして', 'では', 'じゃあ',
    )
    return any(term in question for term in references)
