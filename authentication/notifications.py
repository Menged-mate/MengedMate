from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags


class Notification(models.Model):
    """
    Model for storing user notifications.
    """
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
        """Mark notification as read and update user's unread count"""
        if not self.is_read:
            self.is_read = True
            self.save(update_fields=['is_read'])
            
            # Update user's unread count
            user = self.user
            if user.unread_notifications > 0:
                user.unread_notifications -= 1
                user.save(update_fields=['unread_notifications'])


def create_notification(user, notification_type, title, message, link=None, send_email=True):
    """
    Create a notification for a user and optionally send an email.
    
    Args:
        user: The user to notify
        notification_type: Type of notification (from Notification.NotificationType)
        title: Notification title
        message: Notification message
        link: Optional link to include in the notification
        send_email: Whether to send an email notification
    
    Returns:
        The created notification object
    """
    # Create the notification
    notification = Notification.objects.create(
        user=user,
        notification_type=notification_type,
        title=title,
        message=message,
        link=link
    )
    
    # Update user's unread count
    user.unread_notifications += 1
    user.save(update_fields=['unread_notifications'])
    
    # Check if we should send an email
    if send_email:
        # Get user's notification preferences
        preferences = user.get_notification_preferences()
        
        # Check if user has enabled email notifications
        if preferences.get('email_notifications', True):
            # Check if user has enabled this type of notification
            notification_map = {
                Notification.NotificationType.STATION_UPDATE: 'station_updates',
                Notification.NotificationType.BOOKING: 'booking_notifications',
                Notification.NotificationType.PAYMENT: 'payment_notifications',
                Notification.NotificationType.MAINTENANCE: 'maintenance_alerts',
                Notification.NotificationType.MARKETING: 'marketing_emails',
            }
            
            preference_key = notification_map.get(notification_type)
            
            # If it's a system notification or the user has enabled this type
            if not preference_key or preferences.get(preference_key, True):
                # Send email notification
                send_notification_email(user, notification)
    
    return notification


def send_notification_email(user, notification):
    """Send an email notification to a user"""
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
        # Log the error but don't raise an exception
        print(f"Error sending notification email: {e}")
