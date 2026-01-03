from datetime import datetime
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import (
    StationOwner, ChargingStation, StationImage, ChargingConnector,
    FavoriteStation, StationReview, ReviewReply, StationOwnerSettings, NotificationTemplate,
    PayoutMethod, WithdrawalRequest
)
from utils.fields.base64_field import Base64ImageField, Base64FileField
import random
import string
from utils import firestore_repo

User = get_user_model()

class StationOwnerRegistrationSerializer(serializers.Serializer):

    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, write_only=True)
    password2 = serializers.CharField(required=True, write_only=True)
    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)
    company_name = serializers.CharField(required=True)

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password2": "Password fields didn't match."})

        try:
            validate_password(attrs['password'])
        except ValidationError as e:
            raise serializers.ValidationError({"password": list(e.messages)})

        return attrs

    def create(self, validated_data):
        user = User(
            email=validated_data['email'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            is_verified=False,
        )

        verification_code = ''.join(random.choices(string.digits, k=6))
        user.verification_code = verification_code

        user.set_password(validated_data['password'])
        user.save()

        user.save()

        # Create Station Owner profile in Firestore
        owner_data = {
            'company_name': validated_data['company_name'],
            'is_profile_completed': False,
            'verification_status': 'pending',
            'contact_email': user.email
        }
        station_owner = firestore_repo.create_station_owner(user.id, owner_data)

        return {
            'user': user,
            'station_owner': station_owner,
            'verification_code': verification_code
        }

class StationOwnerProfileSerializer(serializers.ModelSerializer):

    email = serializers.EmailField(source='user.email', read_only=True)
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    
    # Override file fields with Base64 fields for input
    business_document = Base64FileField(required=False, allow_null=True)
    business_license = Base64FileField(required=False, allow_null=True)
    id_proof = Base64FileField(required=False, allow_null=True)
    utility_bill = Base64FileField(required=False, allow_null=True)

    class Meta:
        model = StationOwner
        fields = [
            'id', 'email', 'first_name', 'last_name', 'company_name',
            'business_registration_number', 'verification_status',
            'business_document', 'business_license', 'id_proof', 'utility_bill',
            'website', 'description', 'is_profile_completed',
            'created_at', 'updated_at', 'verified_at'
        ]
        read_only_fields = [
            'id', 'verification_status', 'created_at',
            'updated_at', 'verified_at', 'is_profile_completed'
        ]

    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data)

        # Check if all required fields have actual values (not just empty fields)
        required_text_fields = ['business_registration_number']
        required_file_fields = ['business_license', 'id_proof']

        # Check text fields are not empty
        text_fields_complete = all(
            getattr(instance, field) and str(getattr(instance, field)).strip()
            for field in required_text_fields
        )

        # Check file fields have actual files uploaded
        file_fields_complete = all(
            getattr(instance, field) and getattr(instance, field).name
            for field in required_file_fields
        )

        is_complete = text_fields_complete and file_fields_complete

        if is_complete and not instance.is_profile_completed:
            instance.is_profile_completed = True
            instance.verification_status = 'pending'  # Set to pending when profile is completed
            instance.save()

        return instance

