from production.views import LineBacklogViewSet


class _DummyRequest:
    """自動計画専用の簡易リクエスト"""
    def __init__(self, data):
        self.data = data
        self.user = None


def expand_processes_for_auto_plan(line_id, start_date, end_date):
    """
    自動計画専用の工程展開。
    auto_plan_mode=True を明示して、手動展開ロジックと分離する。
    """
    viewset = LineBacklogViewSet()
    viewset.format_kwarg = None
    viewset.kwargs = {}
    req = _DummyRequest({
        'line_id': line_id,
        'start_date': str(start_date),
        'end_date': str(end_date),
        'items': [],
        'read_only': False,
        'include_coproduct_children': True,
        'auto_plan_mode': True,
    })
    viewset.request = req
    viewset.expand_processes(req)

