from rest_framework import serializers
from django.contrib.auth import get_user_model
from apps.chat.models import ChatRoom, Message, MessageAttachment

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    """User serializer for displaying chat participants"""
    avatar = serializers.SerializerMethodField()
    isVerified = serializers.SerializerMethodField()
    fullName = serializers.SerializerMethodField()
    university = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'fullName', 'avatar', 'isVerified', 'university']
    def get_avatar(self, obj):
        """Get user avatar URL if exists"""
        try:
            if hasattr(obj, 'profile') and obj.profile.avatar:
                request = self.context.get('request')
                if request:
                    return request.build_absolute_uri(obj.profile.avatar.url)
                return obj.profile.avatar.url
            return None
        except:
            return None
    
    def get_isVerified(self, obj):
        """Check if user is verified"""
        try:
            if hasattr(obj, 'profile'):
                return obj.profile.is_verified
            return False
        except:
            return False
    
    def get_fullName(self, obj):
        """Get user's full name"""
        try:
            if hasattr(obj, 'profile'):
                return f"{obj.first_name} {obj.last_name}".strip() or obj.username
            return obj.username
        except:
            return obj.username

    def get_university(self, obj):
        """Get user's university name"""
        try:
            if hasattr(obj, 'profile') and obj.profile.university:
                return obj.profile.university.name
            return None
        except:
            return None

class MessageAttachmentSerializer(serializers.ModelSerializer):
    """Serializer for message attachments (images, files)"""
    file = serializers.SerializerMethodField()
    
    class Meta:
        model = MessageAttachment
        fields = ['id', 'file', 'file_type', 'thumbnail', 'created_at']
    
    def get_file(self, obj):
        """Get full URL for the file"""
        if obj.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
            return obj.file.url
        return None


class MessageSerializer(serializers.ModelSerializer):
    """Serializer for individual messages"""
    sender = UserSerializer(read_only=True)
    attachments = MessageAttachmentSerializer(many=True, read_only=True)
    is_mine = serializers.SerializerMethodField()
    uploaded_images = serializers.ListField(
        child=serializers.ImageField(max_length=1000000, allow_empty_file=False, use_url=False),
        write_only=True,
        required=False
    )
    
    class Meta:
        model = Message
        fields = ['id', 'sender', 'text', 'timestamp', 'is_read', 'is_delivered', 'attachments', 'uploaded_images', 'is_mine']
        read_only_fields = ['is_read', 'is_delivered', 'timestamp']
    
    def get_is_mine(self, obj):
        """Check if this message belongs to the current user"""
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            return obj.sender.id == request.user.id
        return False
    
    def create(self, validated_data):
        """Create a new message with optional attachments"""
        uploaded_images = validated_data.pop('uploaded_images', [])
        message = Message.objects.create(**validated_data)
        
        # Process uploaded images
        for image in uploaded_images:
            print(image)
            attachment = MessageAttachment.objects.create(
                message=message,
                file=image
            )
        
        return message


class ChatRoomSerializer(serializers.ModelSerializer):
    """Serializer for chat rooms (conversations)"""
    participants = UserSerializer(many=True, read_only=True)
    other_participant = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread = serializers.SerializerMethodField()
    is_deleted = serializers.SerializerMethodField()
    
    class Meta:
        model = ChatRoom
        fields = ['id', 'participants', 'other_participant', 'created_at', 'updated_at', 'is_active', 'last_message', 'unread', 'is_deleted']
    
    def get_other_participant(self, obj):
        """Get the other participant (not the current user)"""
        request = self.context.get('request')
        if not request or not hasattr(request, 'user'):
            return None
            
        # Get the current user
        current_user = request.user
        
        # Find the other participant
        other_user = obj.participants.exclude(id=current_user.id).first()
        if other_user:
            return UserSerializer(other_user, context=self.context).data
        return None
    
    def get_last_message(self, obj):
        """Get the last message in the chat room"""
        last_message = obj.get_last_message()
        if last_message:
            return {
                'text': last_message.text,
                'timestamp': last_message.timestamp,
                'sender': UserSerializer(last_message.sender, context=self.context).data
            }
        return None
    def get_unread(self, obj):
        """Get count of unread messages for the current user"""
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            return obj.get_unread_count(request.user)
        return 0
        
    def get_is_deleted(self, obj):
        """Check if the chat room is deleted for the current user"""
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            return obj.deleted_by.filter(id=request.user.id).exists()
        return False