class ChargingConnectorSerializer(serializers.ModelSerializer):

    connector_type_display = serializers.CharField(source='get_connector_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    qr_code_url = serializers.SerializerMethodField()

    class Meta:
        model = ChargingConnector
        fields = [
            'id', 'connector_type', 'connector_type_display', 'power_kw', 'quantity',
            'available_quantity', 'price_per_kwh', 'is_available', 'status',
            'status_display', 'description', 'qr_code_url', 'qr_code_token'
        ]

    def get_qr_code_url(self, obj):
        return obj.get_qr_code_url()

class StationImageSerializer(serializers.ModelSerializer):
    # Use Base64ImageField for image input
    image = Base64ImageField(required=True)

    class Meta:
        model = StationImage
        fields = ['id', 'image', 'caption', 'order']

class ChargingStationSerializer(serializers.ModelSerializer):

    connectors = ChargingConnectorSerializer(many=True, read_only=True)
    images = StationImageSerializer(many=True, read_only=True)
    owner_name = serializers.CharField(source='owner.company_name', read_only=True)
    is_verified_owner = serializers.SerializerMethodField()
    # Use Base64ImageField for main_image input
    main_image = Base64ImageField(required=False, allow_null=True)

    class Meta:
        model = ChargingStation
        fields = [
            'id', 'name', 'address', 'city', 'state', 'zip_code', 'country',
            'latitude', 'longitude', 'description', 'opening_hours',
            'is_active', 'is_public', 'status', 'rating', 'rating_count',
            'price_range', 'available_connectors', 'total_connectors',
            'has_restroom', 'has_wifi', 'has_restaurant', 'has_shopping',
            'main_image', 'marker_icon', 'created_at', 'updated_at',
            'connectors', 'images', 'owner_name', 'is_verified_owner'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'rating', 'rating_count',
                           'available_connectors', 'total_connectors']

    def get_is_verified_owner(self, obj):
        return obj.owner.verification_status == 'verified'

    def create(self, validated_data):
        user = self.context['request'].user
        try:
            station_owner = StationOwner.objects.get(user=user)
        except StationOwner.DoesNotExist:
            raise serializers.ValidationError("You must be a registered station owner to add stations.")

        if not station_owner.is_profile_completed:
            raise serializers.ValidationError("Please complete your profile before adding stations.")

        validated_data['owner'] = station_owner
        return super().create(validated_data)

class MapStationSerializer(serializers.ModelSerializer):

    owner_name = serializers.CharField(source='owner.company_name', read_only=True)
    is_verified_owner = serializers.SerializerMethodField()
    connector_types = serializers.SerializerMethodField()
    marker_color = serializers.SerializerMethodField()
    availability_status = serializers.SerializerMethodField()

    class Meta:
        model = ChargingStation
        fields = [
            'id', 'name', 'latitude', 'longitude', 'rating',
            'status', 'price_range', 'available_connectors',
            'total_connectors', 'marker_icon', 'owner_name',
            'is_verified_owner', 'connector_types', 'marker_color',
            'availability_status', 'city', 'country'
        ]

    def get_is_verified_owner(self, obj):
        return obj.owner.verification_status == 'verified'

    def get_connector_types(self, obj):
        return list(obj.connectors.values_list('connector_type', flat=True).distinct())

    def get_marker_color(self, obj):
        """Return marker color based on availability status"""
        if obj.status in ['closed', 'under_maintenance']:
            return 'red'
        elif obj.available_connectors == 0:
            return 'red'
        elif obj.available_connectors < obj.total_connectors:
            return 'yellow'
        else:
            return 'green'

    def get_availability_status(self, obj):
        """Return human-readable availability status"""
        if obj.status == 'closed':
            return 'Closed'
        elif obj.status == 'under_maintenance':
            return 'Under Maintenance'
        elif obj.available_connectors == 0:
            return 'All Connectors Busy'
        elif obj.available_connectors < obj.total_connectors:
            return f'{obj.available_connectors}/{obj.total_connectors} Available'
        else:
            return 'Available'

class StationDetailSerializer(serializers.ModelSerializer):

    connectors = ChargingConnectorSerializer(many=True, read_only=True)
    images = StationImageSerializer(many=True, read_only=True)
    owner_name = serializers.CharField(source='owner.company_name', read_only=True)
    is_verified_owner = serializers.SerializerMethodField()
    is_favorite = serializers.SerializerMethodField()

    class Meta:
        model = ChargingStation
        fields = [
            'id', 'name', 'address', 'city', 'state', 'zip_code', 'country',
            'latitude', 'longitude', 'description', 'opening_hours',
            'is_active', 'status', 'rating', 'rating_count',
            'price_range', 'available_connectors', 'total_connectors',
            'has_restroom', 'has_wifi', 'has_restaurant', 'has_shopping',
            'main_image', 'created_at', 'updated_at',
            'connectors', 'images', 'owner_name', 'is_verified_owner', 'is_favorite'
        ]

    def get_is_verified_owner(self, obj):
        return obj.owner.verification_status == 'verified'

    def get_is_favorite(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.favorited_by.filter(user=request.user).exists()
        return False

class FavoriteStationSerializer(serializers.ModelSerializer):

    station = MapStationSerializer(read_only=True)

    class Meta:
        model = FavoriteStation
        fields = ['id', 'station', 'created_at']
        read_only_fields = ['id', 'created_at']


class StationReviewSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating station reviews"""

    user_name = serializers.SerializerMethodField()
    user_email = serializers.SerializerMethodField()

    class Meta:
        model = StationReview
        fields = [
            'id', 'user', 'user_name', 'user_email', 'station', 'rating',
            'review_text', 'charging_speed_rating', 'location_rating',
            'amenities_rating', 'is_verified_review', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'user_name', 'user_email', 'station', 'is_verified_review', 'created_at', 'updated_at']

    def get_user_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}".strip() or obj.user.email.split('@')[0]

    def get_user_email(self, obj):
        # Return masked email for privacy
        email = obj.user.email
        if '@' in email:
            username, domain = email.split('@', 1)
            masked_username = username[:2] + '*' * (len(username) - 2) if len(username) > 2 else username
            return f"{masked_username}@{domain}"
        return email

    def validate_rating(self, value):
        if not (1 <= value <= 5):
            raise serializers.ValidationError("Rating must be between 1 and 5 stars.")
        return value

    def validate_charging_speed_rating(self, value):
        if value is not None and not (1 <= value <= 5):
            raise serializers.ValidationError("Charging speed rating must be between 1 and 5 stars.")
        return value

    def validate_location_rating(self, value):
        if value is not None and not (1 <= value <= 5):
            raise serializers.ValidationError("Location rating must be between 1 and 5 stars.")
        return value

    def validate_amenities_rating(self, value):
        if value is not None and not (1 <= value <= 5):
            raise serializers.ValidationError("Amenities rating must be between 1 and 5 stars.")
        return value




class StationReviewListSerializer(serializers.ModelSerializer):
    """Serializer for listing station reviews (read-only)"""

    user_name = serializers.SerializerMethodField()
    user_email = serializers.SerializerMethodField()
    reply = serializers.SerializerMethodField()

    class Meta:
        model = StationReview
        fields = [
            'id', 'user_name', 'user_email', 'rating', 'review_text',
            'charging_speed_rating', 'location_rating', 'amenities_rating',
            'is_verified_review', 'created_at', 'reply'
        ]

    def get_user_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}".strip() or obj.user.email.split('@')[0]

    def get_user_email(self, obj):
        # Return masked email for privacy
        email = obj.user.email
        if '@' in email:
            username, domain = email.split('@', 1)
            masked_username = username[:2] + '*' * (len(username) - 2) if len(username) > 2 else username
            return f"{masked_username}@{domain}"
        return email

    def get_reply(self, obj):
        """Get the station owner's reply if it exists"""
        try:
            reply = obj.reply
            return {
                'id': reply.id,
                'station_owner_name': reply.station_owner.company_name,
                'reply_text': reply.reply_text,
                'created_at': reply.created_at
            }
        except ReviewReply.DoesNotExist:
            return None


class StationOwnerSettingsSerializer(serializers.ModelSerializer):
    """Serializer for station owner settings"""

    class Meta:
        model = StationOwnerSettings
        fields = [
            'id', 'default_pricing_per_kwh', 'auto_accept_bookings',
            'max_session_duration_hours', 'maintenance_mode',
            'email_notifications', 'sms_notifications', 'booking_notifications',
            'payment_notifications', 'maintenance_alerts', 'marketing_emails',
            'station_updates', 'brand_color', 'logo_url', 'custom_welcome_message',
            'display_company_info', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_brand_color(self, value):
        """Validate hex color format"""
        if value and not value.startswith('#'):
            raise serializers.ValidationError("Brand color must be a valid hex color (e.g., #3B82F6)")
        if value and len(value) != 7:
            raise serializers.ValidationError("Brand color must be a 7-character hex color (e.g., #3B82F6)")
        return value

    def validate_max_session_duration_hours(self, value):
        """Validate session duration is reasonable"""
        if value < 1 or value > 24:
            raise serializers.ValidationError("Session duration must be between 1 and 24 hours")
        return value


class NotificationTemplateSerializer(serializers.ModelSerializer):
    """Serializer for notification templates"""

    template_type_display = serializers.CharField(source='get_template_type_display', read_only=True)

    class Meta:
        model = NotificationTemplate
        fields = [
            'id', 'template_type', 'template_type_display', 'subject',
            'email_body', 'sms_body', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'template_type_display', 'created_at', 'updated_at']

    def validate_sms_body(self, value):
        """Validate SMS body length"""
        if len(value) > 160:
            raise serializers.ValidationError("SMS body must be 160 characters or less")
        return value


class AvailableStationSerializer(serializers.ModelSerializer):
    """Serializer for available charging stations with real-time availability"""

    owner_name = serializers.CharField(source='owner.company_name', read_only=True)
    is_verified_owner = serializers.SerializerMethodField()
    available_connectors_detail = serializers.SerializerMethodField()
    distance = serializers.SerializerMethodField()
    estimated_wait_time = serializers.SerializerMethodField()
    pricing_info = serializers.SerializerMethodField()
    real_time_availability = serializers.SerializerMethodField()

    class Meta:
        model = ChargingStation
        fields = [
            'id', 'name', 'address', 'city', 'state', 'zip_code', 'country',
            'latitude', 'longitude', 'description', 'opening_hours',
            'status', 'rating', 'rating_count', 'price_range',
            'available_connectors', 'total_connectors',
            'has_restroom', 'has_wifi', 'has_restaurant', 'has_shopping',
            'main_image', 'created_at', 'owner_name', 'is_verified_owner',
            'available_connectors_detail', 'distance', 'estimated_wait_time',
            'pricing_info', 'real_time_availability'
        ]

    def get_is_verified_owner(self, obj):
        return obj.owner.verification_status == 'verified'

    def get_available_connectors_detail(self, obj):
        """Get detailed information about available connectors"""
        connectors = obj.connectors.filter(
            is_available=True,
            status='available'
        ).values(
            'connector_type',
            'power_kw',
            'available_quantity',
            'price_per_kwh'
        )

        connector_summary = {}
        for connector in connectors:
            connector_type = connector['connector_type']
            if connector_type not in connector_summary:
                connector_summary[connector_type] = {
                    'type': connector_type,
                    'power_kw': connector['power_kw'],
                    'available_count': 0,
                    'price_per_kwh': connector['price_per_kwh']
                }
            connector_summary[connector_type]['available_count'] += connector['available_quantity']

        return list(connector_summary.values())

    def get_distance(self, obj):
        """Calculate distance from user location if provided"""
        request = self.context.get('request')
        if request:
            user_lat = request.query_params.get('user_lat')
            user_lng = request.query_params.get('user_lng')

            if user_lat and user_lng and obj.latitude and obj.longitude:
                try:
                    from math import radians, cos, sin, asin, sqrt

                    # Haversine formula
                    lat1, lon1 = radians(float(user_lat)), radians(float(user_lng))
                    lat2, lon2 = radians(float(obj.latitude)), radians(float(obj.longitude))

                    dlat = lat2 - lat1
                    dlon = lon2 - lon1
                    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
                    c = 2 * asin(sqrt(a))
                    r = 6371  # Radius of earth in kilometers

                    return round(c * r, 2)
                except (ValueError, TypeError):
                    pass
        return None

    def get_estimated_wait_time(self, obj):
        """Estimate wait time based on current usage"""
        if obj.available_connectors > 0:
            return 0  # No wait if connectors are available

        # Simple estimation based on total connectors and typical session duration
        # In a real implementation, this would use historical data
        if obj.total_connectors > 0:
            avg_session_minutes = 45  # Average charging session
            utilization_rate = 0.7  # Typical utilization
            estimated_minutes = int(avg_session_minutes * utilization_rate)
            return max(5, estimated_minutes)  # Minimum 5 minutes

        return None

    def get_pricing_info(self, obj):
        """Get pricing information for the station"""
        connectors = obj.connectors.filter(
            is_available=True,
            price_per_kwh__isnull=False
        ).values_list('price_per_kwh', flat=True)

        if connectors:
            prices = list(connectors)
            return {
                'min_price': min(prices),
                'max_price': max(prices),
                'currency': 'ETB',
                'pricing_model': 'per_kwh'
            }

        return {
            'min_price': None,
            'max_price': None,
            'currency': 'ETB',
            'pricing_model': 'per_kwh'
        }

    def get_real_time_availability(self, obj):
        """Get real-time availability status"""
        if obj.status != 'operational':
            return {
                'status': 'unavailable',
                'reason': obj.get_status_display(),
                'last_updated': obj.updated_at.isoformat()
            }

        if obj.available_connectors == 0:
            return {
                'status': 'busy',
                'reason': 'All connectors occupied',
                'last_updated': obj.updated_at.isoformat()
            }

        return {
            'status': 'available',
            'reason': f'{obj.available_connectors} connectors available',
            'last_updated': obj.updated_at.isoformat()
        }


class ReviewReplySerializer(serializers.ModelSerializer):
    """Serializer for creating and updating review replies"""

    station_owner_name = serializers.SerializerMethodField()

    class Meta:
        model = ReviewReply
        fields = [
            'id', 'review', 'station_owner', 'station_owner_name',
            'reply_text', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'station_owner', 'station_owner_name', 'created_at', 'updated_at']

    def get_station_owner_name(self, obj):
        return obj.station_owner.company_name

    def validate(self, data):
        """Validate that the station owner owns the station being reviewed"""
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            try:
                station_owner = StationOwner.objects.get(user=request.user)
                review = data.get('review')

                if review and review.station.owner != station_owner:
                    raise serializers.ValidationError(
                        "You can only reply to reviews of your own stations."
                    )
            except StationOwner.DoesNotExist:
                raise serializers.ValidationError(
                    "Only station owners can reply to reviews."
                )

        return data


class ReviewReplyListSerializer(serializers.ModelSerializer):
    """Serializer for listing review replies (read-only)"""

    station_owner_name = serializers.SerializerMethodField()

    class Meta:
        model = ReviewReply
        fields = [
            'id', 'station_owner_name', 'reply_text', 'created_at'
        ]

    def get_station_owner_name(self, obj):
        return obj.station_owner.company_name


class PayoutMethodSerializer(serializers.ModelSerializer):
    """Serializer for station owner payout methods"""

    method_type_display = serializers.CharField(source='get_method_type_display', read_only=True)
    masked_details = serializers.SerializerMethodField()

    class Meta:
        model = PayoutMethod
        fields = [
            'id', 'method_type', 'method_type_display', 'account_holder_name',
            'bank_name', 'account_number', 'routing_number', 'swift_code',
            'card_number', 'card_type', 'expiry_month', 'expiry_year',
            'phone_number', 'provider', 'paypal_email', 'is_default',
            'is_verified', 'is_active', 'created_at', 'updated_at', 'masked_details'
        ]
        read_only_fields = ['id', 'is_verified', 'created_at', 'updated_at', 'masked_details']
        extra_kwargs = {
            'account_number': {'write_only': True},
            'card_number': {'write_only': True},
            'routing_number': {'write_only': True},
            'swift_code': {'write_only': True},
        }

    def get_masked_details(self, obj):
        """Return masked details for display"""
        return obj.get_masked_details()

    def validate(self, data):
        """Validate payout method based on type"""
        method_type = data.get('method_type')

        if method_type == PayoutMethod.MethodType.BANK_ACCOUNT:
            required_fields = ['account_holder_name', 'bank_name', 'account_number']
            for field in required_fields:
                if not data.get(field):
                    raise serializers.ValidationError(f"{field} is required for bank account method")

        elif method_type == PayoutMethod.MethodType.CARD:
            required_fields = ['account_holder_name', 'card_number', 'card_type', 'expiry_month', 'expiry_year']
            for field in required_fields:
                if not data.get(field):
                    raise serializers.ValidationError(f"{field} is required for card method")

            # Validate expiry date
            try:
                month = int(data.get('expiry_month', 0))
                year = int(data.get('expiry_year', 0))
                if not (1 <= month <= 12):
                    raise serializers.ValidationError("Invalid expiry month")
                if year < 2024:
                    raise serializers.ValidationError("Card has expired")
            except ValueError:
                raise serializers.ValidationError("Invalid expiry date format")

        elif method_type == PayoutMethod.MethodType.MOBILE_MONEY:
            required_fields = ['phone_number', 'provider']
            for field in required_fields:
                if not data.get(field):
                    raise serializers.ValidationError(f"{field} is required for mobile money method")

        elif method_type == PayoutMethod.MethodType.PAYPAL:
            if not data.get('paypal_email'):
                raise serializers.ValidationError("PayPal email is required for PayPal method")

        return data

    def create(self, validated_data):
        """Create payout method for the authenticated station owner"""
        request = self.context['request']
        try:
            station_owner = StationOwner.objects.get(user=request.user)
        except StationOwner.DoesNotExist:
            raise serializers.ValidationError("You must be a registered station owner to add payout methods")

        validated_data['station_owner'] = station_owner

        # Mask sensitive data before saving
        if 'account_number' in validated_data and validated_data['account_number']:
            # Keep only last 4 digits for display
            account_number = validated_data['account_number']
            validated_data['account_number'] = f"****{account_number[-4:]}"

        if 'card_number' in validated_data and validated_data['card_number']:
            # Keep only last 4 digits for display
            card_number = validated_data['card_number']
            validated_data['card_number'] = f"****{card_number[-4:]}"

        return super().create(validated_data)


class WithdrawalRequestSerializer(serializers.ModelSerializer):
    """Serializer for withdrawal requests"""

    station_owner_name = serializers.CharField(source='station_owner.company_name', read_only=True)
    payout_method_details = PayoutMethodSerializer(source='payout_method', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.username', read_only=True)

    class Meta:
        model = WithdrawalRequest
        fields = [
            'id', 'station_owner', 'station_owner_name', 'payout_method', 'payout_method_details',
            'amount', 'currency', 'description', 'status', 'status_display', 'reference_number',
            'approved_by', 'approved_by_name', 'admin_notes', 'processed_at',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'station_owner', 'station_owner_name', 'reference_number', 'status',
            'approved_by', 'approved_by_name', 'admin_notes', 'processed_at',
            'created_at', 'updated_at'
        ]

    def validate_amount(self, value):
        """Validate withdrawal amount"""
        if value <= 0:
            raise serializers.ValidationError("Withdrawal amount must be greater than 0")

        # TODO: Add balance validation here
        # Check if user has sufficient balance

        return value

    def validate_payout_method(self, value):
        """Validate that the payout method belongs to the requesting station owner"""
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            try:
                station_owner = StationOwner.objects.get(user=request.user)
                if value.station_owner != station_owner:
                    raise serializers.ValidationError("Invalid payout method")
                if not value.is_active:
                    raise serializers.ValidationError("Payout method is not active")
            except StationOwner.DoesNotExist:
                raise serializers.ValidationError("You must be a registered station owner")

        return value

    def create(self, validated_data):
        """Create withdrawal request for the authenticated station owner"""
        request = self.context['request']
        try:
            station_owner = StationOwner.objects.get(user=request.user)
        except StationOwner.DoesNotExist:
            raise serializers.ValidationError("You must be a registered station owner to request withdrawals")

        validated_data['station_owner'] = station_owner
        return super().create(validated_data)


class WithdrawalRequestAdminSerializer(serializers.ModelSerializer):
    """Serializer for admin management of withdrawal requests"""

    station_owner_name = serializers.CharField(source='station_owner.company_name', read_only=True)
    payout_method_details = PayoutMethodSerializer(source='payout_method', read_only=True)

    class Meta:
        model = WithdrawalRequest
        fields = [
            'id', 'station_owner', 'station_owner_name', 'payout_method', 'payout_method_details',
            'amount', 'currency', 'description', 'status', 'reference_number',
            'approved_by', 'admin_notes', 'processed_at', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'station_owner', 'station_owner_name', 'payout_method', 'payout_method_details',
            'amount', 'currency', 'description', 'reference_number', 'created_at', 'updated_at'
        ]

    def update(self, instance, validated_data):
        """Update withdrawal request status"""
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            # Set the admin who is updating the status
            if 'status' in validated_data:
                validated_data['approved_by'] = request.user

                # Set processed_at when status changes to completed/failed/rejected
                if validated_data['status'] in ['completed', 'failed', 'rejected']:
                    from django.utils import timezone
                    validated_data['processed_at'] = timezone.now()

        return super().update(instance, validated_data)


# Firestore Serializers

class FirestoreChargingConnectorSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    connector_type = serializers.ChoiceField(choices=ChargingConnector.ConnectorType.choices)
    connector_type_display = serializers.CharField(read_only=True, required=False)
    power_kw = serializers.DecimalField(max_digits=6, decimal_places=2)
    quantity = serializers.IntegerField(default=1)
    available_quantity = serializers.IntegerField(default=1)
    price_per_kwh = serializers.DecimalField(max_digits=6, decimal_places=2, required=False, allow_null=True)
    is_available = serializers.BooleanField(default=True)
    status = serializers.ChoiceField(choices=ChargingConnector.ConnectorStatus.choices, default='available')
    status_display = serializers.CharField(read_only=True, required=False)
    description = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    qr_code_token = serializers.CharField(read_only=True)
    qr_code_url = serializers.SerializerMethodField()
    
    def get_qr_code_url(self, obj):
        # Obj is a dict here
        return obj.get('qr_code_image')

class FirestoreStationImageSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    image = Base64ImageField(required=True)
    caption = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    order = serializers.IntegerField(default=0)

class FirestoreChargingStationSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    name = serializers.CharField(max_length=255)
    address = serializers.CharField(max_length=255)
    city = serializers.CharField(max_length=100)
    state = serializers.CharField(max_length=100)
    zip_code = serializers.CharField(max_length=20)
    country = serializers.CharField(max_length=100, default='United States')
    
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=False, allow_null=True)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=False, allow_null=True)
    
    description = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    opening_hours = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    
    has_restroom = serializers.BooleanField(default=False)
    has_wifi = serializers.BooleanField(default=False)
    has_restaurant = serializers.BooleanField(default=False)
    has_shopping = serializers.BooleanField(default=False)
    
    is_active = serializers.BooleanField(default=True)
    is_public = serializers.BooleanField(default=True)
    status = serializers.ChoiceField(choices=ChargingStation.StationStatus.choices, default='operational')
    
    rating = serializers.DecimalField(max_digits=3, decimal_places=2, default=0.0, read_only=True)
    rating_count = serializers.IntegerField(default=0, read_only=True)
    
    price_range = serializers.CharField(max_length=20, required=False, allow_blank=True, allow_null=True)
    available_connectors = serializers.IntegerField(default=0, read_only=True)
    total_connectors = serializers.IntegerField(default=0, read_only=True)
    
    main_image = Base64ImageField(required=False, allow_null=True)
    marker_icon = serializers.CharField(max_length=50, required=False, allow_blank=True, default='default')
    
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    
    # Nested fields
    connectors = FirestoreChargingConnectorSerializer(many=True, read_only=True)
    images = FirestoreStationImageSerializer(many=True, read_only=True)
    
    owner_id = serializers.CharField(read_only=True)
    owner_name = serializers.CharField(read_only=True)
    is_verified_owner = serializers.BooleanField(default=False, read_only=True)

    def create(self, validated_data):
        from utils.firestore_repo import firestore_repo
        
        # Add owner info from context
        request = self.context.get('request')
        if request and request.user:
            try:
                station_owner = StationOwner.objects.get(user=request.user)
                validated_data['owner_id'] = str(station_owner.id)
                validated_data['owner_name'] = station_owner.company_name
                validated_data['is_verified_owner'] = (station_owner.verification_status == 'verified')
            except StationOwner.DoesNotExist:
                raise serializers.ValidationError("Station Owner profile not found.")
        
        # Initialize lists
        validated_data['connectors'] = []
        validated_data['images'] = []
        
        return firestore_repo.create_station(validated_data)

    def update(self, instance, validated_data):
        from utils.firestore_repo import firestore_repo
        # instance is a dict here containing the current state
        station_id = instance.get('id')
        return firestore_repo.update_station(station_id, validated_data)


class FirestoreAvailableStationSerializer(serializers.Serializer):
    """Serializer for available charging stations (read-only)"""
    id = serializers.CharField(read_only=True)
    name = serializers.CharField(read_only=True)
    address = serializers.CharField(read_only=True)
    city = serializers.CharField(read_only=True)
    state = serializers.CharField(read_only=True)
    zip_code = serializers.CharField(read_only=True)
    country = serializers.CharField(read_only=True)
    
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6, read_only=True)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6, read_only=True)
    
    description = serializers.CharField(read_only=True)
    opening_hours = serializers.CharField(read_only=True)
    
    has_restroom = serializers.BooleanField(read_only=True)
    has_wifi = serializers.BooleanField(read_only=True)
    has_restaurant = serializers.BooleanField(read_only=True)
    has_shopping = serializers.BooleanField(read_only=True)
    
    status = serializers.CharField(read_only=True)
    rating = serializers.DecimalField(max_digits=3, decimal_places=2, read_only=True)
    rating_count = serializers.IntegerField(read_only=True)
    price_range = serializers.CharField(read_only=True)
    available_connectors = serializers.IntegerField(read_only=True)
    total_connectors = serializers.IntegerField(read_only=True)
    main_image = Base64ImageField(read_only=True, allow_null=True)
    created_at = serializers.DateTimeField(read_only=True)
    
    owner_name = serializers.CharField(read_only=True)
    is_verified_owner = serializers.BooleanField(read_only=True)
    
    available_connectors_detail = serializers.SerializerMethodField()
    distance = serializers.SerializerMethodField()
    estimated_wait_time = serializers.SerializerMethodField()
    pricing_info = serializers.SerializerMethodField()
    real_time_availability = serializers.SerializerMethodField()
    
    def get_available_connectors_detail(self, obj):
        # We need to fetch connectors! But doing it here per row is slow.
        # Ideally passed in obj or handled by view. 
        # For now, return empty or implement efficient fetch if passed.
        # If obj has 'connectors' key we use it. Get_queryset in view should populate it if possible.
        connectors = obj.get('connectors', [])
        summary = {}
        for c in connectors:
            if c.get('is_available') and c.get('status') == 'available':
                c_type = c.get('connector_type')
                if c_type not in summary:
                    summary[c_type] = {
                        'type': c_type,
                        'power_kw': c.get('power_kw'),
                        'available_count': 0,
                        'price_per_kwh': c.get('price_per_kwh')
                    }
                summary[c_type]['available_count'] += c.get('available_quantity', 0)
        return list(summary.values())

    def get_distance(self, obj):
        request = self.context.get('request')
        if request:
            user_lat = request.query_params.get('user_lat')
            user_lng = request.query_params.get('user_lng')
            
            lat = obj.get('latitude')
            lng = obj.get('longitude')
            
            if user_lat and user_lng and lat and lng:
                try:
                    from math import radians, cos, sin, asin, sqrt
                    lat1, lon1 = radians(float(user_lat)), radians(float(user_lng))
                    lat2, lon2 = radians(float(lat)), radians(float(lng))
                    dlat = lat2 - lat1
                    dlon = lon2 - lon1
                    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
                    c = 2 * asin(sqrt(a))
                    return round(c * 6371, 2)
                except (ValueError, TypeError):
                    pass
        return None

    def get_estimated_wait_time(self, obj):
        if obj.get('available_connectors', 0) > 0:
            return 0
        if obj.get('total_connectors', 0) > 0:
            return 5 # Mock 5 mins
        return None

    def get_pricing_info(self, obj):
        # Need connectors
        connectors = obj.get('connectors', [])
        prices = [float(c['price_per_kwh']) for c in connectors if c.get('price_per_kwh') and c.get('is_available')]
        if prices:
             return {
                'min_price': min(prices),
                'max_price': max(prices),
                'currency': 'ETB',
                'pricing_model': 'per_kwh'
             }
        return {'min_price': None, 'max_price': None}

    def get_real_time_availability(self, obj):
         if obj.get('status') != 'operational':
              return {'status': 'unavailable', 'reason': obj.get('status')}
         if obj.get('available_connectors') == 0:
              return {'status': 'busy', 'reason': 'All connectors occupied'}
         return {'status': 'available', 'reason': f"{obj.get('available_connectors')} connectors available"}


