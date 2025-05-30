from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags


class Notification(models.Model):
    class NotificationType(models.TextChoices):
        SYSTEM = 'system', _('System')
        STATION_UPDATE = 'station_update', _('Station Update')
        BOOKING = 'booking', _('Booking')
        PAYMENT = 'payment', _('Payment')
        MAINTENANCE = 'maintenance', _('Maintenance')
        MARKETING = 'marketing', _('Marketing')
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=NotificationType.choices, default=NotificationType.SYSTEM)
    title = models.CharField(max_length=255)
    message = models.TextField()
    link = models.CharField(max_length=255, blank=True, null=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_notification_type_display()}: {self.title}"
    
    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            self.save(update_fields=['is_read'])
            
            user = self.user
            if user.unread_notifications > 0:
                user.unread_notifications -= 1
                user.save(update_fields=['unread_notifications'])


def create_notification(user, notification_type, title, message, link=None, send_email=True):
 
    notification = Notification.objects.create(
        user=user,
        notification_type=notification_type,
        title=title,
        message=message,
        link=link
    )
    
    user.unread_notifications += 1
    user.save(update_fields=['unread_notifications'])
    
    if send_email:
        preferences = user.get_notification_preferences()
        
        if preferences.get('email_notifications', True):
            notification_map = {
                Notification.NotificationType.STATION_UPDATE: 'station_updates',
                Notification.NotificationType.BOOKING: 'booking_notifications',
                Notification.NotificationType.PAYMENT: 'payment_notifications',
                Notification.NotificationType.MAINTENANCE: 'maintenance_alerts',
                Notification.NotificationType.MARKETING: 'marketing_emails',
            }
            
            preference_key = notification_map.get(notification_type)
            
            if not preference_key or preferences.get(preference_key, True):
                send_notification_email(user, notification)
    
    return notification


def send_notification_email(user, notification):
    subject = f"MengedMate: {notification.title}"
    
    context = {
        'user': user,
        'notification': notification,
        'app_name': 'MengedMate'
    }
    
    html_message = render_to_string('email/notification_email.html', context)
    plain_message = strip_tags(html_message)
    
    from_email = settings.DEFAULT_FROM_EMAIL
    recipient_list = [user.email]
    
    try:
        send_mail(
            subject,
            plain_message,
            from_email,
            recipient_list,
            html_message=html_message,
            fail_silently=True
        )
    except Exception as e:
        print(f"Error sending notification email: {e}")
