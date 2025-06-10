from rest_framework import serializers
from ..models import PushToken


class PushTokenSerializer(serializers.ModelSerializer):
    """
    Push Token serializer
    """
    class Meta:
        model = PushToken
        fields = ['expo_token', 'device_name', 'is_active']
        read_only_fields = ['created_at', 'updated_at']


class SendNotificationSerializer(serializers.Serializer):
    """
    Bildirim gönderme serializer
    """
    user_id = serializers.IntegerField()
    title = serializers.CharField(max_length=100)
    body = serializers.CharField(max_length=200)
    data = serializers.JSONField(required=False)


class SendChatNotificationSerializer(serializers.Serializer):
    """
    Chat bildirimi gönderme serializer
    """
    user_id = serializers.IntegerField()
    sender_name = serializers.CharField(max_length=100)
    message = serializers.CharField(max_length=500)
    chat_room_id = serializers.CharField(max_length=50)
