"""
Chat utility functions
"""
from django.contrib.auth import get_user_model

User = get_user_model()

def can_message_user(sender, recipient):
    """
    Checks if a user can message another user based on privacy settings.
    
    Args:
        sender: The user who wants to send the message
        recipient: The user who would receive the message
        
    Returns:
        tuple: (bool, str) - (can_message, reason)
    """
    # If either user doesn't have a profile, allow messaging
    if not hasattr(sender, 'profile') or not hasattr(recipient, 'profile'):
        return True, ""
        
    # Check if users have blocked each other
    if sender.profile.is_blocked(recipient.profile):
        return False, "Bu kullanıcıyı engellediniz. Mesaj göndermek için engeli kaldırın."
        
    if sender.profile.is_blocked_by(recipient.profile):
        return False, "Bu kullanıcı sizi engellemiş. Mesaj gönderemezsiniz."
    
    # Check message privacy settings
    if not recipient.profile.can_receive_message_from(sender.profile):
        # Get privacy setting text
        privacy_setting = dict(recipient.profile.MESSAGE_PRIVACY_CHOICES).get(
            recipient.profile.message_privacy, 'Herkes'
        )
        
        if recipient.profile.message_privacy == 'none':
            reason = f"{recipient.username} hiç kimseden mesaj almayı tercih etmiyor."
        elif recipient.profile.message_privacy == 'followers':
            reason = f"{recipient.username} sadece takipçilerinden mesaj kabul ediyor."
        else:
            reason = f"{recipient.username}'in mesaj gizlilik ayarları bunu engelliyor."
            
        return False, reason
        
    return True, ""
