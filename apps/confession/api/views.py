from rest_framework import viewsets, permissions, generics, status, filters
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count, Exists, OuterRef
from django.contrib.contenttypes.models import ContentType
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from datetime import timedelta

from apps.confession.models import ConfessionModel, ConfessionCategory, ConfessionFilter
from apps.confession.filters import ConfessionFilterSet
from apps.profiles.models import Profile
from apps.dataset.models import University
from .serializers import (
    ConfessionSerializer, ConfessionDetailSerializer, ConfessionCategorySerializer,
    ConfessionFilterSerializer, UniversitySerializer, FilterOptionsSerializer
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


class IsActiveConfession(permissions.BasePermission):
    """
    Custom permission to only allow access to active confessions.
    """
    def has_object_permission(self, request, view, obj):
        # Only allow access to active confessions
        if hasattr(obj, 'is_active'):
            return obj.is_active
        return True


class ConfessionViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing confessions with privacy controls
    """
    serializer_class = ConfessionSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly, IsActiveConfession]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ConfessionFilterSet
    search_fields = ['content']
    ordering_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']

    def get_queryset(self):
        """
        Return confessions filtered by privacy and blocking settings
        """
        # Start with active confessions
        queryset = ConfessionModel.objects.filter(is_active=True)
        
        # Apply privacy and blocking filters
        queryset = self._apply_privacy_filters(queryset)
        
        # Apply performance optimizations
        queryset = queryset.select_related('user', 'category', 'university')
        queryset = queryset.prefetch_related('images', 'likes', 'comments', 'bookmarks')
        
        return queryset.order_by('-created_at')

    def _apply_privacy_filters(self, queryset):
        """
        Apply privacy and blocking filters to queryset
        """
        try:
            profile = Profile.objects.get(user=self.request.user)
            
            # Exclude confessions from blocked users
            blocked_users = [user.user for user in profile.blocked.all()]
            
            # Also exclude confessions from users who blocked the current user
            # (reverse relationship lookup)
            blocked_by_users = []
            try:
                blocked_by_profiles = Profile.objects.filter(blocked=profile)
                blocked_by_users = [p.user for p in blocked_by_profiles]
            except:
                pass  # If relation doesn't exist, continue
            
            all_blocked = list(set(blocked_users + blocked_by_users))
            
            if all_blocked:
                queryset = queryset.exclude(user__in=all_blocked)
            
            # Exclude confessions from users with private profiles who the current user doesn't follow
            private_profiles = Profile.objects.filter(is_private=True).exclude(user=self.request.user)
            following_users = [user.user for user in profile.following.all()]
            private_users_not_following = [p.user for p in private_profiles if p.user not in following_users]
            
            if private_users_not_following:
                queryset = queryset.exclude(user__in=private_users_not_following)
                
        except Profile.DoesNotExist:
            pass
            
        return queryset

    def get_serializer_class(self):
        """
        Return different serializers based on the action
        """
        if self.action == 'retrieve':
            return ConfessionDetailSerializer
        return self.serializer_class

    def create(self, request, *args, **kwargs):
        """
        Create a new confession with optimized image processing
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Create confession (serializer handles image processing)
        confession = serializer.save()
        
        # Response with fresh serializer (all relationships loaded)
        response_serializer = self.get_serializer(confession)
        
        return Response(
            {
                'success': True,
                'message': 'İtiraf başarıyla oluşturuldu',
                'confession': response_serializer.data
            },
            status=status.HTTP_201_CREATED
        )

    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve a specific confession with privacy checks
        """
        try:
            instance = ConfessionModel.objects.get(pk=kwargs['pk'], is_active=True)
            
            # Apply privacy filters
            filtered_queryset = self._apply_privacy_filters(ConfessionModel.objects.filter(pk=instance.pk))
            if not filtered_queryset.exists():
                return Response(
                    {"detail": "Bu itiraf görüntülenemiyor (gizlilik/engelleme ayarları)."},
                    status=status.HTTP_403_FORBIDDEN
                )
                
            # Check object permissions
            self.check_object_permissions(request, instance)
            
            serializer = self.get_serializer(instance)
            return Response(serializer.data)
            
        except ConfessionModel.DoesNotExist:
            return Response(
                {"detail": "İtiraf bulunamadı."},
                status=status.HTTP_404_NOT_FOUND
            )

    def update(self, request, *args, **kwargs):
        """
        Update confession - only content and privacy can be updated
        """
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        # Only allow certain fields to be updated
        allowed_fields = ['content', 'is_privacy']
        filtered_data = {k: v for k, v in request.data.items() if k in allowed_fields}
        
        serializer = self.get_serializer(instance, data=filtered_data, partial=partial)
        serializer.is_valid(raise_exception=True)
        
        confession = serializer.save()
        
        return Response(
            {
                'success': True,
                'message': 'İtiraf başarıyla güncellendi',
                'confession': serializer.data
            }
        )

    def destroy(self, request, *args, **kwargs):
        """
        Soft delete confession (set is_active=False)
        """
        instance = self.get_object()
        instance.is_active = False
        instance.save()
        
        return Response(
            {
                'success': True,
                'message': 'İtiraf başarıyla silindi'
            },
            status=status.HTTP_204_NO_CONTENT
        )

    @action(detail=False, methods=['get'])
    def trending(self, request):
        """
        Get trending confessions (most liked in last 24 hours)
        """
        last_24h = timezone.now() - timedelta(hours=24)
        
        trending_confessions = self.get_queryset().filter(
            created_at__gte=last_24h
        ).annotate(
            like_count=Count('likes')
        ).order_by('-like_count')[:20]
        
        serializer = self.get_serializer(trending_confessions, many=True)
        return Response({
            'message': 'Trend itiraflar',
            'confessions': serializer.data
        })

    @action(detail=False, methods=['get'])
    def by_category(self, request):
        """
        Get confessions filtered by category
        """
        category_id = request.query_params.get('category_id')
        if not category_id:
            return Response(
                {"detail": "category_id parametresi gerekli"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        category = get_object_or_404(ConfessionCategory, id=category_id)
        confessions = self.get_queryset().filter(category=category)
        
        page = self.paginate_queryset(confessions)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(confessions, many=True)
        return Response({
            'category': ConfessionCategorySerializer(category).data,
            'confessions': serializer.data
        })

    @action(detail=False, methods=['get'])
    def by_university(self, request):
        """
        Get confessions filtered by university
        """
        university_id = request.query_params.get('university_id')
        if not university_id:
            return Response(
                {"detail": "university_id parametresi gerekli"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        university = get_object_or_404(University, id=university_id)
        confessions = self.get_queryset().filter(university=university)
        
        page = self.paginate_queryset(confessions)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(confessions, many=True)
        return Response({
            'university': UniversitySerializer(university).data,
            'confessions': serializer.data
        })

    @action(detail=False, methods=['get'])
    def my_confessions(self, request):
        """
        Get current user's confessions
        """
        confessions = ConfessionModel.objects.filter(
            user=request.user,
            is_active=True
        ).select_related('category', 'university').prefetch_related('images', 'likes', 'comments', 'bookmarks').order_by('-created_at')
        
        # Check if the requested page exists
        try:
            page = self.paginate_queryset(confessions)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)
        except Exception:
            # If pagination fails (e.g., page out of range), return empty result
            return Response({
                'results': [],
                'count': confessions.count(),
                'next': None,
                'previous': None,
                'message': 'Benim itiraflarım'
            })
        
        # If no pagination is used, return all results
        serializer = self.get_serializer(confessions, many=True)
        return Response({
            'results': serializer.data,
            'count': confessions.count(),
            'next': None,
            'previous': None,
            'message': 'Benim itiraflarım'
        })

    @action(detail=False, methods=['get'])
    def user_confessions(self, request):
        """
        Get confessions by specific user (only non-private confessions for other users)
        """
        username = request.query_params.get('username')
        if not username:
            return Response(
                {"detail": "username parametresi gerekli"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from django.contrib.auth.models import User
            target_user = User.objects.get(username=username)
        except User.DoesNotExist:
            return Response(
                {"detail": "Kullanıcı bulunamadı"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Start with active confessions from target user
        confessions = ConfessionModel.objects.filter(
            user=target_user,
            is_active=True
        ).select_related('category', 'university').prefetch_related('images', 'likes', 'comments', 'bookmarks')
        
        # If viewing other user's confessions, only show non-private ones
        if target_user != request.user:
            confessions = confessions.filter(is_privacy=False)
            
            # Additional privacy checks for other users
            try:
                target_profile = Profile.objects.get(user=target_user)
                current_profile = Profile.objects.get(user=request.user)
                
                # Check if target user has private profile and current user doesn't follow them
                if target_profile.is_private:
                    is_following = current_profile.following.filter(user=target_user).exists()
                    if not is_following:
                        return Response({
                            'results': [],
                            'count': 0,
                            'next': None,
                            'previous': None,
                            'message': 'Bu kullanıcının profili gizli.'
                        })
                
                # Check if users blocked each other
                is_blocked = current_profile.blocked.filter(user=target_user).exists()
                is_blocked_by = target_profile.blocked.filter(user=request.user).exists()
                
                if is_blocked or is_blocked_by:
                    return Response({
                        'results': [],
                        'count': 0,
                        'next': None,
                        'previous': None,
                        'message': 'Bu kullanıcının itirafları görüntülenemiyor.'
                    })
                    
            except Profile.DoesNotExist:
                pass
        
        # Apply general privacy filters
        confessions = self._apply_privacy_filters(confessions)
        
        # Order by created_at for consistent pagination
        confessions = confessions.order_by('-created_at')
        
        # Check if the requested page exists
        try:
            page = self.paginate_queryset(confessions)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)
        except Exception:
            # If pagination fails (e.g., page out of range), return empty result
            return Response({
                'results': [],
                'count': confessions.count(),
                'next': None,
                'previous': None,
                'message': f'{target_user.username} kullanıcısının itirafları'
            })
        
        # If no pagination is used, return all results
        serializer = self.get_serializer(confessions, many=True)
        return Response({
            'results': serializer.data,
            'count': confessions.count(),
            'next': None,
            'previous': None,
            'message': f'{target_user.username} kullanıcısının itirafları'
        })

    @action(detail=False, methods=['get'])
    def anonymous(self, request):
        """
        Get only anonymous confessions
        """
        confessions = self.get_queryset().filter(is_privacy=True)
        
        page = self.paginate_queryset(confessions)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(confessions, many=True)
        return Response({
            'message': 'Anonim itiraflar',
            'confessions': serializer.data
        })

    @action(detail=False, methods=['get'])
    def open(self, request):
        """
        Get only open (non-anonymous) confessions
        """
        confessions = self.get_queryset().filter(is_privacy=False)
        
        page = self.paginate_queryset(confessions)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(confessions, many=True)
        return Response({
            'message': 'Açık itiraflar',
            'confessions': serializer.data
        })

    @action(detail=True, methods=['post'])
    def toggle_privacy(self, request, pk=None):
        """
        Toggle confession privacy (anonymous/open)
        """
        confession = self.get_object()
        confession.is_privacy = not confession.is_privacy
        confession.save()
        
        privacy_type = 'anonim' if confession.is_privacy else 'açık'
        
        return Response({
            'success': True,
            'message': f'İtiraf {privacy_type} olarak ayarlandı',
            'is_privacy': confession.is_privacy,
            'privacy_type': 'anonymous' if confession.is_privacy else 'open'
        })

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        Get confession statistics
        """
        total_confessions = self.get_queryset().count()
        anonymous_confessions = self.get_queryset().filter(is_privacy=True).count()
        open_confessions = self.get_queryset().filter(is_privacy=False).count()
        
        # Most active categories
        popular_categories = ConfessionCategory.objects.annotate(
            confession_count=Count('confessions', filter=Q(confessions__is_active=True))
        ).filter(confession_count__gt=0).order_by('-confession_count')[:5]
        
        return Response({
            'total_confessions': total_confessions,
            'anonymous_confessions': anonymous_confessions,
            'open_confessions': open_confessions,
            'popular_categories': ConfessionCategorySerializer(popular_categories, many=True).data
        })


class FilterOptionsAPIView(APIView):
    """
    API endpoint to get filter options for confessions
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, *args, **kwargs):
        # Categories with active confessions
        categories = ConfessionCategory.objects.all()
        
        # All universities (not just those with confessions)
        universities = University.objects.all().order_by('name')
        
        # Sort options
        sort_options = [
            {'value': '-created_at', 'label': 'En Yeni'},
            {'value': 'created_at', 'label': 'En Eski'},
            {'value': '-like_count', 'label': 'En Beğenilen'},
            {'value': '-comment_count', 'label': 'En Çok Yorumlanan'},
        ]
        
        return Response({
            'categories': ConfessionCategorySerializer(categories, many=True).data,
            'universities': UniversitySerializer(universities, many=True).data,
            'sort_options': sort_options,
            'privacy_options': [
                {'value': 'all', 'label': 'Tümü'},
                {'value': 'anonymous', 'label': 'Anonim'},
                {'value': 'open', 'label': 'Açık'},
            ]
        })


class ConfessionFilterPreferencesViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing user confession filter preferences
    """
    serializer_class = ConfessionFilterSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return ConfessionFilter.objects.filter(user=self.request.user)
    
    def get_object(self):
        """Get or create filter preferences for current user"""
        filter_prefs, created = ConfessionFilter.objects.get_or_create(user=self.request.user)
        return filter_prefs
    
    def list(self, request, *args, **kwargs):
        """Return current user's filter preferences"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    def create(self, request, *args, **kwargs):
        """Create or update filter preferences"""
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response({
            'success': True,
            'message': 'Filtre tercihleri kaydedildi',
            'preferences': serializer.data
        })
    
    def update(self, request, *args, **kwargs):
        """Update filter preferences"""
        return self.create(request, *args, **kwargs)
    
    @action(detail=False, methods=['post'])
    def clear(self, request):
        """Clear all filter preferences"""
        try:
            filter_prefs = self.get_object()
            filter_prefs.category = None
            filter_prefs.university = None
            filter_prefs.sort_by = None
            filter_prefs.save()
            
            return Response({
                'success': True,
                'message': 'Filtre tercihleri temizlendi'
            })
        except Exception as e:
            return Response(
                {'error': f'Tercihler temizlenirken hata: {str(e)}'}, 
                status=status.HTTP_400_BAD_REQUEST
            )


class ConfessionCategoryListView(generics.ListAPIView):
    """
    API endpoint for listing confession categories
    """
    serializer_class = ConfessionCategorySerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return ConfessionCategory.objects.annotate(
            total_confessions=Count('confessions'),
            active_confessions=Count('confessions', filter=Q(confessions__is_active=True))
        ).order_by('name')


class PopularCategoriesView(generics.ListAPIView):
    """
    API endpoint for getting popular confession categories
    """
    serializer_class = ConfessionCategorySerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return ConfessionCategory.objects.annotate(
            total_confessions=Count('confessions'),
            active_confessions=Count('confessions', filter=Q(confessions__is_active=True))
        ).filter(active_confessions__gt=0).order_by('-active_confessions')[:10]
