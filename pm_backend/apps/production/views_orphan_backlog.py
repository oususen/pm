"""
孤立ライン実績メンテナンス画面のAPI。

ルーティングの入力ミスや後からのライン/工程変更により、現行の有効ルーティングには
もう存在しない(製品×ライン×工程)の組み合わせでLineBacklog/LineDemandが残ってしまう
ケースを検出し、安全なもの(全項目ゼロのゴースト行)に限り削除する。
実体のロジックは production.services.orphan_backlog_service を参照。

resource: settings.orphan_backlog_maintenance (view=レポート閲覧, edit=削除実行)
"""
import logging

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.views import _build_effective_permissions
from production.services import orphan_backlog_service as svc

logger = logging.getLogger('production')

RESOURCE = 'settings.orphan_backlog_maintenance'


def _has_resource_permission(user, level='view'):
    if getattr(user, 'is_superuser', False):
        return True
    for p in _build_effective_permissions(user):
        if p['resource'] == RESOURCE:
            if level == 'edit':
                return bool(p.get('can_edit'))
            return bool(p.get('can_view') or p.get('can_edit'))
    return False


class OrphanLineBacklogReportView(APIView):
    """孤立グループのdry-runレポート取得API"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not _has_resource_permission(request.user, 'view'):
            return Response({'detail': 'この機能を利用する権限がありません。'}, status=status.HTTP_403_FORBIDDEN)

        product_code = (request.query_params.get('product_code') or '').strip() or None
        report = svc.build_report(product_code)
        return Response(report)


class OrphanLineBacklogFixView(APIView):
    """孤立グループの削除実行API"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not _has_resource_permission(request.user, 'edit'):
            return Response({'detail': 'この機能を利用する権限がありません。'}, status=status.HTTP_403_FORBIDDEN)

        backlog_targets = request.data.get('backlog_targets') or []
        demand_targets = request.data.get('demand_targets') or []

        if not isinstance(backlog_targets, list) or not isinstance(demand_targets, list):
            return Response({'detail': '削除対象の指定が不正です。'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            cleaned_backlog = [
                {
                    'product_id': int(t['product_id']),
                    'line_id': int(t['line_id']),
                    'process_id': int(t['process_id']),
                    'force': bool(t.get('force')),
                }
                for t in backlog_targets
            ]
            cleaned_demand = [
                {
                    'product_id': int(t['product_id']),
                    'line_id': int(t['line_id']),
                    'force': bool(t.get('force')),
                }
                for t in demand_targets
            ]
        except (KeyError, TypeError, ValueError):
            return Response({'detail': '削除対象の指定が不正です。'}, status=status.HTTP_400_BAD_REQUEST)

        if not cleaned_backlog and not cleaned_demand:
            return Response({'detail': '削除対象が指定されていません。'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            result = svc.apply_fix(backlog_targets=cleaned_backlog, demand_targets=cleaned_demand)
            return Response({'detail': '削除を実行しました。', **result})
        except Exception as e:
            logger.exception('孤立ライン実績の削除に失敗')
            return Response(
                {'detail': f'削除に失敗しました: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
