from rest_framework.pagination import PageNumberPagination


class StandardResultsSetPagination(PageNumberPagination):
    """
    カスタムページネーション
    - デフォルトページサイズ: 50
    - クライアントが page_size パラメータで指定可能
    - 最大ページサイズ: 10000
    """
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 10000
