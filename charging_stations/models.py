from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
import uuid
import qrcode
from io import BytesIO
from django.core.files import File
import hashlib

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

    # Base64 encoded document fields
    business_document = models.TextField(blank=True, null=True, help_text='Base64 encoded business document')
    business_license = models.TextField(blank=True, null=True, help_text='Base64 encoded business license')
    id_proof = models.TextField(blank=True, null=True, help_text='Base64 encoded ID proof')
    utility_bill = models.TextField(blank=True, null=True, help_text='Base64 encoded utility bill')

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

    main_image = models.TextField(blank=True, null=True, help_text='Base64 encoded main station image')
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
    image = models.TextField(help_text='Base64 encoded station image')
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

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    station = models.ForeignKey(ChargingStation, on_delete=models.CASCADE, related_name='connectors')
    connector_type = models.CharField(max_length=20, choices=ConnectorType.choices)
    power_kw = models.DecimalField(max_digits=6, decimal_places=2, help_text='Power in kW')
    quantity = models.PositiveIntegerField(default=1)
    available_quantity = models.PositiveIntegerField(default=1)
    price_per_kwh = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)
    is_available = models.BooleanField(default=True)
    status = models.CharField(max_length=20, choices=ConnectorStatus.choices, default=ConnectorStatus.AVAILABLE)
    description = models.TextField(blank=True, null=True)

    qr_code_token = models.CharField(max_length=255, unique=True, blank=True, null=True)
    qr_code_image = models.TextField(blank=True, null=True, help_text='Base64 encoded QR code image')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.qr_code_token:
            self.qr_code_token = self.generate_qr_token()

        if not self.available_quantity:
            self.available_quantity = self.quantity

        super().save(*args, **kwargs)

        if not self.qr_code_image:
            self.generate_qr_code()

    def generate_qr_token(self):
        """Generate a unique token for QR code"""
        unique_string = f"{self.station.id}-{self.connector_type}-{self.power_kw}-{uuid.uuid4()}"
        return hashlib.sha256(unique_string.encode()).hexdigest()[:32]

    def generate_qr_code(self):
        """Generate QR code for this connector and store as Base64"""
        if not self.qr_code_token:
            return

        qr_data = f"{settings.API_BASE_URL}/api/payments/qr-initiate/{self.qr_code_token}/"

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_data)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")

        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)

        # Encode to Base64
        import base64
        base64_image = base64.b64encode(buffer.read()).decode('utf-8')
        self.qr_code_image = f"data:image/png;base64,{base64_image}"

        ChargingConnector.objects.filter(id=self.id).update(qr_code_image=self.qr_code_image)

    def get_qr_code_url(self):
        """Get the QR code image as Base64 data URI"""
        if self.qr_code_image:
            return self.qr_code_image  # Already a Base64 data URI
        return None

    def update_availability(self):
        """Update connector availability based on active sessions"""
        from ocpp_integration.models import ChargingSession

        active_sessions = ChargingSession.objects.filter(
            ocpp_connector__charging_connector=self,
            status__in=['started', 'charging', 'preparing']
        ).count()

        self.available_quantity = max(0, self.quantity - active_sessions)
        self.is_available = self.available_quantity > 0 and self.status == 'available'
        self.save(update_fields=['available_quantity', 'is_available'])

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


