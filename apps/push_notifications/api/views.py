from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404

from ..models import FCMToken, NotificationLog
from ..services import (
    firebase_service, 
    send_notification_push, 
    send_chat_push,
    send_like_push,
    send_comment_push,
    send_follow_push
)
from .serializers import (
    FCMTokenSerializer, 
    SendNotificationSerializer
)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def register_fcm_token(request):
    """
    Kullanıcının FCM token'ını kaydeder veya günceller
    """
    try:
        serializer = FCMTokenSerializer(data=request.data)
        
        if serializer.is_valid():
            fcm_token = serializer.validated_data['fcm_token']
            platform = serializer.validated_data['platform']
            device_info = serializer.validated_data.get('device_info', {})
            
            # Token'ı kaydet
            success = firebase_service.register_token(
                user=request.user,
                fcm_token=fcm_token,
                platform=platform,
                device_info=device_info
            )
            
            if success:
                return Response({
                    'status': 'success',
                    'message': 'FCM token başarıyla kaydedildi'
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'status': 'error',
                    'message': 'FCM token kaydedilemedi'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({
            'status': 'error',
            'message': 'Geçersiz veri',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
        
    except Exception as e:
        return Response({
            'status': 'error',
            'message': f'FCM token kaydı sırasında hata: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def remove_fcm_token(request):
    """
    Kullanıcının FCM token'ını siler
    """
    try:
        fcm_token = request.data.get('fcm_token')
        
        success = firebase_service.remove_token(
            user=request.user,
            fcm_token=fcm_token
        )
        
        if success:
            return Response({
                'status': 'success',
                'message': 'FCM token başarıyla silindi'
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'status': 'error',
                'message': 'FCM token silinemedi'
            }, status=status.HTTP_400_BAD_REQUEST)
        
    except Exception as e:
        return Response({
            'status': 'error',
            'message': f'FCM token silme sırasında hata: {str(e)}'
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
            user_id = serializer.validated_data.get('user_id', request.user.id)
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
                    'message': 'Bildirim gönderilemedi. FCM token kontrol edin.'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({
            'status': 'error',
            'message': 'Geçersiz veri',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
        
    except Exception as e:
        return Response({
            'status': 'error',
            'message': f'Test bildirimi gönderim hatası: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_tokens(request):
    """
    Kullanıcının FCM token'larını döndürür
    """
    try:
        tokens = FCMToken.objects.filter(user=request.user, is_active=True)
        
        token_data = []
        for token in tokens:
            token_data.append({
                'platform': token.platform,
                'device_name': token.device_name,
                'created_at': token.created_at,
                'updated_at': token.updated_at
            })
        
        return Response({
            'status': 'success',
            'data': token_data
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'status': 'error',
            'message': f'Token listesi alınırken hata: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
