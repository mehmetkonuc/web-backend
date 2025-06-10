from django import forms
import django_filters
from apps.profiles.models import Profile
from django.contrib.auth.models import User
from apps.dataset.models import University, Department, GraduationStatus
from .models import UserMemberFilter

class MemberFilter(django_filters.FilterSet):
    """
    Üyeleri filtrelemek için kullanılan filtre sınıfı
    """
    name = django_filters.CharFilter(method='filter_by_name', label='Ad Soyad')
    username = django_filters.CharFilter(lookup_expr='icontains', field_name='user__username', label='Kullanıcı Adı')
    university = django_filters.ModelChoiceFilter(
        queryset=University.objects.all(),
        label='Üniversite',
        widget=forms.Select(attrs={
            'class': 'select2 form-select',
             'data-allow-clear': "true",
             "data-placeholder": "Üniversite seçiniz"
        })
    )
    department = django_filters.ModelChoiceFilter(
        queryset=Department.objects.all(),
        label='Bölüm',
        widget=forms.Select(attrs={
            'class': 'select2 form-select',
             'data-allow-clear': "true",
             "data-placeholder": "Bölüm seçiniz"
        })
    )
    graduation_status = django_filters.ModelChoiceFilter(
        queryset=GraduationStatus.objects.all(),
        label='Mezuniyet Durumu',
        widget=forms.Select(attrs={
            'class': 'select2 form-select',
             'data-allow-clear': "true",
             "data-placeholder": "Mezuniyet durumu seçiniz"
        })
    )
    is_verified = django_filters.ChoiceFilter(
        choices=(
            ('', 'Hepsi'),
            ('True', 'Evet'),
            ('False', 'Hayır')
        ),
        label='Doğrulanmış Hesap',
        empty_label=None,
        widget=forms.Select(attrs={
            'class': 'select2 form-select',
             'data-allow-clear': "true",
             "data-placeholder": "Tüm Hesaplar"
        })
    )
    
    def filter_by_name(self, queryset, name, value):
        """
        Ad veya soyada göre filtreleme metodu
        """
        if value:
            parts = value.split()
            if len(parts) == 1:
                # Sadece tek kelime girilmişse hem ad hem soyad içinde ara
                return queryset.filter(
                    user__first_name__icontains=parts[0]
                ) | queryset.filter(
                    user__last_name__icontains=parts[0]
                )
            else:
                # Birden fazla kelime girilmişse ilk kelimeyi ad, kalanları soyad olarak düşün
                first_name = parts[0]
                last_name = ' '.join(parts[1:])
                return queryset.filter(
                    user__first_name__icontains=first_name,
                    user__last_name__icontains=last_name
                )
        return queryset
    
    def save_preferences(self, user):
        """
        Kullanıcının filtre tercihlerini kaydet
        """
        if not user or not user.is_authenticated:
            return
            
        # Kullanıcının mevcut filtre tercihlerini bul veya oluştur
        user_filter, created = UserMemberFilter.objects.get_or_create(user=user)
        
        # Mevcut filtre değerlerini kaydet
        data = self.data.copy()
        if data:
            # Sadece istenen filtreleri kaydet
            if 'university' in data and data['university']:
                try:
                    user_filter.university_id = int(data['university'])
                except (ValueError, TypeError):
                    user_filter.university = None
            else:
                user_filter.university = None
                
            if 'department' in data and data['department']:
                try:
                    user_filter.department_id = int(data['department'])
                except (ValueError, TypeError):
                    user_filter.department = None
            else:
                user_filter.department = None
                
            if 'graduation_status' in data and data['graduation_status']:
                try:
                    user_filter.graduation_status_id = int(data['graduation_status'])
                except (ValueError, TypeError):
                    user_filter.graduation_status = None
            else:
                user_filter.graduation_status = None
                
            if 'is_verified' in data and data['is_verified']:
                if data['is_verified'] == 'True':
                    user_filter.is_verified = True
                elif data['is_verified'] == 'False':
                    user_filter.is_verified = False
                else:
                    user_filter.is_verified = None
            else:
                user_filter.is_verified = None
                
            user_filter.save()
    
    class Meta:
        model = Profile
        fields = ['name', 'username', 'university', 'department', 'graduation_status', 'is_verified']