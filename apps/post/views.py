from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.generic import ListView, DetailView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse, reverse_lazy
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q

from .models import Post, PostImage, Hashtag, UserPostFilter
from .forms import PostForm
from .filters import PostFilter
from apps.profiles.models import Profile
from apps.comment.models import Comment

class PostListView(LoginRequiredMixin, ListView):
    model = Post
    template_name = 'post/index.html'
    context_object_name = 'posts'
    paginate_by = 3
    
    def get_queryset(self):
        # First, get all posts
        queryset = Post.objects.all().order_by('-created_at')
        
        # Get the current user's profile
        try:
            profile = Profile.objects.get(user=self.request.user)
            
            # Exclude posts from blocked users and users who blocked the current user
            blocked_users = [user.user for user in profile.blocked.all()]
            blocked_by_users = [user.user for user in profile.blocked_by.all()]
            all_blocked = list(set(blocked_users + blocked_by_users))
            
            if all_blocked:
                queryset = queryset.exclude(user__in=all_blocked)
            
            # Exclude posts from users with private profiles who the current user doesn't follow
            # First, get all private profiles
            private_profiles = Profile.objects.filter(is_private=True)
            # Exclude the current user's profile from the filter
            private_profiles = private_profiles.exclude(user=self.request.user)
            # Get the users that the current user follows
            following_users = [user.user for user in profile.following.all()]
            # Get users with private profiles that the current user doesn't follow
            private_users_not_following = [p.user for p in private_profiles if p.user not in following_users]
            
            # Exclude these users' posts from the queryset
            if private_users_not_following:
                queryset = queryset.exclude(user__in=private_users_not_following)
                
            # Check if the user has any GET parameters
            filter_data = self.request.GET
            
            # If no GET parameters, try to use saved filter preferences
            if not filter_data:
                try:
                    user_filter = UserPostFilter.objects.get(user=self.request.user)
                    # Create a QueryDict with saved preferences to pass to the filter
                    from django.http import QueryDict
                    filter_data = QueryDict(mutable=True)
                    
                    # Add saved preferences to the filter data
                    if user_filter.posts_type:
                        filter_data['posts_type'] = user_filter.posts_type
                    if user_filter.university:
                        filter_data['university'] = str(user_filter.university.id)
                    if user_filter.department:
                        filter_data['department'] = str(user_filter.department.id)
                except UserPostFilter.DoesNotExist:
                    # No saved preferences found, use empty filter
                    pass
                
            # Apply filters
            self.filterset = PostFilter(filter_data or None, queryset=queryset, user=self.request.user)
            
            # If form is valid, save preferences
            if self.filterset.is_valid():
                self.filterset.save_preferences()
                
            # Return filtered queryset
            return self.filterset.qs
            
        except Profile.DoesNotExist:
            return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = PostForm()
        context['filter'] = self.filterset
        context['trending_hashtags'] = Hashtag.get_trending_hashtags(10)
        context['active_tab'] = 'post'
        context['page_title'] = 'Gönderiler'

        return context

class PostDetailView(LoginRequiredMixin, DetailView):
    model = Post
    template_name = 'post/detail.html'
    context_object_name = 'post'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_tab'] = 'post'
        
        # Trending hastag'leri de context olarak gönderelim
        context['trending_hashtags'] = Hashtag.get_trending_hashtags(10)
        context['page_title'] = 'Gönderi Detayı'
        
        return context

