from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
import uuid

class VerificationStatus(models.TextChoices):
    PENDING = 'pending', _('Pending')
    VERIFIED = 'verified', _('Verified')
    REJECTED = 'rejected', _('Rejected')

class StationOwner(models.Model):

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='station_owner')
    company_name = models.CharField(max_length=255)
    business_registration_number = models.CharField(max_length=100, blank=True, null=True)
    verification_status = models.CharField(
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING
    )

    business_document = models.FileField(upload_to='station_owner_docs/business_docs/', blank=True, null=True)
    business_license = models.FileField(upload_to='station_owner_docs/licenses/', blank=True, null=True)
    id_proof = models.FileField(upload_to='station_owner_docs/id_proofs/', blank=True, null=True)
    utility_bill = models.FileField(upload_to='station_owner_docs/utility_bills/', blank=True, null=True)

    contact_phone = models.CharField(max_length=20, blank=True, null=True)
    contact_email = models.EmailField(blank=True, null=True)

    website = models.URLField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    verified_at = models.DateTimeField(blank=True, null=True)

    is_profile_completed = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.company_name} ({self.user.email})"

class ChargingStation(models.Model):

    class StationStatus(models.TextChoices):
        OPERATIONAL = 'operational', _('Operational')
        UNDER_MAINTENANCE = 'under_maintenance', _('Under Maintenance')
        CLOSED = 'closed', _('Closed')
        COMING_SOON = 'coming_soon', _('Coming Soon')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(StationOwner, on_delete=models.CASCADE, related_name='stations')
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    zip_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100, default='United States')

    latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)


    description = models.TextField(blank=True, null=True)
    opening_hours = models.TextField(blank=True, null=True)


    has_restroom = models.BooleanField(default=False)
    has_wifi = models.BooleanField(default=False)
    has_restaurant = models.BooleanField(default=False)
    has_shopping = models.BooleanField(default=False)

    is_active = models.BooleanField(default=True)
    is_public = models.BooleanField(default=True)
    status = models.CharField(
        max_length=20,
        choices=StationStatus.choices,
        default=StationStatus.OPERATIONAL
    )

    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.0)
    rating_count = models.PositiveIntegerField(default=0)


    price_range = models.CharField(max_length=20, blank=True, null=True)
    available_connectors = models.PositiveIntegerField(default=0)
    total_connectors = models.PositiveIntegerField(default=0)

    main_image = models.ImageField(upload_to='station_images/', blank=True, null=True)
    marker_icon = models.CharField(max_length=50, blank=True, null=True, default='default')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def update_connector_counts(self):
        """Update total and available connector counts based on actual connectors"""
        connectors = self.connectors.all()
        self.total_connectors = sum(connector.quantity for connector in connectors)
        self.available_connectors = sum(
            connector.quantity for connector in connectors
            if connector.is_available and connector.status == 'available'
        )
        self.save(update_fields=['total_connectors', 'available_connectors'])

class StationImage(models.Model):

    station = models.ForeignKey(ChargingStation, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='station_images/')
    caption = models.CharField(max_length=255, blank=True, null=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"Image for {self.station.name}"

class ChargingConnector(models.Model):

    class ConnectorType(models.TextChoices):
        TYPE_1 = 'type1', _('Type 1 (J1772)')
        TYPE_2 = 'type2', _('Type 2 (Mennekes)')
        CCS1 = 'ccs1', _('CCS Combo 1')
        CCS2 = 'ccs2', _('CCS Combo 2')
        CHADEMO = 'chademo', _('CHAdeMO')
        TESLA = 'tesla', _('Tesla')
        OTHER = 'other', _('Other')

    class ConnectorStatus(models.TextChoices):
        AVAILABLE = 'available', _('Available')
        OCCUPIED = 'occupied', _('Occupied')
        OUT_OF_ORDER = 'out_of_order', _('Out of Order')
        MAINTENANCE = 'maintenance', _('Under Maintenance')

    station = models.ForeignKey(ChargingStation, on_delete=models.CASCADE, related_name='connectors')
    connector_type = models.CharField(max_length=20, choices=ConnectorType.choices)
    power_kw = models.DecimalField(max_digits=6, decimal_places=2, help_text='Power in kW')
    quantity = models.PositiveIntegerField(default=1)
    price_per_kwh = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)
    is_available = models.BooleanField(default=True)
    status = models.CharField(max_length=20, choices=ConnectorStatus.choices, default=ConnectorStatus.AVAILABLE)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.get_connector_type_display()} - {self.power_kw}kW"

class FavoriteStation(models.Model):

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='favorite_stations')
    station = models.ForeignKey(ChargingStation, on_delete=models.CASCADE, related_name='favorited_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'station')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} - {self.station.name}"
