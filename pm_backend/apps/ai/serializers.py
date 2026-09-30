from rest_framework import serializers

from ai.context.screen_context import resolve_screen_context
from ai.models import AIConversation


class AIConversationListSerializer(serializers.ModelSerializer):
    """一覧表示用。本文(messages)は含めず軽量にする。"""

    class Meta:
        model = AIConversation
        fields = ['id', 'title', 'screen_context', 'provider', 'created_at', 'updated_at']


class AIConversationSerializer(serializers.ModelSerializer):
    # 画面から来る元パスは長さもクエリ文字列も様々なため、登録済みの画面IDへ正規化して保存する。
    screen_context = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = AIConversation
        fields = ['id', 'title', 'screen_context', 'provider', 'messages', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_screen_context(self, value):
        return resolve_screen_context(value)['id']

    def validate_messages(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError('会話内容の形式が不正です。')
        return value
