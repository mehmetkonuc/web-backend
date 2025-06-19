from rest_framework import viewsets, permissions, status, filters, views
from rest_framework.response import Response
from rest_framework.decorators import action, api_view, permission_classes
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import get_object_or_404

from apps.like.models import Like
from .serializers import LikeSerializer, UserSerializer


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


class LikeViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing likes on any content type
    """
    serializer_class = LikeSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['created_at']
    ordering = ['-created_at']
    http_method_names = ['get', 'post', 'delete', 'head', 'options']  # No PUT or PATCH for likes

    def get_queryset(self):
        """
        This view should return likes filtered by content type and object id
        """
        queryset = Like.objects.all()
        
        # Filter by content type and object if provided in query params
        content_type_id = self.request.query_params.get('content_type_id')
        object_id = self.request.query_params.get('object_id')
        
        if content_type_id:
            try:
                content_type = ContentType.objects.get(pk=content_type_id)
                queryset = queryset.filter(content_type=content_type)
                
                if object_id:
                    queryset = queryset.filter(object_id=object_id)
            except ContentType.DoesNotExist:
                queryset = Like.objects.none()
        
        # Filter by user if provided
        user_id = self.request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        
        return queryset

    def perform_create(self, serializer):
        """
        Set the user when creating a like
        """
        serializer.save(user=self.request.user)

    def create(self, request, *args, **kwargs):
        """
        Create a like or return existing if already liked
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Check if like already exists
        content_type_id = serializer.validated_data.get('content_type_id')
        object_id = serializer.validated_data.get('object_id')
        
        content_type = ContentType.objects.get(pk=content_type_id)
        like, created = Like.objects.get_or_create(
            content_type=content_type,
            object_id=object_id,
            user=request.user
        )
        
        if not created:
            return Response(
                {"detail": "You have already liked this content."},
                status=status.HTTP_200_OK
            )
        
        new_serializer = self.get_serializer(like)
        headers = self.get_success_headers(new_serializer.data)
        return Response(new_serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    @action(detail=False, methods=['post'])
    def toggle(self, request):
        """
        Toggle like status for an object (like if not liked, unlike if already liked)
        """
        content_type_id = request.data.get('content_type_id')
        object_id = request.data.get('object_id')
        if not content_type_id or not object_id:
            return Response(
                {"detail": "Both content_type_id and object_id are required."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            content_type = ContentType.objects.get(pk=content_type_id)
            # Verify the object exists
            model_class = content_type.model_class()
            
            # Kontrol et: model_class None olabilir
            if model_class is None:
                return Response(
                    {"detail": f"Content type with id {content_type_id} is not valid or doesn't have a model."},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            try:
                content_object = model_class.objects.get(pk=object_id)
            except model_class.DoesNotExist:
                return Response(
                    {"detail": f"Object with id {object_id} does not exist for the given content type."},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Check if the user has already liked this object
            try:
                like = Like.objects.get(
                    content_type=content_type,
                    object_id=object_id,
                    user=request.user
                )
                
                # Unlike - delete the existing like
                like.delete()
                return Response(
                    {"detail": "Like removed.", "liked": False},
                    status=status.HTTP_200_OK
                )
                
            except Like.DoesNotExist:
                # Like - create a new like

                like = Like.objects.create(
                    content_type=content_type,
                    object_id=object_id,
                    user=request.user
                )
                
                # # Try to create notification
                # try:

                #     from apps.notifications.services import NotificationService
                #     # Only send notification if the like is not from the content owner
                #     if hasattr(content_object, 'user') and content_object.user != request.user:

                #         NotificationService.create_like_notification(
                #             user=request.user,
                #             like_obj=like
                #         )
                # except (ImportError, AttributeError):
                #     pass
                
                serializer = self.get_serializer(like)
                return Response(
                    {"detail": "Like added.", "liked": True, "data": serializer.data},
                    status=status.HTTP_201_CREATED
                )
                
        except ContentType.DoesNotExist:
            return Response(
                {"detail": f"Content type with id {content_type_id} does not exist."},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['get'])
    def check(self, request):
        """
        Check if the user has liked a specific object
        """
        content_type_id = request.query_params.get('content_type_id')
        object_id = request.query_params.get('object_id')
        
        if not content_type_id or not object_id:
            return Response(
                {"detail": "Both content_type_id and object_id parameters are required."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            content_type = ContentType.objects.get(pk=content_type_id)
            # Verify the object exists
            model_class = content_type.model_class()
            content_object = model_class.objects.get(pk=object_id)
            
            # Check if the user has liked this object
            liked = Like.objects.filter(
                content_type=content_type,
                object_id=object_id,
                user=request.user
            ).exists()
            
            return Response({"liked": liked})
            
        except ContentType.DoesNotExist:
            return Response(
                {"detail": f"Content type with id {content_type_id} does not exist."},
                status=status.HTTP_404_NOT_FOUND
            )
        except model_class.DoesNotExist:
            return Response(
                {"detail": f"Object with id {object_id} does not exist for the given content type."},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['get'])
    def my_likes(self, request):
        """
        Get all likes by the current user
        """
        likes = Like.objects.filter(user=request.user)
        
        page = self.paginate_queryset(likes)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(likes, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def likers(self, request):
        """
        Get users who liked a specific object
        """
        content_type_id = request.query_params.get('content_type_id')
        object_id = request.query_params.get('object_id')
        
        if not content_type_id or not object_id:
            return Response(
                {"detail": "Both content_type_id and object_id parameters are required."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            content_type = ContentType.objects.get(pk=content_type_id)
            # Verify the object exists
            model_class = content_type.model_class()
            content_object = model_class.objects.get(pk=object_id)
            
            # Get users who liked this object
            likes = Like.objects.filter(
                content_type=content_type,
                object_id=object_id
            )
            
            users = [like.user for like in likes]
            
            page = self.paginate_queryset(users)
            if page is not None:
                serializer = UserSerializer(page, many=True, context={'request': request})
                return self.get_paginated_response(serializer.data)
            
            serializer = UserSerializer(users, many=True, context={'request': request})
            return Response(serializer.data)
            
        except ContentType.DoesNotExist:
            return Response(
                {"detail": f"Content type with id {content_type_id} does not exist."},
                status=status.HTTP_404_NOT_FOUND
            )
        except model_class.DoesNotExist:
            return Response(
                {"detail": f"Object with id {object_id} does not exist for the given content type."},
                status=status.HTTP_404_NOT_FOUND
            )


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_content_types(request):
    """
    API view to get all content types and their IDs for likes, comments, etc.
    Returns a dictionary of model names and their content type IDs.
    """
    # Önemli modelleri içeren bir liste
    important_models = {
        'post': 'apps.post.models.Post',
        'comment': 'apps.comment.models.Comment',
        # Diğer önemli modeller buraya eklenebilir
    }
    
    content_types = {}
    
    for key, model_path in important_models.items():
        try:
            app_label, model = model_path.split('models.')
            app_label = app_label.split('apps.')[1].split('.')[0]
            
            content_type = ContentType.objects.get(app_label=app_label, model=model.lower())
            content_types[key] = content_type.id
        except (ContentType.DoesNotExist, ValueError, IndexError):
            content_types[key] = None
    
    return Response(content_types)