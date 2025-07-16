from rest_framework import serializers
from django.contrib.auth.models import User
from django.db.models import Count

from apps.profiles.models import Profile
from apps.profiles.api.serializers import UserSerializer
from apps.dataset.models import University, Department, GraduationStatus
from ..models import UserMemberFilter

class MemberListSerializer(serializers.ModelSerializer):
    """Serializer for listing members"""
    user = UserSerializer(read_only=True)
    university_name = serializers.CharField(source='university.name', read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True)
    graduation_status_name = serializers.CharField(source='graduation_status.name', read_only=True)
    followers_count = serializers.SerializerMethodField()
    following_count = serializers.SerializerMethodField()
    is_following = serializers.SerializerMethodField()
    has_pending_request = serializers.SerializerMethodField()
    is_blocked = serializers.SerializerMethodField()
    # Multi-size avatar support
    avatar_thumbnail = serializers.URLField(read_only=True)
    avatar_medium = serializers.URLField(read_only=True)
    avatar_large = serializers.URLField(read_only=True)
    
    class Meta:
        model = Profile
        fields = [
            'user', 'avatar', 'avatar_thumbnail', 'avatar_medium', 'avatar_large',
            'university', 'university_name', 
            'department', 'department_name', 'graduation_status', 
            'graduation_status_name', 'is_private', 'is_verified', 'bio',
            'followers_count', 'following_count', 'is_following', 
            'has_pending_request', 'is_blocked'
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
                return user_profile.is_following(obj)
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
    
    def get_is_blocked(self, obj):
        """Check if the authenticated user has blocked this profile"""
        request = self.context.get('request')
        if request and request.user.is_authenticated and request.user != obj.user:
            try:
                user_profile = request.user.profile
                return user_profile.is_blocked(obj)
            except Profile.DoesNotExist:
                pass
        return False


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


class GraduationStatusSerializer(serializers.ModelSerializer):
    """Serializer for GraduationStatus model"""
    class Meta:
        model = GraduationStatus
        fields = ['id', 'name']


class UserMemberFilterSerializer(serializers.ModelSerializer):
    """Serializer for user member filter preferences"""
    class Meta:
        model = UserMemberFilter
        fields = ['university', 'department', 'graduation_status', 'is_verified']
        
    def create(self, validated_data):
        """Create or update filter preferences for current user"""
        user = self.context['request'].user
        
        # Try to get existing filter preferences or create new one
        filter_prefs, created = UserMemberFilter.objects.get_or_create(user=user)
        
        # Update with new values
        for attr, value in validated_data.items():
            setattr(filter_prefs, attr, value)
            
        filter_prefs.save()
        return filter_prefs