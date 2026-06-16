from rest_framework.pagination import PageNumberPagination


class StandardResultsSetPagination(PageNumberPagination):
    """
    カスタムページネーション
    - デフォルトページサイズ: 50
    - クライアントが page_size パラメータで指定可能
    - 最大ページサイズ: 20000
    - page_size=0 でページネーション無効（全件返却）
    """
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 20000

    def get_page_size(self, request):
        if self.page_size_query_param in request.query_params:
            try:
                value = int(request.query_params[self.page_size_query_param])
                if value == 0:
                    return None
            except (ValueError, TypeError):
                pass
        return super().get_page_size(request)
