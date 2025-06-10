from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType

from apps.bookmark.models import Bookmark


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


class BookmarkSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    content_type_id = serializers.IntegerField()
    object_id = serializers.IntegerField()
    content_type = serializers.SerializerMethodField()

    class Meta:
        model = Bookmark
        fields = ['id', 'user', 'content_type_id', 'object_id', 'content_type', 'created_at']
        read_only_fields = ['user', 'created_at']

    def get_content_type(self, obj):
        return {
            'id': obj.content_type.id,
            'model': obj.content_type.model,
            'app_label': obj.content_type.app_label
        }

    def validate(self, data):
        # Validate content type exists
        try:
            content_type = ContentType.objects.get(pk=data.get('content_type_id'))
            data['content_type'] = content_type
        except ContentType.DoesNotExist:
            raise serializers.ValidationError({"content_type_id": "Invalid content type ID."})
          # Validate object exists
        model_class = content_type.model_class()
        if model_class is None:
            raise serializers.ValidationError(
                {"content_type_id": f"Content type with id {data.get('content_type_id')} is not valid or doesn't have a model."}
            )
        
        try:
            model_class.objects.get(pk=data.get('object_id'))
        except model_class.DoesNotExist:
            raise serializers.ValidationError(
                {"object_id": f"Object with ID {data.get('object_id')} does not exist."}
            )
        
        # Check if the user already bookmarked this object
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            bookmark_exists = Bookmark.objects.filter(
                content_type=content_type,
                object_id=data.get('object_id'),
                user=request.user
            ).exists()
            
            if bookmark_exists and request.method == 'POST':
                raise serializers.ValidationError(
                    {"non_field_errors": "You have already bookmarked this content."}
                )
        
        return data
    def create(self, validated_data):
        request = self.context.get('request')
        if not request or not request.user:
            raise serializers.ValidationError({"user": "User must be authenticated to bookmark content."})
            
        content_type = validated_data.pop('content_type')
        
        bookmark = Bookmark(
            user=request.user,
            content_type=content_type,
            **validated_data
        )
        bookmark.save()
        
        return bookmark