class HashtagPostListView(LoginRequiredMixin, ListView):
    """View for displaying posts with a specific hashtag"""
    model = Post
    template_name = 'post/hashtag_posts.html'
    context_object_name = 'posts'
    paginate_by = 10
    
    def get_queryset(self):
        self.hashtag = get_object_or_404(Hashtag, name=self.kwargs.get('hashtag').lower())
        queryset = Post.objects.filter(hashtags=self.hashtag).order_by('-created_at')
        
        # Get the current user's profile
        try:
            profile = Profile.objects.get(user=self.request.user)
            
            # Exclude posts from blocked users and users who blocked the current user
            blocked_users = [user.user for user in profile.blocked.all()]
            blocked_by_users = [user.user for user in profile.blocked_by.all()]
            all_blocked = list(set(blocked_users + blocked_by_users))
            
            if all_blocked:
                queryset = queryset.exclude(user__in=all_blocked)
            
            # Exclude posts from users with private profiles who the current user doesn't follow
            # First, get all private profiles
            private_profiles = Profile.objects.filter(is_private=True)
            # Exclude the current user's profile from the filter
            private_profiles = private_profiles.exclude(user=self.request.user)
            # Get the users that the current user follows
            following_users = [user.user for user in profile.following.all()]
            # Get users with private profiles that the current user doesn't follow
            private_users_not_following = [p.user for p in private_profiles if p.user not in following_users]
            
            # Exclude these users' posts from the queryset
            if private_users_not_following:
                queryset = queryset.exclude(user__in=private_users_not_following)
            
            return queryset
            
        except Profile.DoesNotExist:
            return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['hashtag'] = self.hashtag
        context['trending_hashtags'] = Hashtag.get_trending_hashtags(10)
        context['page_title'] = 'Hashtag: ' + self.hashtag.name

        return context

class TrendingView(LoginRequiredMixin, ListView):
    """View for displaying trending hashtags and related posts"""
    model = Hashtag
    template_name = 'post/trending.html'
    context_object_name = 'trending_hashtags'
    
    def get_queryset(self):
        return Hashtag.get_trending_hashtags(20)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get the current user's profile for blocking functionality
        try:
            profile = Profile.objects.get(user=self.request.user)
            
            # Get blocked users
            blocked_users = [user.user for user in profile.blocked.all()]
            blocked_by_users = [user.user for user in profile.blocked_by.all()]
            all_blocked = list(set(blocked_users + blocked_by_users))
            
            # Get users with private profiles that the current user doesn't follow
            # First, get all private profiles
            private_profiles = Profile.objects.filter(is_private=True)
            # Exclude the current user's profile from the filter
            private_profiles = private_profiles.exclude(user=self.request.user)
            # Get the users that the current user follows
            following_users = [user.user for user in profile.following.all()]
            # Get users with private profiles that the current user doesn't follow
            private_users_not_following = [p.user for p in private_profiles if p.user not in following_users]
            
            # Add some recent posts for each trending hashtag, excluding blocked users and private profiles
            trending_posts = {}
            for hashtag in context['trending_hashtags']:
                posts_query = Post.objects.filter(hashtags=hashtag)
                
                if all_blocked:
                    posts_query = posts_query.exclude(user__in=all_blocked)
                
                # Exclude posts from users with private profiles who the current user doesn't follow
                if private_users_not_following:
                    posts_query = posts_query.exclude(user__in=private_users_not_following)
                
                trending_posts[hashtag.id] = posts_query.order_by('-created_at')[:3]
                
            context['trending_posts'] = trending_posts
            
        except Profile.DoesNotExist:
            # Fallback if profile doesn't exist
            trending_posts = {}
            for hashtag in context['trending_hashtags']:
                trending_posts[hashtag.id] = Post.objects.filter(hashtags=hashtag).order_by('-created_at')[:3]
            context['trending_posts'] = trending_posts
        context['active_tab'] = 'trending'
        context['page_title'] = 'Trendler'
            
        return context

@login_required
def create_post(request):
    if request.method == 'POST':
        form = PostForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            post.user = request.user
            post.save()
            
            # Handle multiple image uploads manually
            images = request.FILES.getlist('images')
            
            # Validate image count
            if len(images) > 4:
                messages.error(request, 'En fazla 4 resim yükleyebilirsiniz.')
                post.delete()  # Delete the post if too many images
                return redirect('post:post_list')
            
            # Save each image
            for i, image_file in enumerate(images):
                PostImage.objects.create(
                    post=post,
                    image=image_file,
                    order=i
                )
            
            messages.success(request, 'Gönderi başarıyla oluşturuldu.')
            return redirect('post:post_list')
        else:
            messages.error(request, 'Gönderi oluşturulurken bir hata oluştu.')
    else:
        form = PostForm()
    
    return render(request, 'post/create.html', {'form': form})


class PostDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Post
    template_name = 'post/confirm_delete.html'
    success_url = reverse_lazy('post:post_list')
    
    def test_func(self):
        post = self.get_object()
        return self.request.user == post.user
