"""分析画面と同じ明示資源権限と、既存の本人／全件履歴の条件を照合する。"""
from redis.exceptions import RedisError
from rest_framework.exceptions import APIException, PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ai.analysis_permissions import CanUseAIAnalysis
from ai.services.analysis_job_service import JobStore, WorkerStaleError, execution_enabled
from ai.services.analysis_plan_store import AnalysisError
from ai.services.analysis_run_service import serialize_run, visible_runs
from ai.services.chat_service import _has_resource_permission
from project.pagination import StandardResultsSetPagination


def state_operation(operation):
    try:
        return operation()
    except RedisError as exc:
        raise AnalysisError('実行状態の保持先へ接続できません。自動再実行せず、状態を確認してください。', 503) from exc


class AIAnalysisExecuteView(APIView):
    permission_classes = [IsAuthenticated, CanUseAIAnalysis]

    def post(self, request, plan_id):
        keys = set(request.data) if isinstance(request.data, dict) else set()
        if keys not in ({'revision', 'executed_code_sha256'}, {'revision', 'executed_code_sha256', 'template_confirmed'}):
            raise AnalysisError('承認した版とコード全体のハッシュ(テンプレートから作成した場合はtemplate_confirmedも)のみを指定してください。')
        try:
            job = state_operation(lambda: JobStore().submit(
                request.user, str(plan_id), request.data['revision'], request.data['executed_code_sha256'],
                request.data.get('template_confirmed')))
        except WorkerStaleError:
            return Response({'reason': 'worker_stale', 'detail': '専用ワーカーを再起動してください。'}, status=503)
        return Response(job, status=202)


class AIAnalysisExecutionOptionsView(APIView):
    permission_classes = [IsAuthenticated, CanUseAIAnalysis]

    def get(self, request):
        try:
            execution_enabled()
        except AnalysisError:
            return Response({'enabled': False, 'ready': False, 'notice': '本番では実行無効です。開発はlauncherと専用ワーカーを起動してください。'})
        def ready_now():
            store = JobStore()
            worker = store.client.get(store.worker_key)
            stale = bool(worker) and not store.worker_current(worker)
            return bool(worker) and not stale and not bool(store.client.get(store.active_key)), stale
        ready, stale = state_operation(ready_now)
        if stale:
            return Response({'enabled': True, 'ready': False, 'reason': 'worker_stale',
                             'notice': '専用ワーカーを再起動してください。'})
        return Response({'enabled': True, 'ready': ready, 'notice': '開発限定。実行は1件で、待ち行列はありません。' if ready else '専用ワーカー未起動、実行中、または後始末未確認です。状態を確認してください。'})


class AIAnalysisJobView(APIView):
    permission_classes = [IsAuthenticated, CanUseAIAnalysis]

    def get(self, request, job_id):
        return Response(state_operation(lambda: JobStore().get(str(job_id), request.user.pk)))


class AIAnalysisJobCancelView(APIView):
    permission_classes = [IsAuthenticated, CanUseAIAnalysis]

    def post(self, request, job_id):
        if request.data:
            raise AnalysisError('中止には追加の入力を指定しないでください。')
        return Response(state_operation(lambda: JobStore().cancel(str(job_id), request.user.pk)), status=202)


class AIAnalysisRunsView(APIView):
    permission_classes = [IsAuthenticated, CanUseAIAnalysis]

    def get(self, request):
        include_all = request.query_params.get('include_all') == 'true'
        if include_all:
            try:
                allowed = _has_resource_permission(request.user, 'settings.ai', 'edit')
            except Exception:
                allowed = False
            if not allowed:
                raise PermissionDenied('全利用者の実行履歴を閲覧する権限がありません。')
        try:
            queryset = visible_runs(request.user, include_all)
            paginator = StandardResultsSetPagination()
            rows = paginator.paginate_queryset(queryset, request, view=self)
            if rows is None:
                return Response([serialize_run(row) for row in queryset])
            return paginator.get_paginated_response([serialize_run(row) for row in rows])
        except APIException:
            raise
        except Exception as exc:
            raise AnalysisError('実行履歴を取得できません。DBとマイグレーションを確認してください。', 503) from exc
