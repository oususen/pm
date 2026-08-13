from django.contrib.auth.hashers import make_password, check_password
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response

from .models import SystemSetting
from .serializers import SystemSettingSerializer

PLAN_QTY_EDIT_PW_KEY = 'production.plan_qty_edit_password'


class SystemSettingViewSet(viewsets.GenericViewSet):
    queryset = SystemSetting.objects.all()
    serializer_class = SystemSettingSerializer

    def get_permissions(self):
        if self.action in ('list', 'verify_plan_qty_password'):
            return [IsAuthenticated()]
        return [IsAdminUser()]

    def create(self, request):
        """新規設定を作成"""
        key = request.data.get('key', '').strip()
        value = request.data.get('value', '')
        description = request.data.get('description', '')
        if not key:
            return Response({'key': 'キーは必須です'}, status=status.HTTP_400_BAD_REQUEST)
        if SystemSetting.objects.filter(key=key).exists():
            return Response({'key': 'このキーはすでに存在します'}, status=status.HTTP_400_BAD_REQUEST)
        instance = SystemSetting.objects.create(
            key=key,
            value=str(value),
            description=description,
            updated_by=request.user,
        )
        serializer = self.get_serializer(instance)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def list(self, request):
        """全設定をキーの辞書形式で返す"""
        settings = SystemSetting.objects.all()
        result = {}
        for s in settings:
            result[s.key] = {
                'value': s.value,
                'description': s.description,
                'updated_at': s.updated_at,
                'updated_by': s.updated_by.username if s.updated_by else None,
            }
        return Response(result)

    def list_detail(self, request):
        """設定一覧をリスト形式で返す（管理画面用）"""
        settings = SystemSetting.objects.all()
        serializer = self.get_serializer(settings, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='set-plan-qty-password')
    def set_plan_qty_password(self, request):
        """計画数編集用パスワードを設定"""
        pw = request.data.get('password', '')
        if not pw or len(pw) < 1:
            return Response({'detail': 'パスワードを入力してください。'}, status=status.HTTP_400_BAD_REQUEST)
        hashed = make_password(pw)
        SystemSetting.objects.update_or_create(
            key=PLAN_QTY_EDIT_PW_KEY,
            defaults={'value': hashed, 'description': '計画数編集用パスワード', 'updated_by': request.user},
        )
        return Response({'detail': '計画数編集用パスワードを設定しました。'})

    @action(detail=False, methods=['post'], url_path='verify-plan-qty-password')
    def verify_plan_qty_password(self, request):
        """計画数編集用パスワードを検証"""
        pw = request.data.get('password', '')
        row = SystemSetting.objects.filter(key=PLAN_QTY_EDIT_PW_KEY).first()
        if not row:
            return Response({'detail': 'パスワードが未設定です。'}, status=status.HTTP_400_BAD_REQUEST)
        if not check_password(pw, row.value):
            return Response({'detail': 'パスワードが正しくありません。'}, status=status.HTTP_403_FORBIDDEN)
        return Response({'detail': 'OK'})

    @action(detail=False, methods=['patch'], url_path='update-by-key')
    def update_by_key(self, request):
        """複数キーをまとめて更新: { key: value, ... }"""
        updated = []
        for key, value in request.data.items():
            SystemSetting.objects.update_or_create(
                key=key,
                defaults={'value': str(value), 'updated_by': request.user},
            )
            updated.append(key)
        return Response({'updated': updated})
