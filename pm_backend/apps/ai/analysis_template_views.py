"""テンプレートの保存・一覧・詳細(第3段階3-A)。権限は分析画面と同じai.analysis(閲覧はGET、保存はPOST)。"""
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ai.analysis_permissions import CanUseAIAnalysis
from ai.services.analysis_plan_store import AnalysisError
from ai.services.analysis_template_service import (
    get_visible_template, is_template_admin, parse_plan_id, save_template, serialize_template, visible_templates,
)


class TemplatePagination(PageNumberPagination):
    """一覧は30件ずつ(BOSS承認)。利用者がページサイズを変更できないようにする。"""
    page_size = 30
    page_size_query_param = None
    max_page_size = 30


class AIAnalysisTemplatesView(APIView):
    permission_classes = [IsAuthenticated, CanUseAIAnalysis]

    def get(self, request):
        admin = is_template_admin(request.user)
        paginator = TemplatePagination()
        rows = paginator.paginate_queryset(visible_templates(request.user, admin), request, view=self)
        return paginator.get_paginated_response([serialize_template(row, request.user, admin, False) for row in rows])

    def post(self, request):
        if not isinstance(request.data, dict) or set(request.data) != {'plan_id', 'revision'}:
            raise AnalysisError('plan_idとrevisionだけを指定してください。')
        template, created = save_template(request.user, parse_plan_id(request.data['plan_id']), request.data['revision'])
        data = serialize_template(template, request.user, is_template_admin(request.user), True)
        return Response({**data, 'created': created}, status=201 if created else 200)


class AIAnalysisTemplateView(APIView):
    permission_classes = [IsAuthenticated, CanUseAIAnalysis]

    def get(self, request, template_id):
        admin = is_template_admin(request.user)
        return Response(serialize_template(get_visible_template(template_id, request.user, admin), request.user, admin, True))
