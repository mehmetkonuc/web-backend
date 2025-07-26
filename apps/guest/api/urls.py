from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)
from .views import (
    RegisterView, UserDetailView, CurrentUserView, ChangePasswordView,
    Step1RegisterView, Step2RegisterView, LoginView, DatasetOptionsView,
    CheckUsernameView, PasswordResetStep1View, PasswordResetStep2View, 
    PasswordResetConfirmView, CaptchaStatusView
)


urlpatterns = [
    # Kullanıcı işlemleri
    path('register/', RegisterView.as_view(), name='register'),  # Tek adımlı kayıt (geriye dönük uyumluluk)
    path('register/step1/', Step1RegisterView.as_view(), name='register-step1'),  # İki adımlı kayıt - adım 1
    path('register/step2/', Step2RegisterView.as_view(), name='register-step2'),  # İki adımlı kayıt - adım 2
    path('login/', LoginView.as_view(), name='login'),  # Email veya kullanıcı adı ile giriş
    path('me/', CurrentUserView.as_view(), name='current-user'),  # Mevcut kullanıcı bilgileri
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),  # Şifre değiştirme
    path('check-username/', CheckUsernameView.as_view(), name='check-username'),  # Kullanıcı adı kontrolü
    
    # Şifre sıfırlama
    path('reset-password/step1/', PasswordResetStep1View.as_view(), name='reset-password-step1'),  # Şifre sıfırlama adım 1
    path('reset-password/step2/', PasswordResetStep2View.as_view(), name='reset-password-step2'),  # Şifre sıfırlama adım 2
    path('reset-password/confirm/', PasswordResetConfirmView.as_view(), name='reset-password-confirm'),  # Şifre sıfırlama onay
    
    # Veri seçenekleri
    path('dataset-options/', DatasetOptionsView.as_view(), name='dataset-options'),  # Kayıt için veri seçenekleri
    
    # Güvenlik
    path('captcha-status/', CaptchaStatusView.as_view(), name='captcha-status'),  # reCAPTCHA gerekli mi?
    
    # JWT Token
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),  # JWT token al
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),  # JWT token yenile
    path('token/verify/', TokenVerifyView.as_view(), name='token_verify'),  # JWT token doğrula

    path('user/<int:pk>/', UserDetailView.as_view(), name='user-detail'),  # Kullanıcı detayları

]