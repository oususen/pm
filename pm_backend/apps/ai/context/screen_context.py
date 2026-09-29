"""画面起点ごとに、社内AIが優先して調べる業務領域を決める。

SCREEN_CONTEXTS の allowed_tools / allowed_intents は「その画面で優先するもの」を表す。
他の許可済みツールを使えなくするものではなく、優先指示としてAIへ伝える。
"""
from urllib.parse import urlsplit


_ALL_CURRENT_TOOLS = frozenset({
    'search_product', 'count_products', 'get_business_data',
    'search_employee', 'get_individual_overtime', 'get_personal_overtime_threshold',
    'execute_readonly_sql',
})
_ALL_CURRENT_INTENTS = frozenset({'production', 'scrap', 'interruption', 'overtime'})

SCREEN_CONTEXTS = (
    ('/orders/', {
        'id': 'orders', 'label': '受注',
        'allowed_tools': frozenset({'get_missing_routing_orders', 'execute_readonly_sql'}), 'allowed_intents': frozenset(),
    }),
    ('/production/', {
        'id': 'production', 'label': '生産',
        'allowed_tools': frozenset({'search_product', 'count_products', 'get_business_data', 'execute_readonly_sql'}),
        'allowed_intents': frozenset({'production', 'scrap', 'interruption', 'overtime'}),
    }),
    ('/quality/', {
        'id': 'quality', 'label': '品質',
        'allowed_tools': frozenset({'search_product', 'get_business_data', 'execute_readonly_sql'}),
        'allowed_intents': frozenset({'scrap'}),
    }),
    ('/overtime/', {
        'id': 'overtime', 'label': '勤務',
        'allowed_tools': frozenset({
            'get_business_data', 'search_employee', 'get_individual_overtime',
            'get_personal_overtime_threshold', 'execute_readonly_sql',
        }),
        'allowed_intents': frozenset({'overtime'}),
    }),
    ('/purchase/', {
        'id': 'purchase', 'label': '仕入', 'allowed_tools': frozenset(), 'allowed_intents': frozenset(),
    }),
    ('/shipping/', {
        'id': 'shipping', 'label': '出荷', 'allowed_tools': frozenset(), 'allowed_intents': frozenset(),
    }),
    ('/inventory/', {
        'id': 'inventory', 'label': '在庫', 'allowed_tools': frozenset(), 'allowed_intents': frozenset(),
    }),
)

DEFAULT_SCREEN_CONTEXT = {
    'id': 'ai_home', 'label': '本社横断',
    'allowed_tools': _ALL_CURRENT_TOOLS, 'allowed_intents': _ALL_CURRENT_INTENTS,
}


def resolve_screen_context(value):
    """クエリ文字列を含めず、登録済みの画面領域だけを返す。

    priority_tools / priority_intents は画面で優先して調べる対象。
    allowed_tools / allowed_intents は本社横断を含む許可範囲で、実際に使えるかは管理設定で最終決定する。
    """
    path = urlsplit(str(value or '')).path
    for prefix, context in SCREEN_CONTEXTS:
        if path.startswith(prefix):
            return {
                **context,
                'priority_tools': context['allowed_tools'],
                'priority_intents': context['allowed_intents'],
                'allowed_tools': _ALL_CURRENT_TOOLS | context['allowed_tools'],
                'allowed_intents': _ALL_CURRENT_INTENTS,
            }
    return {**DEFAULT_SCREEN_CONTEXT, 'priority_tools': frozenset(), 'priority_intents': frozenset()}
