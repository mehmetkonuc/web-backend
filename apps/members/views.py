from django.shortcuts import render, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.views.generic import ListView
from django.http import QueryDict
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from apps.profiles.models import Profile
from .filters import MemberFilter
from .models import UserMemberFilter

class MemberListView(LoginRequiredMixin, ListView):
    """
    Sitedeki tüm üyeleri listeler ve filtreler
    """
    model = Profile
    template_name = 'members/members_list.html'
    context_object_name = 'profiles'
    paginate_by = 20
    
    def get_queryset(self):
        # Sadece aktif kullanıcıların profillerini çek
        queryset = Profile.objects.filter(user__is_active=True).select_related('user', 'university', 'department')
        
        # Filtre verisi başlangıçta GET parametrelerinden gelir
        filter_data = self.request.GET.copy()
        
        # Eğer filtre verileri boşsa ve kullanıcı kayıtlı filtreleme tercihlerine sahipse
        if not filter_data and self.request.user.is_authenticated:
            try:
                # Kullanıcının kaydedilmiş filtre tercihlerini al
                user_filter = UserMemberFilter.objects.get(user=self.request.user)
                
                # Kaydedilmiş tercihlerden QueryDict oluştur
                filter_data = QueryDict(mutable=True)
                
                # Kaydedilmiş değerleri ekle (sadece belirtilen alanlar)
                if user_filter.university:
                    filter_data['university'] = str(user_filter.university.id)
                if user_filter.department:
                    filter_data['department'] = str(user_filter.department.id)
                if user_filter.graduation_status:
                    filter_data['graduation_status'] = str(user_filter.graduation_status.id)
                if user_filter.is_verified is not None:
                    filter_data['is_verified'] = str(user_filter.is_verified)
            except UserMemberFilter.DoesNotExist:
                pass
        
        # Filtreyi oluştur
        self.filter = MemberFilter(filter_data, queryset=queryset)
        
        # Eğer kullanıcı aktif olarak filtreleme yapıyorsa, tercihlerini kaydet
        if self.request.GET and self.request.user.is_authenticated:
            self.filter.save_preferences(self.request.user)
        
        return self.filter.qs
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter'] = self.filter
        
        # Mevcut kullanıcının takip ettiği profilleri alma
        following_ids = []
        pending_request_ids = []
        
        if self.request.user.is_authenticated:
            try:
                user_profile = self.request.user.profile
                following_ids = user_profile.following.values_list('id', flat=True)
                
                # Bekleyen takip isteklerini alma
                from django.db.models import Q
                from apps.profiles.models import FollowRequest
                pending_requests = FollowRequest.objects.filter(
                    from_user=user_profile,
                    status='pending'
                )
                pending_request_ids = [req.to_user.id for req in pending_requests]
                
            except Profile.DoesNotExist:
                pass
        
        context['following_ids'] = following_ids
        context['pending_request_ids'] = pending_request_ids
        context['total_profiles'] = self.filter.qs.count()
        context['page_title'] = 'Kişi Bul'
        context['active_tab'] = 'members'
        
        return context


@login_required
def clear_filters_view(request):
    """
    Kullanıcının filtre tercihlerini temizler ve ana listeye yönlendirir
    """
    # Kullanıcının filtre tercihlerini veritabanından sil
    try:
        user_filter = UserMemberFilter.objects.get(user=request.user)
        user_filter.university = None
        user_filter.department = None
        user_filter.graduation_status = None
        user_filter.is_verified = None
        user_filter.save()
    except UserMemberFilter.DoesNotExist:
        # Filtre kaydı yoksa bir şey yapmamıza gerek yok
        pass
    
    # Üyeler listesine yönlendir
    return redirect('members:members_list')