from rest_framework import viewsets, generics, status, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
from django.contrib.auth.models import User

from apps.profiles.models import Profile
from apps.dataset.models import University, Department, GraduationStatus
from ..models import UserMemberFilter
from .serializers import (
    MemberListSerializer,
    UniversitySerializer,
    DepartmentSerializer,
    GraduationStatusSerializer,
    UserMemberFilterSerializer
)


class MemberListAPIView(generics.ListAPIView):
    """
    API endpoint for listing and filtering members
    """
    serializer_class = MemberListSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['university', 'department', 'graduation_status', 'is_verified']
    search_fields = ['user__username', 'user__first_name', 'user__last_name', 'bio']
    
    def get_queryset(self):
        # Sadece aktif kullanıcıların profillerini çek
        queryset = Profile.objects.filter(user__is_active=True).select_related(
            'user', 'university', 'department', 'graduation_status'
        )
        
        # Engellediğim ve beni engelleyen kullanıcıları filtreleme (düzeltilmiş)
        try:
            if self.request.user.is_authenticated:
                user_profile = self.request.user.profile
                
                # Benim engellediğim kullanıcıları filtrele (Daha verimli sorgu)
                blocked_users_ids = user_profile.blocked.values_list('user_id', flat=True)
                queryset = queryset.exclude(user_id__in=blocked_users_ids)
                
                # Beni engelleyen kullanıcıları filtrele (Daha verimli sorgu)
                blocked_by_users_ids = Profile.objects.filter(
                    blocked=user_profile
                ).values_list('user_id', flat=True)
                queryset = queryset.exclude(user_id__in=blocked_by_users_ids).exclude(user_id=self.request.user.id)
                
                # Distinct kullanarak olası duplikasyonları önle
                queryset = queryset.distinct()
                
        except Profile.DoesNotExist:
            pass
        
        # URL parametrelerinden filtreleme
        first_name = self.request.query_params.get('first_name')
        last_name = self.request.query_params.get('last_name')
        name = self.request.query_params.get('name')
        
        if first_name:
            queryset = queryset.filter(user__first_name__icontains=first_name)
        
        if last_name:
            queryset = queryset.filter(user__last_name__icontains=last_name)
        
        if name:
            # Ad ve soyad birleşik arama
            parts = name.split()
            if len(parts) == 1:
                # Tek kelime girildiyse hem ad hem soyad içinde ara
                queryset = queryset.filter(
                    Q(user__first_name__icontains=parts[0]) | 
                    Q(user__last_name__icontains=parts[0])
                )
            else:
                # İlk kelime ad, diğer kelimeler soyad olarak düşün
                first_name = parts[0]
                last_name = ' '.join(parts[1:])
                queryset = queryset.filter(
                    Q(user__first_name__icontains=first_name) & 
                    Q(user__last_name__icontains=last_name)
                )
        
        return queryset
    
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        
        # Optimize pagination for mobile
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
            
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class FilterOptionsAPIView(APIView):
    """
    API endpoint to get filter options for members (universities, departments, graduation statuses)
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, *args, **kwargs):
        universities = University.objects.all()
        departments = Department.objects.all()
        graduation_statuses = GraduationStatus.objects.all()
        
        # Serialize each dataset
        university_serializer = UniversitySerializer(universities, many=True)
        department_serializer = DepartmentSerializer(departments, many=True)
        graduation_status_serializer = GraduationStatusSerializer(graduation_statuses, many=True)
        
        return Response({
            'universities': university_serializer.data,
            'departments': department_serializer.data,
            'graduation_statuses': graduation_status_serializer.data,
        })


class UserFilterPreferencesViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing user member filter preferences
    """
    serializer_class = UserMemberFilterSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return UserMemberFilter.objects.filter(user=self.request.user)
    
    def get_object(self):
        # Get or create filter preferences for current user
        filter_prefs, created = UserMemberFilter.objects.get_or_create(user=self.request.user)
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
            filter_prefs.university = None
            filter_prefs.department = None
            filter_prefs.graduation_status = None
            filter_prefs.is_verified = None
            filter_prefs.save()
            return Response({"detail": "Filter preferences cleared successfully"})
        except Exception as e:
            return Response({"detail": f"Error clearing preferences: {str(e)}"}, 
                           status=status.HTTP_400_BAD_REQUEST)