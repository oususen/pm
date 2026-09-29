"""画面へ公開する社内AI設定の固定カタログ。"""

PROVIDER_CATALOG = {
    'deepseek': {
        'label': 'DeepSeek API',
        'models': (
            ('deepseek-v4-pro', 'DeepSeek V4 Pro（高精度）'),
            ('deepseek-flash', 'DeepSeek Flash（高速）'),
        ),
    },
    'qwen': {
        'label': 'ローカルQwen',
        'models': (('qwen3:4b-instruct', 'Qwen3 4B Instruct（ローカル）'),),
    },
    'openrouter': {
        'label': 'OpenRouter（評価用）',
        'models': (('qwen/qwen3.8-27b:free', 'Qwen3.8 27B（OpenRouter・無料枠）'),),
    },
}

SCREEN_CATALOG = {
    'ai_home': '本社横断',
    'orders': '受注',
    'production': '生産',
    'quality': '品質',
    'overtime': '勤務',
    'purchase': '仕入',
    'shipping': '出荷',
    'inventory': '在庫',
}

TOOL_CATALOG = {
    'search_product': {'label': '品番マスタ検索', 'kind': 'master'},
    'count_products': {'label': '品番マスタ件数集計', 'kind': 'master'},
    'get_business_data': {'label': '生産・品質・残業の集計', 'kind': 'aggregate'},
    'get_missing_routing_orders': {'label': 'ルーティング未設定品の確認', 'kind': 'aggregate'},
    'search_employee': {'label': '社員候補検索', 'kind': 'personal'},
    'get_individual_overtime': {'label': '個人別残業集計', 'kind': 'personal'},
    'get_personal_overtime_threshold': {'label': '残業しきい値超過者集計', 'kind': 'personal'},
    'execute_readonly_sql': {'label': 'AI用DB辞書の読み取りSQL', 'kind': 'sql'},
}

KNOWLEDGE_CATEGORY_CHOICES = (
    ('pm_structure', 'PMアプリ構造'),
    ('manual', 'マニュアル'),
    ('procedure', '手順書'),
    ('security', '安全・運用規約'),
)
