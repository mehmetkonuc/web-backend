from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse, reverse_lazy
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q, Count
from django.http import QueryDict

from .models import ConfessionModel, ConfessionCategory, ConfessionImage, ConfessionFilter
from .filters import ConfessionFilterSet
from .forms import ConfessionForm, ConfessionImageForm
from apps.profiles.models import Profile
from apps.comment.models import Comment

class ConfessionListView(LoginRequiredMixin, ListView):
    """Main confession list view with filtering and privacy controls"""
    model = ConfessionModel
    template_name = 'confession/index.html'
    context_object_name = 'confessions'
    paginate_by = 20
    
    def get_queryset(self):
        # Start with active confessions
        queryset = ConfessionModel.objects.filter(is_active=True).order_by('-created_at')
        
        # Get the current user's profile
        try:
            profile = Profile.objects.get(user=self.request.user)
            
            # Exclude confessions from blocked users and users who blocked the current user
            blocked_users = [user.user for user in profile.blocked.all()]
            blocked_by_users = [user.user for user in profile.blocked_by.all()]
            all_blocked = list(set(blocked_users + blocked_by_users))
            
            if all_blocked:
                queryset = queryset.exclude(user__in=all_blocked)
            
            # Exclude confessions from users with private profiles who the current user doesn't follow
            # First, get all private profiles
            private_profiles = Profile.objects.filter(is_private=True)
            # Exclude the current user's profile from the filter
            private_profiles = private_profiles.exclude(user=self.request.user)
            # Get the users that the current user follows
            following_users = [user.user for user in profile.following.all()]
            # Get users with private profiles that the current user doesn't follow
            private_users_not_following = [p.user for p in private_profiles if p.user not in following_users]
            
            # Exclude these users' confessions from the queryset
            if private_users_not_following:
                queryset = queryset.exclude(user__in=private_users_not_following)
                
            # Check if the user has any GET parameters
            filter_data = self.request.GET
            
            # If no GET parameters, try to use saved filter preferences
            if not filter_data:
                try:
                    user_filter = ConfessionFilter.objects.get(user=self.request.user)
                    # Create a QueryDict with saved preferences to pass to the filter
                    filter_data = QueryDict(mutable=True)
                    
                    # Add saved preferences to the filter data
                    if user_filter.category:
                        filter_data['category'] = str(user_filter.category.pk)
                    if user_filter.university:
                        filter_data['university'] = str(user_filter.university.pk)
                    if user_filter.sort_by:
                        filter_data['sort_by'] = user_filter.sort_by
                except ConfessionFilter.DoesNotExist:
                    # No saved preferences found, use empty filter
                    pass
                
            # Apply filters
            self.filterset = ConfessionFilterSet(filter_data or None, queryset=queryset, user=self.request.user)
            
            # If form is valid, save preferences
            if self.filterset.is_valid():
                self.filterset.save_preferences()
                
            # Return filtered queryset
            return self.filterset.qs
            
        except Profile.DoesNotExist:
            return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter'] = self.filterset
        context['categories'] = ConfessionCategory.objects.annotate(
            total_confessions=Count('confessions')
        ).order_by('-total_confessions')[:10]
        context['active_tab'] = 'confession'
        context['page_title'] = 'İtiraflar'
        return context

class ConfessionDetailView(LoginRequiredMixin, DetailView):
    """Confession detail view with privacy controls"""
    model = ConfessionModel
    template_name = 'confession/detail.html'
    context_object_name = 'confession'
    
    def get_queryset(self):
        # Start with active confessions
        queryset = ConfessionModel.objects.filter(is_active=True)
        
        # Get the current user's profile
        try:
            profile = Profile.objects.get(user=self.request.user)
            
            # Exclude confessions from blocked users and users who blocked the current user
            blocked_users = [user.user for user in profile.blocked.all()]
            blocked_by_users = [user.user for user in profile.blocked_by.all()]
            all_blocked = list(set(blocked_users + blocked_by_users))
            
            if all_blocked:
                queryset = queryset.exclude(user__in=all_blocked)
            
            # Exclude confessions from users with private profiles who the current user doesn't follow
            private_profiles = Profile.objects.filter(is_private=True)
            private_profiles = private_profiles.exclude(user=self.request.user)
            following_users = [user.user for user in profile.following.all()]
            private_users_not_following = [p.user for p in private_profiles if p.user not in following_users]
            
            if private_users_not_following:
                queryset = queryset.exclude(user__in=private_users_not_following)
            
            # Add performance optimizations
            queryset = queryset.select_related('user', 'category', 'university')
            queryset = queryset.prefetch_related('likes', 'comments', 'bookmarks', 'images')
            
            return queryset
            
        except Profile.DoesNotExist:
            return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_tab'] = 'confession'
        context['page_title'] = 'İtiraf Detayı'
        return context

class ConfessionCategoryView(LoginRequiredMixin, ListView):
    """View for displaying confessions of a specific category"""
    model = ConfessionModel
    template_name = 'confession/category.html'
    context_object_name = 'confessions'
    paginate_by = 20
    
    def get_queryset(self):
        self.category = get_object_or_404(ConfessionCategory, pk=self.kwargs.get('pk'))
        queryset = ConfessionModel.objects.filter(
            category=self.category, 
            is_active=True
        ).order_by('-created_at')
        
        # Get the current user's profile
        try:
            profile = Profile.objects.get(user=self.request.user)
            
            # Exclude confessions from blocked users and users who blocked the current user
            blocked_users = [user.user for user in profile.blocked.all()]
            blocked_by_users = [user.user for user in profile.blocked_by.all()]
            all_blocked = list(set(blocked_users + blocked_by_users))
            
            if all_blocked:
                queryset = queryset.exclude(user__in=all_blocked)
            
            # Exclude confessions from users with private profiles who the current user doesn't follow
            private_profiles = Profile.objects.filter(is_private=True)
            private_profiles = private_profiles.exclude(user=self.request.user)
            following_users = [user.user for user in profile.following.all()]
            private_users_not_following = [p.user for p in private_profiles if p.user not in following_users]
            
            if private_users_not_following:
                queryset = queryset.exclude(user__in=private_users_not_following)
            
            # Add performance optimizations
            queryset = queryset.select_related('user', 'category', 'university')
            queryset = queryset.prefetch_related('likes', 'comments', 'bookmarks', 'images')
            
            return queryset
            
        except Profile.DoesNotExist:
            return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['category'] = self.category
        context['categories'] = ConfessionCategory.objects.annotate(
            total_confessions=Count('confessions')
        ).order_by('-total_confessions')[:10]
        context['page_title'] = f'Kategori: {self.category.name}'
        return context

class ConfessionCreateView(LoginRequiredMixin, CreateView):
    """Create new confession view"""
    model = ConfessionModel
    form_class = ConfessionForm
    template_name = 'confession/create.html'
    
    def get_form_kwargs(self):
        """Pass user to form for initial university setting"""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        print(f"DEBUG: Form is valid. Data: {form.cleaned_data}")
        form.instance.user = self.request.user
        
        # University will be set from the form selection
        # No need to override from profile since user can choose
        
        response = super().form_valid(form)
        print(f"DEBUG: Confession created with ID: {self.object.pk}")
        
        # Handle multiple image uploads
        images = self.request.FILES.getlist('images')
        print(f"DEBUG: Number of images uploaded: {len(images)}")
        
        # Validate image count
        if len(images) > 4:
            messages.error(self.request, 'En fazla 4 resim yükleyebilirsiniz.')
            self.object.delete()  # Delete the confession if too many images
            return redirect('confession:confession_list')
        
        # Save each image
        for i, image_file in enumerate(images):
            print(f"DEBUG: Saving image {i+1}: {image_file.name}")
            ConfessionImage.objects.create(
                confession=self.object,
                user=self.request.user,
                image=image_file,
                order=i
            )
        
        messages.success(self.request, 'İtiraf başarıyla oluşturuldu.')
        return response
    
    def form_invalid(self, form):
        print(f"DEBUG: Form is invalid. Errors: {form.errors}")
        print(f"DEBUG: Form data: {form.data}")
        return super().form_invalid(form)
    
    def get_success_url(self):
        return reverse('confession:confession_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'İtiraf Oluştur'
        context['image_form'] = ConfessionImageForm()
        return context

class ConfessionUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """Update confession view - only author can edit"""
    model = ConfessionModel
    form_class = ConfessionForm
    template_name = 'confession/update.html'
    
    def test_func(self):
        confession = self.get_object()
        return self.request.user == confession.user
    
    def get_success_url(self):
        return reverse('confession:confession_detail', kwargs={'pk': self.object.pk})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'İtiraf Düzenle'
        context['image_form'] = ConfessionImageForm()

        return context

class ConfessionDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """Delete confession view - only author can delete"""
    model = ConfessionModel
    template_name = 'confession/confirm_delete.html'
    success_url = reverse_lazy('confession:confession_list')
    
    def test_func(self):
        confession = self.get_object()
        return self.request.user == confession.user
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'İtiraf Sil'
        return context

@login_required
def clear_filters_view(request):
    """
    Kullanıcının filtre tercihlerini temizler ve ana listeye yönlendirir
    """
    # Kullanıcının filtre tercihlerini veritabanından sil
    try:
        user_filter = ConfessionFilter.objects.get(user=request.user)
        user_filter.university = None
        user_filter.category = None
        user_filter.sort_by = None
        user_filter.save()
    except ConfessionFilter.DoesNotExist:
        # Filtre kaydı yoksa bir şey yapmamıza gerek yok
        pass

    # İtiraflar listesine yönlendir
    return redirect('confession:confession_list')


@login_required
def confession_toggle_privacy(request, pk):
    """Toggle confession privacy status - AJAX endpoint"""
    if request.method == 'POST':
        confession = get_object_or_404(ConfessionModel, pk=pk, user=request.user)
        confession.is_privacy = not confession.is_privacy
        confession.save()
        
        return JsonResponse({
            'success': True,
            'is_privacy': confession.is_privacy,
            'message': 'Gizlilik durumu güncellendi.'
        })
    
    return JsonResponse({'success': False, 'message': 'Geçersiz istek.'})

@login_required
def confession_toggle_active(request, pk):
    """Toggle confession active status - AJAX endpoint"""
    if request.method == 'POST':
        confession = get_object_or_404(ConfessionModel, pk=pk, user=request.user)
        confession.is_active = not confession.is_active
        confession.save()
        
        return JsonResponse({
            'success': True,
            'is_active': confession.is_active,
            'message': 'İtiraf durumu güncellendi.'
        })
    
    return JsonResponse({'success': False, 'message': 'Geçersiz istek.'})
