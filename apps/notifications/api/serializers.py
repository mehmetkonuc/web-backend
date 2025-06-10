from rest_framework import serializers
from django.contrib.auth.models import User
from apps.notifications.models import Notification, NotificationType


class UserMinimalSerializer(serializers.ModelSerializer):
    """Minimal user information for notifications"""
    avatar_url = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'username', 'avatar_url', 'full_name')

    def get_avatar_url(self, obj):
        if hasattr(obj, 'profile') and obj.profile and obj.profile.avatar:
            return obj.profile.avatar.url
        return None

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username


class NotificationTypeSerializer(serializers.ModelSerializer):
    """Serializer for notification types"""
    class Meta:
        model = NotificationType
        fields = ('id', 'code', 'name', 'icon_class')


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for notifications"""
    sender = UserMinimalSerializer(read_only=True)
    notification_type = NotificationTypeSerializer(read_only=True)
    content_type_name = serializers.SerializerMethodField()
    parent_content_type_name = serializers.SerializerMethodField()
    # Add origin content fields to track the root content (usually a post)
    origin_content_type = serializers.SerializerMethodField()
    origin_object_id = serializers.SerializerMethodField()
    origin_content_type_name = serializers.SerializerMethodField()
    # Yanıt beğenileri için parent comment ID bilgisi
    reply_parent_id = serializers.SerializerMethodField()
    
    class Meta:
        model = Notification
        fields = (
            'id', 
            'sender', 
            'notification_type', 
            'title', 
            'text', 
            'url', 
            'is_read', 
            'read_at', 
            'created_at',
            'content_type',
            'object_id',
            'content_type_name',
            'parent_content_type',
            'parent_object_id',
            'parent_content_type_name',
            'origin_content_type',
            'origin_object_id',
            'origin_content_type_name',
            'reply_parent_id'
        )
    
    def get_content_type_name(self, obj):
        """Nesnenin model adını döndürür (ör: 'comment', 'like')"""
        if obj.content_type:
            return obj.content_type.model
        return None
        
    def get_parent_content_type_name(self, obj):
        """Ana nesnenin model adını döndürür (ör: 'post', 'event')"""
        if obj.parent_content_type:
            return obj.parent_content_type.model
        return None
        
    def get_origin_content_type(self, obj):
        """Orijinal içeriğin (genellikle post) content type ID'sini döndürür"""
        # For comment likes, we need to determine what post the comment belongs to
        if obj.notification_type and obj.notification_type.code in ['comment_like', 'reply_like']:
            from django.contrib.contenttypes.models import ContentType
            from apps.comment.models import Comment
            
            # If the parent is a comment
            if obj.parent_content_type and obj.parent_content_type.model == 'comment':
                try:
                    # Get the comment object
                    comment = Comment.objects.get(id=obj.parent_object_id)
                    # Return the content type of whatever the comment is attached to
                    if comment.content_type:
                        return comment.content_type.id
                except Exception:
                    pass
        
        # For notifications already having the right parent content (like post_like, comment)
        return obj.parent_content_type.id if obj.parent_content_type else None
    
    def get_origin_object_id(self, obj):
        """Orijinal içeriğin (genellikle post) ID'sini döndürür"""
        # For comment likes, get the post ID the comment belongs to
        if obj.notification_type and obj.notification_type.code in ['comment_like', 'reply_like']:
            from apps.comment.models import Comment
            
            # If the parent is a comment
            if obj.parent_content_type and obj.parent_content_type.model == 'comment':
                try:
                    # Get the comment object
                    comment = Comment.objects.get(id=obj.parent_object_id)
                    # Return the ID of whatever the comment is attached to
                    return comment.object_id
                except Exception:
                    pass
        
        # For notifications already having the right parent content
        return obj.parent_object_id
    
    def get_origin_content_type_name(self, obj):
        """Orijinal içeriğin (genellikle post) model adını döndürür"""
        origin_type_id = self.get_origin_content_type(obj)
        if origin_type_id:
            from django.contrib.contenttypes.models import ContentType
            try:
                content_type = ContentType.objects.get(id=origin_type_id)
                return content_type.model
            except ContentType.DoesNotExist:
                pass
        return None
        
    def get_reply_parent_id(self, obj):
        """Yanıt beğenisinde, beğenilen yanıtın bağlı olduğu ana yorumun ID'sini döndürür"""
        # Sadece reply_like bildirimleri için bu işlemi yap
        if obj.notification_type.code == 'reply_like':
            try:
                from apps.like.models import Like
                from apps.comment.models import Comment
                
                # Beğeni objesini al
                like = Like.objects.get(id=obj.object_id)
                
                # Beğenilen içerik (reply) bir yorum mu kontrol et
                if like.content_type.model == 'comment':
                    # Beğenilen yorumu (reply) al
                    reply = Comment.objects.get(id=like.object_id)
                    
                    # Bu yorumun parent ID'si varsa döndür
                    if reply.parent_id:
                        return reply.parent_id
            except Exception as e:
                print(f"Reply parent ID alınırken hata: {e}")
        elif obj.notification_type.code == 'comment_reply':
            from apps.comment.models import Comment

            try:
                reply = Comment.objects.get(id=obj.object_id)
                if reply.parent_id:
                    return reply.parent_id
            except Comment.DoesNotExist:
                return None

        return None