from rest_framework import serializers
from utils.fields.base64_field import Base64ImageField

class FirestoreVehicleSerializer(serializers.Serializer):
    """Serializer for Vehicle data in Firestore"""
    id = serializers.CharField(read_only=True)
    name = serializers.CharField(max_length=100, help_text='Vehicle name or nickname')
    make = serializers.CharField(max_length=100)
    model = serializers.CharField(max_length=100)
    year = serializers.IntegerField()
    
    battery_capacity_kwh = serializers.DecimalField(max_digits=6, decimal_places=2)
    usable_battery_kwh = serializers.DecimalField(max_digits=6, decimal_places=2, required=False, allow_null=True)
    
    connector_type = serializers.CharField(max_length=20) # Choice field ideally, but string for NoSQL flexibility
    max_charging_speed_kw = serializers.DecimalField(max_digits=6, decimal_places=2, required=False, allow_null=True)
    preferred_charging_speed = serializers.CharField(max_length=20, required=False, default='fast')
    
    estimated_range_km = serializers.IntegerField(required=False, allow_null=True)
    efficiency_kwh_per_100km = serializers.DecimalField(max_digits=4, decimal_places=2, required=False, allow_null=True)
    
    is_primary = serializers.BooleanField(default=False)
    is_active = serializers.BooleanField(default=True)
    
    color = serializers.CharField(max_length=50, required=False, allow_blank=True)
    license_plate = serializers.CharField(max_length=20, required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    
    vehicle_image = Base64ImageField(required=False, allow_null=True)
    
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)


class FirestoreUserSerializer(serializers.Serializer):
    """Serializer for User Profile data in Firestore"""
    id = serializers.CharField(read_only=True)
    email = serializers.EmailField(read_only=True) # From Auth
    
    # Profile Fields
    first_name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    phone_number = serializers.CharField(max_length=20, required=False, allow_blank=True)
    address = serializers.CharField(max_length=255, required=False, allow_blank=True)
    city = serializers.CharField(max_length=100, required=False, allow_blank=True)
    state = serializers.CharField(max_length=100, required=False, allow_blank=True)
    zip_code = serializers.CharField(max_length=20, required=False, allow_blank=True)
    
    profile_picture = Base64ImageField(required=False, allow_null=True)
    
    # Telegram
    telegram_username = serializers.CharField(max_length=100, required=False, allow_blank=True)
    
    # Preferences
    notification_preferences = serializers.DictField(required=False, default=dict)
    
    is_verified = serializers.BooleanField(read_only=True) # Managed by backend logic
    
    active_vehicle_id = serializers.CharField(required=False, allow_null=True)
    
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