class FirestoreStationReviewSerializer(serializers.Serializer):
    """Serializer for Firestore reviews"""
    id = serializers.CharField(read_only=True)
    user_id = serializers.CharField(read_only=True)
    user_name = serializers.CharField(required=False)
    user_email = serializers.CharField(required=False)
    station_id = serializers.CharField(read_only=True) # or required if creating independently
    
    rating = serializers.IntegerField(min_value=1, max_value=5)
    review_text = serializers.CharField(required=False, allow_blank=True)
    charging_speed_rating = serializers.IntegerField(min_value=1, max_value=5, required=False, allow_null=True)
    location_rating = serializers.IntegerField(min_value=1, max_value=5, required=False, allow_null=True)
    amenities_rating = serializers.IntegerField(min_value=1, max_value=5, required=False, allow_null=True)
    
    is_verified_review = serializers.BooleanField(default=False, read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    
    reply = serializers.DictField(read_only=True, required=False, allow_null=True)

    def create(self, validated_data):
        from utils.firestore_repo import firestore_repo
        
        request = self.context.get('request')
        station_id = self.context.get('station_id')
        
        if request and request.user:
            validated_data['user_id'] = str(request.user.id)
            validated_data['user_name'] = f"{request.user.first_name} {request.user.last_name}".strip() or request.user.email.split('@')[0]
            # Mask email
            email = request.user.email
            if '@' in email:
                 u, d = email.split('@', 1)
                 validated_data['user_email'] = f"{u[:2]}***@{d}"
            
        validated_data['created_at'] = datetime.now()
        
        # We need station owner id for filtering by owner
        # Fetch station
        station = firestore_repo.get_station(station_id)
        if station:
             validated_data['station_owner_id'] = station.get('owner_id')
             validated_data['station_name'] = station.get('name')
        
        return firestore_repo.create_review(station_id, validated_data)

    def update(self, instance, validated_data):
        from utils.firestore_repo import firestore_repo
        # instance is dict
        station_id = instance.get('station_id')
        review_id = instance.get('id')
        return firestore_repo.update_review(station_id, review_id, validated_data)

