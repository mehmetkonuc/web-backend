from django.db import models
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.db.models.signals import post_delete
from django.core.files.storage import default_storage
from django.dispatch import receiver

User = get_user_model()

class ChatRoom(models.Model):
    """
    Represents a chat conversation between two users.
    A ChatRoom is created when two users start messaging each other.
    """
    participants = models.ManyToManyField(
        User,
        related_name='chat_rooms',
        verbose_name=_("Participants")
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created at")
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Updated at")
    )
    is_active = models.BooleanField(
        default=False,
        verbose_name=_("Is active")
    )
    deleted_by = models.ManyToManyField(
        User,
        related_name='deleted_chat_rooms',
        verbose_name=_("Deleted by"),
        blank=True
    )

    class Meta:
        verbose_name = _("Chat Room")
        verbose_name_plural = _("Chat Rooms")
        ordering = ['-updated_at']
    
    def __str__(self):
        participants_str = ", ".join([user.username for user in self.participants.all()[:2]])
        return f"Chat between {participants_str}"
    
    def get_last_message(self):
        """Returns the last message sent in this chat room"""
        return self.messages.order_by('-timestamp').first()
    
    def get_unread_count(self, user):
        """Returns the number of unread messages for a specific user"""
        return self.messages.filter(is_read=False).exclude(sender=user).count()
    
    def mark_messages_as_read(self, user):
        """Mark all messages as read for a specific user"""
        return self.messages.filter(is_read=False).exclude(sender=user).update(is_read=True)
    
    def activate(self):
        """Activates the chat room when the first message is sent"""
        if not self.is_active:
            self.is_active = True
            self.save(update_fields=['is_active'])
    
    @classmethod
    def get_active_rooms_for_user(cls, user):
        """
        Returns only active chat rooms for a specific user.
        Excludes chat rooms that the user has deleted and that have no new messages since deletion.
        """
        # Get all active chat rooms for this user

        chat_rooms = cls.objects.filter(
            participants=user,
            is_active=True
        ).distinct()
        print(chat_rooms)
        # Exclude chat rooms marked as deleted by the user with no new messages
        deleted_chat_room_ids = []
        
        for chat_room in chat_rooms:
            # Check if this chat room was deleted by the user
            if chat_room.deleted_by.filter(id=user.id).exists():
                # Get the latest deletion record - avoid circular import
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
        return chat_rooms.exclude(id__in=deleted_chat_room_ids).order_by('-updated_at')
    @classmethod
    def get_or_create_chat_room(cls, user1, user2):
        """
        Get an existing chat room between two users or create a new one
        Returns tuple (chat_room, created) like Django's get_or_create
        """
        # Try to find an existing chat room
        chat_rooms = ChatRoom.objects.filter(participants=user1).filter(participants=user2)
        
        if chat_rooms.exists():
            return chat_rooms.first(), False
        
        # Create a new chat room if one doesn't exist
        chat_room = ChatRoom.objects.create()
        chat_room.participants.add(user1, user2)
        return chat_room, True

    @classmethod
    def cleanup_deleted_rooms(cls):
        """
        Permanently deletes chat rooms where all participants have marked them as deleted.
        This can be run as a periodic task to clean up the database.
        
        Returns:
            int: Number of chat rooms deleted
        """
        rooms_to_delete = []
        
        # Get all chat rooms
        for chat_room in cls.objects.all():
            # Get all participants and deleted_by users
            participants = set(chat_room.participants.all().values_list('id', flat=True))
            deleted_by = set(chat_room.deleted_by.all().values_list('id', flat=True))
            
            # If all participants have deleted the chat room, mark it for deletion
            if participants and participants == deleted_by:
                rooms_to_delete.append(chat_room.id)
        
        # Get count before deletion
        count = len(rooms_to_delete)
        
        # First delete messages to avoid foreign key constraints
        from apps.chat.models import Message
        Message.objects.filter(chat_room_id__in=rooms_to_delete).delete()
        
        # Then delete chat rooms
        cls.objects.filter(id__in=rooms_to_delete).delete()
        
        return count


class Message(models.Model):
    """
    Represents a message within a chat room.
    """
    chat_room = models.ForeignKey(
        ChatRoom,
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name=_("Chat Room")
    )
    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sent_messages',
        verbose_name=_("Sender")
    )
    text = models.TextField(
        verbose_name=_("Message Text"),
        blank=True,
        null=True
    )
    timestamp = models.DateTimeField(
        default=timezone.now,
        verbose_name=_("Timestamp")
    )
    is_read = models.BooleanField(
        default=False,
        verbose_name=_("Is Read")
    )
    is_delivered = models.BooleanField(
        default=False,
        verbose_name=_("Is Delivered")
    )
    
    class Meta:
        verbose_name = _("Message")
        verbose_name_plural = _("Messages")
        ordering = ['timestamp']
    
    def __str__(self):
        return f"Message from {self.sender.username} at {self.timestamp.strftime('%Y-%m-%d %H:%M')}"
    
    def mark_as_read(self):
        """Mark message as read"""
        if not self.is_read:
            self.is_read = True
            self.save(update_fields=['is_read'])
    
    def mark_as_delivered(self):
        """Mark message as delivered"""
        if not self.is_delivered:
            self.is_delivered = True
            self.save(update_fields=['is_delivered'])


class MessageAttachment(models.Model):
    """
    Represents a file or media attachment to a message.
    """
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name='attachments',
        verbose_name=_("Message")
    )
    file = models.FileField(
        upload_to='chat_attachments/%Y/%m/%d/',
        verbose_name=_("File")
    )
    file_type = models.CharField(
        max_length=50,
        verbose_name=_("File Type"),
        blank=True
    )
    thumbnail = models.ImageField(
        upload_to='chat_thumbnails/%Y/%m/%d/',
        verbose_name=_("Thumbnail"),
        blank=True,
        null=True
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created at")
    )
    
    class Meta:
        verbose_name = _("Message Attachment")
        verbose_name_plural = _("Message Attachments")
    
    def __str__(self):
        return f"Attachment for message {self.message.id}"
    
    def is_image(self):
        """Check if attachment is an image"""
        image_types = ['image/jpeg', 'image/png', 'image/gif', 'image/jpg', 'image/webp']
        return self.file_type in image_types
    
    def save(self, *args, **kwargs):
        # Try to determine file type if not provided
        if not self.file_type and self.file:
            from mimetypes import guess_type
            guessed_type = guess_type(self.file.name)[0]
            if guessed_type:
                self.file_type = guessed_type
        
        super().save(*args, **kwargs)

@receiver(post_delete, sender=MessageAttachment)
def delete_photo_file(sender, instance, **kwargs):
    if instance.file:
        if default_storage.exists(instance.file.name):
            default_storage.delete(instance.file.name)

class ChatRoomDeletion(models.Model):
    """Model to track when a user deleted a chat room"""
    chat_room = models.ForeignKey('ChatRoom', on_delete=models.CASCADE, related_name='deletion_records')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_deletions')
    deleted_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('chat_room', 'user')
        
    def __str__(self):
        return f"ChatRoom #{self.chat_room_id} deleted by {self.user.username} at {self.deleted_at}"