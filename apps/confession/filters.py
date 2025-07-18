import django_filters
from django import forms
from django.db.models import Q, Count
from django.contrib.auth.models import User

from .models import ConfessionModel, ConfessionCategory, ConfessionFilter
from apps.dataset.models import University

class ConfessionFilterSet(django_filters.FilterSet):
    """Filter for ConfessionModel with category, university and sorting filters"""
    
    # Content search
    content = django_filters.CharFilter(
        field_name='content',
        lookup_expr='icontains',
        label='İçerik Arama',
        help_text='İtiraf içeriğinde arama yapın',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'İtiraf içeriğinde ara...'
        })
    )
    
    # Category filter
    category = django_filters.ModelChoiceFilter(
        queryset=ConfessionCategory.objects.all(),
        label='Kategori',
        help_text='İtirafın kategorisi',
        empty_label='Tüm Kategoriler',
        widget=forms.Select(attrs={
            'class': 'select2 form-select',
             'data-allow-clear': "true",
             "data-placeholder": "Kategori seçiniz"
        })
    )

    # University filter
    university = django_filters.ModelChoiceFilter(
        queryset=University.objects.all(),
        label='Üniversite',
        help_text='Yazarın üniversitesi',
        empty_label='Tüm Üniversiteler',
        widget=forms.Select(attrs={
            'class': 'select2 form-select',
             'data-allow-clear': "true",
             "data-placeholder": "Üniversite seçiniz"
        })
    )
    
    # Custom ordering choices
    sort_by = django_filters.OrderingFilter(
        choices=[
            ('-created_at', 'Yeniye Göre'),
            ('created_at', 'Eskiden Yeniye Göre'),
            ('-like_count', 'Beğeni Sayısına Göre'),
            ('like_count', 'Beğeni Sayısına Göre (Artan)'),
            ('-comment_count', 'Yorum Sayısına Göre'),
            ('comment_count', 'Yorum Sayısına Göre (Artan)')
        ],
        label='Sıralama',
        help_text='İtirafların sıralamasını seçin',
        empty_label='Varsayılan Sıralama (Yeniye Göre)',
        required=False
    )
    
    class Meta:
        model = ConfessionModel
        fields = ['content', 'category', 'university', 'sort_by']

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Load saved filter preferences
        if self.user and self.user.is_authenticated:
            self.load_user_preferences()
    
    def load_user_preferences(self):
        """Load user's saved filter preferences"""
        try:
            user_filter, created = ConfessionFilter.objects.get_or_create(user=self.user)
            
            # Set initial values from saved preferences if this is a new request (not a filter request)
            if not self.data:
                if user_filter.category:
                    self.form.initial['category'] = user_filter.category.pk
                if user_filter.university:
                    self.form.initial['university'] = user_filter.university.pk
                if user_filter.sort_by and user_filter.sort_by.strip() and user_filter.sort_by != '[]':
                    self.form.initial['sort_by'] = user_filter.sort_by
                    
        except Exception as e:
            print(f"Error loading user filter preferences: {e}")
    
    def save_preferences(self):
        """Save the current filter preferences for the user"""
        if not self.user or not self.user.is_authenticated:
            return
            
        try:
            user_filter, created = ConfessionFilter.objects.get_or_create(user=self.user)
            
            # Update preferences
            user_filter.category = self.form.cleaned_data.get('category')
            user_filter.university = self.form.cleaned_data.get('university')
            
            # Sort by için boş değer kontrolü
            sort_by = self.form.cleaned_data.get('sort_by')
            if sort_by and not (isinstance(sort_by, (list, tuple)) and len(sort_by) == 0):
                if isinstance(sort_by, (list, tuple)):
                    # Eğer liste ise ilk elementi al
                    user_filter.sort_by = sort_by[0] if sort_by else '-created_at'
                else:
                    # String ise direkt kullan
                    user_filter.sort_by = sort_by if sort_by.strip() else '-created_at'
            else:
                user_filter.sort_by = '-created_at'  # Varsayılan değer
            
            user_filter.save()
            
        except Exception as e:
            print(f"Error saving user filter preferences: {e}")
            print(f"Sort by value: {self.form.cleaned_data.get('sort_by')}")
            print(f"Sort by type: {type(self.form.cleaned_data.get('sort_by'))}")
    
    def filter_privacy_type(self, queryset, name, value):
        """Filter confessions by privacy type"""
        if value == 'anonymous':
            return queryset.filter(is_privacy=True)
        elif value == 'open':
            return queryset.filter(is_privacy=False)
        return queryset  # 'all' - no filtering
    
    @property
    def qs(self):
        """Override queryset to add performance optimizations"""
        queryset = super().qs
        
        # Always filter active confessions
        queryset = queryset.filter(is_active=True)
        
        # Add select_related for performance
        queryset = queryset.select_related('user', 'category', 'university')
        
        # Add prefetch_related for generic relations
        queryset = queryset.prefetch_related('likes', 'comments', 'bookmarks', 'images')
        
        # Add annotations for sorting
        if self.data and 'sort_by' in self.data:
            sort_value = self.data['sort_by']
            if 'like_count' in sort_value:
                queryset = queryset.annotate(like_count=Count('likes'))
            if 'comment_count' in sort_value:
                queryset = queryset.annotate(comment_count=Count('comments'))
        
        return queryset