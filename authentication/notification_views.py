from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from .notifications import Notification
from .notification_serializers import NotificationSerializer


class NotificationListView(generics.ListAPIView):
   
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    
    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)


class NotificationMarkReadView(APIView):
   
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    
    def post(self, request, notification_id=None):
        if notification_id:
            try:
                notification = Notification.objects.get(id=notification_id, user=request.user)
                notification.mark_as_read()
                return Response({'status': 'success'}, status=status.HTTP_200_OK)
            except Notification.DoesNotExist:
                return Response(
                    {'error': 'Notification not found'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            notifications = Notification.objects.filter(user=request.user, is_read=False)
            for notification in notifications:
                notification.mark_as_read()
            
            request.user.unread_notifications = 0
            request.user.save(update_fields=['unread_notifications'])
            
            return Response({'status': 'success'}, status=status.HTTP_200_OK)


class NotificationDeleteView(APIView):
   
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    
    def delete(self, request, notification_id):
        try:
            notification = Notification.objects.get(id=notification_id, user=request.user)
            
            if not notification.is_read and request.user.unread_notifications > 0:
                request.user.unread_notifications -= 1
                request.user.save(update_fields=['unread_notifications'])
            
            notification.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Notification.DoesNotExist:
            return Response(
                {'error': 'Notification not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )



