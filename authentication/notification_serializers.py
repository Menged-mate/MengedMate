from rest_framework import serializers
from .notifications import Notification


class NotificationSerializer(serializers.ModelSerializer):
    notification_type_display = serializers.CharField(source='get_notification_type_display', read_only=True)
    time_ago = serializers.SerializerMethodField()
    
    class Meta:
        model = Notification
        fields = (
            'id', 'notification_type', 'notification_type_display', 
            'title', 'message', 'link', 'is_read', 'created_at', 'time_ago'
        )
        read_only_fields = (
            'id', 'notification_type', 'notification_type_display', 
            'title', 'message', 'link', 'created_at', 'time_ago'
        )
    
    def get_time_ago(self, obj):
        """Return a human-readable time difference"""
        from django.utils import timezone
        from django.utils.timesince import timesince
        
        now = timezone.now()
        diff = now - obj.created_at
        
        if diff.days == 0:
            # Less than a day
            if diff.seconds < 60:
                return 'just now'
            elif diff.seconds < 3600:
                minutes = diff.seconds // 60
                return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
            else:
                hours = diff.seconds // 3600
                return f"{hours} hour{'s' if hours > 1 else ''} ago"
        elif diff.days == 1:
            return 'yesterday'
        elif diff.days < 7:
            return f"{diff.days} days ago"
        else:
            return timesince(obj.created_at)
