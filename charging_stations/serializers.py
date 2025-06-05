from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import StationOwner, ChargingStation, StationImage, ChargingConnector, FavoriteStation, StationReview
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

    class Meta:
        model = ChargingStation
        fields = [
            'id', 'name', 'latitude', 'longitude', 'rating',
            'status', 'price_range', 'available_connectors',
            'total_connectors', 'marker_icon', 'owner_name',
            'is_verified_owner', 'connector_types'
        ]

    def get_is_verified_owner(self, obj):
        return obj.owner.verification_status == 'verified'

    def get_connector_types(self, obj):
        return list(obj.connectors.values_list('connector_type', flat=True).distinct())

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

    class Meta:
        model = StationReview
        fields = [
            'id', 'user_name', 'user_email', 'rating', 'review_text',
            'charging_speed_rating', 'location_rating', 'amenities_rating',
            'is_verified_review', 'created_at'
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