class StationReview(models.Model):
    """Model for station reviews and ratings"""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='station_reviews')
    station = models.ForeignKey(ChargingStation, on_delete=models.CASCADE, related_name='reviews')
    rating = models.PositiveIntegerField(
        choices=[(i, i) for i in range(1, 6)],  # 1-5 star rating
        help_text="Rating from 1 to 5 stars"
    )
    review_text = models.TextField(blank=True, null=True, help_text="Optional review text")

    charging_speed_rating = models.PositiveIntegerField(
        choices=[(i, i) for i in range(1, 6)],
        blank=True, null=True,
        help_text="Rating for charging speed (1-5 stars)"
    )
    location_rating = models.PositiveIntegerField(
        choices=[(i, i) for i in range(1, 6)],
        blank=True, null=True,
        help_text="Rating for location convenience (1-5 stars)"
    )
    amenities_rating = models.PositiveIntegerField(
        choices=[(i, i) for i in range(1, 6)],
        blank=True, null=True,
        help_text="Rating for amenities (1-5 stars)"
    )

    is_verified_review = models.BooleanField(default=False, help_text="Review from verified charging session")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'station')  
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['station', '-created_at']),
            models.Index(fields=['rating']),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.station.name} ({self.rating} stars)"

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        was_verified = False

        if not is_new:
            try:
                # Check if review was just verified
                old_review = StationReview.objects.get(pk=self.pk)
                was_verified = not old_review.is_verified_review and self.is_verified_review
            except StationReview.DoesNotExist:
                pass

        super().save(*args, **kwargs)

        # Update station rating after saving review
        self.update_station_rating()

        # Send notifications (with error handling)
        try:
            if is_new:
                self._send_new_review_notification()
            elif was_verified:
                self._send_review_verified_notification()
        except Exception as e:
            # Log error but don't fail the save operation
            print(f"Error sending review notification: {e}")

    def _send_new_review_notification(self):
        """Send notification to station owner about new review"""
        try:
            # Check if notification system is available
            try:
                from authentication.notifications import create_notification, Notification
            except ImportError:
                print("Notification system not available")
                return

            # Notify station owner
            create_notification(
                user=self.station.owner.user,
                notification_type=Notification.NotificationType.STATION_UPDATE,
                title='New Review Received',
                message=f'Your station "{self.station.name}" received a new {self.rating}-star review.',
                link=f'/dashboard/stations/{self.station.id}/reviews'
            )
        except Exception as e:
            print(f"Error sending new review notification: {e}")

    def _send_review_verified_notification(self):
        """Send notification to reviewer when review is verified"""
        try:
            # Check if notification system is available
            try:
                from authentication.notifications import create_notification, Notification
            except ImportError:
                print("Notification system not available")
                return

            # Notify the reviewer
            create_notification(
                user=self.user,
                notification_type=Notification.NotificationType.SYSTEM,
                title='Review Verified',
                message=f'Your review for "{self.station.name}" has been verified and is now featured.',
                link=f'/stations/{self.station.id}'
            )
        except Exception as e:
            print(f"Error sending review verified notification: {e}")

    def delete(self, *args, **kwargs):
        station = self.station
        super().delete(*args, **kwargs)
        self._update_station_rating_after_delete(station)

    def update_station_rating(self):
        """Update the station's overall rating and count"""
        from django.db.models import Avg, Count

        reviews = StationReview.objects.filter(station=self.station, is_active=True)

        rating_data = reviews.aggregate(
            avg_rating=Avg('rating'),
            total_count=Count('id')
        )

        self.station.rating = round(rating_data['avg_rating'] or 0, 2)
        self.station.rating_count = rating_data['total_count']
        self.station.save(update_fields=['rating', 'rating_count'])

    @staticmethod
    def _update_station_rating_after_delete(station):
        """Update station rating after a review is deleted"""
        from django.db.models import Avg, Count

        reviews = StationReview.objects.filter(station=station, is_active=True)
        rating_data = reviews.aggregate(
            avg_rating=Avg('rating'),
            total_count=Count('id')
        )

        station.rating = round(rating_data['avg_rating'] or 0, 2)
        station.rating_count = rating_data['total_count']
        station.save(update_fields=['rating', 'rating_count'])


class ReviewReply(models.Model):
    """Model for station owner replies to reviews"""

    review = models.OneToOneField(
        StationReview,
        on_delete=models.CASCADE,
        related_name='reply',
        help_text="The review this reply is responding to"
    )
    station_owner = models.ForeignKey(
        'StationOwner',
        on_delete=models.CASCADE,
        related_name='review_replies',
        help_text="Station owner who wrote the reply"
    )
    reply_text = models.TextField(
        help_text="Reply text from station owner"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['review', '-created_at']),
            models.Index(fields=['station_owner', '-created_at']),
        ]

    def __str__(self):
        return f"Reply by {self.station_owner.company_name} to review #{self.review.id}"

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)

        # Send notification to reviewer when owner replies
        if is_new:
            self._send_reply_notification()

    def _send_reply_notification(self):
        """Send notification to reviewer when station owner replies"""
        try:
            # Check if notification system is available
            try:
                from authentication.notifications import create_notification, Notification
            except ImportError:
                print("Notification system not available")
                return

            # Notify the reviewer
            create_notification(
                user=self.review.user,
                notification_type=Notification.NotificationType.SYSTEM,
                title='Station Owner Replied',
                message=f'{self.station_owner.company_name} replied to your review for "{self.review.station.name}".',
                link=f'/stations/{self.review.station.id}'
            )
        except Exception as e:
            print(f"Error sending reply notification: {e}")

    def clean(self):
        """Validate that the station owner owns the station being reviewed"""
        from django.core.exceptions import ValidationError

        if self.review.station.owner != self.station_owner:
            raise ValidationError(
                "Station owner can only reply to reviews of their own stations."
            )


class AppContent(models.Model):
    """Model to store app content like About, Privacy Policy, Terms of Service"""

    CONTENT_TYPES = [
        ('about', 'About evmeri'),
        ('privacy_policy', 'Privacy Policy'),
        ('terms_of_service', 'Terms of Service'),
    ]

    content_type = models.CharField(max_length=20, choices=CONTENT_TYPES, unique=True)
    title = models.CharField(max_length=255)
    content = models.TextField()
    version = models.CharField(max_length=10, default='1.0')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['content_type']
        verbose_name = 'App Content'
        verbose_name_plural = 'App Contents'

    def __str__(self):
        return f"{self.get_content_type_display()} - v{self.version}"


class StationOwnerSettings(models.Model):
    """Model to store station owner specific settings"""

    owner = models.OneToOneField(StationOwner, on_delete=models.CASCADE, related_name='settings')

    # Station Configuration Settings
    default_pricing_per_kwh = models.DecimalField(max_digits=6, decimal_places=2, default=5.50)
    auto_accept_bookings = models.BooleanField(default=True)
    max_session_duration_hours = models.PositiveIntegerField(default=4)
    maintenance_mode = models.BooleanField(default=False)

    # Notification Settings
    email_notifications = models.BooleanField(default=True)
    sms_notifications = models.BooleanField(default=False)
    booking_notifications = models.BooleanField(default=True)
    payment_notifications = models.BooleanField(default=True)
    maintenance_alerts = models.BooleanField(default=True)
    marketing_emails = models.BooleanField(default=False)
    station_updates = models.BooleanField(default=True)

    # Branding Settings
    brand_color = models.CharField(max_length=7, default='#3B82F6')  # Hex color
    logo_url = models.URLField(blank=True, null=True)
    custom_welcome_message = models.TextField(blank=True, null=True)
    display_company_info = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Station Owner Settings'
        verbose_name_plural = 'Station Owner Settings'

    def __str__(self):
        return f"Settings for {self.owner.company_name}"


class NotificationTemplate(models.Model):
    """Model to store notification templates"""

    TEMPLATE_TYPES = [
        ('booking_confirmed', 'Booking Confirmed'),
        ('payment_received', 'Payment Received'),
        ('session_started', 'Session Started'),
        ('session_completed', 'Session Completed'),
        ('maintenance_required', 'Maintenance Required'),
        ('station_offline', 'Station Offline'),
        ('low_balance', 'Low Balance'),
    ]

    template_type = models.CharField(max_length=30, choices=TEMPLATE_TYPES, unique=True)
    subject = models.CharField(max_length=255)
    email_body = models.TextField()
    sms_body = models.TextField(max_length=160)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Notification Template'
        verbose_name_plural = 'Notification Templates'

    def __str__(self):
        return f"{self.get_template_type_display()} Template"


