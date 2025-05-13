from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
import uuid

# Verification status choices
class VerificationStatus(models.TextChoices):
    PENDING = 'pending', _('Pending')
    VERIFIED = 'verified', _('Verified')
    REJECTED = 'rejected', _('Rejected')

class StationOwner(models.Model):
    """
    Model for station owners who can register and manage charging stations.
    """
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='station_owner')
    company_name = models.CharField(max_length=255)
    business_registration_number = models.CharField(max_length=100, blank=True, null=True)
    verification_status = models.CharField(
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING
    )

    # Documents for verification
    business_license = models.FileField(upload_to='station_owner_docs/licenses/', blank=True, null=True)
    id_proof = models.FileField(upload_to='station_owner_docs/id_proofs/', blank=True, null=True)
    utility_bill = models.FileField(upload_to='station_owner_docs/utility_bills/', blank=True, null=True)

    # Additional information
    website = models.URLField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    verified_at = models.DateTimeField(blank=True, null=True)

    # Profile completion status
    is_profile_completed = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.company_name} ({self.user.email})"

class ChargingStation(models.Model):
    """
    Model for charging stations managed by station owners.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(StationOwner, on_delete=models.CASCADE, related_name='stations')
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    zip_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100, default='United States')

    # Location coordinates
    latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)

    # Station details
    description = models.TextField(blank=True, null=True)
    amenities = models.TextField(blank=True, null=True)  # Comma-separated list of amenities
    opening_hours = models.TextField(blank=True, null=True)  # JSON format for opening hours

    # Status
    is_active = models.BooleanField(default=True)

    # Images
    main_image = models.ImageField(upload_to='station_images/', blank=True, null=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class StationImage(models.Model):
    """
    Model for additional images of charging stations.
    """
    station = models.ForeignKey(ChargingStation, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='station_images/')
    caption = models.CharField(max_length=255, blank=True, null=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"Image for {self.station.name}"

class ChargingConnector(models.Model):
    """
    Model for charging connectors available at a station.
    """
    class ConnectorType(models.TextChoices):
        TYPE_1 = 'type1', _('Type 1 (J1772)')
        TYPE_2 = 'type2', _('Type 2 (Mennekes)')
        CCS1 = 'ccs1', _('CCS Combo 1')
        CCS2 = 'ccs2', _('CCS Combo 2')
        CHADEMO = 'chademo', _('CHAdeMO')
        TESLA = 'tesla', _('Tesla')
        OTHER = 'other', _('Other')

    station = models.ForeignKey(ChargingStation, on_delete=models.CASCADE, related_name='connectors')
    connector_type = models.CharField(max_length=20, choices=ConnectorType.choices)
    power_output = models.DecimalField(max_digits=6, decimal_places=2, help_text='Power in kW')
    quantity = models.PositiveIntegerField(default=1)
    price_per_kwh = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)

    def __str__(self):
        return f"{self.get_connector_type_display()} - {self.power_output}kW"
