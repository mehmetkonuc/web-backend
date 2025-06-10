from rest_framework import serializers
from django.contrib.auth.models import User
from apps.post.models import Post, PostImage, Hashtag, UserPostFilter
from apps.dataset.models import University, Department
from django.urls import reverse


class UserSerializer(serializers.ModelSerializer):
    profile_url = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()
    is_verified = serializers.SerializerMethodField()
    university = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'profile_url', 'avatar_url', 'full_name', 'is_verified', 'university']
    
    def get_profile_url(self, obj):
        return reverse('profiles:profile', kwargs={'username': obj.username})
    
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
    
    def get_university(self, obj):
        if hasattr(obj, 'profile') and obj.profile.university:
            return obj.profile.university.name
        return None


class HashtagSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()
    
    class Meta:
        model = Hashtag
        fields = ['id', 'name', 'post_count', 'post_count_last_24h', 'url']
    
    def get_url(self, obj):
        return reverse('post:hashtag_posts', kwargs={'hashtag': obj.name})


class PostImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = PostImage
        fields = ['id', 'image', 'order']


class PostSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    images = PostImageSerializer(many=True, read_only=True)
    hashtags = HashtagSerializer(many=True, read_only=True)
    post_content_type_id = serializers.SerializerMethodField()
    like_count = serializers.SerializerMethodField()
    comment_count = serializers.SerializerMethodField()
    bookmark_count = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    is_bookmarked = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()
    images_upload = serializers.ListField(
        child=serializers.ImageField(max_length=1000000, allow_empty_file=False, use_url=False),
        write_only=True,
        required=False
    )
    
    class Meta:
        model = Post
        fields = [
            'id', 'user', 'content', 'created_at', 'updated_at', 
            'images', 'images_upload', 'post_content_type_id', 'hashtags', 'like_count', 
            'comment_count', 'bookmark_count', 'is_liked', 'is_bookmarked', 'url'
        ]
        read_only_fields = ['user', 'created_at', 'updated_at']

    def get_post_content_type_id(self, obj):
        """Post modelinin ContentType ID'sini döndürür"""
        from django.contrib.contenttypes.models import ContentType
        return ContentType.objects.get_for_model(Post).id

    def get_like_count(self, obj):
        return obj.get_like_count()
    
    def get_comment_count(self, obj):
        from apps.comment.models import Comment
        from django.contrib.contenttypes.models import ContentType
        content_type = ContentType.objects.get_for_model(Post)
        return Comment.objects.filter(content_type=content_type, object_id=obj.id, is_active=True).count()

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

    def get_url(self, obj):
        return reverse('post:post_detail', kwargs={'pk': obj.pk})
    
    def create(self, validated_data):
        request = self.context.get('request')
        images_data = validated_data.pop('images_upload', [])
        # Create post
        post = Post(
            user=request.user,
            content=validated_data.get('content', '')
        )
        post.save()
        
        # Handle images
        if len(images_data) > 4:
            raise serializers.ValidationError({"images": "En fazla 4 resim yükleyebilirsiniz."})
        
        for i, image_data in enumerate(images_data):
            PostImage.objects.create(
                post=post,
                image=image_data,
                order=i
            )
        
        return post


class UniversitySerializer(serializers.ModelSerializer):
    """Serializer for University model"""
    class Meta:
        model = University
        fields = ['id', 'name']


class DepartmentSerializer(serializers.ModelSerializer):
    """Serializer for Department model"""
    class Meta:
        model = Department
        fields = ['id', 'name']


class PostFilterSerializer(serializers.ModelSerializer):
    """Serializer for user post filter preferences"""
    class Meta:
        model = UserPostFilter
        fields = ['posts_type', 'university', 'department']
    
    def create(self, validated_data):
        """Create or update filter preferences for current user"""
        user = self.context['request'].user
        
        # Try to get existing filter preferences or create new one
        filter_prefs, created = UserPostFilter.objects.get_or_create(user=user)
        
        # Update with new values
        for attr, value in validated_data.items():
            setattr(filter_prefs, attr, value)
            
        filter_prefs.save()
        return filter_prefs


class PostDetailSerializer(PostSerializer):
    """Detailed serializer for a single post with comments"""
    comments = serializers.SerializerMethodField()
    
    class Meta(PostSerializer.Meta):
        fields = PostSerializer.Meta.fields + ['comments']
    
    def get_comments(self, obj):
        from apps.comment.api.serializers import CommentSerializer
        from apps.comment.models import Comment
        from django.contrib.contenttypes.models import ContentType
        
        content_type = ContentType.objects.get_for_model(Post)
        comments = Comment.objects.filter(
            content_type=content_type, 
            object_id=obj.id,
            parent=None,  # Only get top-level comments
            is_active=True
        ).order_by('-created_at')
        
        return CommentSerializer(comments, many=True, context=self.context).data