class PayoutMethod(models.Model):
    """Model for station owner payout methods"""

    class MethodType(models.TextChoices):
        BANK_ACCOUNT = 'bank_account', 'Bank Account'
        CARD = 'card', 'Credit/Debit Card'
        MOBILE_MONEY = 'mobile_money', 'Mobile Money'
        PAYPAL = 'paypal', 'PayPal'

    station_owner = models.ForeignKey(
        StationOwner,
        on_delete=models.CASCADE,
        related_name='payout_methods',
        help_text="Station owner who owns this payout method"
    )
    method_type = models.CharField(
        max_length=20,
        choices=MethodType.choices,
        default=MethodType.BANK_ACCOUNT
    )

    # Bank account fields
    account_holder_name = models.CharField(max_length=255, blank=True)
    bank_name = models.CharField(max_length=255, blank=True)
    account_number = models.CharField(max_length=50, blank=True)
    routing_number = models.CharField(max_length=20, blank=True)
    swift_code = models.CharField(max_length=20, blank=True)

    # Card fields
    card_number = models.CharField(max_length=20, blank=True)  # Encrypted/masked
    card_type = models.CharField(max_length=20, blank=True)  # Visa, MasterCard, etc.
    expiry_month = models.CharField(max_length=2, blank=True)
    expiry_year = models.CharField(max_length=4, blank=True)

    # Mobile money fields
    phone_number = models.CharField(max_length=20, blank=True)
    provider = models.CharField(max_length=50, blank=True)  # M-Pesa, Airtel Money, etc.

    # PayPal fields
    paypal_email = models.EmailField(blank=True)

    # Common fields
    is_default = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_default', '-created_at']
        indexes = [
            models.Index(fields=['station_owner', '-created_at']),
            models.Index(fields=['station_owner', 'is_default']),
            models.Index(fields=['method_type', 'is_active']),
        ]

    def __str__(self):
        if self.method_type == self.MethodType.BANK_ACCOUNT:
            return f"{self.bank_name} - ****{self.account_number[-4:] if self.account_number else ''}"
        elif self.method_type == self.MethodType.CARD:
            return f"{self.card_type} - ****{self.card_number[-4:] if self.card_number else ''}"
        elif self.method_type == self.MethodType.MOBILE_MONEY:
            return f"{self.provider} - {self.phone_number}"
        elif self.method_type == self.MethodType.PAYPAL:
            return f"PayPal - {self.paypal_email}"
        return f"{self.get_method_type_display()}"

    def save(self, *args, **kwargs):
        # Ensure only one default method per station owner
        if self.is_default:
            PayoutMethod.objects.filter(
                station_owner=self.station_owner,
                is_default=True
            ).exclude(id=self.id).update(is_default=False)
        super().save(*args, **kwargs)

    def get_masked_details(self):
        """Return masked details for display"""
        if self.method_type == self.MethodType.BANK_ACCOUNT:
            return {
                'type': 'Bank Account',
                'details': f"{self.bank_name} - ****{self.account_number[-4:] if self.account_number else ''}",
                'holder': self.account_holder_name
            }
        elif self.method_type == self.MethodType.CARD:
            return {
                'type': self.card_type or 'Card',
                'details': f"****{self.card_number[-4:] if self.card_number else ''}",
                'holder': self.account_holder_name
            }
        elif self.method_type == self.MethodType.MOBILE_MONEY:
            return {
                'type': self.provider or 'Mobile Money',
                'details': self.phone_number,
                'holder': self.account_holder_name
            }
        elif self.method_type == self.MethodType.PAYPAL:
            return {
                'type': 'PayPal',
                'details': self.paypal_email,
                'holder': self.account_holder_name
            }
        return {'type': 'Unknown', 'details': '', 'holder': ''}


class WithdrawalRequest(models.Model):
    """Model for tracking withdrawal/payout requests from station owners"""

    class WithdrawalStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        APPROVED = 'approved', 'Approved'
        PROCESSING = 'processing', 'Processing'
        COMPLETED = 'completed', 'Completed'
        REJECTED = 'rejected', 'Rejected'
        FAILED = 'failed', 'Failed'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    station_owner = models.ForeignKey(
        StationOwner,
        on_delete=models.CASCADE,
        related_name='withdrawal_requests',
        help_text="Station owner requesting the withdrawal"
    )
    payout_method = models.ForeignKey(
        PayoutMethod,
        on_delete=models.CASCADE,
        related_name='withdrawals',
        help_text="Payment method for the withdrawal"
    )

    # Withdrawal details
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Amount to withdraw"
    )
    currency = models.CharField(max_length=3, default='ETB')
    description = models.TextField(blank=True, null=True)

    # Status and tracking
    status = models.CharField(
        max_length=20,
        choices=WithdrawalStatus.choices,
        default=WithdrawalStatus.PENDING
    )
    reference_number = models.CharField(max_length=100, unique=True, blank=True)

    # Admin fields
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='approved_withdrawals',
        help_text="Admin who approved/rejected this withdrawal"
    )
    admin_notes = models.TextField(blank=True, null=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['station_owner', '-created_at']),
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['reference_number']),
        ]

    def __str__(self):
        return f"Withdrawal {self.reference_number} - {self.amount} {self.currency} ({self.status})"

    def save(self, *args, **kwargs):
        if not self.reference_number:
            import random
            import string
            self.reference_number = 'WD' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        super().save(*args, **kwargs)
