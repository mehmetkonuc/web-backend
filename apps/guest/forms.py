from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, SetPasswordForm
from django.contrib.auth.models import User
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from apps.dataset.models import University, Department, GraduationStatus

class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label="Email veya Kullanıcı Adı",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email veya kullanıcı adı giriniz'
        })
    )
    remember_me = forms.BooleanField(
        label="Beni Hatırla", 
        required=False, 
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    def clean_username(self):
        username = self.cleaned_data.get('username')
        try:
            validate_email(username)
            return username
        except ValidationError:
            # Email değilse kullanıcı adı olarak kabul et
            return username

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Email veya kullanıcı adı giriniz'
        })
        self.fields['password'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': '············'
        })


class UserRegistrationForm(UserCreationForm):
    """Kullanıcı kaydının ilk adımı için form"""
    email = forms.EmailField(required=True, label="Email", help_text="@edu.tr mail adresi ile kayıt olmanız halinde onaylanmış hesap mavi tiki tanımlanacaktır.", widget=forms.EmailInput(attrs={
        'class': 'form-control',
        'placeholder': 'Email adresinizi giriniz'
    }))
    
    class Meta:
        model = User
        fields = ["username", 'first_name', 'last_name', "email", "password1", "password2"]
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Form alanlarını özelleştir
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Kullanıcı adı giriniz'
        })
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Şifre oluşturun'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Şifreyi tekrar girin'
        })
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
        
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError("Bu email adresi zaten kullanılıyor.")
        return email


class ProfileRegistrationForm(forms.Form):
    """Kullanıcı kaydının ikinci adımı için form"""
    university = forms.ModelChoiceField(
        queryset=University.objects.all(),
        required=True,
        label="Üniversite",
        widget=forms.Select(attrs={
            'class': 'select2 form-select',
             'data-allow-clear': "true",
             "data-placeholder": "Üniversite seçiniz"
        })
    )
    department = forms.ModelChoiceField(
        queryset=Department.objects.all(),
        required=True,
        label="Bölüm",
        widget=forms.Select(attrs={
            'class': 'select2 form-select',
            'data-allow-clear': "true",
            "data-placeholder": "Bölüm seçiniz"
        })
    )
    graduation_status = forms.ModelChoiceField(
        queryset=GraduationStatus.objects.all(),
        required=True,
        label="Mezuniyet Durumu",
        widget=forms.Select(attrs={
            'class': 'select2 form-select',
            'data-allow-clear': "true",
            "data-placeholder": "Mezuniyet durumu seçiniz"
        })
    )


class PasswordResetRequestForm(forms.Form):
    identifier = forms.CharField(
        label="Email veya Kullanıcı Adı",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email veya kullanıcı adınızı giriniz',
            'autofocus': 'autofocus',
            'autocomplete': 'email'
        })
    )
    
    def clean_identifier(self):
        identifier = self.cleaned_data.get('identifier')
        # Validation artık view tarafında yapılacak
        return identifier


class PasswordResetStepTwoForm(forms.Form):
    """İkinci adım için şifre sıfırlama formu"""
    second_identifier = forms.CharField(
        label="",  # Label view tarafında dinamik olarak belirlenecek
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'autofocus': 'autofocus',
        })
    )
    
    def __init__(self, *args, identifier_type=None, **kwargs):
        super().__init__(*args, **kwargs)
        # İlk adımda girilen değere göre ikinci adımda ne isteneceğini belirle
        if identifier_type == 'email':
            self.fields['second_identifier'].label = "Kullanıcı Adı"
            self.fields['second_identifier'].widget.attrs['placeholder'] = 'Kullanıcı adınızı giriniz'
        else:
            self.fields['second_identifier'].label = "Email Adresi"
            self.fields['second_identifier'].widget.attrs['placeholder'] = 'Email adresinizi giriniz'


class SetNewPasswordForm(SetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['new_password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': '············',
            'autocomplete': 'new-password'
        })
        self.fields['new_password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': '············',
            'autocomplete': 'new-password'
        })
