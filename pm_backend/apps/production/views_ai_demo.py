"""ローカルLLMと許可済み集計だけで動作する社内AIチャット。"""
import json
import os
import re
import unicodedata
from calendar import monthrange
from datetime import date
from decimal import Decimal
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from django.db.models import Count, DecimalField, ExpressionWrapper, F, Q, Sum, Value
from django.db.models.functions import Coalesce, TruncDate
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Department
from production.models_brake_line_record import BrakeLineRecord
from production.models_process_realtime import ProcessRealtimeRecord
from quality.models_scrap import ScrapRecord
from overtime.models import OvertimeApplication


MODEL = os.environ.get('OLLAMA_MODEL', 'qwen3:4b-instruct')
OLLAMA_URL = os.environ.get('OLLAMA_BASE_URL', 'http://127.0.0.1:11434').rstrip('/')
MAX_RANGE_DAYS = 93

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
    """ローカルLLMと通信できない、または応答形式が不正。"""


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


def _date_range(question, history):
    today = date.today()
    start_default = today.replace(day=1)
    prompt = {
        'today': today.isoformat(),
        'default_start_date': start_default.isoformat(),
        'default_end_date': today.isoformat(),
        'recent_context': history[-4:],
        'current_request': question,
    }
    raw = _ollama_chat([
        {
            'role': 'system',
            'content': (
                '社内生産AIのリクエスト分類器です。次のJSONだけを返してください。'
                'intent は production, operator, scrap, interruption, overtime, report, help のいずれか。'
                'production=生産数・出来高、operator=特定作業者の生産数、scrap=仕損・不良、'
                'interruption=ブレーキラインの中断・強制終了、overtime=残業時間、report=複合報告書。'
                '入荷・購買・在庫・受注・出荷・サプライヤーなど上記に該当しない質問は help にすること。'
                '日付範囲は明示がなければ与えられた既定値。operator_name は質問に明記された作業者名だけ。'
                'overtime は残業時間の質問。質問中に「板金の残業」または「板金グループの残業」とあれば group_name は必ず「板金」。'
                '「グループ」という語がなくても組織名をgroup_nameに抽出し、末尾の「グループ」は含めない。'
                'process_name は仕損が起きた工程名だけ。工程指定がなければ空文字。'
                'document は報告書・文書作成の依頼なら true。show_chart は図表・グラフ表示を頼まれた場合だけ true。'
                '形式: {"intent":"production","start_date":"YYYY-MM-DD","end_date":"YYYY-MM-DD","operator_name":"","group_name":"","process_name":"","document":false,"show_chart":false}'
            ),
        },
        {'role': 'user', 'content': json.dumps(prompt, ensure_ascii=False)},
    ], json_mode=True, num_predict=256, timeout=90)
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
    for user in get_user_model().objects.filter(is_active=True).only(
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
    """指定した一人の提出済み残業申請を承認段階別に集計する。"""
    user = _find_user_by_name(name)
    statuses = {
        'submitted': '申請中',
        'approved_leader': 'リーダー承認済み',
        'approved_supervisor': '班長承認済み',
        'approved_chief': '係長承認済み',
        'approved_manager': '最終承認済み',
    }
    rows = list(
        OvertimeApplication.objects.filter(
            applicant=user,
            work_date__gte=start,
            work_date__lte=end,
            application_type='overtime',
            status__in=statuses,
        ).values('status').annotate(
            hours=Sum('hours'), midnight_hours=Sum('midnight_hours'), records=Count('id')
        )
    )
    by_status = {row['status']: row for row in rows}
    items = []
    for status, label in statuses.items():
        row = by_status.get(status)
        hours = (row['hours'] or Decimal('0')) + (row['midnight_hours'] or Decimal('0')) if row else Decimal('0')
        records = row['records'] if row else 0
        if records:
            items.append({'label': label, 'hours': float(hours), 'records': records})
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
    queryset = ScrapRecord.objects.filter(
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


def _production_facts(start, end, operator_name=''):
    queryset = ProcessRealtimeRecord.objects.filter(
        timestamp__date__gte=start,
        timestamp__date__lte=end,
        record_type='PRODUCTION',
    )
    if operator_name:
        queryset = queryset.filter(operator_name__iexact=operator_name)
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
    total = sum((row['quantity'] or Decimal('0') for row in by_day), Decimal('0'))
    return {
        'total': float(total),
        'records': sum(row['records'] for row in by_day),
        'labels': [row['day'].isoformat() for row in by_day],
        'values': [float(row['quantity'] or 0) for row in by_day],
        'processes': [{'process': row['process__process_name'] or '工程未登録', 'quantity': float(row['quantity'] or 0), 'records': row['records']} for row in by_process],
        'operator_name': operator_name,
    }


def _interruption_facts(start, end):
    queryset = BrakeLineRecord.objects.filter(
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
    groups = list(Department.objects.filter(level='unit', name__iexact=search_name).values('id', 'name')[:2])
    if not groups:
        raise LocalAIError(f'「{group_name}」に一致する組織グループがDBにありません。')
    if len(groups) > 1:
        raise LocalAIError(f'「{group_name}」に一致する組織グループが複数あります。正式なグループ名を指定してください。')
    group = groups[0]
    queryset = OvertimeApplication.objects.filter(
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
        production = _production_facts(start, end, plan['operator_name'] if intent == 'operator' else '')
        return '工程実績（生産数）', production, {
            '生産数量': production['total'], '記録件数': production['records'],
            '作業者': production['operator_name'] or '全体', '日別推移': list(zip(production['labels'], production['values'])),
            '工程別': production['processes'],
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


class ProductionAIDemoView(APIView):
    """Ollama上のQwenに会話をそのまま渡すチャットAPI。"""

    def get(self, request):
        """ローカルOllamaと指定モデルの起動状態を返す。"""
        try:
            with urlopen(f'{OLLAMA_URL}/api/tags', timeout=3) as response:
                payload = json.loads(response.read().decode('utf-8'))
            models = [item.get('name', '') for item in payload.get('models', [])]
            return Response({'connected': True, 'model_ready': MODEL in models, 'model': MODEL})
        except (HTTPError, URLError, TimeoutError, OSError, ValueError):
            return Response({'connected': False, 'model_ready': False, 'model': MODEL})

    def post(self, request):
        question = str(request.data.get('message') or '').strip()
        if not question or len(question) > 1200:
            return Response({'detail': '質問を入力してください（最大1200文字）。'}, status=400)
        raw_history = request.data.get('history') or []
        history = [
            {'role': row['role'], 'content': str(row.get('content', ''))[:1200]}
            for row in raw_history[-8:]
            if isinstance(row, dict)
            and row.get('role') in {'user', 'assistant'}
            and str(row.get('content', '')).strip()
        ]
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
                'local_model': MODEL,
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
                'local_model': MODEL,
                'inference': None,
            })

        # 3. 報告書の追質問（前回データを使い、再分類・再集計をスキップ）
        if _is_report_followup(question, history):
            return self._report_from_context(question, history)

        # 4. DB集計が必要な質問
        if _needs_database(question, history):
            return self._data_chat(question, history)

        # 5. 一般会話
        return self._general_chat(question, history)

    def _general_chat(self, question, history):
        """システムプロンプトで役割を与え、Qwenの会話として実行する。"""
        system = {
            'role': 'system',
            'content': (
                'あなたは製造業の社内生産管理システムに組み込まれたAIアシスタント「社内AI」です。'
                'PC内のローカルモデルとして動作し、外部にデータを送信しません。\n'
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
            ),
        }
        chat_history = history if _uses_chat_context(question) else []
        try:
            answer, inference = _ollama_chat([
                system,
                *chat_history,
                {'role': 'user', 'content': question},
            ], num_predict=512, timeout=180, include_metadata=True)
        except LocalAIError as exc:
            return Response({'detail': str(exc)}, status=503)
        return Response({
            'answer': answer,
            'analysis': '',
            'document': '',
            'source': 'ローカルQwenの会話',
            'chart': None,
            'local_model': inference['model'],
            'inference': inference,
        })


    def _data_chat(self, question, history):
        """DB集計結果をQwenに渡して自然文で回答する。"""
        try:
            plan = _date_range(question, history)
        except LocalAIError as exc:
            return Response({'detail': str(exc)}, status=400)

        if plan['intent'] == 'help':
            return self._general_chat(question, history)

        source, raw_data, facts = _build_facts(plan)
        if source is None:
            return self._general_chat(question, history)

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
                'production': '日別生産数',
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
        try:
            answer, inference = _ollama_chat([
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
                    ),
                },
                {'role': 'user', 'content': f'質問: {question}\n\nDB集計結果:\n{facts_text}'},
            ], num_predict=512, timeout=180, include_metadata=True)
        except LocalAIError as exc:
            return Response({'detail': str(exc)}, status=503)

        document = ''
        if plan.get('document'):
            try:
                document = _ollama_chat([
                    {
                        'role': 'system',
                        'content': (
                            '社内の幹部会向け報告書をMarkdown形式で作成してください。'
                            '見出し・箇条書きを使い、データの根拠を明示してください。'
                        ),
                    },
                    {'role': 'user', 'content': f'対象期間: {start.isoformat()} ～ {end.isoformat()}\n\nDB集計結果:\n{facts_text}'},
                ], num_predict=1024, timeout=180)
            except LocalAIError:
                document = ''

        return Response({
            'answer': answer,
            'analysis': '',
            'source': source,
            'period': period,
            'chart': chart,
            'document': document,
            'local_model': inference['model'],
            'inference': inference,
        })


    def _report_from_context(self, question, history):
        """前回の回答データから報告書を生成する。DB再集計・意図分類をスキップする。"""
        last_data = ''
        for msg in reversed(history):
            if msg['role'] == 'assistant' and msg['content'].strip():
                last_data = msg['content']
                break
        if not last_data:
            return self._general_chat(question, history)
        try:
            document, inference = _ollama_chat([
                {
                    'role': 'system',
                    'content': (
                        '社内の幹部会向け報告書をMarkdown形式で作成してください。'
                        '見出し・箇条書きを使い、データの根拠を明示してください。'
                        '提供されたデータだけを使い、推測や捏造はしないでください。'
                    ),
                },
                {'role': 'user', 'content': f'以下のデータを報告書にまとめてください:\n\n{last_data}'},
            ], num_predict=1024, timeout=180, include_metadata=True)
        except LocalAIError as exc:
            return Response({'detail': str(exc)}, status=503)
        return Response({
            'answer': '報告書を作成しました。下のボタンからダウンロードできます。',
            'analysis': '',
            'source': '前回の回答データ',
            'period': None,
            'chart': None,
            'document': document,
            'local_model': inference['model'],
            'inference': inference,
        })


_LOOKUP_PATTERNS = [
    re.compile(r'(?:それでは|それじゃ|では|じゃあ|じゃ|あと)?(.+?)の(?:サプライヤー|仕入先|得意先)?コード'),
    re.compile(r'(?:それでは|それじゃ|では|じゃあ|じゃ|あと)?(.+?)(?:を|って)(?:調べて|検索して|検索|教えて)'),
]


def _get_search_configs():
    """DB設定を取得し、未登録時はデフォルト設定にフォールバックする。"""
    from production.models_ai_config import AISearchConfig
    configs = list(AISearchConfig.objects.filter(is_active=True))
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

        queryset = model.objects.filter(q)
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
