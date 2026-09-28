from django.apps import apps
from rest_framework import serializers, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from production.models_ai_config import AISearchConfig


class AISearchConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = AISearchConfig
        fields = '__all__'

    def validate_model_path(self, value):
        try:
            app_label, model_name = value.split('.')
            apps.get_model(app_label, model_name)
        except (ValueError, LookupError):
            raise serializers.ValidationError(f'モデル「{value}」が見つかりません。「app名.Model名」の形式で指定してください。')
        return value

    def validate_search_fields(self, value):
        if not isinstance(value, list) or not value:
            raise serializers.ValidationError('検索フィールドを1つ以上指定してください。')
        return value

    def validate_display_fields(self, value):
        if not isinstance(value, list) or not value:
            raise serializers.ValidationError('表示フィールドを1つ以上指定してください。')
        return value


class AISearchConfigViewSet(viewsets.ModelViewSet):
    queryset = AISearchConfig.objects.all()
    serializer_class = AISearchConfigSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None


class AISearchConfigModelsView(APIView):
    """AIチャットで検索対象にできるモデルとフィールドの一覧"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        allowed_apps = (
            'masters', 'production', 'orders', 'shipping',
            'purchase', 'quality', 'overtime', 'outsource', 'accounts',
        )
        result = []
        for app_config in apps.get_app_configs():
            if app_config.label not in allowed_apps:
                continue
            for model in app_config.get_models():
                fields = []
                for f in model._meta.get_fields():
                    if not hasattr(f, 'column'):
                        continue
                    fields.append({
                        'name': f.name,
                        'type': f.get_internal_type(),
                        'verbose_name': str(f.verbose_name) if hasattr(f, 'verbose_name') else f.name,
                    })
                result.append({
                    'model_path': f'{app_config.label}.{model.__name__}',
                    'verbose_name': str(model._meta.verbose_name),
                    'fields': fields,
                })
        result.sort(key=lambda x: x['model_path'])
        return Response(result)
