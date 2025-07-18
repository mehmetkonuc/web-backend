from django import forms
from .models import ConfessionModel, ConfessionCategory
from apps.dataset.models import University

class ConfessionForm(forms.ModelForm):
    """Form for creating and editing confessions"""
    
    class Meta:
        model = ConfessionModel
        fields = ['category', 'university', 'content', 'is_privacy']
        widgets = {
            'category': forms.Select(attrs={
                'class': 'select2 form-select',
                'data-allow-clear': "true",
                'data-placeholder': "Kategori seçiniz"
            }),
            'university': forms.Select(attrs={
                'class': 'select2 form-select',
                'data-allow-clear': "true",
                'data-placeholder': "Üniversite seçiniz"
            }),
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 6,
                'placeholder': 'İtirafınızı buraya yazın...',
                'maxlength': 2000
            }),
            'is_privacy': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
        labels = {
            'category': 'Kategori',
            'university': 'Üniversite',
            'content': 'İtiraf Metni',
            'is_privacy': 'Anonim İtiraf'
        }
        help_texts = {
            'category': 'İtirafınızın kategorisini seçin',
            'university': 'İtirafın hangi üniversite ile ilgili olduğunu seçin',
            'content': 'İtirafınızı detaylı olarak yazın (maksimum 2000 karakter)',
            'is_privacy': 'İşaretlenirse, adınız gizli kalacak'
        }
    
    def __init__(self, *args, **kwargs):
        # Get user from kwargs to set initial university
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Category queryset'ini tüm kategorilerle sınırla
        self.fields['category'].queryset = ConfessionCategory.objects.all().order_by('name')
        
        # University queryset'ini tüm üniversitelerle sınırla
        self.fields['university'].queryset = University.objects.all().order_by('name')
        
        # If user provided and creating new confession, set initial university
        if user and not self.instance.pk:
            try:
                from apps.profiles.models import Profile
                profile = Profile.objects.get(user=user)
                if profile.university:
                    self.fields['university'].initial = profile.university
            except Profile.DoesNotExist:
                pass
        
        # Content alanını zorunlu yap
        self.fields['content'].required = True
        
        # Category alanını zorunlu yap
        self.fields['category'].required = True
        
        # University alanını zorunlu yap
        self.fields['university'].required = True
    
    def clean_content(self):
        """Content alanını temizle ve doğrula"""
        content = self.cleaned_data.get('content')
        
        if not content:
            raise forms.ValidationError('İtiraf metni boş olamaz.')
        
        # Minimum karakter kontrolü
        if len(content.strip()) < 10:
            raise forms.ValidationError('İtiraf metni en az 10 karakter olmalıdır.')
        
        # Maksimum karakter kontrolü
        if len(content) > 2000:
            raise forms.ValidationError('İtiraf metni maksimum 2000 karakter olabilir.')
        
        return content.strip()
    
    def clean_category(self):
        """Category alanını doğrula"""
        category = self.cleaned_data.get('category')
        
        if not category:
            raise forms.ValidationError('Kategori seçimi zorunludur.')
        
        return category

class MultipleFileInput(forms.ClearableFileInput):
    """Custom widget to handle multiple file uploads"""
    allow_multiple_selected = True

class MultipleFileField(forms.FileField):
    """Custom field to handle multiple file uploads"""
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = single_file_clean(data, initial)
        return result

class ConfessionImageForm(forms.Form):
    """Form for handling multiple image uploads"""
    
    images = MultipleFileField(
        widget=MultipleFileInput(attrs={
            'accept': 'image/*',
            'class': 'form-control'
        }),
        required=False,
        help_text='En fazla 4 resim yükleyebilirsiniz (JPEG, PNG, WebP formatlarında)'
    )
    
    def clean_images(self):
        """Image dosyalarını doğrula"""
        images = self.files.getlist('images')
        
        if len(images) > 4:
            raise forms.ValidationError('En fazla 4 resim yükleyebilirsiniz.')
        
        # Her resim için validasyon
        for image in images:
            # Dosya boyutu kontrolü (5MB limit)
            if image.size > 5 * 1024 * 1024:
                raise forms.ValidationError(f'{image.name} dosyası çok büyük (maksimum 5MB).')
            
            # Dosya formatı kontrolü
            if not image.content_type or not image.content_type.startswith('image/'):
                raise forms.ValidationError(f'{image.name} geçerli bir resim dosyası değil.')
            
            # Desteklenen formatlar
            allowed_formats = ['image/jpeg', 'image/png', 'image/webp']
            if image.content_type not in allowed_formats:
                raise forms.ValidationError(f'{image.name} desteklenmeyen format. Sadece JPEG, PNG, WebP kabul edilir.')
        
        return images
