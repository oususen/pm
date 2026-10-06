"""テンプレートの保存・一覧・詳細(第3段階3-A)と、管理者の承認・却下(3-B)。

保存・一覧・詳細の権限は分析画面と同じai.analysis(閲覧はGET、保存はPOST)。承認・却下はAI設定の編集権限(settings.ai / can_edit)。
"""
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ai.analysis_permissions import CanReviewAITemplates, CanUseAIAnalysis
from ai.models import AIAnalysisTemplate
from ai.services.analysis_plan_store import AnalysisError
from ai.services.analysis_template_reuse_service import create_plan_from_template
from ai.services.analysis_template_notify_service import resend as resend_notification
from ai.services.analysis_template_review_service import approve_template, reject_template
from ai.services.analysis_template_service import (
    change_category, get_visible_template, is_template_admin, parse_plan_id, save_template, serialize_template, validate_category,
    visible_templates,
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
        queryset = visible_templates(request.user, admin)
        status = request.query_params.get('status')
        if status is not None:
            # 状態の絞り込み(管理者の確認一覧など)。値は4つの状態だけ。見える範囲は変えない
            if status not in dict(AIAnalysisTemplate.STATUS_CHOICES):
                raise AnalysisError('状態の指定が不正です。')
            queryset = queryset.filter(status=status)
        category = request.query_params.get('category')
        if category is not None:
            queryset = queryset.filter(category=validate_category(category))  # 見える範囲は変えない
        paginator = TemplatePagination()
        rows = paginator.paginate_queryset(queryset, request, view=self)
        return paginator.get_paginated_response([serialize_template(row, request.user, admin, False) for row in rows])

    def post(self, request):
        keys = set(request.data) if isinstance(request.data, dict) else set()
        if keys not in ({'plan_id', 'revision', 'category'}, {'plan_id', 'revision', 'category', 'replaces'}):
            raise AnalysisError('plan_id・revision・category(訂正版はreplacesも)だけを指定してください。')
        template, created = save_template(
            request.user, parse_plan_id(request.data['plan_id']), request.data['revision'], request.data.get('replaces'), request.data['category'],
        )
        data = serialize_template(template, request.user, is_template_admin(request.user), True)
        return Response({**data, 'created': created}, status=201 if created else 200)


class AIAnalysisTemplateView(APIView):
    permission_classes = [IsAuthenticated, CanUseAIAnalysis]

    def get(self, request, template_id):
        admin = is_template_admin(request.user)
        return Response(serialize_template(get_visible_template(template_id, request.user, admin), request.user, admin, True))


class AIAnalysisTemplateCategoryView(APIView):
    """カテゴリの変更(作成者と管理者)。内容・状態・ハッシュは変えない。"""
    permission_classes = [IsAuthenticated, CanUseAIAnalysis]

    def post(self, request, template_id):
        if not isinstance(request.data, dict) or set(request.data) != {'category'}:
            raise AnalysisError('categoryだけを指定してください。')
        admin = is_template_admin(request.user)
        template = change_category(request.user, template_id, request.data['category'], admin)
        return Response(serialize_template(template, request.user, admin, True))


class AIAnalysisTemplateApproveView(APIView):
    permission_classes = [IsAuthenticated, CanReviewAITemplates]

    def post(self, request, template_id):
        if not isinstance(request.data, dict) or set(request.data) != {'state_revision'}:
            raise AnalysisError('state_revisionだけを指定してください。')
        template = approve_template(request.user, template_id, request.data['state_revision'])
        return Response(serialize_template(template, request.user, True, True))


class AIAnalysisTemplateRejectView(APIView):
    permission_classes = [IsAuthenticated, CanReviewAITemplates]

    def post(self, request, template_id):
        if not isinstance(request.data, dict) or set(request.data) != {'state_revision', 'reason'}:
            raise AnalysisError('state_revisionとreasonだけを指定してください。')
        template = reject_template(request.user, template_id, request.data['state_revision'], request.data['reason'])
        return Response(serialize_template(template, request.user, True, True))


class AIAnalysisTemplateNotificationResendView(APIView):
    """失敗・送れなかったメールの手動の再送(同じ宛先へ1回だけ)。作成者と管理者だけ。"""
    permission_classes = [IsAuthenticated, CanUseAIAnalysis]

    def post(self, request, record_id):
        if not isinstance(request.data, dict) or len(request.data):
            raise AnalysisError('本文は指定できません。')
        admin = is_template_admin(request.user)
        template = resend_notification(request.user, record_id, admin)
        return Response(serialize_template(template, request.user, admin, True))


class AIAnalysisTemplatePlanView(APIView):
    """保存済みのテンプレートから、新しい分析案(手順の承認待ち)を作る。AIは呼ばない。"""
    permission_classes = [IsAuthenticated, CanUseAIAnalysis]

    def post(self, request, template_id):
        if not isinstance(request.data, dict) or set(request.data) - {'parameters'}:
            raise AnalysisError('指定できるのは、変数の値(parameters)だけです。')
        supplied = request.data.get('parameters')
        if 'parameters' in request.data and not isinstance(supplied, dict):
            raise AnalysisError('変数の値の形式が不正です。')  # 0・空文字・空の配列・nullを、「指定なし」として通さない
        from ai.views import _codegen_response  # 分析案の応答の形を、既存の分析案APIと同じにする
        return Response(_codegen_response(create_plan_from_template(request.user, template_id, supplied)), status=201)
