from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, Http404
from django.contrib.auth.models import User
from django.contrib.auth import update_session_auth_hash
from .models import Profile, FollowRequest
import base64
from django.core.files.base import ContentFile
import os
import uuid
from .forms import ProfileSettingsForm, PrivacySettingsForm, DeleteAccountForm, PasswordChangeForm
from apps.post.models import Post
from apps.notifications.services import NotificationService
from django.core.paginator import Paginator
from datetime import datetime, timedelta

@login_required
def profile_redirect_view(request):
    """Kullanıcıyı kendi profil sayfasına yönlendirir"""
    return redirect('profiles:profile', username=request.user.username)

@login_required
def profile_view(request, username):
    """Belirtilen kullanıcının profil sayfası"""
    # Kullanıcıyı bul veya 404 hatası döndür
    user = get_object_or_404(User, username=username, is_active=True)
    
    try:
        # Kullanıcının profilini bul
        profile = Profile.objects.get(user=user)
        
        # Kullanıcı, profile sahibi tarafından engellenmişse kontrol et
        is_blocked_by = False
        if request.user.is_authenticated and request.user != user:
            try:
                user_profile = request.user.profile
                # Kullanıcı, profile sahibi tarafından engellenmişse
                is_blocked_by = profile.is_blocked(user_profile)
                if is_blocked_by:
                    messages.warning(request, f"{user.username} sizi engellediği için bu kullanıcının içeriklerini görüntüleyemezsiniz.")
            except Profile.DoesNotExist:
                pass
            
    except Profile.DoesNotExist:
        # Eğer profil mevcut kullanıcıya aitse, profil oluştur
        if user == request.user:
            profile = Profile.objects.create(user=user)
        else:
            # Başkasının profili bulunamadıysa hata ver
            messages.error(request, "Bu kullanıcının profili henüz oluşturulmamış.")
            return redirect('profiles:profile_redirect')
    
    # Mevcut kullanıcının bu profili takip edip etmediğini kontrol et
    is_following = False
    is_blocked = False
    has_pending_request = False
    
    if request.user.is_authenticated and request.user != user:
        try:
            user_profile = request.user.profile
            is_following = user_profile.is_following(profile)
            is_blocked = user_profile.is_blocked(profile)
            
            # Bekleyen takip isteği var mı kontrol et
            has_pending_request = user_profile.has_pending_follow_request(profile)
            
        except Profile.DoesNotExist:
            pass
    posts = Post.objects.filter(user=profile.user).order_by('-created_at')
    from django.core.paginator import Paginator
    paginator = Paginator(posts, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        "profile": profile,
        "is_following": is_following,
        "is_blocked": is_blocked,
        "is_blocked_by": is_blocked_by,
        "has_pending_request": has_pending_request,
        "followers_count": profile.get_followers_count(),
        "following_count": profile.get_following_count(),
        'page_obj': page_obj,
        'page_title': f"{profile.user.get_full_name()} - Profili",
    }
    
    return render(request, "profiles/profile.html", context)

@login_required
def upload_avatar_view(request):
    """Profil resmi yükleme ve kırpma sayfası"""
    try:
        # Kullanıcının profilini bul
        profile = Profile.objects.get(user=request.user)
    except Profile.DoesNotExist:
        # Profil yoksa oluştur
        profile = Profile.objects.create(user=request.user)
    
    if request.method == 'POST' and 'skip' in request.POST:
        # Kullanıcı profil yüklemeyi atladı
        messages.info(request, "Profil resmi yüklemeyi atladınız. İstediğiniz zaman profilinizden ekleyebilirsiniz.")
        return redirect('guest:home')
    
    elif request.method == 'POST' and 'avatar' in request.POST:
        # Kullanıcı base64 formatında resim gönderdi (kırpılmış halde)
        avatar_data = request.POST.get('avatar')
        
        if avatar_data:
            # Base64 önekini kaldırma (data:image/jpeg;base64,)
            format, imgstr = avatar_data.split(';base64,')
            ext = format.split('/')[-1]
            
            # Dosya adı oluşturma
            filename = f"{uuid.uuid4()}.{ext}"
            
            # Base64'ten dosyaya dönüştürme
            data = ContentFile(base64.b64decode(imgstr))
            
            # Profil resmi güncelleme
            if profile.avatar:
                # Eski resmi sil
                if os.path.isfile(profile.avatar.path):
                    os.remove(profile.avatar.path)
            
            profile.avatar.save(filename, data, save=True)
            messages.success(request, "Profil resminiz başarıyla güncellendi!")
            return redirect('profiles:profile', username=request.user.username)
    
    return render(request, "profiles/upload_avatar.html", {"profile": profile, 'page_title': "Profil Resmi Yükle"})

