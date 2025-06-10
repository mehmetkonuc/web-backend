from django.views import View
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import get_user_model
from django.db.models import Q, Max, OuterRef, Subquery
from django.http import JsonResponse
from django.utils import timezone
import json

from .models import ChatRoom, Message, ChatRoomDeletion, MessageAttachment
from .utils import can_message_user

User = get_user_model()

class ChatView(LoginRequiredMixin, View):
    """
    Main chat view displaying the chat interface with user's chat rooms
    """
    def get(self, request):
        user = request.user
        
        # Get the latest message for each chat room using subquery
        latest_message_subquery = Message.objects.filter(
            chat_room=OuterRef('pk')
        ).order_by('-timestamp').values('timestamp')[:1]

        # Get all active chat rooms for the user
        chat_rooms = ChatRoom.get_active_rooms_for_user(user).annotate(
            last_message_time=Subquery(latest_message_subquery)
        ).order_by('-last_message_time')
        
        
        # Process chat rooms to get data for rendering
        chat_data = []
        for room in chat_rooms:
            # Get the other participant
            other_user = room.participants.exclude(id=user.id).first()
            
            if not other_user:
                continue
                  # Get the last message
            last_message = room.get_last_message()
            
            # Get unread count for this room
            unread_count = room.get_unread_count(user)
            
            # Get user avatar URL
            avatar_url = None
            if hasattr(other_user, 'profile') and other_user.profile.avatar:
                avatar_url = other_user.profile.avatar.url
                
            # Prepare data for template
            chat_data.append({
                'id': room.id,
                'other_user': {
                    'id': other_user.id,
                    'username': other_user.username,
                    'first_name': other_user.first_name,
                    'last_name': other_user.last_name,
                    'full_name': f"{other_user.first_name} {other_user.last_name}".strip() or other_user.username,
                    'avatar': avatar_url,
                },
                'last_message': {
                    'text': last_message.text if last_message else None,
                    'timestamp': last_message.timestamp if last_message else None,
                    'is_mine': last_message.sender == user if last_message else False,
                },
                'unread_count': unread_count,
            })
        
        return render(request, 'chat/chat.html', {'chat_rooms': chat_data, 'page_title': 'Sohbetlerim'})


class ChatDetailView(LoginRequiredMixin, View):
    """
    View for displaying a specific chat room with its messages
    """
    def get(self, request, chat_room_id):
        user = request.user
        chat_room = get_object_or_404(ChatRoom, id=chat_room_id, participants=user)
        
        # Mark all messages as read
        chat_room.mark_messages_as_read(user)
        
        # Get the other participant
        other_user = chat_room.participants.exclude(id=user.id).first()
        
        # Mesaj gizlilik kontrolü
        can_message = True
        message_status = {
            'can_message': True,
            'message': None,
            'reason': None
        }
        
        if other_user:
            can_message, reason = can_message_user(user, other_user)
            message_status = {
                'can_message': can_message,
                'message': reason,
                'reason': None
            }
            
            # Reason detaylarını belirle
            if not can_message:
                if 'engellemiş' in reason:
                    message_status['reason'] = 'blocked'
                elif 'takipçilerinden mesaj' in reason:
                    message_status['reason'] = 'followers_only'
                elif 'hiç kimseden mesaj' in reason or 'mesaj almayı tercih etmiyor' in reason:
                    message_status['reason'] = 'no_messages'
                else:
                    message_status['reason'] = 'other'
                      # Check for deletion record
        deletion_record = ChatRoomDeletion.objects.filter(
            chat_room=chat_room,
            user=user
        ).order_by('-deleted_at').first()
        
        # Get messages, filtered by deletion, limited to last 20
        if deletion_record:
            messages = chat_room.messages.filter(timestamp__gt=deletion_record.deleted_at).order_by('-timestamp')[:20]
        else:
            messages = chat_room.messages.all().order_by('-timestamp')[:20]
        
        # Convert to list and reverse to get chronological order (oldest first)
        messages = list(messages)
        messages.reverse()
        
        # Get user avatar URL
        avatar_url = None
        if hasattr(other_user, 'profile') and other_user.profile.avatar:
            avatar_url = other_user.profile.avatar.url
        
        # User information for the template
        other_user_data = {
            'id': other_user.id,
            'username': other_user.username,
            'first_name': other_user.first_name,
            'last_name': other_user.last_name,
            'full_name': f"{other_user.first_name} {other_user.last_name}".strip() or other_user.username,
            'avatar': avatar_url,
            'university': other_user.profile.university if hasattr(other_user, 'profile') else None,
            'is_verified': other_user.profile.is_verified if hasattr(other_user, 'profile') else None,
        }
          # Get chat rooms for sidebar just like in the main chat view
        latest_message_subquery = Message.objects.filter(
            chat_room=OuterRef('pk')
        ).order_by('-timestamp').values('timestamp')[:1]
        
        # Get all active chat rooms for the user
        chat_rooms = ChatRoom.get_active_rooms_for_user(user).annotate(
            last_message_time=Subquery(latest_message_subquery)
        ).order_by('-last_message_time')
        
        # Process chat rooms for sidebar
        chat_data = []
        for room in chat_rooms:
            room_other_user = room.participants.exclude(id=user.id).first()
            
            if not room_other_user:
                continue
                
            room_last_message = room.get_last_message()
            room_unread_count = room.get_unread_count(user)
            
            room_avatar_url = None
            if hasattr(room_other_user, 'profile') and room_other_user.profile.avatar:
                room_avatar_url = room_other_user.profile.avatar.url
                
            chat_data.append({
                'id': room.id,
                'other_user': {
                    'id': room_other_user.id,
                    'username': room_other_user.username,
                    'first_name': room_other_user.first_name,
                    'last_name': room_other_user.last_name,
                    'full_name': f"{room_other_user.first_name} {room_other_user.last_name}".strip() or room_other_user.username,
                    'avatar': room_avatar_url,
                },
                'last_message': {
                    'text': room_last_message.text if room_last_message else None,
                    'timestamp': room_last_message.timestamp if room_last_message else None,
                    'is_mine': room_last_message.sender == user if room_last_message else False,
                },
                'unread_count': room_unread_count,
            })
          # Return to chat list view with active chat room and all chat rooms for sidebar
        return render(request, 'chat/chat.html', {
            'active_chat_room': {
                'id': chat_room.id,
                'other_user': other_user_data,
                'message_status': message_status,  # Mesaj gizlilik durumunu ekle
            },
            'messages': messages,
            'chat_rooms': chat_data,
            'page_title': f"Sohbet - {other_user_data['full_name']}",
        })
    

