"""AIチャットに適用する設定値を、固定カタログの範囲内で読み出す。"""
from ai.config.catalog import PROVIDER_CATALOG, TOOL_CATALOG
from ai.config.models import AIDataPolicy, AIProviderConfig, AIToolPolicy


def get_provider_settings():
    """保存済み設定と固定カタログを結合し、画面へ返す。"""
    configured = {item.provider: item for item in AIProviderConfig.objects.all()}
    return [
        {
            'provider': provider,
            'label': item['label'],
            'models': [{'id': model_id, 'label': model_label} for model_id, model_label in item['models']],
            'default_model': configured[provider].default_model,
            'is_enabled': configured[provider].is_enabled,
            'display_order': configured[provider].display_order,
        }
        for provider, item in PROVIDER_CATALOG.items()
        if provider in configured
    ]


def get_data_policy():
    """全体データ送信方針を返す。初期データにより必ず1件存在する。"""
    return AIDataPolicy.objects.get()


def apply_tool_policy(screen_context, is_external_provider=False):
    """管理設定でツールを絞り込む。

    画面ごと、または本社横断(ai_home)の設定のどちらかで有効なツールを使用可能とする。
    画面で優先するツール(priority_tools)も、管理設定で許可されたものだけに限る。
    """
    enabled = set()
    for screen_id in {'ai_home', screen_context['id']}:
        for item in AIToolPolicy.objects.filter(screen_id=screen_id):
            if not item.is_enabled:
                continue
            if is_external_provider and not item.allow_external_transfer:
                continue
            enabled.add(item.tool_code)
    allowed_tools = frozenset(
        tool_code for tool_code in screen_context['allowed_tools']
        if tool_code in enabled and tool_code in TOOL_CATALOG
    )
    priority_tools = frozenset(screen_context.get('priority_tools', ())) & allowed_tools
    return {**screen_context, 'allowed_tools': allowed_tools, 'priority_tools': priority_tools}


def external_aggregate_transfer_allowed():
    """外部AIへ集計結果を送る全体許可を返す。"""
    return get_data_policy().allow_aggregated_external_transfer


def authorized_personal_data_allowed():
    """画面側で権限を確認済みの個人別集計を許可するか返す。"""
    return get_data_policy().allow_authorized_personal_data


def external_image_transfer_allowed():
    """利用者が明示添付した画像を外部AIへ渡す全体許可を返す。"""
    return get_data_policy().allow_external_image_transfer


def limit_external_result_rows(result):
    """DeepSeekへ渡すリスト型の集計結果を、管理上限までに限定する。"""
    max_rows = get_data_policy().max_external_result_rows
    if not isinstance(result, dict):
        return result
    limited = dict(result)
    for key, value in result.items():
        if isinstance(value, list):
            limited[key] = value[:max_rows]
    return limited
