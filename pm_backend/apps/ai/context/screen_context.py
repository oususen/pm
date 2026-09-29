"""画面起点ごとに、社内AIが使用できる業務領域を決める。"""
from urllib.parse import urlsplit


_ALL_CURRENT_TOOLS = frozenset({
    'search_product', 'count_products', 'get_business_data',
    'search_employee', 'get_individual_overtime', 'get_personal_overtime_threshold',
})
_ALL_CURRENT_INTENTS = frozenset({'production', 'scrap', 'interruption', 'overtime'})

SCREEN_CONTEXTS = (
    ('/orders/', {
        'id': 'orders', 'label': '受注',
        'allowed_tools': frozenset({'get_missing_routing_orders'}), 'allowed_intents': frozenset(),
    }),
    ('/production/', {
        'id': 'production', 'label': '生産',
        'allowed_tools': frozenset({'search_product', 'count_products', 'get_business_data'}),
        'allowed_intents': frozenset({'production', 'scrap', 'interruption', 'overtime'}),
    }),
    ('/quality/', {
        'id': 'quality', 'label': '品質',
        'allowed_tools': frozenset({'search_product', 'get_business_data'}),
        'allowed_intents': frozenset({'scrap'}),
    }),
    ('/overtime/', {
        'id': 'overtime', 'label': '勤務',
        'allowed_tools': frozenset({
            'get_business_data', 'search_employee', 'get_individual_overtime',
            'get_personal_overtime_threshold',
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
    """クエリ文字列を含めず、登録済みの画面領域だけを返す。"""
    path = urlsplit(str(value or '')).path
    for prefix, context in SCREEN_CONTEXTS:
        if path.startswith(prefix):
            return context
    return DEFAULT_SCREEN_CONTEXT
