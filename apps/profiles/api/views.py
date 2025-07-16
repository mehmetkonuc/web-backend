from rest_framework import viewsets, generics, status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.contrib.auth import update_session_auth_hash
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
import uuid

from apps.profiles.models import Profile, FollowRequest
from .serializers import (
    ProfileSerializer, ProfileUpdateSerializer, PrivacySettingsSerializer,
    AvatarSerializer, PasswordChangeSerializer, AccountDeleteSerializer,
    FollowRequestSerializer, UserSerializer
)
import os
from datetime import datetime
import base64
from django.core.files.base import ContentFile


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class ProfileViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows profiles to be viewed.
    """
    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """
        Returns all profiles regardless of privacy or blocking status.
        Similar to web implementation, profiles are always visible,
        but content (posts) will be restricted later based on privacy/blocking.
        """
        # Return all profiles - restriction on content will be handled separately
        return Profile.objects.all()
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """
        Returns the authenticated user's profile
        """
        try:
            profile = request.user.profile
            serializer = ProfileSerializer(profile, context={'request': request})
            return Response(serializer.data)
        except Profile.DoesNotExist:
            # Profil yoksa yeni oluştur
            profile = Profile.objects.create(user=request.user)
            serializer = ProfileSerializer(profile, context={'request': request})
            return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def followers(self, request, pk=None):
        """
        Returns the followers of a profile (paginated)
        """
        profile = self.get_object()
        followers = profile.followers.all()
        
        # Eğer profil gizliyse ve takip edilmiyorsa, sadece profil sahibi görebilir
        if profile.is_private and not (request.user == profile.user or request.user.profile in profile.followers.all()):
            return Response({"detail": "Bu kullanıcının takipçilerini görüntüleme yetkiniz yok."}, 
                            status=status.HTTP_403_FORBIDDEN)
        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(followers, request)
        serializer = ProfileSerializer(page, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)
        
    @action(detail=True, methods=['get'])
    def following(self, request, pk=None):
        """
        Returns the profiles that this profile is following (paginated)
        """
        profile = self.get_object()
        following = profile.following.all()
        
        # Eğer profil gizliyse ve takip edilmiyorsa, sadece profil sahibi görebilir
        if profile.is_private and not (request.user == profile.user or request.user.profile in profile.followers.all()):
            return Response({"detail": "Bu kullanıcının takip ettiklerini görüntüleme yetkiniz yok."}, 
                            status=status.HTTP_403_FORBIDDEN)
        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(following, request)
        serializer = ProfileSerializer(page, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)
        
    @action(detail=False, methods=['get'])
    def blocked_users(self, request):
        """
        Returns the profiles that the current user has blocked (paginated)
        """
        try:
            profile = request.user.profile
            blocked_users = profile.blocked.all()
            
            paginator = StandardResultsSetPagination()
            page = paginator.paginate_queryset(blocked_users, request)
            serializer = ProfileSerializer(page, many=True, context={'request': request})
            return paginator.get_paginated_response(serializer.data)
        
        except Profile.DoesNotExist:
            # If the profile doesn't exist, create it and return empty list
            profile = Profile.objects.create(user=request.user)
            return Response([])


class FollowToggleView(APIView):
    """
    API endpoint to follow or unfollow a user
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, username):
        # Takip edilecek kullanıcıyı bul
        target_user = get_object_or_404(User, username=username)
        
        # Kendi kendini takip etmeyi engelle
        if target_user == request.user:
            return Response({"detail": "Kendinizi takip edemezsiniz"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Profilleri al
            user_profile = request.user.profile
            target_profile = target_user.profile
            
            # Takip durumunu kontrol et
            is_following = user_profile.is_following(target_profile)
            has_pending_request = user_profile.has_pending_follow_request(target_profile)
            
            if is_following:
                # Takipten çık
                user_profile.unfollow(target_profile)
                
                return Response({
                    "status": "unfollowed",
                    "followers_count": target_profile.get_followers_count()
                })
            elif has_pending_request:
                # Takip isteğini iptal et
                follow_request = FollowRequest.objects.get(
                    from_user=user_profile,
                    to_user=target_profile,
                    status='pending'
                )
                
                # FollowRequest modelindeki cancel metodunu kullanarak isteği ve bildirimi sil
                follow_request.cancel()
                
                return Response({
                    "status": "request_canceled",
                    "followers_count": target_profile.get_followers_count(),
                    "message": f"{target_user.username} için takip isteğiniz iptal edildi."
                })
            else:
                # Takip et
                result = user_profile.follow(target_profile)
                
                if result == "requested":
                    # Takip isteği gönderildi
                    return Response({
                        "status": "requested",
                        "followers_count": target_profile.get_followers_count(),
                        "message": f"{target_user.username} hesabı gizli. Takip isteği gönderildi."
                    })
                elif result:
                    # Başarıyla takip edildi
                    return Response({
                        "status": "followed",
                        "followers_count": target_profile.get_followers_count()
                    })
                else:
                    return Response({
                        "detail": "Takip işlemi başarısız oldu.",
                        "followers_count": target_profile.get_followers_count()
                    }, status=status.HTTP_400_BAD_REQUEST)
                
        except Profile.DoesNotExist:
            return Response({"detail": "Profil bulunamadı"}, status=status.HTTP_404_NOT_FOUND)


class BlockToggleView(APIView):
    """
    API endpoint to block or unblock a user
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, username):
        # Engellenecek kullanıcıyı bul
        target_user = get_object_or_404(User, username=username)
        
        # Kendi kendini engellemeyi önle
        if target_user == request.user:
            return Response({"detail": "Kendinizi engelleyemezsiniz"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Profilleri al
            user_profile = request.user.profile
            target_profile = target_user.profile
            
            # Engelleme durumunu kontrol et
            is_blocked = user_profile.is_blocked(target_profile)
            
            if is_blocked:
                # Engeli kaldır
                user_profile.unblock(target_profile)
                return Response({"status": "unblocked"})
            else:
                # Engelle
                user_profile.block(target_profile)
                return Response({"status": "blocked"})
                
        except Profile.DoesNotExist:
            return Response({"detail": "Profil bulunamadı"}, status=status.HTTP_404_NOT_FOUND)


class BlockStatusView(APIView):
    """
    API endpoint to check if a user is blocked
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, username):
        # Kontrol edilecek kullanıcıyı bul
        target_user = get_object_or_404(User, username=username)
        
        # Kendi kendini kontrol etmeyi önle
        if target_user == request.user:
            return Response({"detail": "Kendinizi kontrol edemezsiniz"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Profilleri al
            user_profile = request.user.profile
            target_profile = target_user.profile
            
            # Engelleme durumunu kontrol et
            is_blocked = user_profile.is_blocked(target_profile)
            
            return Response({
                "is_blocked": is_blocked,
                "username": username
            })
                
        except Profile.DoesNotExist:
            return Response({"detail": "Profil bulunamadı"}, status=status.HTTP_404_NOT_FOUND)


class BatchBlockStatusView(APIView):
    """
    API endpoint to check if multiple users are blocked in a single request
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        usernames = request.data.get('usernames', [])
        
        if not isinstance(usernames, list) or len(usernames) == 0:
            return Response({"detail": "usernames listesi gerekli"}, status=status.HTTP_400_BAD_REQUEST)
        
        if len(usernames) > 50:  # Limit to prevent abuse
            return Response({"detail": "En fazla 50 kullanıcı kontrol edilebilir"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user_profile = request.user.profile
            results = {}
            
            for username in usernames:
                try:
                    target_user = User.objects.get(username=username)
                    if target_user != request.user:  # Kendi kendini kontrol etmeyi önle
                        target_profile = target_user.profile
                        is_blocked = user_profile.is_blocked(target_profile)
                        results[username] = {"is_blocked": is_blocked}
                    else:
                        results[username] = {"error": "Kendinizi kontrol edemezsiniz"}
                except User.DoesNotExist:
                    results[username] = {"error": "Kullanıcı bulunamadı"}
                except Profile.DoesNotExist:
                    results[username] = {"error": "Profil bulunamadı"}
            
            return Response({"results": results})
                
        except Profile.DoesNotExist:
            return Response({"detail": "Profil bulunamadı"}, status=status.HTTP_404_NOT_FOUND)


class ProfileUpdateView(generics.UpdateAPIView):
    """
    API endpoint to update a profile
    """
    serializer_class = ProfileUpdateSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        try:
            return self.request.user.profile
        except Profile.DoesNotExist:
            # Profil yoksa oluştur
            return Profile.objects.create(user=self.request.user)
            
    def update(self, request, *args, **kwargs):
        # Standart güncelleme işlemini yap
        response = super().update(request, *args, **kwargs)

        # Serializer context'ten email_changed değerini kontrol et
        if self.get_serializer().context.get('email_changed', True):
            profile = self.get_object()
            
            # Doğrulama tokeni oluştur
            import uuid
            from django.utils import timezone
            from django.core.mail import send_mail
            from django.template.loader import render_to_string
            from django.conf import settings
            
            # Doğrulama bilgilerini güncelle
            profile.email_verification_token = uuid.uuid4()
            profile.email_verification_sent_at = timezone.now()
            profile.save()
            
            # Yeni adrese doğrulama emaili gönder
            verification_url = f"{request.scheme}://{request.get_host()}/profile/verify-email/{profile.email_verification_token}/"
            subject = "Fakulten - E-posta Adresinizi Doğrulayın"
            message = render_to_string('profiles/email_verification_email.html', {
                'user': request.user,
                'verification_url': verification_url,
            })
            
            try:
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [request.user.email],
                    fail_silently=False,
                    html_message=message
                )
                
                # E-posta doğrulama bildirimi ekle
                response.data['email_verification'] = {
                    "status": "success", 
                    "message": "E-posta adresiniz değiştiği için, yeni adresinize bir doğrulama bağlantısı gönderdik. Lütfen e-postanızı kontrol edin."
                }
                
            except Exception as e:
                response.data['email_verification'] = {
                    "status": "error",
                    "message": f"E-posta doğrulama bağlantısı gönderilirken bir hata oluştu: {str(e)}"
                }
        
        return response


class PrivacySettingsView(generics.UpdateAPIView):
    """
    API endpoint to update privacy settings
    """
    serializer_class = PrivacySettingsSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        try:
            return self.request.user.profile
        except Profile.DoesNotExist:
            return Profile.objects.create(user=self.request.user)
    
    def update(self, request, *args, **kwargs):
        profile = self.get_object()
        
        # Önceki gizlilik durumunu kaydet
        was_private = profile.is_private
        
        # Güncelleme işlemi
        response = super().update(request, *args, **kwargs)
        
        # Profil gizli olmaktan çıkarıldıysa, bekleyen istekleri kabul et
        if was_private and not profile.is_private:
            # Bekleyen tüm takip isteklerini al
            pending_requests = profile.get_pending_follow_requests()
            accepted_count = 0
            
            if pending_requests.exists():
                # Her bekleyen istek için
                for follow_request in pending_requests:
                    # İsteği kabul et
                    if follow_request.accept():
                        accepted_count += 1
                
                # Kabul edilen istek sayısını ekle
                response.data['accepted_requests'] = accepted_count
        
        return response


class FollowRequestListView(generics.ListAPIView):
    """
    API endpoint to list follow requests
    """
    serializer_class = FollowRequestSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        try:
            profile = self.request.user.profile
        except Profile.DoesNotExist:
            profile = Profile.objects.create(user=self.request.user)
        return profile.get_pending_follow_requests()


class AcceptFollowRequestView(APIView):
    """
    API endpoint to accept a follow request
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, request_id):
        try:
            # İsteği bul ve sadece o isteğin alıcısı olan kullanıcının kabul etmesine izin ver
            follow_request = get_object_or_404(
                FollowRequest, 
                id=request_id, 
                to_user=request.user.profile,
                status='pending'
            )
            
            # İsteği kabul et
            if follow_request.accept():
                return Response({"status": "accepted", "message": "Takip isteği kabul edildi."})
            else:
                return Response({"detail": "İstek kabul edilemedi."}, status=status.HTTP_400_BAD_REQUEST)
                
        except FollowRequest.DoesNotExist:
            return Response({"detail": "Takip isteği bulunamadı"}, status=status.HTTP_404_NOT_FOUND)


class RejectFollowRequestView(APIView):
    """
    API endpoint to reject a follow request
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, request_id):
        try:
            # İsteği bul ve sadece o isteğin alıcısı olan kullanıcının reddetmesine izin ver
            follow_request = get_object_or_404(
                FollowRequest, 
                id=request_id, 
                to_user=request.user.profile,
                status='pending'
            )
            
            # İsteği reddet
            if follow_request.reject():
                return Response({"status": "rejected", "message": "Takip isteği reddedildi."})
            else:
                return Response({"detail": "İstek reddedilemedi."}, status=status.HTTP_400_BAD_REQUEST)
                
        except FollowRequest.DoesNotExist:
            return Response({"detail": "Takip isteği bulunamadı"}, status=status.HTTP_404_NOT_FOUND)


class AvatarUploadView(APIView):
    """
    API endpoint to upload a profile avatar
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            # Kullanıcının profilini bul
            profile = request.user.profile
        except Profile.DoesNotExist:
            # Profil yoksa oluştur
            profile = Profile.objects.create(user=request.user)
        
        # Base64 formatında resim gönderildi mi kontrol et
        avatar_data = request.data.get('avatar')
        
        if avatar_data:
            try:
                # Base64 önekini kaldırma (data:image/jpeg;base64,)
                format, imgstr = avatar_data.split(';base64,')
                ext = format.split('/')[-1]
                
                # Dosya adı oluşturma
                filename = f"{uuid.uuid4()}.{ext}"
                
                # Base64'ten dosyaya dönüştürme
                data = ContentFile(base64.b64decode(imgstr))
                
                # Eski avatar resimlerini temizle
                if profile.avatar:
                    # Eski resmi sil (signal handler yeni boyutları oluşturacak)
                    if os.path.isfile(profile.avatar.path):
                        os.remove(profile.avatar.path)
                
                # Processing flag'ini sıfırla ki signal handler çalışsın
                profile.avatar_processed = False
                
                # Yeni avatar'ı kaydet (signal handler otomatik olarak processing yapacak)
                profile.avatar.save(filename, data, save=True)
                
                # Signal handler'ın işlemesini bekle
                profile.refresh_from_db()
                
                # Response'a yeni multi-size avatar bilgilerini ekle
                serializer = ProfileSerializer(profile, context={'request': request})
                return Response({
                    "success": True,
                    "message": "Profil resmi başarıyla yüklendi",
                    "profile": serializer.data
                })
            except Exception as e:
                return Response({"detail": f"Profil resmi yüklenirken hata oluştu: {str(e)}"}, 
                                status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({"detail": "Profil resmi verileri bulunamadı"}, status=status.HTTP_400_BAD_REQUEST)


class AvatarDeleteView(APIView):
    """
    API endpoint to delete a profile avatar
    """
    permission_classes = [IsAuthenticated]
    
    def delete(self, request):
        try:
            # Kullanıcının profilini bul
            profile = request.user.profile
            
            # Profil resmi varsa sil
            if profile.avatar:
                # Dosya sisteminden sil (original)
                if os.path.isfile(profile.avatar.path):
                    os.remove(profile.avatar.path)
                
                # Tüm processed boyutları da sil
                try:
                    avatar_dir = os.path.dirname(profile.avatar.path)
                    avatar_name = os.path.splitext(os.path.basename(profile.avatar.path))[0]
                    
                    # thumbnail, medium, large dosyalarını ara ve sil
                    for size in ['thumbnail', 'medium', 'large']:
                        processed_file = os.path.join(avatar_dir, f"{avatar_name}_{size}.webp")
                        if os.path.isfile(processed_file):
                            os.remove(processed_file)
                except Exception as e:
                    # Processed dosyalar silinmese de devam et
                    pass
                
                # Veritabanı kaydını sil
                profile.avatar = None
                profile.save()
                
                serializer = ProfileSerializer(profile, context={'request': request})
                return Response({
                    "success": True,
                    "message": "Profil resmi başarıyla silindi",
                    "profile": serializer.data
                })
            else:
                return Response({"detail": "Kaldırılacak bir profil resmi bulunamadı"}, 
                                status=status.HTTP_400_BAD_REQUEST)
                
        except Profile.DoesNotExist:
            return Response({"detail": "Profil bulunamadı"}, status=status.HTTP_404_NOT_FOUND)


class PasswordChangeView(APIView):
    """
    API endpoint to change password
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = PasswordChangeSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = request.user
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            
            # Şifre değiştiğinde oturum da güncellenir böylece kullanıcı çıkış yapmak zorunda kalmaz
            # (Bu kısım Web API için çalışmaz, sadece JWT tokenı geçersiz kılmaz)
            update_session_auth_hash(request, user)
            
            return Response({"message": "Şifreniz başarıyla değiştirildi."})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AccountDeleteView(APIView):
    """
    API endpoint to delete account
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = AccountDeleteSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = request.user
            # Hesabı sil (devre dışı bırak)
            user.is_active = False
            user.save()
            
            return Response({"message": "Hesabınız başarıyla silinmiştir."})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ResendVerificationEmailView(APIView):
    """API endpoint to resend verification email"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        # Kullanıcının profilini kontrol et
        try:
            profile = request.user.profile
            
            # Zaten doğrulanmış ise
            if profile.email_verified:
                return Response({
                    "status": "warning",
                    "message": "E-posta adresiniz zaten doğrulanmış."
                }, status=status.HTTP_200_OK)
                
            # Yeni token oluştur
            profile.email_verification_token = uuid.uuid4()
            profile.email_verification_sent_at = timezone.now()
            profile.save()
            
            # Doğrulama bağlantısını hazırla ve e-posta gönder
            verification_url = f"{request.scheme}://{request.get_host()}/profile/verify-email/{profile.email_verification_token}/"
            subject = "Fakulten - E-posta Adresinizi Doğrulayın"
            message = render_to_string('profiles/email_verification_email.html', {
                'user': request.user,
                'verification_url': verification_url,
            })
            
            try:
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [request.user.email],
                    fail_silently=False,
                    html_message=message
                )
                
                return Response({
                    "status": "success",
                    "message": "E-posta doğrulama bağlantısı tekrar gönderildi. Lütfen e-postanızı kontrol edin."
                }, status=status.HTTP_200_OK)
                
            except Exception as e:
                return Response({
                    "status": "error",
                    "message": f"E-posta gönderimi sırasında bir hata oluştu: {str(e)}"
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        except Profile.DoesNotExist:
            return Response({
                "status": "error",
                "message": "Kullanıcı profili bulunamadı."
            }, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
def get_dataset_options(request):
    """
    API endpoint to get dataset options for profile settings
    """
    from apps.dataset.models import University, Department, GraduationStatus
    
    universities = University.objects.all()
    departments = Department.objects.all()
    graduation_statuses = GraduationStatus.objects.all()
    
    university_data = [{"id": uni.id, "name": uni.name} for uni in universities]
    department_data = [{"id": dept.id, "name": dept.name} for dept in departments]
    graduation_data = [{"id": status.id, "name": status.name} for status in graduation_statuses]
    
    return Response({
        "universities": university_data,
        "departments": department_data,
        "graduation_statuses": graduation_data
    })