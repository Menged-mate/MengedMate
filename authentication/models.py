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

    # Telegram fields
    telegram_id = models.CharField(max_length=100, blank=True, null=True, unique=True)
    telegram_username = models.CharField(max_length=100, blank=True, null=True)
    telegram_first_name = models.CharField(max_length=100, blank=True, null=True)
    telegram_last_name = models.CharField(max_length=100, blank=True, null=True)
    telegram_photo_url = models.URLField(max_length=500, blank=True, null=True)
    telegram_auth_date = models.DateTimeField(blank=True, null=True)

    phone_number = models.CharField(max_length=20, blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    zip_code = models.CharField(max_length=20, blank=True, null=True)
    profile_picture = models.TextField(blank=True, null=True, help_text='Base64 encoded profile picture')

    
    ev_battery_capacity_kwh = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True,
                                                 help_text=_('Battery capacity in kWh'))
    ev_connector_type = models.CharField(max_length=20, choices=EVConnectorType.choices,
                                        default=EVConnectorType.NONE, blank=True)

    active_vehicle = models.ForeignKey('Vehicle', on_delete=models.SET_NULL, blank=True, null=True,
                                     related_name='active_for_users',
                                     help_text=_('Currently selected vehicle for recommendations'))


    notification_preferences = models.TextField(blank=True, null=True)

   
    unread_notifications = models.PositiveIntegerField(default=0)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    def __str__(self):
        return self.email

    def get_notification_preferences(self):
        if not self.notification_preferences:
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
            
            return {
                'email_notifications': True,
                'station_updates': True,
                'booking_notifications': True,
                'payment_notifications': True,
                'maintenance_alerts': True,
                'marketing_emails': False
            }

    def set_notification_preferences(self, preferences):
        self.notification_preferences = json.dumps(preferences)
        self.save(update_fields=['notification_preferences'])

    def get_active_vehicle(self):
        if self.active_vehicle:
            return self.active_vehicle
        primary_vehicle = self.vehicles.filter(is_primary=True).first()
        if primary_vehicle:
            return primary_vehicle
        return self.vehicles.first()

    def set_active_vehicle(self, vehicle):
        if vehicle and vehicle.user == self:
            self.active_vehicle = vehicle
            self.save(update_fields=['active_vehicle'])
            return True
        return False

    def get_vehicle_count(self):
        return self.vehicles.count()

    def has_vehicles(self):
        return self.vehicles.exists()

    def get_compatible_connector_types(self):
        connector_types = set()
        for vehicle in self.vehicles.all():
            if vehicle.connector_type and vehicle.connector_type != 'none':
                connector_types.add(vehicle.connector_type)
        return list(connector_types)


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

    class ChargingSpeed(models.TextChoices):
        SLOW = 'slow', _('Slow (3-7 kW)')
        FAST = 'fast', _('Fast (7-22 kW)')
        RAPID = 'rapid', _('Rapid (22-50 kW)')
        ULTRA_RAPID = 'ultra_rapid', _('Ultra Rapid (50+ kW)')

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='vehicles')
    name = models.CharField(max_length=100, help_text=_('Vehicle name or nickname'))
    make = models.CharField(max_length=100)
    model = models.CharField(max_length=100)
    year = models.PositiveIntegerField()

    battery_capacity_kwh = models.DecimalField(max_digits=6, decimal_places=2,
                                             help_text=_('Total battery capacity in kWh'))
    usable_battery_kwh = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True,
                                           help_text=_('Usable battery capacity in kWh'))
    connector_type = models.CharField(max_length=20, choices=EVConnectorType.choices)
    max_charging_speed_kw = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True,
                                              help_text=_('Maximum charging speed in kW'))
    preferred_charging_speed = models.CharField(max_length=20, choices=ChargingSpeed.choices,
                                              default=ChargingSpeed.FAST, blank=True)

    estimated_range_km = models.PositiveIntegerField(blank=True, null=True,
                                                   help_text=_('Estimated range in kilometers'))
    efficiency_kwh_per_100km = models.DecimalField(max_digits=4, decimal_places=2, blank=True, null=True,
                                                  help_text=_('Energy consumption in kWh per 100km'))

    is_primary = models.BooleanField(default=False, help_text=_('Primary vehicle (shown first in lists)'))
    is_active = models.BooleanField(default=True, help_text=_('Vehicle is actively used'))

    total_charging_sessions = models.PositiveIntegerField(default=0)
    total_energy_charged_kwh = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    last_used_at = models.DateTimeField(blank=True, null=True)

    color = models.CharField(max_length=50, blank=True, null=True)
    license_plate = models.CharField(max_length=20, blank=True, null=True)
    notes = models.TextField(blank=True, null=True, help_text=_('Personal notes about the vehicle'))
    vehicle_image = models.TextField(blank=True, null=True, help_text='Base64 encoded vehicle image')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_primary', '-last_used_at', '-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'license_plate'],
                condition=models.Q(license_plate__isnull=False),
                name='unique_license_plate_per_user'
            )
        ]

    def __str__(self):
        return f"{self.year} {self.make} {self.model} ({self.name})"

    def save(self, *args, **kwargs):
        if self.is_primary:
            Vehicle.objects.filter(user=self.user, is_primary=True).exclude(pk=self.pk).update(is_primary=False)

        if not self.pk and not Vehicle.objects.filter(user=self.user).exists():
            self.is_primary = True

        if not self.usable_battery_kwh and self.battery_capacity_kwh:
            from decimal import Decimal
            self.usable_battery_kwh = self.battery_capacity_kwh * Decimal('0.92')

        super().save(*args, **kwargs)

        if not self.user.active_vehicle:
            self.user.set_active_vehicle(self)

    def get_display_name(self):
        return f"{self.name} ({self.year} {self.make} {self.model})"

    def get_short_name(self):
        return f"{self.make} {self.model}"

    def get_estimated_charging_time(self, target_percentage=80, current_percentage=20):
        if not self.usable_battery_kwh or not self.max_charging_speed_kw:
            return None

        energy_needed = self.usable_battery_kwh * (target_percentage - current_percentage) / 100
        charging_time_hours = energy_needed / self.max_charging_speed_kw
        return round(charging_time_hours * 60)  

    def get_range_at_percentage(self, percentage):
        if not self.estimated_range_km:
            return None
        return round(self.estimated_range_km * percentage / 100)

    def is_compatible_with_connector(self, connector_type):
        return self.connector_type == connector_type

    def update_usage_stats(self, energy_charged_kwh=None):
        from django.utils import timezone

        self.last_used_at = timezone.now()
        if energy_charged_kwh:
            self.total_charging_sessions += 1
            self.total_energy_charged_kwh += energy_charged_kwh
        self.save(update_fields=['last_used_at', 'total_charging_sessions', 'total_energy_charged_kwh'])

    def get_efficiency_rating(self):
        if not self.efficiency_kwh_per_100km:
            return 'Unknown'

        if self.efficiency_kwh_per_100km <= 15:
            return 'Excellent'
        elif self.efficiency_kwh_per_100km <= 20:
            return 'Good'
        elif self.efficiency_kwh_per_100km <= 25:
            return 'Average'
        else:
            return 'Poor'

    def get_charging_speed_category(self):
        if not self.max_charging_speed_kw:
            return 'Unknown'

        if self.max_charging_speed_kw >= 150:
            return 'Ultra Rapid'
        elif self.max_charging_speed_kw >= 50:
            return 'Rapid'
        elif self.max_charging_speed_kw >= 22:
            return 'Fast'
        else:
            return 'Slow'



