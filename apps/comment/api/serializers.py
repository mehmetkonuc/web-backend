from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.utils.module_loading import import_string

from apps.comment.models import Comment, CommentImage


class UserSerializer(serializers.ModelSerializer):
    avatar_url = serializers.SerializerMethodField()
    avatar_thumbnail = serializers.SerializerMethodField()
    avatar_medium = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()
    is_verified = serializers.SerializerMethodField()
    university = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'avatar_url', 'avatar_thumbnail', 
            'avatar_medium', 'full_name', 'is_verified', 'university'
        ]
    
    def get_avatar_url(self, obj):
        """Backward compatibility için original avatar"""
        if hasattr(obj, 'profile') and obj.profile:
            url = obj.profile.get_avatar_url('original')
            if url:
                request = self.context.get('request')
                if request:
                    return request.build_absolute_uri(url)
        return None
    
    def get_avatar_thumbnail(self, obj):
        """Avatar thumbnail (150x150)"""
        if hasattr(obj, 'profile') and obj.profile:
            url = obj.profile.get_avatar_url('thumbnail')
            if url:
                request = self.context.get('request')
                if request:
                    return request.build_absolute_uri(url)
        return None
    
    def get_avatar_medium(self, obj):
        """Avatar medium (300x300)"""
        if hasattr(obj, 'profile') and obj.profile:
            url = obj.profile.get_avatar_url('medium')
            if url:
                request = self.context.get('request')
                if request:
                    return request.build_absolute_uri(url)
        return None
    
    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username
    
    def get_is_verified(self, obj):
        if hasattr(obj, 'profile'):
            return obj.profile.is_verified
        return False
    
    def get_university(self, obj):
        if hasattr(obj, 'profile') and obj.profile.university:
            return obj.profile.university.name
        return None


class CommentImageSerializer(serializers.ModelSerializer):
    """
    Optimize edilmiş CommentImage serializer - multiple image sizes destekler
    """
    # Multiple image sizes
    image_thumbnail = serializers.SerializerMethodField()
    image_medium = serializers.SerializerMethodField()
    image_large = serializers.SerializerMethodField()
    image_original = serializers.SerializerMethodField()
    
    # Metadata
    file_size_formatted = serializers.SerializerMethodField()
    dimensions = serializers.SerializerMethodField()
    
    class Meta:
        model = CommentImage
        fields = [
            'id', 'order', 'processed',
            'image_thumbnail', 'image_medium', 'image_large', 'image_original',
            'file_size', 'file_size_formatted', 'format', 'dimensions'
        ]
    
    def get_image_thumbnail(self, obj):
        """Thumbnail URL'ini döndür (150x150)"""
        url = obj.get_best_image_url('thumbnail')
        if url:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(url)
        return None
    
    def get_image_medium(self, obj):
        """Medium URL'ini döndür (600x600)"""
        url = obj.get_best_image_url('medium')
        if url:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(url)
        return None
    
    def get_image_large(self, obj):
        """Large URL'ini döndür (1200x1200)"""
        url = obj.get_best_image_url('large')
        if url:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(url)
        return None
    
    def get_image_original(self, obj):
        """Original URL'ini döndür"""
        url = obj.get_best_image_url('original')
        if url:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(url)
        return None
    
    def get_file_size_formatted(self, obj):
        """Dosya boyutunu human-readable formatta döndür"""
        if not obj.file_size:
            return None
        
        # Convert bytes to human readable format
        file_size = obj.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if file_size < 1024.0:
                return f"{file_size:.1f} {unit}"
            file_size /= 1024.0
        return f"{file_size:.1f} TB"
    
    def get_dimensions(self, obj):
        """Resim boyutlarını döndür"""
        if obj.original_width and obj.original_height:
            return f"{obj.original_width}x{obj.original_height}"
        return None


class RecursiveCommentSerializer(serializers.Serializer):
    """
    A serializer for handling recursive comments (replies)
    """
    def to_representation(self, instance):
        serializer = CommentSerializer(instance, context=self.context)
        return serializer.data


class CommentSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    replies = RecursiveCommentSerializer(many=True, read_only=True)
    images = serializers.SerializerMethodField()
    like_count = serializers.SerializerMethodField()
    bookmark_count = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    is_bookmarked = serializers.SerializerMethodField()
    comment_content_type_id = serializers.SerializerMethodField()
    content_type_id = serializers.IntegerField()
    object_id = serializers.IntegerField()
    parent_id = serializers.IntegerField(required=False, allow_null=True)
    images_upload = serializers.ListField(
        child=serializers.ImageField(max_length=1000000, allow_empty_file=False, use_url=False),
        write_only=True,
        required=False
    )
    
    class Meta:
        model = Comment
        fields = [
            'id', 'user', 'comment_content_type_id', 'content_type_id', 'object_id', 'parent_id',
            'body', 'created_at', 'updated_at', 'replies', 'images',
            'images_upload', 'like_count', 'is_liked', 'bookmark_count', 'is_bookmarked'
        ]
        read_only_fields = ['user', 'created_at', 'updated_at']

    def get_comment_content_type_id(self, obj):
        """Comment modelinin ContentType ID'sini döndürür"""
        from django.contrib.contenttypes.models import ContentType
        return ContentType.objects.get_for_model(Comment).id
    
    def get_like_count(self, obj):
        return obj.get_like_count()

    def get_bookmark_count(self, obj):
        return obj.get_bookmark_count()
    
    def get_is_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.is_liked_by(request.user)
        return False
    
    def get_is_bookmarked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.is_bookmarked_by(request.user)
        return False
    
    def get_images(self, obj):
        # Yorumun resimlerini sıralı şekilde al
        comment_images = obj.images.all().order_by('order')
        serializer = CommentImageSerializer(comment_images, many=True, context=self.context)
        return serializer.data
    
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
            raise serializers.ValidationError({"object_id": f"Object with ID {data.get('object_id')} does not exist."})
        
        # Validate parent comment exists if provided
        parent_id = data.get('parent_id')
        if parent_id:
            try:
                parent_comment = Comment.objects.get(pk=parent_id)
                # Ensure the parent comment is associated with the same content object
                if parent_comment.content_type_id != data['content_type'].id or parent_comment.object_id != data.get('object_id'):
                    raise serializers.ValidationError({"parent_id": "Parent comment must be associated with the same content object."})
                # Ensure we're not replying to a reply (only one level of nesting)
                # if parent_comment.parent is not None:
                #     raise serializers.ValidationError({"parent_id": "Cannot reply to a reply. Only one level of nesting is allowed."})
                data['parent'] = parent_comment
            except Comment.DoesNotExist:
                raise serializers.ValidationError({"parent_id": "Parent comment does not exist."})
        
        # Validate image count
        images_data = data.get('images_upload', [])
        if len(images_data) > 4:
            raise serializers.ValidationError({"images_upload": "En fazla 4 resim yükleyebilirsiniz."})
        
        return data
    
    def create(self, validated_data):
        request = self.context.get('request')
        content_type = validated_data.pop('content_type')
        images_data = validated_data.pop('images_upload', [])
        parent = validated_data.pop('parent', None)

        # 'user' anahtarı validated_data içinde varsa çıkartalım
        if 'user' in validated_data:
            validated_data.pop('user')

        # Create comment
        comment = Comment(
            user=request.user,
            content_type=content_type,
            parent=parent,
            **validated_data
        )
        comment.save()
        
        # Handle images
        for i, image_data in enumerate(images_data):
            CommentImage.objects.create(
                comment=comment,
                image=image_data,
                order=i
            )
        
        # Create notification for the comment
        try:
            from apps.notifications.services import NotificationService
            model_class = content_type.model_class()
            content_object = model_class.objects.get(pk=validated_data.get('object_id'))
            
            # Only send notification if the comment is not from the content owner
            if content_object.user != request.user:
                NotificationService.create_comment_notification(
                    user=request.user,
                    comment=comment
                )
            
            # If this is a reply, also notify the parent comment's user
            if parent and parent.user != request.user and parent.user != content_object.user:
                NotificationService.create_comment_reply_notification(
                    user=request.user,
                    comment=comment,
                    parent_comment=parent
                )
        except (ImportError, AttributeError):
            # If notification service is not available, continue without notifications
            pass
        
        return comment