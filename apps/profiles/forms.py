from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import PasswordChangeForm as AuthPasswordChangeForm
from .models import Profile
from django.core.exceptions import ValidationError

class ProfileSettingsForm(forms.ModelForm):
    """Profile settings form for the account tab"""
    username = forms.CharField(label="Kullanıcı Adı", max_length=150, required=True)
    first_name = forms.CharField(label="Ad", max_length=150, required=True)
    last_name = forms.CharField(label="Soyad", max_length=150, required=True)
    email = forms.EmailField(label="E-posta", help_text="@edu.tr mail adresi ile kayıt olmanız halinde onaylanmış hesap mavi tiki tanımlanacaktır.", required=True)
    bio = forms.CharField(widget=forms.Textarea(attrs={'rows': 4}), required=False)

    class Meta:
        model = Profile
        fields = ['university', 'department', 'graduation_status', 'bio']
        labels = {
            'university': 'Üniversite',
            'department': 'Bölüm',
            'graduation_status': 'Mezuniyet Durumu',
        }
        widgets = {
            'university': forms.Select(attrs={
                'class': 'select2 form-select',
                'data-allow-clear': "true",
                "data-placeholder": "Üniversite seçiniz"
            }),
            'department': forms.Select(attrs={
                'class': 'select2 form-select',
                'data-allow-clear': "true",
                "data-placeholder": "Bölüm seçiniz"
            }),
            'graduation_status': forms.Select(attrs={
                'class': 'select2 form-select',
                'data-allow-clear': "true",
                "data-placeholder": "Mezuniyet durumu seçiniz"
            }),
        }
        
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.fields['university'].required = True
        self.fields['department'].required = True
        self.fields['graduation_status'].required = True
        self.email_changed = False
        self.old_email = None
        
        if self.user:
            self.fields['username'].initial = self.user.username
            self.fields['first_name'].initial = self.user.first_name
            self.fields['last_name'].initial = self.user.last_name
            self.fields['email'].initial = self.user.email
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            # Eğer email değişmediyse, doğrulamayı atla
            if email == self.user.email:
                return email
                
            # Email başka bir kullanıcı tarafından kullanılıyor mu kontrol et
            if User.objects.filter(email__iexact=email).exclude(id=self.user.id).exists():
                raise ValidationError("Bu e-posta adresi başka bir kullanıcı tarafından kullanılıyor.")
        return email
        
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if username:
            # Eğer kullanıcı adı değişmediyse, doğrulamayı atla
            if username == self.user.username:
                return username
                
            # Kullanıcı adı başka bir kullanıcı tarafından kullanılıyor mu kontrol et
            if User.objects.filter(username__iexact=username).exists():
                raise ValidationError("Bu kullanıcı adı başka bir kullanıcı tarafından kullanılıyor.")
            
            # Kullanıcı adında geçersiz karakterler var mı?
            if not username.isalnum() and not ('_' in username or '-' in username or '.' in username):
                raise ValidationError("Kullanıcı adı yalnızca harf, rakam ve '_', '-', '.' karakterlerini içerebilir.")
        return username
    def save(self, commit=True):
        profile = super().save(commit=False)
        
        if self.user:
            # Check if email is changed
            email_changed = self.cleaned_data['email'] != self.user.email
            old_email = self.user.email
            
            # Update User model fields
            self.user.username = self.cleaned_data['username']
            self.user.first_name = self.cleaned_data['first_name']
            self.user.last_name = self.cleaned_data['last_name']
            self.user.email = self.cleaned_data['email']
            
            # E-posta adresinin edu.tr ile bitip bitmediğini kontrol et
            email = self.cleaned_data['email'].lower()
            is_edu_email = email.endswith('.edu.tr')
            
            # If email changed, reset verification status
            if email_changed:
                profile.email_verified = False
                profile.is_verified = False
                # Keep track that email was changed to send verification in view
                self.email_changed = True
                self.old_email = old_email
            else:
                # If email is not changed, keep verification status as is for edu.tr
                if is_edu_email and profile.email_verified:
                    profile.is_verified = True

            if commit:
                self.user.save()
                profile.save()
                
        return profile

class PrivacySettingsForm(forms.ModelForm):
    """Privacy settings form"""
    
    class Meta:
        model = Profile
        fields = ['is_private', 'message_privacy']
        labels = {
            'is_private': 'Gizli Profil',
            'message_privacy': 'Kimler mesaj gönderebilir',
        }
        help_texts = {
            'is_private': 'Profilinizi gizli yapmak, yalnızca takipçilerinizin içeriğinizi görmesini sağlar.',
            'message_privacy': 'Size kimlerin doğrudan mesaj gönderebileceğini seçin.',
        }

class DeleteAccountForm(forms.Form):
    """Form for account deletion confirmation"""
    confirm_deletion = forms.BooleanField(
        required=True,
        label="Hesabımı silmeyi onaylıyorum",
        error_messages={'required': 'Hesabınızı silmek için bu kutuyu işaretlemeniz gerekmektedir.'}
    )
    password = forms.CharField(
        widget=forms.PasswordInput,
        required=True,
        label="Parola",
        error_messages={'required': 'Hesap silme işlemini onaylamak için şifreniz gereklidir.'}
    )

class PasswordChangeForm(AuthPasswordChangeForm):
    """Özelleştirilmiş parola değiştirme formu"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['old_password'].required = True
        self.fields['new_password1'].required = True
        self.fields['new_password2'].required = True
        
        # Form alanlarını özelleştir
        self.fields['old_password'].label = "Mevcut Şifre"
        self.fields['new_password1'].label = "Yeni Şifre"
        self.fields['new_password2'].label = "Yeni Şifre (Tekrar)"
        
        # Hata mesajlarını özelleştir
        self.fields['old_password'].error_messages = {'required': 'Lütfen mevcut şifrenizi girin.'}
        self.fields['new_password1'].error_messages = {'required': 'Lütfen yeni şifrenizi girin.'}
        self.fields['new_password2'].error_messages = {'required': 'Lütfen yeni şifrenizi tekrar girin.'}
        