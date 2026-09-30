"""AI管理設定APIの入力検証。固定カタログ以外のツールは登録させない。"""
from rest_framework import serializers

from ai.config.catalog import PROVIDER_CATALOG, TOOL_CATALOG
from ai.config.models import AIDataPolicy, AIKnowledgeDocument, AIKnowledgeSource, AIProviderConfig, AIToolPolicy


class AIProviderConfigSerializer(serializers.ModelSerializer):
    label = serializers.SerializerMethodField()
    models = serializers.SerializerMethodField()

    class Meta:
        model = AIProviderConfig
        fields = ('id', 'provider', 'label', 'models', 'default_model', 'is_enabled', 'display_order', 'updated_at')
        read_only_fields = ('provider', 'label', 'models', 'updated_at')

    def get_label(self, obj):
        return PROVIDER_CATALOG[obj.provider]['label']

    def get_models(self, obj):
        return [
            {'id': model_id, 'label': model_label}
            for model_id, model_label in PROVIDER_CATALOG[obj.provider]['models']
        ]

    def validate_default_model(self, value):
        provider = self.instance.provider if self.instance else self.initial_data.get('provider')
        allowed = {model_id for model_id, _ in PROVIDER_CATALOG.get(provider, {}).get('models', ())}
        if value not in allowed:
            raise serializers.ValidationError('このプロバイダで選択できないモデルです。')
        return value


class AIToolPolicySerializer(serializers.ModelSerializer):
    screen_label = serializers.SerializerMethodField()
    tool_label = serializers.SerializerMethodField()
    tool_kind = serializers.SerializerMethodField()

    class Meta:
        model = AIToolPolicy
        fields = (
            'id', 'screen_id', 'screen_label', 'tool_code', 'tool_label', 'tool_kind',
            'is_enabled', 'allow_external_transfer', 'updated_at',
        )
        read_only_fields = ('screen_id', 'screen_label', 'tool_code', 'tool_label', 'tool_kind', 'updated_at')

    def get_screen_label(self, obj):
        return obj.get_screen_id_display()

    def get_tool_label(self, obj):
        return TOOL_CATALOG[obj.tool_code]['label']

    def get_tool_kind(self, obj):
        return TOOL_CATALOG[obj.tool_code]['kind']


class AIDataPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = AIDataPolicy
        fields = (
            'id', 'allow_aggregated_external_transfer', 'allow_authorized_personal_data',
            'allow_external_image_transfer',
            'max_external_result_rows', 'conversation_retention_days', 'updated_at',
        )
        read_only_fields = ('updated_at',)

    def validate_conversation_retention_days(self, value):
        if value > 3650:
            raise serializers.ValidationError('保存期間は3650日以下で指定してください。')
        return value

    def validate_max_external_result_rows(self, value):
        if not 1 <= value <= 100:
            raise serializers.ValidationError('外部送信する集計行数は1〜100件で指定してください。')
        return value


class AIKnowledgeSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIKnowledgeSource
        fields = '__all__'
        read_only_fields = ('updated_at',)

    def validate_relative_path(self, value):
        normalized = value.replace('\\', '/').strip()
        if not normalized.startswith('apps/ai/knowledge/'):
            raise serializers.ValidationError('AIナレッジフォルダ配下の相対パスを指定してください。')
        if '..' in normalized.split('/'):
            raise serializers.ValidationError('親フォルダへの移動は指定できません。')
        return normalized


class AIKnowledgeDocumentSerializer(serializers.ModelSerializer):
    """アップロード可能な資料種別とサイズを限定する。"""
    class Meta:
        model = AIKnowledgeDocument
        fields = '__all__'
        read_only_fields = ('uploaded_at', 'updated_at')

    def validate_file(self, value):
        suffix = value.name.rsplit('.', 1)[-1].lower() if '.' in value.name else ''
        if suffix not in {'pdf', 'xlsx', 'xls', 'csv', 'tsv', 'png', 'jpg', 'jpeg', 'webp', 'bmp'}:
            raise serializers.ValidationError('PDF、Excel、CSV、TSV、画像（PNG / JPG / WEBP / BMP）だけを登録できます。')
        if value.size > 15 * 1024 * 1024:
            raise serializers.ValidationError('登録できる資料は15MBまでです。')
        return value
