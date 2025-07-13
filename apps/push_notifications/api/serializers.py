from rest_framework import serializers
from ..models import FCMToken


class FCMTokenSerializer(serializers.ModelSerializer):
    """
    FCM Token serializer
    """
    
    class Meta:
        model = FCMToken
        fields = ['fcm_token', 'platform', 'device_info', 'device_name']
        extra_kwargs = {
            'fcm_token': {'required': True},
            'platform': {'required': True},
        }


class SendNotificationSerializer(serializers.Serializer):
    """
    Notification gönderme için serializer
    """
    user_id = serializers.IntegerField(required=False)
    title = serializers.CharField(max_length=255)
    body = serializers.CharField()
    data = serializers.JSONField(required=False)


class SendChatNotificationSerializer(serializers.Serializer):
    """
    Chat notification gönderme için serializer
    """
    user_id = serializers.IntegerField()
    sender_name = serializers.CharField(max_length=150)
    message = serializers.CharField()
    chat_id = serializers.CharField()


class SendLikeNotificationSerializer(serializers.Serializer):
    """
    Like notification gönderme için serializer
    """
    user_id = serializers.IntegerField()
    liker_name = serializers.CharField(max_length=150)
    post_id = serializers.CharField()


class SendCommentNotificationSerializer(serializers.Serializer):
    """
    Comment notification gönderme için serializer
    """
    user_id = serializers.IntegerField()
    commenter_name = serializers.CharField(max_length=150)
    post_id = serializers.CharField()


class SendFollowNotificationSerializer(serializers.Serializer):
    """
    Follow notification gönderme için serializer
    """
    user_id = serializers.IntegerField()
    follower_name = serializers.CharField(max_length=150)
    follower_id = serializers.CharField()
