from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import StationOwner, ChargingStation, StationImage, ChargingConnector, FavoriteStation
import random
import string

User = get_user_model()

class StationOwnerRegistrationSerializer(serializers.Serializer):
    """
    Serializer for station owner registration.
    """
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
        # Create user
        user = User(
            email=validated_data['email'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            is_verified=False,  # User needs to verify email
        )

        # Generate verification code
        verification_code = ''.join(random.choices(string.digits, k=6))
        user.verification_code = verification_code

        # Set password
        user.set_password(validated_data['password'])
        user.save()

        # Create station owner profile
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
    """
    Serializer for station owner profile.
    """
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
        # Update the station owner profile
        instance = super().update(instance, validated_data)

        # Check if all required fields are filled
        required_fields = ['business_registration_number', 'business_license', 'id_proof']
        is_complete = all(getattr(instance, field) for field in required_fields)

        # Update profile completion status
        if is_complete and not instance.is_profile_completed:
            instance.is_profile_completed = True
            instance.save()

        return instance

class ChargingConnectorSerializer(serializers.ModelSerializer):
    """
    Serializer for charging connectors.
    """
    connector_type_display = serializers.CharField(source='get_connector_type_display', read_only=True)

    class Meta:
        model = ChargingConnector
        fields = ['id', 'connector_type', 'connector_type_display', 'power_kw', 'quantity', 'price_per_kwh', 'is_available']

class StationImageSerializer(serializers.ModelSerializer):
    """
    Serializer for station images.
    """
    class Meta:
        model = StationImage
        fields = ['id', 'image', 'caption', 'order']

class ChargingStationSerializer(serializers.ModelSerializer):
    """
    Serializer for charging stations.
    """
    connectors = ChargingConnectorSerializer(many=True, read_only=True)
    images = StationImageSerializer(many=True, read_only=True)
    owner_name = serializers.CharField(source='owner.company_name', read_only=True)
    is_verified_owner = serializers.SerializerMethodField()

    class Meta:
        model = ChargingStation
        fields = [
            'id', 'name', 'address', 'city', 'state', 'zip_code', 'country',
            'latitude', 'longitude', 'description', 'opening_hours',
            'is_active', 'is_operational', 'is_public', 'status', 'rating', 'rating_count',
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
        # Get the current user's station owner profile
        user = self.context['request'].user
        try:
            station_owner = StationOwner.objects.get(user=user)
        except StationOwner.DoesNotExist:
            raise serializers.ValidationError("You must be a registered station owner to add stations.")

        # Check if the station owner's profile is completed and verified
        if not station_owner.is_profile_completed:
            raise serializers.ValidationError("Please complete your profile before adding stations.")

        # Create the charging station
        validated_data['owner'] = station_owner
        return super().create(validated_data)

class MapStationSerializer(serializers.ModelSerializer):
    """
    Simplified serializer for charging stations on the map.
    """
    owner_name = serializers.CharField(source='owner.company_name', read_only=True)
    is_verified_owner = serializers.SerializerMethodField()
    connector_types = serializers.SerializerMethodField()

    class Meta:
        model = ChargingStation
        fields = [
            'id', 'name', 'latitude', 'longitude', 'rating',
            'is_operational', 'status', 'price_range', 'available_connectors',
            'total_connectors', 'marker_icon', 'owner_name',
            'is_verified_owner', 'connector_types'
        ]

    def get_is_verified_owner(self, obj):
        return obj.owner.verification_status == 'verified'

    def get_connector_types(self, obj):
        return list(obj.connectors.values_list('connector_type', flat=True).distinct())

class StationDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for a single charging station.
    """
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
            'is_active', 'is_operational', 'status', 'rating', 'rating_count',
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
    """
    Serializer for favorite stations.
    """
    station = MapStationSerializer(read_only=True)

    class Meta:
        model = FavoriteStation
        fields = ['id', 'station', 'created_at']
        read_only_fields = ['id', 'created_at']