class MessageListView(LoginRequiredMixin, View):
    """
    API endpoint for fetching messages for a specific chat room
    Supports pagination for infinite scroll and can fetch older messages
    """
    def get(self, request, chat_room_id):
        user = request.user
        chat_room = get_object_or_404(ChatRoom, id=chat_room_id, participants=user)
        
        # Get pagination parameters
        page_size = int(request.GET.get('page_size', 20))  # Default to 20 messages per page
        before_id = request.GET.get('before_id')  # For pagination, get messages before this ID
        
        # Check for deletion record first
        deletion_record = ChatRoomDeletion.objects.filter(
            chat_room=chat_room,
            user=user
        ).order_by('-deleted_at').first()
        
        # If we have a deletion record, filter out messages before deletion
        if deletion_record:
            messages_query = chat_room.messages.filter(timestamp__gt=deletion_record.deleted_at)
        else:
            messages_query = chat_room.messages.all()
        
        # For pagination - if we have a before_id, get messages before that ID
        if before_id:
            try:
                before_message = Message.objects.get(id=before_id)
                messages_query = messages_query.filter(timestamp__lt=before_message.timestamp)
            except (Message.DoesNotExist, ValueError):
                pass
                
        # Order by timestamp descending to get most recent first, then reverse for display
        messages_query = messages_query.order_by('-timestamp')[:page_size]
        
        # Convert to list so we can reverse the order for display (oldest first)
        messages_list = list(messages_query)
        messages_list.reverse()          # Process messages for JSON response
        messages_data = []
        for message in messages_list:
            sender = message.sender
            avatar_url = None
            
            if hasattr(sender, 'profile') and sender.profile.avatar:
                avatar_url = sender.profile.avatar.url
                
            # Get message attachments
            attachments = []
            for attachment in message.attachments.all():
                if attachment.file_type.startswith('image/'):
                    attachments.append({
                        'id': attachment.id,
                        'url': attachment.file.url,
                        'type': attachment.file_type
                    })
                
            messages_data.append({
                'id': message.id,
                'text': message.text,
                'timestamp': message.timestamp.isoformat(),
                'formatted_time': message.timestamp.strftime('%H:%M'),
                'is_mine': message.sender == user,
                'sender': {
                    'id': sender.id,
                    'username': sender.username,
                    'avatar': avatar_url,
                },
                'attachments': attachments
            })
        
        # Add pagination info
        has_more = len(messages_list) == page_size
        oldest_message_id = messages_list[0].id if messages_list else None
        
        # Mark messages as read
        chat_room.mark_messages_as_read(user)
        
        return JsonResponse({
            'messages': messages_data,
            'pagination': {
                'has_more': has_more,
                'oldest_message_id': oldest_message_id
            }
        })


class ChatDeleteView(LoginRequiredMixin, View):
    """
    View for deleting a chat for the current user
    """
    def post(self, request, chat_room_id):
        user = request.user
        chat_room = get_object_or_404(ChatRoom, id=chat_room_id, participants=user)
        
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
            
            return JsonResponse({'status': 'Chat permanently deleted'})
        
        return JsonResponse({'status': 'Chat deleted for you'})


class UserSearchView(LoginRequiredMixin, View):
    def get(self, request):
        query = request.GET.get('q', '')
        if not query or len(query) < 2:
            return JsonResponse({'users': []})
            
        # Get users that match the search query, initially excluding current user
        users = User.objects.filter(
            Q(username__icontains=query) | 
            Q(first_name__icontains=query) | 
            Q(last_name__icontains=query)
        ).exclude(id=request.user.id)
        
        # Filter out blocked users and apply message privacy settings
        filtered_users = []
        
        try:
            # Get current user's profile
            current_user = request.user
            
            # Safely process users with proper error handling
            for user in users:
                try:
                    # Kullanıcı gizlilik kontrolü
                    can_message, _ = can_message_user(current_user, user)
                    if not can_message:
                        continue
                    
                    # Kullanıcıyı ekle
                    filtered_users.append(user)
                except Exception as e:
                    # On error for a specific user, include them anyway
                    print(f"Error checking privacy status for user {user.username}: {e}")
                    filtered_users.append(user)
        except Exception as e:
            # If there's a general error, just return all matched users
            print(f"Error in privacy filtering: {e}")
            filtered_users = list(users)
        
        # Limit to 10 users
        filtered_users = filtered_users[:10]
        
        # Prepare user data for response
        users_data = []
        for user in filtered_users:
            user_data = {
                'id': user.id,
                'username': user.username,
                'full_name': f"{user.first_name} {user.last_name}".strip() or user.username,
                'avatar': None
            }
            
            # Try to add avatar if available
            try:
                if hasattr(user, 'profile') and user.profile.avatar:
                    user_data['avatar'] = user.profile.avatar.url
            except Exception:
                pass
                
            users_data.append(user_data)
        
        return JsonResponse({'users': users_data})


class ChatRoomCreateView(LoginRequiredMixin, View):
    def post(self, request):
        try:
            data = json.loads(request.body)
            user_id = data.get('user_id')
            
            if not user_id:
                return JsonResponse({'error': 'User ID is required'}, status=400)
                
            other_user = get_object_or_404(User, id=user_id)
            
            # Mesaj gizlilik kontrolü
            can_message, reason = can_message_user(request.user, other_user)
            if not can_message:
                return JsonResponse({
                    'error': reason,
                    'privacy_error': True
                }, status=403)
            
            # Check if chat room already exists
            # Find chat rooms where both users are participants
            chat_rooms = ChatRoom.objects.filter(participants=request.user) \
                .filter(participants=other_user)
            
            if chat_rooms.exists():
                # Use existing chat room
                chat_room = chat_rooms.first()
                
                # Important: We do NOT remove from deleted_by list here
                # We also do NOT delete ChatRoomDeletion records
                # This ensures old messages remain hidden when recreating a chat room
                # The messages will only become visible when the user sends a new message
                # This matches the behavior in the React Native app
            else:
                # Create new chat room
                chat_room = ChatRoom.objects.create()
                chat_room.participants.add(request.user, other_user)
                
            return JsonResponse({
                'id': chat_room.id,
                'status': 'success'
            })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


@login_required
def upload_attachments(request):
    """
    Resim dosyalarını yükler ve bir mesaja ekler
    """
    if request.method == 'POST':
        chat_room_id = request.POST.get('chat_room_id')
        message_text = request.POST.get('message', '')
        
        try:
            # Sohbet odasını kontrol et
            room = ChatRoom.objects.get(id=chat_room_id, participants=request.user)
            
            # Yeni mesaj oluştur
            message = Message.objects.create(
                chat_room=room,
                sender=request.user,
                text=message_text,
                is_read=False
            )
            
            # Dosyaları işle
            files = []
            for key, file in request.FILES.items():
                if key.startswith('image_'):
                    attachment = MessageAttachment.objects.create(
                        message=message,
                        file=file,
                        file_type=file.content_type
                    )
                    files.append({
                        'id': attachment.id,
                        'url': attachment.file.url,
                        'file_type': attachment.file_type
                    })
            
            # Chat room'u aktif olarak işaretle (ilk mesaj gönderildiğinde)
            room.activate()
            
            return JsonResponse({
                'success': True,
                'message_id': message.id,
                'files': files
            })
            
        except ChatRoom.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Sohbet odası bulunamadı'
            }, status=404)
            
    return JsonResponse({
        'success': False,
        'error': 'Geçersiz istek'
    }, status=400)