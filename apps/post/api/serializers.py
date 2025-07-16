from rest_framework import serializers
from django.contrib.auth.models import User
from apps.post.models import Post, PostImage, Hashtag, UserPostFilter
from apps.dataset.models import University, Department
from django.urls import reverse


class UserSerializer(serializers.ModelSerializer):
    profile_url = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()
    avatar_thumbnail = serializers.SerializerMethodField()
    avatar_medium = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()
    is_verified = serializers.SerializerMethodField()
    university = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'profile_url', 'avatar_url', 'avatar_thumbnail', 
            'avatar_medium', 'full_name', 'is_verified', 'university'
        ]
    
    def get_profile_url(self, obj):
        return reverse('profiles:profile', kwargs={'username': obj.username})
    
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


class HashtagSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()
    
    class Meta:
        model = Hashtag
        fields = ['id', 'name', 'post_count', 'post_count_last_24h', 'url']
    
    def get_url(self, obj):
        return reverse('post:hashtag_posts', kwargs={'hashtag': obj.name})


class PostImageSerializer(serializers.ModelSerializer):
    """
    Optimize edilmiş PostImage serializer - multiple image sizes destekler
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
        model = PostImage
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
        for unit in ['B', 'KB', 'MB', 'GB']:
            if obj.file_size < 1024.0:
                return f"{obj.file_size:.1f} {unit}"
            obj.file_size /= 1024.0
        return f"{obj.file_size:.1f} TB"
    
    def get_dimensions(self, obj):
        """Resim boyutlarını döndür"""
        if obj.original_width and obj.original_height:
            return {
                'width': obj.original_width,
                'height': obj.original_height,
                'aspect_ratio': round(obj.original_width / obj.original_height, 2)
            }
        return None


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
    
    def validate_images_upload(self, value):
        """Image upload validation"""
        if len(value) > 4:
            raise serializers.ValidationError("En fazla 4 resim yükleyebilirsiniz.")
        
        # Validate each image
        for i, image in enumerate(value):
            # Size validation
            if image.size > 10 * 1024 * 1024:  # 10MB
                raise serializers.ValidationError(f"Resim {i+1} çok büyük (maksimum 10MB).")
            
            # Format validation
            allowed_formats = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp']
            if hasattr(image, 'content_type') and image.content_type not in allowed_formats:
                raise serializers.ValidationError(f"Resim {i+1} desteklenmeyen format. Sadece JPEG, PNG, WEBP desteklenir.")
        
        return value
    
    def validate_content(self, value):
        """Content validation"""
        if not value or not value.strip():
            # Content boşsa image olmalı - bu initial_data üzerinden kontrol edilir
            pass  # Create metodunda kontrol edilecek
        
        if value and len(value) > 2000:  # Character limit
            raise serializers.ValidationError("Post içeriği çok uzun (maksimum 2000 karakter).")
        
        return value.strip() if value else ""
    
    def create(self, validated_data):
        """
        Post oluştur - optimize edilmiş image processing ile
        """
        request = self.context.get('request')
        if not request or not request.user:
            raise serializers.ValidationError({"error": "Authentication required"})
            
        images_data = validated_data.pop('images_upload', [])
        content = validated_data.get('content', '').strip()
        
        # Content ve image validation
        if not content and not images_data:
            raise serializers.ValidationError({"error": "Post içeriği veya en az bir resim gerekli."})
        
        # Image validation
        if len(images_data) > 4:
            raise serializers.ValidationError({"images": "En fazla 4 resim yükleyebilirsiniz."})
        
        # Create post
        post = Post(
            user=request.user,
            content=content
        )
        post.save()
        
        # Handle images with processing
        for i, image_data in enumerate(images_data):
            try:
                # Image validation
                if image_data.size > 10 * 1024 * 1024:  # 10MB limit
                    raise serializers.ValidationError({"images": f"Resim {i+1} çok büyük (max 10MB)."})
                
                # PostImage oluştur - signal handler otomatik olarak işleyecek
                post_image = PostImage.objects.create(
                    post=post,
                    image=image_data,
                    order=i
                )
                
                # Image info'yu hemen kaydet (signal handler için)
                from apps.common.utils.image_processor import ImageProcessor
                from PIL import Image
                
                try:
                    # Basic image info
                    with Image.open(image_data) as img:
                        post_image.original_width = img.width
                        post_image.original_height = img.height
                        post_image.file_size = image_data.size
                        
                        # Format detection
                        processor = ImageProcessor()
                        post_image.format = 'WEBP' if processor.webp_supported else 'JPEG'
                        
                        post_image.save(update_fields=[
                            'original_width', 'original_height', 'file_size', 'format'
                        ])
                        
                except Exception as e:
                    # Resim bilgisi alınamazsa devam et
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"Post image info extraction failed: {e}")
                    
            except Exception as e:
                # Resim yüklenirken hata olursa post'u sil
                post.delete()
                raise serializers.ValidationError({"images": f"Resim {i+1} yüklenirken hata: {str(e)}"})
        
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