from rest_framework import viewsets, permissions, status, filters
from rest_framework.response import Response
from rest_framework.decorators import action
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import get_object_or_404

from apps.comment.models import Comment
from .serializers import CommentSerializer


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


class CommentViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing comments on any content type
    """
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']

    def get_queryset(self):
        """
        This view should return all comments for the authenticated user,
        or filtered by content type and object id
        """
        queryset = Comment.objects.filter(is_active=True)
        
        # Filter by content type and object if provided in query params
        content_type_id = self.request.query_params.get('content_type_id')
        object_id = self.request.query_params.get('object_id')
        
        if content_type_id and object_id:
            try:
                content_type = ContentType.objects.get(pk=content_type_id)
                # Only return parent comments (top-level) as we'll get replies through serializer
                queryset = queryset.filter(
                    content_type=content_type,
                    object_id=object_id,
                    parent=None
                )
            except ContentType.DoesNotExist:
                queryset = Comment.objects.none()
        
        return queryset

    def perform_create(self, serializer):
        """
        Set the user when creating a comment
        """
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['get'])
    def my_comments(self, request):
        """
        Get all comments made by the current user
        """
        comments = Comment.objects.filter(user=request.user, is_active=True)
        page = self.paginate_queryset(comments)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(comments, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def for_content(self, request):
        """
        Get comments for a specific content type and object id
        """
        content_type_id = request.query_params.get('content_type_id')
        object_id = request.query_params.get('object_id')
        
        if not content_type_id or not object_id:
            return Response(
                {"detail": "Both content_type_id and object_id parameters are required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            content_type = ContentType.objects.get(pk=content_type_id)
            # Get the content object to check if it exists
            model_class = content_type.model_class()
            content_object = model_class.objects.get(pk=object_id)
            
            # Check if the content is from a private profile that the user can't access
            if hasattr(content_object, 'user') and hasattr(content_object.user, 'profile'):
                if content_object.user.profile.is_private and content_object.user != request.user:
                    from apps.profiles.models import Profile
                    try:
                        user_profile = Profile.objects.get(user=request.user)
                        if content_object.user not in [user.user for user in user_profile.following.all()]:
                            return Response(
                                {"detail": "You cannot view comments on this content because the user's profile is private."},
                                status=status.HTTP_403_FORBIDDEN
                            )
                    except Profile.DoesNotExist:
                        return Response(
                            {"detail": "You cannot view comments on this content because the user's profile is private."},
                            status=status.HTTP_403_FORBIDDEN
                        )
            
            # Get only parent comments (top-level), we'll get replies through serializer
            comments = Comment.objects.filter(
                content_type=content_type,
                object_id=object_id,
                parent=None,
                is_active=True
            ).order_by('-created_at')
            
            page = self.paginate_queryset(comments)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)
                
            serializer = self.get_serializer(comments, many=True)
            return Response(serializer.data)
            
        except ContentType.DoesNotExist:
            return Response(
                {"detail": f"Content type with id {content_type_id} does not exist"},
                status=status.HTTP_404_NOT_FOUND
            )
        except model_class.DoesNotExist:
            return Response(
                {"detail": f"Object with id {object_id} does not exist for the given content type"},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['get'])
    def replies(self, request, pk=None):
        """
        Get replies for a specific comment
        """
        comment = self.get_object()
        replies = Comment.objects.filter(parent=comment, is_active=True).order_by('-created_at')
        
        page = self.paginate_queryset(replies)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(replies, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def parent_info(self, request, pk=None):
        """
        Get the content type and object ID information for a specific comment.
        This helps mobile clients to determine the correct content_type_id and object_id
        when creating replies to comments.
        """
        try:
            comment = self.get_object()
            
            # Get the content type and object ID that this comment is associated with
            data = {
                'content_type_id': comment.content_type_id,
                'object_id': comment.object_id,
                'post_id': comment.object_id,  # For backward compatibility with mobile app
                'parent_id': comment.parent_id,  # Also return parent ID if it's a reply
            }
            
            # If this is already a reply, we need the original post's info, not the parent comment's info
            if comment.parent:
                # For a reply, we must use the same content_type_id and object_id as the parent
                data['content_type_id'] = comment.parent.content_type_id
                data['object_id'] = comment.parent.object_id
                data['post_id'] = comment.parent.object_id  # For backward compatibility
            
            return Response(data)
            
        except Exception as e:
            return Response(
                {"detail": f"Error retrieving parent info: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )