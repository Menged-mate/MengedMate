from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import (
    StationOwner, ChargingStation, StationImage, ChargingConnector,
    FavoriteStation, StationReview, ReviewReply, StationOwnerSettings, NotificationTemplate,
    PayoutMethod
)
import random
import string

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

        station_owner = StationOwner.objects.create(
            user=user,
            company_name=validated_data['company_name'],
            is_profile_completed=False,
            verification_status='pending'
        )

        return {
            'user': user,
            'station_owner': station_owner,
            'verification_code': verification_code
        }

class StationOwnerProfileSerializer(serializers.ModelSerializer):

    email = serializers.EmailField(source='user.email', read_only=True)
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)

    class Meta:
        model = StationOwner
        fields = [
            'id', 'email', 'first_name', 'last_name', 'company_name',
            'business_registration_number', 'verification_status',
            'business_license', 'id_proof', 'utility_bill',
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

    class Meta:
        model = StationImage
        fields = ['id', 'image', 'caption', 'order']

class ChargingStationSerializer(serializers.ModelSerializer):

    connectors = ChargingConnectorSerializer(many=True, read_only=True)
    images = StationImageSerializer(many=True, read_only=True)
    owner_name = serializers.CharField(source='owner.company_name', read_only=True)
    is_verified_owner = serializers.SerializerMethodField()

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
