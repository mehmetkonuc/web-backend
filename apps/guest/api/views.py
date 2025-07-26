from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator
import uuid
from .serializers import (
    UserSerializer, RegisterSerializer, ChangePasswordSerializer,
    Step1RegisterSerializer, Step2RegisterSerializer,
    LoginSerializer, UserWithProfileSerializer, UsernameCheckSerializer,
    PasswordResetStep1Serializer, PasswordResetStep2Serializer, PasswordResetConfirmSerializer
)
from django.contrib.auth import get_user_model
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from apps.dataset.models import University, Department, GraduationStatus
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.urls import reverse
from apps.common.security import increment_registration_attempt, log_suspicious_activity
import logging

logger = logging.getLogger(__name__)


class RegisterView(generics.CreateAPIView):
    """Kullanıcı kayıt görünümü - tek adımlı kayıt (geriye dönük uyumluluk)."""
    permission_classes = [permissions.AllowAny]
    serializer_class = RegisterSerializer


@method_decorator(ratelimit(key='ip', rate='3/h', method='POST', block=True), name='post')
class Step1RegisterView(generics.GenericAPIView):
    """İki adımlı kayıt sürecinin ilk adımı."""
    permission_classes = [permissions.AllowAny]
    serializer_class = Step1RegisterSerializer

    def post(self, request, *args, **kwargs):
        # IP adresini al
        ip_address = request.META.get('REMOTE_ADDR', 'unknown')
        
        try:
            serializer = self.get_serializer(data=request.data, context={'request': request})
            serializer.is_valid(raise_exception=True)
            
            # Başarılı validasyon sonrası rate limit sayacını artır
            increment_registration_attempt(ip_address, serializer.validated_data.get('email'))
            
            # İlk adım verilerini geçici olarak session'da sakla (şifreler hariç)
            step1_data = serializer.validated_data.copy()
            # Şifreyi ayrı bir yerde sakla veya hash'le
            password = step1_data.pop('password', None)
            password2 = step1_data.pop('password2', None)
            website = step1_data.pop('website', None)  # Honeypot field'ını kaldır
            
            # Session'da hassas olmayan verileri sakla
            request.session['registration_step1_data'] = step1_data
            request.session['registration_step'] = 2
            # Şifreyi güvenli bir şekilde sakla (geçici)
            request.session['temp_password'] = password
            
            # Başarı logla
            logger.info(f"Step1 registration success: IP={ip_address}, Email={serializer.validated_data.get('email')}")
            
            return Response({
                'message': 'İlk adım başarıyla tamamlandı',
                'data': step1_data,
                'step': 2
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            # Hata durumunda şüpheli aktiviteyi logla
            log_suspicious_activity(
                ip_address=ip_address,
                email=request.data.get('email', ''),
                reason="Step1 registration failed",
                additional_data={'error': str(e), 'request_data': {k: v for k, v in request.data.items() if k not in ['password', 'password2']}}
            )
            raise


class Step2RegisterView(generics.GenericAPIView):
    """İki adımlı kayıt sürecinin ikinci adımı."""
    permission_classes = [permissions.AllowAny]
    serializer_class = Step2RegisterSerializer
    
    def get(self, request, *args, **kwargs):
        """Kullanıcıya mevcut verileri ve seçenekleri döndür."""
        step1_data = request.session.get('registration_step1_data', {})
        step = request.session.get('registration_step', 1)
        
        if not step1_data or step != 2:
            return Response({
                'error': 'İlk adım tamamlanmadı',
                'step': 1
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Şifre bilgileri döndürülmesin
        safe_data = {k: v for k, v in step1_data.items() if k not in ['password', 'password2']}
        
        # Kullanıcıya sunulacak seçenekleri hazırla
        universities = University.objects.all().values('id', 'name')
        departments = Department.objects.all().values('id', 'name')
        graduation_statuses = GraduationStatus.objects.all().values('id', 'name')
        
        return Response({
            'step1_data': safe_data,
            'universities': universities,
            'departments': departments,
            'graduation_statuses': graduation_statuses,
            'step': 2
        })

    def post(self, request, *args, **kwargs):
        # IP adresini al
        ip_address = request.META.get('REMOTE_ADDR', 'unknown')
        
        # Session'dan ilk adım verilerini al
        step1_data = request.session.get('registration_step1_data', {})
        step = request.session.get('registration_step', 1)
        temp_password = request.session.get('temp_password', None)
        
        if not step1_data or step != 2 or not temp_password:
            log_suspicious_activity(
                ip_address=ip_address,
                email=step1_data.get('email', ''),
                reason="Step2 access without step1 completion",
                additional_data={'step1_data_exists': bool(step1_data), 'step': step}
            )
            return Response({
                'error': 'İlk adım tamamlanmadı',
                'step': 1
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Şifreyi step1_data'ya geri ekle
        step1_data_with_password = step1_data.copy()
        step1_data_with_password['password'] = temp_password
        
        serializer = self.get_serializer(
            data=request.data, 
            context={'step1_data': step1_data_with_password}
        )
        serializer.is_valid(raise_exception=True)
        
        try:
            user = serializer.create(serializer.validated_data)
            
            # Başarılı kayıt logla
            logger.info(f"Registration completed: IP={ip_address}, Email={step1_data.get('email')}, User={user.username}")
            
            # E-posta doğrulama bağlantısı gönder
            try:
                # Kullanıcı profilini al
                profile = user.profile
                
                # Doğrulama URL'i oluştur
                verification_token = profile.email_verification_token
                verification_url = f"{request.scheme}://{request.get_host()}/profile/verify-email/{verification_token}/"
                
                # E-posta hazırla
                subject = "Kampuslu - E-posta Adresinizi Doğrulayın"
                message = render_to_string('profiles/email_verification_email.html', {
                    'user': user,
                    'verification_url': verification_url,
                })
                
                # E-postayı gönder
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                    fail_silently=False,
                    html_message=message
                )
            except Exception as e:
                logger.error(f"Email sending error for user {user.username}: {e}")
            
            # Session'daki kayıt verilerini temizle
            if 'registration_step1_data' in request.session:
                del request.session['registration_step1_data']
            if 'registration_step' in request.session:
                del request.session['registration_step']
            if 'temp_password' in request.session:
                del request.session['temp_password']
            
            # JWT token oluştur
            refresh = RefreshToken.for_user(user)
            
            return Response({
                'message': 'Kayıt başarıyla tamamlandı. Lütfen e-posta adresinizi doğrulayın.',
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': UserWithProfileSerializer(user).data
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            # Kayıt hatası durumunda logla
            log_suspicious_activity(
                ip_address=ip_address,
                email=step1_data.get('email', ''),
                reason="Step2 registration failed",
                additional_data={'error': str(e)}
            )
            raise
            message = render_to_string('profiles/email_verification_email.html', {
                'user': user,
                'verification_url': verification_url,
            })
            
            # E-postayı gönder
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
                html_message=message
            )
        except Exception as e:
            print(f"API E-posta gönderim hatası: {e}")
        
        # Session'daki kayıt verilerini temizle
        if 'registration_step1_data' in request.session:
            del request.session['registration_step1_data']
        if 'registration_step' in request.session:
            del request.session['registration_step']
        
        # JWT token oluştur
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'message': 'Kayıt başarıyla tamamlandı. Lütfen e-posta adresinizi doğrulayın.',
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': UserWithProfileSerializer(user).data
        }, status=status.HTTP_201_CREATED)


@method_decorator(ratelimit(key='ip', rate='10/h', method='POST', block=True), name='post')
class LoginView(APIView):
    """Email veya kullanıcı adı ile giriş görünümü."""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request, *args, **kwargs):
        ip_address = request.META.get('REMOTE_ADDR', 'unknown')
        
        try:
            serializer = LoginSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            login_identifier = serializer.validated_data['login_identifier']
            password = serializer.validated_data['password']
            remember_me = serializer.validated_data.get('remember_me', False)
            
            # Kullanıcı adı mı e-posta mı kontrol et
            try:
                validate_email(login_identifier)
                # E-posta ise, o e-postaya sahip kullanıcıyı bul
                users = User.objects.filter(email=login_identifier)
                if users.exists():
                    username = users.first().username
                else:
                    log_suspicious_activity(
                        ip_address=ip_address,
                        email=login_identifier,
                        reason="Login attempt with non-existent email",
                        additional_data={'identifier': login_identifier}
                    )
                    return Response({
                        'error': 'Bu e-posta adresi ile kayıtlı bir kullanıcı bulunamadı.'
                    }, status=status.HTTP_404_NOT_FOUND)
            except ValidationError:
                # Kullanıcı adı ise doğrudan kullan
                username = login_identifier
            
            # Kullanıcıyı doğrula
            user = authenticate(username=username, password=password)
            if not user:
                log_suspicious_activity(
                    ip_address=ip_address,
                    email=login_identifier,
                    reason="Failed login attempt",
                    additional_data={'identifier': login_identifier}
                )
                return Response({
                    'error': 'Geçersiz kullanıcı adı veya şifre.'
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            # Başarılı login logla
            logger.info(f"Successful login: IP={ip_address}, User={user.username}")
            
            # Tarayıcı kapanınca oturum düşsün mü? (Mobil uygulamada genelde gerekli değil)
            if not remember_me:
                request.session.set_expiry(0)
            
            # JWT token oluştur
            refresh = RefreshToken.for_user(user)
            
            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': UserWithProfileSerializer(user).data
            })
            
        except Exception as e:
            log_suspicious_activity(
                ip_address=ip_address,
                email=request.data.get('login_identifier', ''),
                reason="Login error",
                additional_data={'error': str(e)}
            )
            raise


class UserDetailView(generics.RetrieveAPIView):
    """Kullanıcı detayları görünümü."""
    queryset = User.objects.all()
    serializer_class = UserWithProfileSerializer
    permission_classes = [permissions.IsAuthenticated]


class CurrentUserView(APIView):
    """Oturum açmış kullanıcının bilgilerini döndüren görünüm."""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        serializer = UserWithProfileSerializer(request.user)
        return Response(serializer.data)


class ChangePasswordView(generics.UpdateAPIView):
    """Şifre değiştirme görünümü."""
    serializer_class = ChangePasswordSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def update(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = request.user
        if not user.check_password(serializer.data.get("old_password")):
            return Response({"old_password": "Mevcut şifre yanlış."}, status=status.HTTP_400_BAD_REQUEST)
        
        user.set_password(serializer.data.get("new_password"))
        user.save()
        return Response({"message": "Şifre başarıyla değiştirildi."}, status=status.HTTP_200_OK)


class DatasetOptionsView(APIView):
    """Kayıt sırasında kullanılacak veri seçeneklerini döndüren görünüm."""
    permission_classes = [permissions.AllowAny]
    
    def get(self, request):
        universities = University.objects.all().values('id', 'name')
        departments = Department.objects.all().values('id', 'name')
        graduation_statuses = GraduationStatus.objects.all().values('id', 'name')
        
        return Response({
            'universities': universities,
            'departments': departments,
            'graduation_statuses': graduation_statuses
        })


class CheckUsernameView(APIView):
    """Kullanıcı adının kullanılabilirliğini kontrol eden API."""
    permission_classes = [permissions.AllowAny]
    
    def get(self, request, *args, **kwargs):
        serializer = UsernameCheckSerializer(data=request.query_params)
        if serializer.is_valid():
            username = serializer.validated_data['username']
            is_taken = User.objects.filter(username__iexact=username).exists()
            
            return Response({
                'is_taken': is_taken,
                'available': not is_taken,
                'message': 'Bu kullanıcı adı zaten kullanılıyor.' if is_taken else 'Bu kullanıcı adı kullanılabilir.'
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PasswordResetStep1View(APIView):
    """Şifre sıfırlama işleminin ilk adımı."""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request, *args, **kwargs):
        serializer = PasswordResetStep1Serializer(data=request.data)
        # Validate but handle validation errors explicitly for better error messages
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Doğrulanan bilgileri session'a kaydet
        request.session['password_reset_step1_data'] = serializer.validated_data
        request.session['password_reset_step'] = 2
        
        # İkinci adımda hangi bilginin isteneceğini belirt
        identifier_type = serializer.validated_data['identifier_type']
        next_step_info = {
            'email': {'field': 'username', 'label': 'Kullanıcı Adı'},
            'username': {'field': 'email', 'label': 'E-posta Adresi'}
        }
        
        return Response({
            'message': 'İlk adım başarıyla tamamlandı',
            'next_step': next_step_info[identifier_type],
            'step': 2
        }, status=status.HTTP_200_OK)


class PasswordResetStep2View(APIView):
    """Şifre sıfırlama işleminin ikinci adımı."""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request, *args, **kwargs):
        # Session'dan ilk adım verilerini al
        step1_data = request.session.get('password_reset_step1_data', {})
        step = request.session.get('password_reset_step', 1)
        
        if not step1_data or step != 2:
            return Response({
                'error': 'İlk adım tamamlanmadı',
                'step': 1
            }, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = PasswordResetStep2Serializer(
            data=request.data, 
            context={'step1_data': step1_data}
        )
        serializer.is_valid(raise_exception=True)
        
        # Doğrulanan kullanıcıyı al
        user = serializer.context['user']
        
        # Şifre sıfırlama token'ı oluştur
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        
        # Şifre sıfırlama URL'ini oluştur
        reset_url = f"{settings.FRONTEND_URL}/reset-password/{uid}/{token}/"
        
        # E-posta içeriğini hazırla
        context = {
            'user': user,
            'reset_url': reset_url,
            'site_name': 'UniMobile'
        }
        email_subject = "UniMobile - Şifre Sıfırlama"
        email_message = render_to_string('guest/password_reset_email.html', context)
        
        # Bu kısımda bir HTML şablonu kullanılacak, şimdilik basit mesaj
        if not email_message:
            email_message = f"""
            Merhaba {user.first_name},
            
            Şifrenizi sıfırlamak için aşağıdaki linke tıklayın:
            
            {reset_url}
            
            Bu linkin geçerlilik süresi 24 saattir.
            
            Eğer şifre sıfırlama talebinde bulunmadıysanız, bu e-postayı dikkate almayınız.
            
            Saygılarımızla,
            UniMobile Ekibi
            """
        
        # E-postayı gönder
        try:
            send_mail(
                email_subject,
                email_message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
                html_message=email_message if '<html>' in email_message else None
            )
        except Exception as e:
            return Response({
                'error': str(e),
                'message': 'E-posta gönderilirken bir hata oluştu.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Session'daki şifre sıfırlama verilerini temizle
        if 'password_reset_step1_data' in request.session:
            del request.session['password_reset_step1_data']
        if 'password_reset_step' in request.session:
            del request.session['password_reset_step']
        
        return Response({
            'message': 'Şifre sıfırlama bağlantısı e-posta adresinize gönderildi.',
            'email': user.email
        }, status=status.HTTP_200_OK)


class PasswordResetConfirmView(APIView):
    """Şifre sıfırlama token'ı doğrulama ve yeni şifre ayarlama."""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request, *args, **kwargs):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Token ve kullanıcı doğrulama
        try:
            uid = force_str(urlsafe_base64_decode(serializer.validated_data['uidb64']))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response({
                'error': 'Geçersiz kullanıcı.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Token geçerli mi kontrol et
        if not default_token_generator.check_token(user, serializer.validated_data['token']):
            return Response({
                'error': 'Geçersiz veya süresi dolmuş token.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Yeni şifre ayarla
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        
        return Response({
            'message': 'Şifreniz başarıyla sıfırlandı. Yeni şifrenizle giriş yapabilirsiniz.'
        }, status=status.HTTP_200_OK)


class CaptchaStatusView(APIView):
    """reCAPTCHA gerekli mi kontrol eden endpoint (opsiyonel)"""
    permission_classes = [permissions.AllowAny]
    
    def get(self, request):
        from django.conf import settings
        from django.core.cache import cache
        
        # Static setting kontrol et
        static_required = getattr(settings, 'RECAPTCHA_REQUIRED', False)
        
        # Dynamic activation kontrol et
        auto_required = cache.get('auto_recaptcha_required', False)
        
        # reCAPTCHA gerekli mi?
        required = static_required or auto_required
        
        response_data = {
            'required': required,
            'reason': None
        }
        
        if auto_required:
            response_data['reason'] = 'high_security_risk'
        elif static_required:
            response_data['reason'] = 'admin_enabled'
        
        return Response(response_data)