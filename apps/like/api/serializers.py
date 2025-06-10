from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType

from apps.like.models import Like


class UserSerializer(serializers.ModelSerializer):
    avatar_url = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()
    is_verified = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'avatar_url', 'full_name', 'is_verified']
    
    def get_avatar_url(self, obj):
        if hasattr(obj, 'profile') and obj.profile.avatar:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.profile.avatar.url)
            return obj.profile.avatar.url
        return None
    
    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username
    
    def get_is_verified(self, obj):
        if hasattr(obj, 'profile'):
            return obj.profile.is_verified
        return False


class LikeSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    content_type_id = serializers.IntegerField(write_only=True)
    object_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = Like
        fields = ['id', 'user', 'content_type_id', 'object_id', 'created_at']
        read_only_fields = ['user', 'created_at']
    
    def validate(self, data):
        # Validate content type exists
        try:
            content_type = ContentType.objects.get(pk=data.get('content_type_id'))
            data['content_type'] = content_type
        except ContentType.DoesNotExist:
            raise serializers.ValidationError({"content_type_id": "Invalid content type ID."})
        
        # Validate object exists
        try:
            model_class = content_type.model_class()
            model_class.objects.get(pk=data.get('object_id'))
        except model_class.DoesNotExist:
            raise serializers.ValidationError(
                {"object_id": f"Object with ID {data.get('object_id')} does not exist."}
            )
        
        # Check if the user already liked this object
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            like_exists = Like.objects.filter(
                content_type=content_type,
                object_id=data.get('object_id'),
                user=request.user
            ).exists()
            
            if like_exists and request.method == 'POST':
                raise serializers.ValidationError(
                    {"non_field_errors": "You have already liked this content."}
                )
        
        return data
    
    def create(self, validated_data):
        request = self.context.get('request')
        content_type = validated_data.pop('content_type')
        
        like = Like(
            user=request.user,
            content_type=content_type,
            **validated_data
        )
        like.save()
        
        # Create notification for the like
        try:
            from apps.notifications.services import NotificationService
            model_class = content_type.model_class()
            content_object = model_class.objects.get(pk=validated_data.get('object_id'))
            
            # Only send notification if the like is not from the content owner
            if hasattr(content_object, 'user') and content_object.user != request.user:
                NotificationService.create_like_notification(
                    actor=request.user,
                    recipient=content_object.user,
                    content_object=content_object
                )
        except (ImportError, AttributeError):
            # If notification service is not available, continue without notifications
            pass
        
        return like