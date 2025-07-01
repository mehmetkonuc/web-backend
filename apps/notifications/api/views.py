from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from apps.notifications.models import Notification, NotificationType
from .serializers import NotificationSerializer, NotificationTypeSerializer
from apps.notifications.services import NotificationService
from rest_framework.exceptions import NotFound


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """Viewset for handling notification operations"""
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Return notifications belonging to the current user"""
        user = self.request.user
        return Notification.objects.filter(recipient=user).order_by('-created_at')
    def list(self, request, *args, **kwargs):
        """Return paginated list of notifications with optional filtering"""
        queryset = self.get_queryset()
        
        # Apply filters if present
        notification_type = request.query_params.get('type')
        notification_types = request.query_params.getlist('types')  # Support for multiple types
        is_read = request.query_params.get('is_read')
        
        if notification_type:
            queryset = queryset.filter(notification_type__code=notification_type)
        elif notification_types:
            # Filter by multiple notification types
            queryset = queryset.filter(notification_type__code__in=notification_types)
        
        if is_read is not None:
            is_read_bool = is_read.lower() == 'true'
            queryset = queryset.filter(is_read=is_read_bool)
        
        # Sayfa numarası kontrolü
        page_num = request.query_params.get('page', 1)
        try:
            page_num = int(page_num)
        except (TypeError, ValueError):
            page_num = 1
            
        try:
            page = self.paginate_queryset(queryset)
        except NotFound:
            # Sayfa yoksa boş sonuç dön
            return Response({'results': [], 'count': 0, 'next': None, 'previous': None})
        if page is not None:
            serializer = self.get_serializer(page, many=True)


            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)

        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        """Mark a single notification as read"""
        try:
            notification = self.get_object()
            notification.mark_as_read()
            serializer = self.get_serializer(notification)
            return Response(serializer.data)
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['post'])
    def mark_all_as_read(self, request):
        """Mark all unread notifications as read"""
        try:
            count = NotificationService.mark_all_as_read(request.user)
            return Response({
                "success": True,
                "count": count,
                "message": f"{count} notifications marked as read."
            })
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """Get count of unread notifications"""
        count = Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).count()
        
        return Response({"count": count})
    
    @action(detail=False, methods=['get'])
    def recent(self, request):
        """Get recent notifications (last 5)"""
        notifications = Notification.objects.filter(
            recipient=request.user
        ).order_by('-created_at')[:5]
        
        serializer = self.get_serializer(notifications, many=True)
        return Response(serializer.data)


class NotificationTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """Viewset for querying notification types"""
    queryset = NotificationType.objects.all()
    serializer_class = NotificationTypeSerializer
    permission_classes = [permissions.IsAuthenticated]