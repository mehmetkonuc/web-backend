from rest_framework import serializers
from django.contrib.auth.models import User
from apps.confession.models import ConfessionModel, ConfessionCategory, ConfessionImage, ConfessionFilter
from apps.dataset.models import University
from django.urls import reverse
import logging

logger = logging.getLogger(__name__)


class UserSerializer(serializers.ModelSerializer):
    """
    User serializer for confession - supports anonymous display
    """
    profile_url = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()
    avatar_thumbnail = serializers.SerializerMethodField()
    avatar_medium = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()
    is_verified = serializers.SerializerMethodField()
    university = serializers.SerializerMethodField()
    is_anonymous = serializers.SerializerMethodField()
    display_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'profile_url', 'avatar_url', 'avatar_thumbnail', 
            'avatar_medium', 'full_name', 'is_verified', 'university',
            'is_anonymous', 'display_name'
        ]
    
    def get_profile_url(self, obj):
        # If confession is anonymous, don't show profile URL
        confession = self.context.get('confession')
        if confession and confession.is_anonymous():
            return None
        return reverse('profiles:profile', kwargs={'username': obj.username})
    
    def get_avatar_url(self, obj):
        """Avatar URL - hidden for anonymous confessions"""
        confession = self.context.get('confession')
        if confession and confession.is_anonymous():
            return None
            
        if hasattr(obj, 'profile') and obj.profile:
            url = obj.profile.get_avatar_url('original')
            if url:
                request = self.context.get('request')
                if request:
                    return request.build_absolute_uri(url)
        return None
    
    def get_avatar_thumbnail(self, obj):
        """Avatar thumbnail (150x150) - hidden for anonymous confessions"""
        confession = self.context.get('confession')
        if confession and confession.is_anonymous():
            return None
            
        if hasattr(obj, 'profile') and obj.profile:
            url = obj.profile.get_avatar_url('thumbnail')
            if url:
                request = self.context.get('request')
                if request:
                    return request.build_absolute_uri(url)
        return None
    
    def get_avatar_medium(self, obj):
        """Avatar medium (300x300) - hidden for anonymous confessions"""
        confession = self.context.get('confession')
        if confession and confession.is_anonymous():
            return None
            
        if hasattr(obj, 'profile') and obj.profile:
            url = obj.profile.get_avatar_url('medium')
            if url:
                request = self.context.get('request')
                if request:
                    return request.build_absolute_uri(url)
        return None
    
    def get_full_name(self, obj):
        confession = self.context.get('confession')
        if confession and confession.is_anonymous():
            return "Anonim"
        return obj.get_full_name() or obj.username
    
    def get_is_verified(self, obj):
        confession = self.context.get('confession')
        if confession and confession.is_anonymous():
            return False
        if hasattr(obj, 'profile'):
            return obj.profile.is_verified
        return False
    
    def get_university(self, obj):
        # User's university is always shown (even for anonymous confessions)
        # This should be the user's profile university, not the confession's university
        if hasattr(obj, 'profile') and obj.profile.university:
            return obj.profile.university.name
        return None
    
    def get_is_anonymous(self, obj):
        confession = self.context.get('confession')
        if confession:
            return confession.is_anonymous()
        return False
    
    def get_display_name(self, obj):
        confession = self.context.get('confession')
        if confession and confession.is_anonymous():
            return "Anonim"
        return obj.get_full_name() or obj.username


class ConfessionCategorySerializer(serializers.ModelSerializer):
    """Serializer for confession categories"""
    
    class Meta:
        model = ConfessionCategory
        fields = ['id', 'name']


class ConfessionImageSerializer(serializers.ModelSerializer):
    """
    Optimize edilmiş ConfessionImage serializer - multiple image sizes destekler
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
        model = ConfessionImage
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
        size = obj.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    
    def get_dimensions(self, obj):
        """Resim boyutlarını döndür"""
        if obj.original_width and obj.original_height:
            return {
                'width': obj.original_width,
                'height': obj.original_height,
                'aspect_ratio': round(obj.original_width / obj.original_height, 2)
            }
        return None


class UniversitySerializer(serializers.ModelSerializer):
    """Serializer for University model"""
    class Meta:
        model = University
        fields = ['id', 'name']


class ConfessionSerializer(serializers.ModelSerializer):
    """
    Main confession serializer with privacy-aware user display
    """
    user = serializers.SerializerMethodField()
    category = serializers.PrimaryKeyRelatedField(queryset=ConfessionCategory.objects.all(), write_only=True)
    university = serializers.PrimaryKeyRelatedField(queryset=University.objects.all(), write_only=True)
    category_detail = serializers.SerializerMethodField()
    university_detail = serializers.SerializerMethodField()
    images = ConfessionImageSerializer(many=True, read_only=True)
    
    # Interaction counts
    confession_content_type_id = serializers.SerializerMethodField()
    like_count = serializers.SerializerMethodField()
    comment_count = serializers.SerializerMethodField()
    bookmark_count = serializers.SerializerMethodField()
    
    # User-specific fields
    is_liked = serializers.SerializerMethodField()
    is_bookmarked = serializers.SerializerMethodField()
    is_owner = serializers.SerializerMethodField()
    
    # URLs
    url = serializers.SerializerMethodField()
    
    # Privacy
    privacy_type = serializers.SerializerMethodField()
    
    # Image upload field for creation
    images_upload = serializers.ListField(
        child=serializers.ImageField(max_length=1000000, allow_empty_file=False, use_url=False),
        write_only=True,
        required=False
    )
    
    class Meta:
        model = ConfessionModel
        fields = [
            'id', 'user', 'content', 'category', 'university', 'category_detail', 'university_detail', 
            'images', 'images_upload', 'created_at', 'updated_at', 'is_active', 'is_privacy',
            'confession_content_type_id', 'like_count', 'comment_count', 'bookmark_count',
            'is_liked', 'is_bookmarked', 'is_owner', 'url', 'privacy_type'
        ]
        read_only_fields = ['user', 'created_at', 'updated_at', 'is_active']
    
    def get_user(self, obj):
        """Return user info with privacy handling"""
        user_serializer = UserSerializer(obj.user, context={'confession': obj, 'request': self.context.get('request')})
        return user_serializer.data
    
    def get_category(self, obj):
        """Return category info"""
        return ConfessionCategorySerializer(obj.category).data
    
    def get_university(self, obj):
        """Return university info"""
        return UniversitySerializer(obj.university).data
    
    def get_category_detail(self, obj):
        """Return category detail"""
        return ConfessionCategorySerializer(obj.category).data
    
    def get_university_detail(self, obj):
        """Return university detail"""
        return UniversitySerializer(obj.university).data
    
    def get_confession_content_type_id(self, obj):
        """ConfessionModel ContentType ID'sini döndürür"""
        from django.contrib.contenttypes.models import ContentType
        return ContentType.objects.get_for_model(ConfessionModel).id
    
    def get_like_count(self, obj):
        return obj.get_like_count()
    
    def get_comment_count(self, obj):
        return obj.get_comment_count()
    
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
    
    def get_is_owner(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.user == request.user
        return False
    
    def get_url(self, obj):
        return reverse('confession:confession_detail', kwargs={'pk': obj.pk})
    
    def get_privacy_type(self, obj):
        return 'anonymous' if obj.is_privacy else 'open'
    
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
            raise serializers.ValidationError("İtiraf içeriği boş olamaz.")
        
        if len(value) > 2000:  # Character limit
            raise serializers.ValidationError("İtiraf içeriği çok uzun (maksimum 2000 karakter).")
        
        return value.strip()
    
    def validate_category(self, value):
        """Category validation"""
        if not value:
            raise serializers.ValidationError("Kategori seçimi zorunludur.")
        return value
    
    def validate_university(self, value):
        """University validation"""
        if not value:
            raise serializers.ValidationError("Üniversite seçimi zorunludur.")
        return value
    
    def create(self, validated_data):
        """
        Confession oluştur - optimize edilmiş image processing ile
        """        
        request = self.context.get('request')
        if not request or not request.user:
            raise serializers.ValidationError({"error": "Authentication required"})
        
        images_data = validated_data.pop('images_upload', [])
        
        # Required fields kontrolü
        if 'category' not in validated_data:
            raise serializers.ValidationError({"category": "Bu alan zorunludur."})
        if 'university' not in validated_data:
            raise serializers.ValidationError({"university": "Bu alan zorunludur."})
        if 'content' not in validated_data:
            raise serializers.ValidationError({"content": "Bu alan zorunludur."})
                
        # Create confession - artık ID'ler otomatik olarak object'lere dönüşecek
        confession = ConfessionModel(
            user=request.user,
            content=validated_data['content'],
            category=validated_data['category'],
            university=validated_data['university'],
            is_privacy=validated_data.get('is_privacy', True)  # Default to anonymous
        )
        confession.save()
                
        # Handle images with processing
        for i, image_data in enumerate(images_data):
            try:
                # Image validation
                if image_data.size > 10 * 1024 * 1024:  # 10MB limit
                    raise serializers.ValidationError({"images": f"Resim {i+1} çok büyük (max 10MB)."})
                
                # ConfessionImage oluştur - signal handler otomatik olarak işleyecek
                confession_image = ConfessionImage.objects.create(
                    confession=confession,
                    user=request.user,
                    image=image_data,
                    order=i
                )
                
                # Image info'yu hemen kaydet (signal handler için)
                from apps.common.utils.image_processor import ImageProcessor
                from PIL import Image
                
                try:
                    # Basic image info
                    with Image.open(image_data) as img:
                        confession_image.original_width = img.width
                        confession_image.original_height = img.height
                        confession_image.file_size = image_data.size
                        
                        # Format detection
                        processor = ImageProcessor()
                        confession_image.format = 'WEBP' if processor.webp_supported else 'JPEG'
                        
                        confession_image.save(update_fields=[
                            'original_width', 'original_height', 'file_size', 'format'
                        ])
                        
                except Exception as e:
                    # Resim bilgisi alınamazsa devam et
                    logger.warning(f"Confession image info extraction failed: {e}")
                    
            except Exception as e:
                # Resim yüklenirken hata olursa confession'u sil
                confession.delete()
                raise serializers.ValidationError({"images": f"Resim {i+1} yüklenirken hata: {str(e)}"})
        
        return confession
    
    def update(self, instance, validated_data):
        """
        Confession güncelle - sadece content ve privacy güncellenebilir
        """
        # Remove images_upload from validated_data if present
        validated_data.pop('images_upload', None)
        
        # Only allow updating content and privacy
        allowed_fields = ['content', 'is_privacy']
        for field in allowed_fields:
            if field in validated_data:
                setattr(instance, field, validated_data[field])
        
        instance.save()
        return instance


class ConfessionDetailSerializer(ConfessionSerializer):
    """Detailed serializer for a single confession with comments"""
    comments = serializers.SerializerMethodField()
    
    class Meta(ConfessionSerializer.Meta):
        fields = ConfessionSerializer.Meta.fields + ['comments']
    
    def get_comments(self, obj):
        from apps.comment.api.serializers import CommentSerializer
        from apps.comment.models import Comment
        from django.contrib.contenttypes.models import ContentType
        
        content_type = ContentType.objects.get_for_model(ConfessionModel)
        comments = Comment.objects.filter(
            content_type=content_type, 
            object_id=obj.id,
            parent=None,  # Only get top-level comments
            is_active=True
        ).order_by('-created_at')
        
        return CommentSerializer(comments, many=True, context=self.context).data


class ConfessionFilterSerializer(serializers.ModelSerializer):
    """Serializer for user confession filter preferences"""
    class Meta:
        model = ConfessionFilter
        fields = ['category', 'university', 'sort_by']
    
    def create(self, validated_data):
        """Create or update filter preferences for current user"""
        user = self.context['request'].user
        
        # Try to get existing filter preferences or create new one
        filter_prefs, created = ConfessionFilter.objects.get_or_create(user=user)
        
        # Update with new values
        for attr, value in validated_data.items():
            setattr(filter_prefs, attr, value)
            
        filter_prefs.save()
        return filter_prefs


class FilterOptionsSerializer(serializers.Serializer):
    """Serializer for filter options (categories, universities, sort options)"""
    categories = ConfessionCategorySerializer(many=True, read_only=True)
    universities = UniversitySerializer(many=True, read_only=True)
    sort_options = serializers.SerializerMethodField()
    
    def get_sort_options(self, obj):
        return [
            {'value': '-created_at', 'label': 'En Yeni'},
            {'value': 'created_at', 'label': 'En Eski'},
            {'value': '-like_count', 'label': 'En Beğenilen'},
            {'value': '-comment_count', 'label': 'En Çok Yorumlanan'},
        ]
