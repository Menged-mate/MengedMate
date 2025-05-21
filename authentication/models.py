from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils.translation import gettext_lazy as _
import json


class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError(_('The Email must be set'))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))
        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractUser):
    class EVConnectorType(models.TextChoices):
        TYPE_1 = 'type1', _('Type 1 (J1772)')
        TYPE_2 = 'type2', _('Type 2 (Mennekes)')
        CCS1 = 'ccs1', _('CCS Combo 1')
        CCS2 = 'ccs2', _('CCS Combo 2')
        CHADEMO = 'chademo', _('CHAdeMO')
        TESLA = 'tesla', _('Tesla')
        OTHER = 'other', _('Other')
        NONE = 'none', _('None')

    username = None
    email = models.EmailField(_('email address'), unique=True)
    is_verified = models.BooleanField(default=False)
    verification_code = models.CharField(max_length=6, blank=True, null=True)
    password_reset_token = models.CharField(max_length=100, blank=True, null=True)

    phone_number = models.CharField(max_length=20, blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    zip_code = models.CharField(max_length=20, blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pictures/', blank=True, null=True)

    ev_battery_capacity_kwh = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True,
                                                 help_text=_('Battery capacity in kWh'))
    ev_connector_type = models.CharField(max_length=20, choices=EVConnectorType.choices,
                                        default=EVConnectorType.NONE, blank=True)

    # Notification preferences stored as JSON
    notification_preferences = models.TextField(blank=True, null=True)

    # Unread notification count
    unread_notifications = models.PositiveIntegerField(default=0)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    def __str__(self):
        return self.email

    def get_notification_preferences(self):
        """Get notification preferences as a dictionary"""
        if not self.notification_preferences:
            # Default preferences
            return {
                'email_notifications': True,
                'station_updates': True,
                'booking_notifications': True,
                'payment_notifications': True,
                'maintenance_alerts': True,
                'marketing_emails': False
            }
        try:
            return json.loads(self.notification_preferences)
        except json.JSONDecodeError:
            # Return default preferences if JSON is invalid
            return {
                'email_notifications': True,
                'station_updates': True,
                'booking_notifications': True,
                'payment_notifications': True,
                'maintenance_alerts': True,
                'marketing_emails': False
            }

    def set_notification_preferences(self, preferences):
        """Set notification preferences from a dictionary"""
        self.notification_preferences = json.dumps(preferences)
        self.save(update_fields=['notification_preferences'])


class Vehicle(models.Model):
    class EVConnectorType(models.TextChoices):
        TYPE_1 = 'type1', _('Type 1 (J1772)')
        TYPE_2 = 'type2', _('Type 2 (Mennekes)')
        CCS1 = 'ccs1', _('CCS Combo 1')
        CCS2 = 'ccs2', _('CCS Combo 2')
        CHADEMO = 'chademo', _('CHAdeMO')
        TESLA = 'tesla', _('Tesla')
        OTHER = 'other', _('Other')
        NONE = 'none', _('None')

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='vehicles')
    name = models.CharField(max_length=100, help_text=_('Vehicle name or nickname'))
    make = models.CharField(max_length=100)
    model = models.CharField(max_length=100)
    year = models.PositiveIntegerField()
    battery_capacity_kwh = models.DecimalField(max_digits=6, decimal_places=2)
    connector_type = models.CharField(max_length=20, choices=EVConnectorType.choices)
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_primary', '-created_at']

    def __str__(self):
        return f"{self.year} {self.make} {self.model} ({self.name})"

    def save(self, *args, **kwargs):
        if self.is_primary:
            Vehicle.objects.filter(user=self.user, is_primary=True).exclude(pk=self.pk).update(is_primary=False)
        super().save(*args, **kwargs)
