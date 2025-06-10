from rest_framework import viewsets, permissions, generics, status, filters
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.contrib.contenttypes.models import ContentType
from django_filters.rest_framework import DjangoFilterBackend

from apps.post.models import Post, Hashtag, UserPostFilter
from apps.post.filters import PostFilter
from apps.profiles.models import Profile
from apps.dataset.models import University, Department
from .serializers import (
    PostSerializer, PostDetailSerializer, HashtagSerializer, 
    PostFilterSerializer, UniversitySerializer, DepartmentSerializer
)


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    """

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions are only allowed to the owner
        return obj.user == request.user


class PostViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing posts
    """
    serializer_class = PostSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['content']
    ordering_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']

    def get_queryset(self):
        """
        This view should return a list of all posts
        filtered based on user's profile settings (blocked users, private profiles)
        and optionally filtered by saved preferences
        """
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
            private_profiles = Profile.objects.filter(is_private=True).exclude(user=self.request.user)
            following_users = [user.user for user in profile.following.all()]
            private_users_not_following = [p.user for p in private_profiles if p.user not in following_users]
            
            if private_users_not_following:
                queryset = queryset.exclude(user__in=private_users_not_following)
                
            # Check if the user has any query parameters for filtering
            filter_data = self.request.query_params
            
            # If no query parameters, try to use saved filter preferences
            if not filter_data:
                try:
                    user_filter = UserPostFilter.objects.get(user=self.request.user)
                    
                    # Apply saved preferences
                    if user_filter.posts_type == 'following':
                        following_users = [user.user for user in profile.following.all()]
                        following_users.append(self.request.user)
                        queryset = queryset.filter(user__in=following_users)
                    elif user_filter.posts_type == 'verified':
                        verified_profiles = Profile.objects.filter(is_verified=True)
                        verified_users = [profile.user for profile in verified_profiles]
                        queryset = queryset.filter(user__in=verified_users)
                        
                    if user_filter.university:
                        profiles = Profile.objects.filter(university=user_filter.university)
                        users = [profile.user for profile in profiles]
                        queryset = queryset.filter(user__in=users)
                        
                    if user_filter.department:
                        profiles = Profile.objects.filter(department=user_filter.department)
                        users = [profile.user for profile in profiles]
                        queryset = queryset.filter(user__in=users)
                except UserPostFilter.DoesNotExist:
                    # No saved preferences found, use default
                    pass
            else:
                # Apply query parameter filters
                posts_type = self.request.query_params.get('posts_type')
                university_id = self.request.query_params.get('university')
                department_id = self.request.query_params.get('department')
                
                if posts_type == 'following':
                    following_users = [user.user for user in profile.following.all()]
                    following_users.append(self.request.user)
                    queryset = queryset.filter(user__in=following_users)
                elif posts_type == 'verified':
                    verified_profiles = Profile.objects.filter(is_verified=True)
                    verified_users = [profile.user for profile in verified_profiles]
                    queryset = queryset.filter(user__in=verified_users)
                
                if university_id:
                    profiles = Profile.objects.filter(university_id=university_id)
                    users = [profile.user for profile in profiles]
                    queryset = queryset.filter(user__in=users)
                
                if department_id:
                    profiles = Profile.objects.filter(department_id=department_id)
                    users = [profile.user for profile in profiles]
                    queryset = queryset.filter(user__in=users)
            
            return queryset
            
        except Profile.DoesNotExist:
            return queryset

    def get_serializer_class(self):
        """
        Return different serializers based on the action
        """
        if self.action == 'retrieve':
            return PostDetailSerializer
        return self.serializer_class

    def perform_create(self, serializer):
        """
        Set the user when creating a post
        """
        serializer.save(user=self.request.user)
        
    def retrieve(self, request, *args, **kwargs):
        """
        Override retrieve to bypass privacy filters when fetching a specific post by ID
        """
        try:
            # Get the post directly by ID
            instance = Post.objects.get(pk=kwargs['pk'])
            
            # Check if the post is from a private profile and the user is not following
            if hasattr(instance.user, 'profile') and instance.user.profile.is_private and request.user != instance.user:
                # Get the current user's profile
                try:
                    profile = Profile.objects.get(user=request.user)
                    # Check if the user follows the post creator
                    if instance.user not in [user.user for user in profile.following.all()]:
                        return Response(
                            {"detail": "This post is from a private profile. You need to follow this user to see their posts."},
                            status=status.HTTP_403_FORBIDDEN
                        )
                except Profile.DoesNotExist:
                    return Response(
                        {"detail": "This post is from a private profile. You need to follow this user to see their posts."},
                        status=status.HTTP_403_FORBIDDEN
                    )
                    
            # Check if the user is blocked or has blocked the post creator
            try:
                profile = Profile.objects.get(user=request.user)
                blocked_users = [user.user for user in profile.blocked.all()]
                blocked_by_users = [user.user for user in profile.blocked_by.all()]
                
                if instance.user in blocked_users or instance.user in blocked_by_users:
                    return Response(
                        {"detail": "You cannot view this post due to blocking settings."},
                        status=status.HTTP_403_FORBIDDEN
                    )
            except Profile.DoesNotExist:
                pass
                
            # Serialize and return the post
            serializer = self.get_serializer(instance)
            return Response(serializer.data)
            
        except Post.DoesNotExist:
            return Response(
                {"detail": "No Post matches the given query."},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['get'], url_path='direct/(?P<post_id>[^/.]+)')
    def get_post_direct(self, request, post_id=None):
        """
        Get a specific post by ID without any privacy or blocking filters
        This endpoint bypasses all privacy and blocking settings
        """
        try:
            # Get the post directly by ID without any filters
            instance = Post.objects.get(pk=post_id)
            
            # Serialize and return the post without any privacy checks
            serializer = self.get_serializer(instance)
            return Response(serializer.data)
            
        except Post.DoesNotExist:
            return Response(
                {"detail": "No Post matches the given query."},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['get'])
    def trending(self, request):
        """
        Get trending hashtags and their associated posts
        """
        trending_hashtags = Hashtag.get_trending_hashtags(20)
        serializer = HashtagSerializer(trending_hashtags, many=True, context={'request': request})
        
        # Get a few posts for each hashtag
        trending_posts = {}
        for hashtag in trending_hashtags:
            posts_query = self.get_queryset().filter(hashtags=hashtag)
            posts = posts_query.order_by('-created_at')[:3]
            trending_posts[hashtag.id] = PostSerializer(posts, many=True, context={'request': request}).data
        
        return Response({
            'hashtags': serializer.data,
            'posts': trending_posts
        })

    @action(detail=False, methods=['get'])
    def by_hashtag(self, request):
        """
        Get posts filtered by hashtag
        """
        hashtag_name = request.query_params.get('hashtag')
        if not hashtag_name:
            return Response({"detail": "Hashtag parameter is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        hashtag = get_object_or_404(Hashtag, name=hashtag_name.lower())
        posts = self.get_queryset().filter(hashtags=hashtag)
        
        page = self.paginate_queryset(posts)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(posts, many=True)
        return Response({
            'hashtag': HashtagSerializer(hashtag, context={'request': request}).data,
            'posts': serializer.data
        })

    @action(detail=False, methods=['get'])
    def my_posts(self, request):
        """
        Get the current user's posts
        """
        posts = self.get_queryset().filter(user=request.user)
        
        page = self.paginate_queryset(posts)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(posts, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def user_posts(self, request):
        """
        Get posts from a specific user
        """
        username = request.query_params.get('username')
        if not username:
            return Response({"detail": "Username parameter is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        user = get_object_or_404(Profile, user__username=username)
        
        # Check if the profile is private and the requester is not following
        if user.is_private and request.user != user.user:
            try:
                profile = Profile.objects.get(user=request.user)
                if user.user not in [followed.user for followed in profile.following.all()]:
                    return Response(
                        {"detail": "This profile is private. You need to follow this user to see their posts."},
                        status=status.HTTP_403_FORBIDDEN
                    )
            except Profile.DoesNotExist:
                return Response(
                    {"detail": "This profile is private. You need to follow this user to see their posts."},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        posts = self.get_queryset().filter(user=user.user)
        
        page = self.paginate_queryset(posts)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(posts, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['delete'])
    def delete_post(self, request, pk=None):
        """
        Delete a specific post - only allowed for post owner or site admin
        """
        try:
            # Get the post by ID
            post = get_object_or_404(Post, pk=pk)
            
            # Check if user is the post owner or site admin
            if request.user != post.user and not request.user.is_staff:
                return Response(
                    {"detail": "You don't have permission to delete this post."},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Delete the post
            post.delete()
            
            return Response(
                {"detail": "Post deleted successfully."},
                status=status.HTTP_204_NO_CONTENT
            )
            
        except Post.DoesNotExist:
            return Response(
                {"detail": "No Post matches the given query."},
                status=status.HTTP_404_NOT_FOUND
            )

class TrendingHashtagView(generics.ListAPIView):
    """
    API endpoint for getting trending hashtags
    """
    serializer_class = HashtagSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Hashtag.get_trending_hashtags(20)


class FilterOptionsAPIView(APIView):
    """
    API endpoint to get filter options for posts (universities, departments, post types)
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, *args, **kwargs):
        universities = University.objects.all()
        departments = Department.objects.all()
        
        # Gönderi tipleri seçenekleri
        post_types = [
            {'id': 'all', 'name': 'Bütün Gönderiler'},
            {'id': 'following', 'name': 'Sadece Takip Ettiklerim'},
            {'id': 'verified', 'name': 'Sadece Doğrulanmış Hesaplar'},
        ]
        
        # Serialize each dataset
        university_serializer = UniversitySerializer(universities, many=True)
        department_serializer = DepartmentSerializer(departments, many=True)
        
        return Response({
            'universities': university_serializer.data,
            'departments': department_serializer.data,
            'post_types': post_types,
        })


class PostFilterPreferencesViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing user post filter preferences
    """
    serializer_class = PostFilterSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return UserPostFilter.objects.filter(user=self.request.user)
    
    def get_object(self):
        # Get or create filter preferences for current user
        filter_prefs, created = UserPostFilter.objects.get_or_create(user=self.request.user)
        return filter_prefs
    
    def list(self, request, *args, **kwargs):
        # Return current user's filter preferences
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    def create(self, request, *args, **kwargs):
        # Delegate to update
        return self.update(request, *args, **kwargs)
    
    @action(detail=False, methods=['post'])
    def clear(self, request):
        """Clear all filter preferences"""
        try:
            filter_prefs = self.get_object()
            filter_prefs.posts_type = 'all'  # Varsayılan değere ayarla
            filter_prefs.university = None
            filter_prefs.department = None
            filter_prefs.save()
            return Response({"detail": "Filter preferences cleared successfully"})
        except Exception as e:
            return Response(
                {"detail": f"Error clearing preferences: {str(e)}"}, 
                status=status.HTTP_400_BAD_REQUEST
            )