@login_required
def reset_avatar_view(request):
    """Kullanıcının profil resmini siler"""
    if request.method != 'POST':
        return redirect('profiles:profile', username=request.user.username)
    
    try:
        # Kullanıcının profilini bul
        profile = request.user.profile
        
        # Profil resmi varsa sil
        if profile.avatar:
            # Dosya sisteminden sil
            if os.path.isfile(profile.avatar.path):
                os.remove(profile.avatar.path)
            
            # Veritabanı kaydını sil
            profile.avatar = None
            profile.save()
            
            messages.success(request, "Profil resminiz başarıyla kaldırıldı.")
        else:
            messages.info(request, "Kaldırılacak bir profil resmi bulunamadı.")
            
        # Yönlendirilecek sayfa
        if request.GET.get('next'):
            return redirect(request.GET.get('next'))
        
        return redirect('profiles:settings')
        
    except Profile.DoesNotExist:
        messages.error(request, "Profil bulunamadı.")
        return redirect('profiles:profile_redirect')

@login_required
def follow_toggle_view(request, username):
    """Kullanıcıyı takip etme veya takipten çıkma işlemi"""
    if request.method != 'POST':
        return JsonResponse({"error": "Geçersiz istek metodu"}, status=405)
    
    # Takip edilecek kullanıcıyı bul
    target_user = get_object_or_404(User, username=username)
    
    # Kendi kendini takip etmeyi engelle
    if target_user == request.user:
        return JsonResponse({"error": "Kendinizi takip edemezsiniz"}, status=400)
    
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
            
            return JsonResponse({
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
            
            # İptal metodunu kullanarak takip isteğini ve bildirimini sil
            follow_request.cancel()
            
            return JsonResponse({
                "status": "request_canceled",
                "followers_count": target_profile.get_followers_count(),
                "message": f"{target_user.username} için takip isteğiniz iptal edildi."
            })
        else:
            # Takip et
            result = user_profile.follow(target_profile)
            
            if result == "requested":
                # Takip isteği gönderildi
                return JsonResponse({
                    "status": "requested",
                    "followers_count": target_profile.get_followers_count(),
                    "message": f"{target_user.username} hesabı gizli. Takip isteği gönderildi."
                })
            elif result:
                # Başarıyla takip edildi
                return JsonResponse({
                    "status": "followed",
                    "followers_count": target_profile.get_followers_count()
                })
            else:
                return JsonResponse({
                    "error": "Takip işlemi başarısız oldu.",
                    "followers_count": target_profile.get_followers_count()
                }, status=400)
            
    except Profile.DoesNotExist:
        return JsonResponse({"error": "Profil bulunamadı"}, status=404)

@login_required
def followers_view(request, username):
    """Kullanıcının takipçilerini listeler"""
    user = get_object_or_404(User, username=username)

    try:
        profile = Profile.objects.get(user=user)
        
        # Kullanıcı, profile sahibi tarafından engellenmişse kontrol et
        is_blocked_by = False
        is_blocked = False
        if request.user.is_authenticated:
            try:
                user_profile = request.user.profile
                following_ids = user_profile.following.values_list('id', flat=True)

                # Kullanıcı, profile sahibi tarafından engellenmişse
                is_blocked_by = profile.is_blocked(user_profile)
                is_blocked = user_profile.is_blocked(profile)
                if is_blocked_by:
                    messages.warning(request, f"{user.username} sizi engellediği için bu kullanıcının içeriklerini görüntüleyemezsiniz.")
            except Profile.DoesNotExist:
                pass
                
        followers = profile.followers.all()

        context = {
            "profile": profile,
            "followers": followers,
            "following_ids": following_ids,
            "is_followers_page": True,
            "is_blocked_by": is_blocked_by,
            'is_blocked' : is_blocked,
            "followers_count": profile.get_followers_count(),
            "following_count": profile.get_following_count()
        }
        
        return render(request, "profiles/followers.html", context)
    
    except Profile.DoesNotExist:
        raise Http404("Profil bulunamadı")

@login_required
def following_view(request, username):
    """Kullanıcının takip ettiği kişileri listeler"""
    user = get_object_or_404(User, username=username)
    try:
        profile = Profile.objects.get(user=user)
        
        # Kullanıcı, profile sahibi tarafından engellenmişse kontrol et
        is_blocked_by = False
        is_blocked = False
        if request.user.is_authenticated:
            try:
                user_profile = request.user.profile
                following_ids = user_profile.following.values_list('id', flat=True)

                # Kullanıcı, profile sahibi tarafından engellenmişse
                is_blocked_by = profile.is_blocked(user_profile)
                is_blocked = user_profile.is_blocked(profile)
                if is_blocked_by:
                    messages.warning(request, f"{user.username} sizi engellediği için bu kullanıcının içeriklerini görüntüleyemezsiniz.")
            except Profile.DoesNotExist:
                pass
                
        following = profile.following.all()
        
        context = {
            "profile": profile,
            "following": following,
            "following_ids": following_ids,
            "is_following_page": True,
            "is_blocked_by": is_blocked_by,
            "is_blocked": is_blocked,
            "followers_count": profile.get_followers_count(),
            "following_count": profile.get_following_count()
        }
        
        return render(request, "profiles/following.html", context)
    
    except Profile.DoesNotExist:
        raise Http404("Profil bulunamadı")

@login_required
def block_toggle_view(request, username):
    """Kullanıcıyı engelleme veya engelini kaldırma işlemi"""
    if request.method != 'POST':
        return JsonResponse({"error": "Geçersiz istek metodu"}, status=405)
    
    # Engellenecek kullanıcıyı bul
    target_user = get_object_or_404(User, username=username)
    
    # Kendi kendini engellemeyi önle
    if target_user == request.user:
        return JsonResponse({"error": "Kendinizi engelleyemezsiniz"}, status=400)
    
    try:
        # Profilleri al
        user_profile = request.user.profile
        target_profile = target_user.profile
        
        # Engelleme durumunu kontrol et
        is_blocked = user_profile.is_blocked(target_profile)
        
        if is_blocked:
            # Engeli kaldır
            user_profile.unblock(target_profile)
            return JsonResponse({"status": "unblocked"})
        else:
            # Engelle
            user_profile.block(target_profile)
            return JsonResponse({"status": "blocked"})
            
    except Profile.DoesNotExist:
        return JsonResponse({"error": "Profil bulunamadı"}, status=404)

@login_required
def blocked_users_view(request):
    """Kullanıcının engellediği profilleri listeler"""
    try:
        # Kullanıcının profilini al
        profile = request.user.profile
        
        # Engellenen kullanıcıları al
        blocked_users = profile.blocked.all().select_related('user', 'university', 'department')
        
        # Sayfalama işlemi
        paginator = Paginator(blocked_users, 12)  # Her sayfada 12 kullanıcı
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        context = {
            "profiles": page_obj,
            "title": "Engellenen Kullanıcılar",
            "total_profiles": blocked_users.count(),
            "active_tab": "blocked_users",
            'page_title': "Engellenen Kullanıcılar",
        }
        
        return render(request, "profiles/blocked_users.html", context)
        
    except Profile.DoesNotExist:
        # Kullanıcının profili yoksa oluştur
        profile = Profile.objects.create(user=request.user)
        context = {
            "profiles": [],
            "title": "Engellenen Kullanıcılar",
            "total_profiles": 0,
            "active_tab": "blocked_users",
        }
        
        return render(request, "profiles/blocked_users.html", context)

@login_required
def follow_requests_view(request):
    """Kullanıcının aldığı takip isteklerini listeler"""
    try:
        profile = request.user.profile
        follow_requests = profile.get_pending_follow_requests()
        
        context = {
            "follow_requests": follow_requests,
            "requests_count": follow_requests.count()
        }
        
        return render(request, "profiles/follow_requests.html", context)
        
    except Profile.DoesNotExist:
        profile = Profile.objects.create(user=request.user)
        return render(request, "profiles/follow_requests.html", {"follow_requests": [], "requests_count": 0})

@login_required
def accept_follow_request_view(request, request_id):
    """Takip isteğini kabul et"""
    if request.method != 'POST':
        return JsonResponse({"error": "Geçersiz istek metodu"}, status=405)
    
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
            return JsonResponse({"status": "accepted", "message": "Takip isteği kabul edildi."})
        else:
            return JsonResponse({"error": "İstek kabul edilemedi."}, status=400)
            
    except FollowRequest.DoesNotExist:
        return JsonResponse({"error": "Takip isteği bulunamadı"}, status=404)

@login_required
def reject_follow_request_view(request, request_id):
    """Takip isteğini reddet"""
    if request.method != 'POST':
        return JsonResponse({"error": "Geçersiz istek metodu"}, status=405)
    
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
            return JsonResponse({"status": "rejected", "message": "Takip isteği reddedildi."})
        else:
            return JsonResponse({"error": "İstek reddedilemedi."}, status=400)
            
    except FollowRequest.DoesNotExist:
        return JsonResponse({"error": "Takip isteği bulunamadı"}, status=404)

@login_required
def toggle_profile_privacy_view(request):
    """Profil gizliliğini değiştir"""
    if request.method != 'POST':
        return JsonResponse({"error": "Geçersiz istek metodu"}, status=405)
    
    try:
        profile = request.user.profile
        
        # Önceki gizlilik durumunu kaydet
        was_private = profile.is_private
        
        # Gizlilik durumunu tersine çevir
        profile.is_private = not profile.is_private
        profile.save()
        
        message = f"Profiliniz {'gizli' if profile.is_private else 'herkese açık'} olarak ayarlandı."
        
        # Eğer profil gizli olmaktan çıkarıldıysa (was_private=True ve şimdi False olduysa)
        if was_private and not profile.is_private:
            # Bekleyen tüm takip isteklerini al
            pending_requests = profile.get_pending_follow_requests()
            
            if pending_requests.exists():
                # Her bekleyen istek için
                for follow_request in pending_requests:
                    # İsteği kabul et
                    follow_request.accept()
                
                # Kaç tane isteğin onaylandığını bildir
                request_count = pending_requests.count()
                message += f" Bekleyen {request_count} takip isteği otomatik olarak kabul edildi."
        
        return JsonResponse({
            "status": "success", 
            "is_private": profile.is_private, 
            "message": message
        })
        
    except Profile.DoesNotExist:
        return JsonResponse({"error": "Profil bulunamadı"}, status=404)

@login_required
def profile_settings_view(request):
    """Kullanıcı profil ayarları sayfası"""
    try:
        profile = request.user.profile
    except Profile.DoesNotExist:
        profile = Profile.objects.create(user=request.user)
    if request.method == 'POST':
        form = ProfileSettingsForm(request.POST, request.FILES, instance=profile, user=request.user)
        if form.is_valid():
            saved_profile = form.save()
            
            # Check if email changed (form has tracked this)
            if hasattr(form, 'email_changed') and form.email_changed:
                # Generate new verification token
                import uuid
                from django.utils import timezone
                from django.core.mail import send_mail
                from django.template.loader import render_to_string
                from django.conf import settings
                
                # Update verification information
                profile.email_verification_token = uuid.uuid4()
                profile.email_verification_sent_at = timezone.now()
                profile.save()
                
                # Send verification email to new address
                verification_url = f"{request.scheme}://{request.get_host()}/profile/verify-email/{profile.email_verification_token}/"
                subject = "Kampuslu - E-posta Adresinizi Doğrulayın"
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
                    messages.success(request, "Hesap ayarlarınız güncellendi. E-posta adresiniz değiştiğinden dolayı, yeni adresinize bir doğrulama bağlantısı gönderdik. Lütfen e-postanızı kontrol edin.")
                except Exception as e:
                    messages.error(request, f"E-posta gönderimi sırasında bir hata oluştu: {str(e)}")
                    messages.success(request, "Hesap ayarlarınız güncellendi, ancak e-posta doğrulama bağlantısı gönderilemedi.")
            else:
                messages.success(request, "Hesap ayarlarınız başarıyla güncellendi.")
            
            return redirect('profiles:settings')
    else:
        form = ProfileSettingsForm(instance=profile, user=request.user)
    
    return render(request, "profiles/profile_settings.html", {
        'form': form,
        'profile': profile,
        'active_tab': 'account',
        'page_title': "Hesap Ayarları"
    })

@login_required
def privacy_settings_view(request):
    """Kullanıcı gizlilik ayarları sayfası"""
    try:
        profile = request.user.profile
    except Profile.DoesNotExist:
        profile = Profile.objects.create(user=request.user)
    
    if request.method == 'POST':
        form = PrivacySettingsForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Gizlilik ayarlarınız başarıyla güncellendi.")
            return redirect('profiles:privacy_settings')
    else:
        form = PrivacySettingsForm(instance=profile)
    
    return render(request, "profiles/profile_settings.html", {
        'form': form,
        'profile': profile,
        'active_tab': 'privacy',
        'page_title': "Gizlilik Ayarları"
    })

@login_required
def delete_account_view(request):
    """Kullanıcı hesabını silme sayfası"""
    if request.method == 'POST':
        form = DeleteAccountForm(request.POST)
        if form.is_valid():
            password = form.cleaned_data.get('password')
            user = request.user
            
            # Şifre doğruluğunu kontrol et
            if user.check_password(password):
                # Hesabı sil
                user.is_active = False
                user.save()
                
                # Kullanıcı oturumunu sonlandır
                from django.contrib.auth import logout
                logout(request)
                
                messages.success(request, "Hesabınız başarıyla silinmiştir.")
                return redirect('guest:home')
            else:
                form.add_error('password', "Girilen parola hatalı.")
    else:
        form = DeleteAccountForm()
    
    return render(request, "profiles/profile_settings.html", {
        'form': form,
        'active_tab': 'delete',
        'page_title': "Hesabı Sil"
    })

@login_required
def password_change_view(request):
    """Kullanıcı şifre değiştirme sayfası"""
    if request.method == 'POST':
        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            form.save()
            # Şifre değiştiğinde oturum da güncellenir böylece kullanıcı çıkış yapmak zorunda kalmaz
            update_session_auth_hash(request, form.user)
            messages.success(request, "Şifreniz başarıyla değiştirildi.")
            return redirect('profiles:password_change')
    else:
        form = PasswordChangeForm(user=request.user)
    
    try:
        profile = request.user.profile
    except Profile.DoesNotExist:
        profile = Profile.objects.create(user=request.user)
    
    return render(request, "profiles/profile_settings.html", {
        'form': form,
        'profile': profile,
        'active_tab': 'password',
        'page_title': "Şifre Değiştir"
    })

def verify_email_view(request, token):
    """E-posta doğrulama görünümü"""
    try:
        # Token'a göre profili bul
        profile = get_object_or_404(Profile, email_verification_token=token)
          # Token'ın geçerlilik süresini kontrol et (24 saat)
        from django.utils import timezone
        if profile.email_verification_sent_at and timezone.now() - profile.email_verification_sent_at > timedelta(hours=24):
            messages.error(request, "Doğrulama bağlantısının süresi dolmuş. Lütfen yeni bir doğrulama bağlantısı isteyin.")
            return redirect("guest:home")
        
        # E-posta doğrulama işlemi
        profile.email_verified = True
        
        # Edu.tr e-postası ise rozeti ver
        if profile.user.email.lower().endswith('.edu.tr'):
            profile.is_verified = True
            messages.success(request, "E-posta adresiniz başarıyla doğrulandı! Edu.tr uzantılı e-posta kullandığınız için hesabınız doğrulanmış olarak işaretlendi.")
        else:
            messages.success(request, "E-posta adresiniz başarıyla doğrulandı!")
        
        # Token'ı temizle
        profile.email_verification_token = None
        profile.save()
        
        # Kullanıcı giriş yapmışsa ana sayfaya, değilse giriş sayfasına yönlendir
        if request.user.is_authenticated:
            return redirect("post:post_list")
        else:
            return redirect("guest:login")
            
    except Profile.DoesNotExist:
        messages.error(request, "Geçersiz doğrulama bağlantısı.")
        return redirect("guest:home")

@login_required
def resend_verification_email_view(request):
    """E-posta doğrulama bağlantısını yeniden gönder"""
    from django.core.mail import send_mail
    from django.template.loader import render_to_string
    from django.conf import settings
    
    # Kullanıcının profilini kontrol et
    profile = request.user.profile
    
    # Zaten doğrulanmış ise
    if profile.email_verified:
        messages.info(request, "E-posta adresiniz zaten doğrulanmış.")
        return redirect("profiles:profile", username=request.user.username)
      # Yeni token oluştur
    import uuid
    from django.utils import timezone
    
    profile.email_verification_token = uuid.uuid4()
    profile.email_verification_sent_at = timezone.now()
    profile.save()
      # Doğrulama bağlantısını hazırla ve e-posta gönder
    verification_url = f"{request.scheme}://{request.get_host()}/profile/verify-email/{profile.email_verification_token}/"
    subject = "Kampuslu - E-posta Adresinizi Doğrulayın"
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
        messages.success(request, "E-posta doğrulama bağlantısı tekrar gönderildi. Lütfen e-postanızı kontrol edin.")
    except Exception as e:
        messages.error(request, f"E-posta gönderimi sırasında bir hata oluştu: {str(e)}")
    
    return redirect("profiles:profile", username=request.user.username)