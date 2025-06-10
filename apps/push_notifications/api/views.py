from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404

from ..models import PushToken
from ..services import send_notification_push, send_chat_push
from .serializers import (
    PushTokenSerializer, 
    SendNotificationSerializer, 
    SendChatNotificationSerializer
)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def register_push_token(request):
    """
    Kullanıcının push token'ını kaydeder veya günceller
    """
    try:
        data = request.data.copy()
        
        # Mevcut token'ı kontrol et
        existing_token = PushToken.objects.filter(user=request.user).first()
        
        if existing_token:
            # Güncelle
            serializer = PushTokenSerializer(existing_token, data=data, partial=True)
        else:
            # Yeni oluştur
            serializer = PushTokenSerializer(data=data)
        
        if serializer.is_valid():
            if existing_token:
                serializer.save()
            else:
                serializer.save(user=request.user)
            
            return Response({
                'status': 'success',
                'message': 'Push token başarıyla kaydedildi',
                'data': serializer.data
            }, status=status.HTTP_200_OK)
        
        return Response({
            'status': 'error',
            'message': 'Geçersiz veri',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
        
    except Exception as e:
        return Response({
            'status': 'error',
            'message': f'Push token kaydı sırasında hata: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_test_notification(request):
    """
    Test bildirimi gönderir
    """
    try:
        serializer = SendNotificationSerializer(data=request.data)
        
        if serializer.is_valid():
            user_id = serializer.validated_data['user_id']
            title = serializer.validated_data['title']
            body = serializer.validated_data['body']
            data = serializer.validated_data.get('data', {})
            
            # Kullanıcı kontrolü
            if not User.objects.filter(id=user_id).exists():
                return Response({
                    'status': 'error',
                    'message': 'Kullanıcı bulunamadı'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Bildirim gönder
            success = send_notification_push(user_id, title, body, data)
            
            if success:
                return Response({
                    'status': 'success',
                    'message': 'Test bildirimi başarıyla gönderildi'
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'status': 'error',
                    'message': 'Bildirim gönderilemedi. Push token kontrol edin.'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({
            'status': 'error',
            'message': 'Geçersiz veri',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
        
    except Exception as e:
        return Response({
            'status': 'error',
            'message': f'Test bildirimi sırasında hata: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_test_chat_notification(request):
    """
    Test chat bildirimi gönderir
    """
    try:
        serializer = SendChatNotificationSerializer(data=request.data)
        
        if serializer.is_valid():
            user_id = serializer.validated_data['user_id']
            sender_name = serializer.validated_data['sender_name']
            message = serializer.validated_data['message']
            chat_room_id = serializer.validated_data['chat_room_id']
            
            # Kullanıcı kontrolü
            if not User.objects.filter(id=user_id).exists():
                return Response({
                    'status': 'error',
                    'message': 'Kullanıcı bulunamadı'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Chat bildirimi gönder
            success = send_chat_push(user_id, sender_name, message, chat_room_id)
            
            if success:
                return Response({
                    'status': 'success',
                    'message': 'Test chat bildirimi başarıyla gönderildi'
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'status': 'error',
                    'message': 'Chat bildirimi gönderilemedi. Push token kontrol edin.'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({
            'status': 'error',
            'message': 'Geçersiz veri',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
        
    except Exception as e:
        return Response({
            'status': 'error',
            'message': f'Test chat bildirimi sırasında hata: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_push_token(request):
    """
    Kullanıcının push token bilgilerini getirir
    """
    try:
        push_token = PushToken.objects.filter(user=request.user).first()
        
        if push_token:
            serializer = PushTokenSerializer(push_token)
            return Response({
                'status': 'success',
                'data': serializer.data
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'status': 'error',
                'message': 'Push token bulunamadı'
            }, status=status.HTTP_404_NOT_FOUND)
            
    except Exception as e:
        return Response({
            'status': 'error',
            'message': f'Push token getirme sırasında hata: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_push_token(request):
    """
    Kullanıcının push token'ını siler
    """
    try:
        push_token = PushToken.objects.filter(user=request.user).first()
        
        if push_token:
            push_token.delete()
            return Response({
                'status': 'success',
                'message': 'Push token başarıyla silindi'
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'status': 'error',
                'message': 'Push token bulunamadı'
            }, status=status.HTTP_404_NOT_FOUND)
            
    except Exception as e:
        return Response({
            'status': 'error',
            'message': f'Push token silme sırasında hata: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def test_notification_push(request):
    """
    Notifications modülü entegrasyonunu test eder
    """
    try:
        from apps.notifications.services import NotificationService
        
        # Test verilerini al
        recipient_id = request.data.get('recipient_id')
        sender_id = request.data.get('sender_id', request.user.id)
        code = request.data.get('code', 'follow')  # Default test: takip bildirimi
        
        # Kullanıcıları kontrol et
        try:
            recipient = User.objects.get(id=recipient_id)
            sender = User.objects.get(id=sender_id)
        except User.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Kullanıcı bulunamadı'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Notifications modülü üzerinden bildirim oluştur
        # Bu otomatik olarak hem WebSocket hem Push Notification gönderecek
        notification = NotificationService.create_notification(
            sender=sender,
            recipient=recipient,
            code=code
        )
        
        if notification:
            return Response({
                'status': 'success',
                'message': 'Test bildirimi başarıyla oluşturuldu ve gönderildi',
                'notification_id': notification.id,
                'title': notification.title,
                'text': notification.text
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'status': 'error',
                'message': 'Test bildirimi oluşturulamadı'
            }, status=status.HTTP_400_BAD_REQUEST)
        
    except Exception as e:
        return Response({
            'status': 'error',
            'message': f'Test sırasında hata: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
