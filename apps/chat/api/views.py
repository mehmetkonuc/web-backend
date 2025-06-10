from rest_framework import viewsets, status, generics
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from django.db.models import Q, OuterRef, Subquery
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from django.utils import timezone
from rest_framework.pagination import PageNumberPagination
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from apps.chat.models import ChatRoom, Message, MessageAttachment, ChatRoomDeletion
from apps.chat.utils import can_message_user
from .serializers import (
    ChatRoomSerializer, 
    MessageSerializer,
    UserSerializer
)

User = get_user_model()

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20  # Her sayfada kaç mesaj olacağını belirtir
    page_size_query_param = 'page_size' # İstemcinin sayfa boyutunu değiştirmesine izin verir
    max_page_size = 100 # Maksimum sayfa boyutu

class ChatRoomViewSet(viewsets.ModelViewSet):
    """ViewSet for chat rooms (conversations)"""
    serializer_class = ChatRoomSerializer
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        """Return ChatRoomSerializer for all actions since ChatRoomDetailSerializer is removed"""
        return ChatRoomSerializer
    
    def get_queryset(self):
        """Return chat rooms for the authenticated user, excluding those marked as deleted by the user"""
        user = self.request.user
        
        if self.action == 'retrieve':
            # For retrieve, allow access to the chat room even if user deleted it
            return ChatRoom.objects.filter(
                participants=user
            ).distinct()
        
        # For list action, first get all chat rooms the user is part of
        chat_rooms = ChatRoom.objects.filter(
            participants=user,
            is_active=True
        ).distinct()
          # Exclude chat rooms marked as deleted by the user
        deleted_chat_room_ids = []
        
        for chat_room in chat_rooms:
            # Check if this chat room was deleted by the user
            if chat_room.deleted_by.filter(id=user.id).exists():
                # Get the latest deletion record using the related_name
                deletion_record = chat_room.deletion_records.filter(
                    user=user
                ).order_by('-deleted_at').first()
                
                if deletion_record:
                    # Check if there are any messages after deletion
                    has_new_messages = chat_room.messages.filter(
                        timestamp__gt=deletion_record.deleted_at
                    ).exists()
                    
                    # If no new messages after deletion, add to exclusion list
                    if not has_new_messages:
                        deleted_chat_room_ids.append(chat_room.id)
          # Return chat rooms excluding the deleted ones without new messages
        
        # Get the latest message for each chat room using subquery to order by most recent message
        latest_message_subquery = Message.objects.filter(
            chat_room=OuterRef('pk')
        ).order_by('-timestamp').values('timestamp')[:1]
        
        return chat_rooms.exclude(id__in=deleted_chat_room_ids).annotate(
            last_message_time=Subquery(latest_message_subquery)
        ).order_by('-last_message_time')
    
    def create(self, request):
        """Create a new chat room or return existing one between two users"""
        user_id = request.data.get('user_id')
        
        if not user_id:
            return Response(
                {'detail': 'User ID is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            other_user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {'detail': 'User not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # If trying to create a chat with yourself
        if request.user.id == other_user.id:
            return Response(
                {'detail': 'Cannot create a chat with yourself'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Mesaj gizlilik kontrolü
        can_message, reason = can_message_user(request.user, other_user)
        if not can_message:
            return Response(
                {'detail': reason},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get or create the chat room
        chat_room = ChatRoom.get_or_create_chat_room(request.user, other_user)
        
        # NOT removing the deletion records here
        # Let the MessageViewSet.create method handle this when the user actually sends a message
        
        serializer = self.get_serializer(chat_room)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    @action(detail=True, methods=['post'])
    def delete_for_me(self, request, pk=None):
        """Mark a chat room as deleted for the current user only"""
        chat_room = self.get_object()
        user = request.user
        
        # Check if the user is a participant in this chat room
        if user not in chat_room.participants.all():
            return Response(
                {'detail': 'You are not a participant in this chat room'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Mark as deleted for this user
        chat_room.deleted_by.add(user)
        
        # Create or update deletion record with current timestamp
        ChatRoomDeletion.objects.update_or_create(
            chat_room=chat_room,
            user=user,
            defaults={'deleted_at': timezone.now()}
        )
        
        # Check if all participants have deleted the chat
        all_participants = set(chat_room.participants.all().values_list('id', flat=True))
        deleted_by_participants = set(chat_room.deleted_by.all().values_list('id', flat=True))
        
        # If all participants have deleted the chat, delete it permanently
        if all_participants == deleted_by_participants:
            # First delete all messages to avoid foreign key constraints
            Message.objects.filter(chat_room=chat_room).delete()
            
            # Then delete the chat room itself
            chat_room.delete()
            
            return Response({'status': 'Chat permanently deleted'}, status=status.HTTP_200_OK)
        
        return Response({'status': 'Chat deleted for you'}, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        """Search for chat rooms by participant name"""
        query = request.query_params.get('q', '')
        user = request.user
        
        if not query:
            return Response(
                {'detail': 'Search query is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Search for chat rooms by participant's name or username
        # Only include chat rooms that the current user is in
        queryset = self.get_queryset().filter(
            participants__in=User.objects.filter(
                Q(username__icontains=query) | 
                Q(first_name__icontains=query) | 
                Q(last_name__icontains=query)
            ).exclude(id=user.id)
        ).distinct()
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    def retrieve(self, request, *args, **kwargs):
        """Retrieve a chat room and mark all messages as read for the requesting user"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        
        # Mark all messages as read for the requesting user
        instance.mark_messages_as_read(request.user)
        
        # Get the serialized data
        data = serializer.data
        
        # Check if the user has deleted this chat before
        deletion_record = instance.deletion_records.filter(
            user=request.user
        ).order_by('-deleted_at').first()
        
        # If there's a deletion record, check if there are any new messages
        if deletion_record:
            # Count messages after deletion
            new_messages_count = instance.messages.filter(
                timestamp__gt=deletion_record.deleted_at
            ).count()
            
            # If no new messages, clear the last_message field
            if new_messages_count == 0:
                data['last_message'] = None
        
        return Response(data)
    
    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        """Mark all messages in a chat room as read for the current user"""
        chat_room = self.get_object()
        user = request.user
        
        # Check if the user is a participant in this chat room
        if user not in chat_room.participants.all():
            return Response(
                {'detail': 'You are not a participant in this chat room'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Mark all messages as read for this user
        marked_count = chat_room.mark_messages_as_read(user)
        
        # Send WebSocket notification to update ChatContext
        # if marked_count > 0:
        channel_layer = get_channel_layer()
        personal_group_name = f'chat_personal_{user.id}'
        
        # Calculate new unread count for this room (should be 0 after marking as read)
        unread_count = 0
        
        # Send the notification asynchronously
        async_to_sync(channel_layer.group_send)(
            personal_group_name,
            {
                'type': 'messages_read_notification',
                'room_id': int(pk),
                'unread_count': unread_count,
                'message_id': None  # Not specific to a single message
            }
        )
            
        
        return Response({
            'status': 'success',
            'marked_count': marked_count,
            'message': f'{marked_count} messages marked as read'
        })

class MessageViewSet(viewsets.ModelViewSet):
    """ViewSet for managing messages within a chat room"""
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination  # Sayfalama sınıfı eklendi

    def get_queryset(self):
        """Return messages for the specific chat room, ordered by timestamp descending"""
        chat_room_pk = self.kwargs.get('chat_room_pk')
        
        # Kullanıcının silme kaydını kontrol et
        user = self.request.user
        chat_room = get_object_or_404(ChatRoom, id=chat_room_pk)
        
        deletion_record = ChatRoomDeletion.objects.filter(
            chat_room=chat_room,
            user=user
        ).order_by('-deleted_at').first()
        
        messages_query = Message.objects.filter(chat_room__id=chat_room_pk)
        
        if deletion_record:
            messages_query = messages_query.filter(timestamp__gt=deletion_record.deleted_at)
            
        # Mesajları en yeniden eskiye doğru sırala (infinite scroll için genellikle bu tercih edilir)
        return messages_query.order_by('-timestamp')
    def create(self, request, chat_room_pk=None):
        """Create a new message in the specified chat room"""
        try:
            chat_room = ChatRoom.objects.get(id=chat_room_pk)
            
            # Check if user is a participant
            if request.user not in chat_room.participants.all():
                return Response(
                    {'detail': 'You are not a participant in this chat room'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Get the other participant for blocking checks
            other_user = chat_room.participants.exclude(id=request.user.id).first()
            
            if other_user:
                # Engelleme kontrolü - gönderen kullanıcı engellendi mi?                
                # Mesaj gizlilik kontrolü (mevcut kontrol)
                can_message, reason = can_message_user(request.user, other_user)
                if not can_message:
                    return Response(
                        {'detail': reason},
                        status=status.HTTP_403_FORBIDDEN
                    )
            
            # Create the message
            serializer = self.get_serializer(data=request.data)
            if serializer.is_valid():
                message = serializer.save(
                    chat_room=chat_room,
                    sender=request.user
                )
                
                # Activate the chat room if not already active
                chat_room.activate()
                
                # If this user previously deleted the chat, remove from deleted_by
                # but keep the ChatRoomDeletion record so old messages remain hidden
                if chat_room.deleted_by.filter(id=request.user.id).exists():
                    chat_room.deleted_by.remove(request.user)
                    
                    # DO NOT delete the ChatRoomDeletion record
                    # This way, old messages will remain hidden
                
                # Update chat room's updated_at timestamp
                chat_room.save(update_fields=['updated_at'])
                
                return Response(
                    serializer.data, 
                    status=status.HTTP_201_CREATED
                )
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
            
        except ChatRoom.DoesNotExist:
            return Response(
                {'detail': 'Chat room not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class UserSearchAPIView(generics.ListAPIView):
    """
    API endpoint to search for users to start a conversation with
    """
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Search users by username, first_name, or last_name, excluding blocked users and respecting message privacy settings"""
        query = self.request.query_params.get('q', '')
        if not query:
            return User.objects.none()
            
        # Get users that match the search query, initially excluding current user
        users_query = User.objects.filter(
            ~Q(id=self.request.user.id) &  # Exclude the current user
            (Q(username__icontains=query) | 
             Q(first_name__icontains=query) | 
             Q(last_name__icontains=query))
        )
        
        # Manuel filtreleme yaklaşımı
        filtered_users = []
        current_user = self.request.user
        
        # Her bir kullanıcıyı kontrol et
        for user in users_query:
            try:
                # Mesaj gizlilik kontrolü
                can_message, _ = can_message_user(current_user, user)
                if can_message:
                    filtered_users.append(user)
            except Exception as e:
                # Hata durumunda kullanıcıyı dahil et
                print(f"Error checking privacy for user {user.username}: {e}")
                filtered_users.append(user)
          # Return the filtered users, limited to max 20 results
        return filtered_users[:20]
