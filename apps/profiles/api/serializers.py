from rest_framework import serializers
from django.contrib.auth.models import User
from apps.profiles.models import Profile, FollowRequest
from apps.dataset.models import University, Department, GraduationStatus
from apps.chat.utils import can_message_user

class UserSerializer(serializers.ModelSerializer):
    """Kullanıcı bilgilerini gösteren serializer"""
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'date_joined', 'is_active']


class ProfileSerializer(serializers.ModelSerializer):
    """Temel profil bilgilerini gösteren serializer."""
    user = UserSerializer(read_only=True)
    university_name = serializers.CharField(source='university.name', read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True)
    graduation_status_name = serializers.CharField(source='graduation_status.name', read_only=True)
    followers_count = serializers.SerializerMethodField()
    following_count = serializers.SerializerMethodField()
    is_following = serializers.SerializerMethodField()
    has_pending_request = serializers.SerializerMethodField()
    is_blocked = serializers.SerializerMethodField()
    is_blocked_by = serializers.SerializerMethodField()
    is_messaging = serializers.SerializerMethodField()
    follow_requests_count = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = [
            'user', 'avatar', 'university', 'university_name', 
            'department', 'department_name', 'graduation_status', 
            'graduation_status_name', 'is_private', 'is_verified', 'bio',
            'followers_count', 'following_count', 'is_following', 'has_pending_request',
            'is_blocked_by', 'is_blocked', 'follow_requests_count', 'email_verified', 'is_messaging',
            'message_privacy'
        ]
    
    def get_followers_count(self, obj):
        return obj.get_followers_count()
    
    def get_following_count(self, obj):
        return obj.get_following_count()
    
    def get_is_following(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated and request.user != obj.user:
            try:
                user_profile = request.user.profile
                return user_profile.is_following(obj.user.profile)
            except Profile.DoesNotExist:
                pass
        return False
        
    def get_has_pending_request(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated and request.user != obj.user:
            try:
                user_profile = request.user.profile
                return user_profile.has_pending_follow_request(obj)
            except Profile.DoesNotExist:
                pass
        return False
    
    def get_is_blocked_by(self, obj):
        """Kullanıcı, profil sahibi tarafından engellenmiş mi?"""
        request = self.context.get('request')
        if request and request.user.is_authenticated and request.user != obj.user:
            try:
                user_profile = request.user.profile
                return obj.is_blocked(user_profile)
            except Profile.DoesNotExist:
                pass
        return False

    def get_is_blocked(self, obj):
        """Kullanıcı, profil sahibi tarafından engellenmiş mi?"""
        request = self.context.get('request')
        if request and request.user.is_authenticated and request.user != obj.user:
            try:
                user_profile = request.user.profile
                return user_profile.is_blocked(obj)
                # return obj.is_blocked(user_profile)
            except Profile.DoesNotExist:
                pass
        return False


    def get_is_messaging(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated and request.user != obj.user:
            can_message, _ = can_message_user(request.user, obj.user)
            return can_message
        return False

    def get_follow_requests_count(self, obj):
        return obj.get_pending_follow_requests().count()


class FollowRequestSerializer(serializers.ModelSerializer):
    """Takip isteği bilgilerini gösteren serializer"""
    from_user = ProfileSerializer(read_only=True)
    to_user = ProfileSerializer(read_only=True)
    
    class Meta:
        model = FollowRequest
        fields = ['id', 'from_user', 'to_user', 'status', 'created_at', 'updated_at']


class ProfileUpdateSerializer(serializers.ModelSerializer):
    """Profil güncelleme için kullanılan serializer"""
    username = serializers.CharField(source='user.username', required=False)
    first_name = serializers.CharField(source='user.first_name', required=False)
    last_name = serializers.CharField(source='user.last_name', required=False)
    email = serializers.EmailField(source='user.email', required=False)
    
    class Meta:
        model = Profile
        fields = [
            'username', 'email', 'first_name', 'last_name', 'bio',
            'university', 'department', 'graduation_status'
        ]
    
    def validate_email(self, value):
        user = self.context['request'].user
        if User.objects.exclude(id=user.id).filter(email__iexact=value).exists():
            raise serializers.ValidationError("Bu e-posta adresi başka bir kullanıcı tarafından kullanılıyor.")
        return value
        
    def validate_username(self, value):
        user = self.context['request'].user
        if User.objects.exclude(id=user.id).filter(username__iexact=value).exists():
            raise serializers.ValidationError("Bu kullanıcı adı başka bir kullanıcı tarafından kullanılıyor.")
        
        # Kullanıcı adında geçersiz karakterler var mı?
        if not value.isalnum() and not ('_' in value or '-' in value or '.' in value):
            raise serializers.ValidationError("Kullanıcı adı yalnızca harf, rakam ve '_', '-', '.' karakterlerini içerebilir.")
        return value
    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', {})
        user = instance.user
        
        # Track if email changed
        email_changed = False
        old_email = user.email
        
        # Update User model fields if they exist in request
        if 'username' in user_data:
            user.username = user_data['username']
        if 'first_name' in user_data:
            user.first_name = user_data['first_name']
        if 'last_name' in user_data:
            user.last_name = user_data['last_name']
        if 'email' in user_data:
            # Check if email has changed
            if user.email != user_data['email']:
                email_changed = True
                user.email = user_data['email']
                # Reset verification status if email changed
                instance.email_verified = False
                instance.is_verified = False

        user.save()
        
        # Update Profile model fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
            
        instance.save()
        
        # Add email_changed flag to context for view to use
        self.context['email_changed'] = email_changed
        
        return instance


class PrivacySettingsSerializer(serializers.ModelSerializer):
    """Gizlilik ayarları için serializer"""
    
    class Meta:
        model = Profile
        fields = ['is_private', 'message_privacy']


class AvatarSerializer(serializers.ModelSerializer):
    """Profil resmi işlemleri için serializer"""
    
    class Meta:
        model = Profile
        fields = ['avatar']


class PasswordChangeSerializer(serializers.Serializer):
    """Şifre değiştirme için serializer"""
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)
    new_password2 = serializers.CharField(required=True)
    
    def validate(self, data):
        if data['new_password'] != data['new_password2']:
            raise serializers.ValidationError({'new_password2': "Yeni şifreler eşleşmiyor."})
        return data
        
    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Mevcut şifreniz yanlış.")
        return value
    

class AccountDeleteSerializer(serializers.Serializer):
    """Hesap silme için serializer"""
    password = serializers.CharField(required=True)
    
    def validate_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Şifreniz yanlış.")
        return value