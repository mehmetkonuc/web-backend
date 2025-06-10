import django_filters
from django import forms
from django.db.models import Q
from django.contrib.auth.models import User

from .models import Post, UserPostFilter
from apps.dataset.models import University, Department
from apps.profiles.models import Profile

class PostFilter(django_filters.FilterSet):
    """Filter for Post model with university, department and following filters"""
    POSTS_TYPE_CHOICES = [
        ('all', 'Bütün Gönderiler'),
        ('following', 'Sadece Takip Ettiklerim'),
        ('verified', 'Sadece Doğrulanmış Hesaplar'),
    ]
    
    posts_type = django_filters.ChoiceFilter(
        choices=POSTS_TYPE_CHOICES,
        label="Gönderi Tipi",
        method='filter_posts_type',
        empty_label=None,
        widget=forms.Select(attrs={
            'class': 'select2 form-select',
             'data-allow-clear': "true",
             "data-placeholder": "Üniversite seçiniz"
        })    )
    
    university = django_filters.ModelChoiceFilter(
        queryset=University.objects.all(),
        label="Üniversite",
        method='filter_university',
        empty_label="Bütün Üniversiteler",
        widget=forms.Select(attrs={
            'class': 'select2 form-select',
             'data-allow-clear': "true",
             "data-placeholder": "Üniversite seçiniz"
        })
    )
    
    department = django_filters.ModelChoiceFilter(
        queryset=Department.objects.all(),
        label="Bölüm",
        method='filter_department',
        empty_label="Bütün Bölümler",
        widget=forms.Select(attrs={
            'class': 'select2 form-select',
             'data-allow-clear': "true",
             "data-placeholder": "Bölüm seçiniz"
        })
    )
    
    class Meta:
        model = Post
        fields = ['posts_type', 'university', 'department']
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        super(PostFilter, self).__init__(*args, **kwargs)
        
        # Try to load saved filter preferences
        try:
            user_filter, created = UserPostFilter.objects.get_or_create(user=self.user)
            
            # Set initial values from saved preferences if this is a new request (not a filter request)
            if not args and not kwargs.get('data'):
                self.form.initial['posts_type'] = user_filter.posts_type
                if user_filter.university:
                    self.form.initial['university'] = user_filter.university.id
                if user_filter.department:
                    self.form.initial['department'] = user_filter.department.id
        except Exception as e:
            print(f"Error loading user filter preferences: {e}")
    
    def save_preferences(self):
        """Save the current filter preferences for the user"""
        try:
            user_filter, created = UserPostFilter.objects.get_or_create(user=self.user)
            
            # Update preferences
            user_filter.posts_type = self.form.cleaned_data.get('posts_type', 'all')
            user_filter.university = self.form.cleaned_data.get('university')
            user_filter.department = self.form.cleaned_data.get('department')
            user_filter.save()
        except Exception as e:
            print(f"Error saving user filter preferences: {e}")
    
    def filter_posts_type(self, queryset, name, value):
        """Filter posts by type (all, following, or verified)"""
        if value == 'following':
            # Get users that the current user follows
            try:
                profile = Profile.objects.get(user=self.user)
                following_users = [user.user for user in profile.following.all()]
                following_users.append(self.user)  # Include user's own posts
                return queryset.filter(user__in=following_users)
            except Profile.DoesNotExist:
                return queryset.filter(user=self.user)
        elif value == 'verified':
            # Get only verified users' posts
            try:
                verified_profiles = Profile.objects.filter(is_verified=True)
                verified_users = [profile.user for profile in verified_profiles]
                return queryset.filter(user__in=verified_users)
            except Exception as e:
                print(f"Error filtering verified users: {e}")
                return queryset
        return queryset
    
    def filter_university(self, queryset, name, value):
        """Filter posts by users' university"""
        if value:
            # Find profiles with the selected university
            profiles = Profile.objects.filter(university=value)
            users = User.objects.filter(profile__in=profiles)
            return queryset.filter(user__in=users)
        return queryset
    
    def filter_department(self, queryset, name, value):
        """Filter posts by users' department"""
        if value:
            # Find profiles with the selected department
            profiles = Profile.objects.filter(department=value)
            users = User.objects.filter(profile__in=profiles)
            return queryset.filter(user__in=users)
        return queryset