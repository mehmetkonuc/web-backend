import re
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
import uuid
from .forms import UserRegistrationForm, ProfileRegistrationForm, LoginForm, PasswordResetRequestForm, SetNewPasswordForm, PasswordResetStepTwoForm
from apps.profiles.models import Profile

def custom_404_view(request, exception=None):
    """
    Custom 404 sayfası görünümü
    Django'nun otomatik olarak çağıracağı handler
    """
    return render(request, 'pages/404.html', status=404, context={
        'page_title': 'Sayfa Bulunamadı',
    })

def home_view(request):
    """Ana sayfa görünümü"""
    if request.user.is_authenticated:
        return redirect("post:post_list")  # Giriş yapmış kullanıcıları profil sayfasına yönlendir
    return render(request, "guest/home.html")
    # return redirect("guest:home")  # Giriş yapmamış kullanıcıları giriş sayfasına yönlendir

def register_view(request):
    # Kullanıcı Geri Dön butonuna basarsa, ilk adıma dön
    if request.method == "POST" and 'reset_step' in request.POST:
        request.session['registration_step'] = 1
        return redirect("guest:register")
        
    step = request.session.get('registration_step', 1)
    
    if step == 1:
        # Birinci adım: Kullanıcı kimlik bilgileri
        if request.method == "POST":
            form = UserRegistrationForm(request.POST)
            if form.is_valid():
                # Formu doğrula, ancak kaydetme - verileri session'da tut
                request.session['user_form_data'] = {
                    'username': form.cleaned_data['username'],
                    'first_name': form.cleaned_data['first_name'],
                    'last_name': form.cleaned_data['last_name'],
                    'email': form.cleaned_data['email'],
                    'password1': form.cleaned_data['password1'],
                }
                request.session['registration_step'] = 2
                return redirect("guest:register")
        else:
            form = UserRegistrationForm()
        
        return render(request, "guest/register.html", {
            "form": form,
            "step": step,
            "total_steps": 2,
            'page_title': 'Kayıt Ol - Adım 1',
        })
    
    elif step == 2:
        # İkinci adım: Profil bilgileri
        if request.method == "POST":
            form = ProfileRegistrationForm(request.POST)
            if form.is_valid():
                # İlk adımdan verileri al
                user_data = request.session.get('user_form_data')
                print(user_data['first_name'])
                if not user_data:
                    # Session verisi yoksa, adım 1'e geri dön
                    messages.error(request, "Kayıt işlemi zaman aşımına uğradı, lütfen tekrar deneyin.")
                    request.session['registration_step'] = 1
                    return redirect("guest:register")
                
                # Kullanıcıyı oluştur
                user = User.objects.create_user(
                    username=user_data['username'],
                    first_name=user_data['first_name'],
                    last_name=user_data['last_name'],
                    email=user_data['email'],
                    password=user_data['password1']
                )
                email = user_data['email'].lower()

                # Doğrulama kodu oluştur
                import uuid
                from django.utils import timezone
                verification_token = uuid.uuid4()

                # Profil bilgilerini ekle
                profile = Profile.objects.create(
                    user=user,
                    university=form.cleaned_data['university'],
                    department=form.cleaned_data['department'],
                    graduation_status=form.cleaned_data['graduation_status'],
                    is_verified=False,  # E-posta doğrulandıktan sonra ve edu.tr ise True olacak
                    email_verified=False,
                    email_verification_token=verification_token,
                    email_verification_sent_at=timezone.now()
                )
                
                # E-posta doğrulama bağlantısı gönder
                verification_url = f"{request.scheme}://{request.get_host()}/profile/verify-email/{verification_token}/"
                subject = "Fakulten - E-posta Adresinizi Doğrulayın"
                message = render_to_string('profiles/email_verification_email.html', {
                    'user': user,
                    'verification_url': verification_url,
                })
                
                try:
                    send_mail(
                        subject,
                        message,
                        settings.DEFAULT_FROM_EMAIL,
                        [user.email],
                        fail_silently=False,
                        html_message=message
                    )
                except Exception as e:
                    print(f"E-posta gönderim hatası: {e}")



                # Session temizle
                if 'user_form_data' in request.session:
                    del request.session['user_form_data']
                if 'registration_step' in request.session:
                    del request.session['registration_step']
                
                # Kullanıcıyı otomatik giriş yap (backend belirterek)
                login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                messages.success(request, "Hesabınız başarıyla oluşturuldu!")
                return redirect("profiles:upload_avatar")
        else:
            form = ProfileRegistrationForm()
            
        return render(request, "guest/register.html", {
            "form": form,
            "step": step,
            "total_steps": 2,
            'page_title': 'Kayıt Ol - Adım 2',
        })
    
    else:
        # Geçersiz adım, başa dön
        request.session['registration_step'] = 1
        return redirect("guest:register")

def login_view(request):
    if request.method == "POST":
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            if not form.cleaned_data['remember_me']:
                request.session.set_expiry(0)  # Tarayıcı kapanınca oturum düşer
            return redirect("guest:home")
    else:
        form = LoginForm()
    return render(request, "guest/login.html", {"form": form, 'page_title': 'Giriş Yap'})

def logout_view(request):
    logout(request)
    return redirect("guest:login")

def password_reset_request(request):
    # Eğer kullanıcı geri dönme isteği göndermişse adım 1'e geri dön
    if request.method == "POST" and 'reset_step' in request.POST:
        # Session'dan tüm şifre sıfırlama bilgilerini temizle
        for key in ['reset_identifier', 'reset_identifier_type', 'reset_user_exists', 'reset_step']:
            if key in request.session:
                del request.session[key]
        # Sayfayı yeniden yükleyerek adım 1'e başlatacak
        return redirect("guest:password_reset_request")
    
    step = request.session.get('reset_step', 1)
    
    if step == 1:
        # Birinci adım: Email veya kullanıcı adı girişi
        if request.method == "POST":
            form = PasswordResetRequestForm(request.POST)
            if form.is_valid():
                identifier = form.cleaned_data.get('identifier')
                
                # Email mi kullanıcı adı mı kontrol et
                try:
                    from django.core.validators import validate_email
                    validate_email(identifier)
                    # Email ise
                    identifier_type = 'email'
                    # Bu email ile kullanıcı var mı kontrol et (sonucu şimdi gösterme)
                    user_exists = User.objects.filter(email=identifier).exists()
                except:
                    # Kullanıcı adı ise
                    identifier_type = 'username'
                    # Bu kullanıcı adı var mı kontrol et (sonucu şimdi gösterme)
                    user_exists = User.objects.filter(username=identifier).exists()
                
                # Session'a bilgileri kaydet
                request.session['reset_identifier'] = identifier
                request.session['reset_identifier_type'] = identifier_type
                request.session['reset_user_exists'] = user_exists
                request.session['reset_step'] = 2
                
                # Her durumda ikinci adıma git (kullanıcının varlığını açıklama)
                return redirect("guest:password_reset_request")
        else:
            form = PasswordResetRequestForm()
        
        return render(request, "guest/password_reset_request.html", {
            "form": form, 
            "step": 1,
            'page_title': 'Şifre Sıfırlama - Adım 1'
        })
    
    elif step == 2:
        # İkinci adım: Doğrulama için diğer bilginin istenmesi
        identifier = request.session.get('reset_identifier')
        identifier_type = request.session.get('reset_identifier_type')
        user_exists = request.session.get('reset_user_exists')
        
        if not identifier or not identifier_type:
            # Session verisi geçersiz, baştan başla
            request.session['reset_step'] = 1
            messages.error(request, "Oturum zaman aşımına uğradı, lütfen tekrar deneyin.")
            return redirect("guest:password_reset_request")
        
        if request.method == "POST":
            form = PasswordResetStepTwoForm(request.POST, identifier_type=identifier_type)
            if form.is_valid():
                second_identifier = form.cleaned_data.get('second_identifier')
                
                # Her iki tanımlayıcı ile eşleşen kullanıcıyı bul
                if identifier_type == 'email':
                    # İlk değer email, ikincisi kullanıcı adı
                    users = User.objects.filter(email=identifier, username=second_identifier)
                else:
                    # İlk değer kullanıcı adı, ikincisi email
                    users = User.objects.filter(username=identifier, email=second_identifier)
                
                if users.exists():
                    user = users.first()
                    # Şifre sıfırlama e-postası gönder
                    token = default_token_generator.make_token(user)
                    uid = urlsafe_base64_encode(force_bytes(user.pk))
                    
                    # Email şablonu hazırla
                    reset_link = f"{request.scheme}://{request.get_host()}/password-reset-confirm/{uid}/{token}/"
                    subject = "Şifre Sıfırlama İsteği"
                    message = render_to_string('guest/password_reset_email.html', {
                        'user': user,
                        'reset_link': reset_link,
                    })
                    
                    # E-posta gönder
                    send_mail(
                        subject,
                        message,
                        settings.DEFAULT_FROM_EMAIL,
                        [user.email],
                        fail_silently=False,
                        html_message=message
                    )
                    
                    # Session verisini temizle
                    for key in ['reset_identifier', 'reset_identifier_type', 'reset_user_exists', 'reset_step']:
                        if key in request.session:
                            del request.session[key]
                    
                    messages.success(request, "Şifre sıfırlama bağlantısı e-posta adresinize gönderildi.")
                    return redirect("guest:login")
                else:
                    # Kullanıcı bulunamadı, ama bunu açıkça belirtme (güvenlik)
                    messages.error(request, "Girdiğiniz bilgiler eşleşmiyor. Lütfen tekrar deneyin.")
                    return redirect("guest:password_reset_request")
        else:
            form = PasswordResetStepTwoForm(identifier_type=identifier_type)
        
        return render(request, "guest/password_reset_step_two.html", {
            "form": form, 
            "step": 2,
            'page_title': 'Şifre Sıfırlama - Adım 2'
        })
    
    else:
        # Geçersiz adım, başa dön
        for key in ['reset_identifier', 'reset_identifier_type', 'reset_user_exists', 'reset_step']:
            if key in request.session:
                del request.session[key]
                
        request.session['reset_step'] = 1
        return redirect("guest:password_reset_request")

def password_reset_confirm(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    
    # Token geçerli mi kontrol et
    if user is not None and default_token_generator.check_token(user, token):
        if request.method == "POST":
            form = SetNewPasswordForm(user, request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, "Şifreniz başarıyla değiştirildi. Şimdi giriş yapabilirsiniz.")
                return redirect("guest:login")
        else:
            form = SetNewPasswordForm(user)
        
        return render(request, "guest/password_reset_confirm.html", {"form": form, 'page_title': 'Şifre Sıfırlama - Adım 2'})
    else:
        messages.error(request, "Şifre sıfırlama bağlantısı geçersiz veya süresi dolmuş.")
        return redirect("guest:password_reset_request")

def check_username_availability(request):
    """Kullanıcı adının kullanılabilir olup olmadığını kontrol eden AJAX view"""
    username = request.GET.get('username', None)
    data = {
        'is_taken': User.objects.filter(username__iexact=username).exists()
    }
    return JsonResponse(data)