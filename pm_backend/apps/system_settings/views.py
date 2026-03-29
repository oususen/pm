from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response

from .models import SystemSetting
from .serializers import SystemSettingSerializer


class SystemSettingViewSet(viewsets.GenericViewSet):
    queryset = SystemSetting.objects.all()
    serializer_class = SystemSettingSerializer

    def get_permissions(self):
        if self.action == 'list':
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

    @action(detail=False, methods=['patch'], url_path='update-by-key')
    def update_by_key(self, request):
        """複数キーをまとめて更新: { key: value, ... }"""
        updated = []
        errors = {}
        for key, value in request.data.items():
            try:
                instance = SystemSetting.objects.get(key=key)
                instance.value = str(value)
                instance.updated_by = request.user
                instance.save()
                updated.append(key)
            except SystemSetting.DoesNotExist:
                errors[key] = 'キーが存在しません'

        if errors:
            return Response({'updated': updated, 'errors': errors}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'updated': updated})
