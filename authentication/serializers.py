from rest_framework import serializers
from django.contrib.auth import get_user_model, authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from rest_framework.authtoken.models import Token
from django.utils.crypto import get_random_string
from dj_rest_auth.registration.serializers import RegisterSerializer as DjRestAuthRegisterSerializer
from dj_rest_auth.serializers import LoginSerializer as DjRestAuthLoginSerializer
from dj_rest_auth.serializers import UserDetailsSerializer
from .models import Vehicle
import random
import string
import uuid

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'first_name', 'last_name', 'is_verified')
        read_only_fields = ('id', 'is_verified')


class UserProfileSerializer(serializers.ModelSerializer):
    ev_connector_type_display = serializers.SerializerMethodField()
    notification_preferences = serializers.SerializerMethodField()
    unread_notifications_count = serializers.IntegerField(source='unread_notifications', read_only=True)

    class Meta:
        model = User
        fields = (
            'id', 'email', 'first_name', 'last_name',
            'phone_number', 'address', 'city', 'state', 'zip_code',
            'profile_picture', 'is_verified', 'ev_battery_capacity_kwh',
            'ev_connector_type', 'ev_connector_type_display',
            'notification_preferences', 'unread_notifications_count'
        )
        read_only_fields = ('id', 'email', 'is_verified', 'ev_connector_type_display',
                           'unread_notifications_count')

    def get_ev_connector_type_display(self, obj):
        return obj.get_ev_connector_type_display() if obj.ev_connector_type else None

    def get_notification_preferences(self, obj):
        return obj.get_notification_preferences()

    def update(self, instance, validated_data):
        # Handle notification preferences separately
        notification_preferences = self.initial_data.get('notification_preferences')
        if notification_preferences:
            instance.set_notification_preferences(notification_preferences)

        return super().update(instance, validated_data)


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    password2 = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})

    class Meta:
        model = User
        fields = ('email', 'password', 'password2', 'first_name', 'last_name')
        extra_kwargs = {
            'first_name': {'required': True},
            'last_name': {'required': True}
        }

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        try:
            validate_password(attrs['password'])
        except ValidationError as e:
            raise serializers.ValidationError({"password": list(e.messages)})

        return attrs

    def create(self, validated_data):
        verification_code = ''.join(random.choices(string.digits, k=6))

        user = User.objects.create_user(
            email=validated_data['email'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            verification_code=verification_code
        )

        user.set_password(validated_data['password'])
        user.save()

        return user


class VerifyEmailSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    verification_code = serializers.CharField(required=True)

    def validate(self, attrs):
        email = attrs.get('email')
        verification_code = attrs.get('verification_code')

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError({"email": "User with this email does not exist."})

        if user.is_verified:
            raise serializers.ValidationError({"email": "Email is already verified."})

        if user.verification_code != verification_code:
            raise serializers.ValidationError({"verification_code": "Invalid verification code."})

        return attrs


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, style={'input_type': 'password'})


class ResendVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)

    def validate(self, attrs):
        email = attrs.get('email')

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError({"email": "User with this email does not exist."})

        if user.is_verified:
            raise serializers.ValidationError({"email": "Email is already verified."})

        return attrs


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(required=True, style={'input_type': 'password'})
    new_password = serializers.CharField(required=True, style={'input_type': 'password'})

    def validate_current_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value

    def validate_new_password(self, value):
        try:
            validate_password(value)
        except ValidationError as e:
            raise serializers.ValidationError(list(e.messages))
        return value

    def save(self, **kwargs):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)

    def validate_email(self, value):
        User = get_user_model()
        try:
            user = User.objects.get(email=value)
        except User.DoesNotExist:
            pass
        return value


class ResetPasswordSerializer(serializers.Serializer):
    token = serializers.CharField(required=True)
    email = serializers.EmailField(required=True)
    new_password = serializers.CharField(required=True, style={'input_type': 'password'})

    def validate(self, attrs):
        User = get_user_model()

        try:
            user = User.objects.get(email=attrs.get('email'))
        except User.DoesNotExist:
            raise serializers.ValidationError({"email": "User with this email does not exist."})


        if not hasattr(user, 'password_reset_token') or user.password_reset_token != attrs.get('token'):
            raise serializers.ValidationError({"token": "Invalid or expired token."})

        try:
            validate_password(attrs.get('new_password'), user)
        except ValidationError as e:
            raise serializers.ValidationError({"new_password": list(e.messages)})

        return attrs

    def save(self, **kwargs):
        User = get_user_model()
        email = self.validated_data['email']
        new_password = self.validated_data['new_password']

        try:
            user = User.objects.get(email=email)
            user.set_password(new_password)
            user.password_reset_token = None
            user.save()
            return user
        except User.DoesNotExist:
            raise serializers.ValidationError({"email": "User with this email does not exist."})


class CustomUserDetailsSerializer(UserDetailsSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'first_name', 'last_name', 'is_verified')
        read_only_fields = ('id', 'email', 'is_verified')


class CustomRegisterSerializer(DjRestAuthRegisterSerializer):
    username = None
    email = serializers.EmailField(required=True)
    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)
    password1 = serializers.CharField(write_only=True, style={'input_type': 'password'})
    password2 = serializers.CharField(write_only=True, style={'input_type': 'password'})

    def validate(self, attrs):
        if attrs['password1'] != attrs['password2']:
            raise serializers.ValidationError({"password2": "Password fields didn't match."})
        return attrs

    def get_cleaned_data(self):
        return {
            'email': self.validated_data.get('email', ''),
            'first_name': self.validated_data.get('first_name', ''),
            'last_name': self.validated_data.get('last_name', ''),
            'password1': self.validated_data.get('password1', ''),
        }

    def save(self, request):
        user = User.objects.create_user(
            email=self.validated_data['email'],
            first_name=self.validated_data['first_name'],
            last_name=self.validated_data['last_name'],
            verification_code=''.join(random.choices(string.digits, k=6))
        )
        user.set_password(self.validated_data['password1'])
        user.save()
        return user


class CustomLoginSerializer(DjRestAuthLoginSerializer):
    username = None
    email = serializers.EmailField(required=True)
    password = serializers.CharField(style={'input_type': 'password'})

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        if email and password:
            user = authenticate(request=self.context.get('request'), email=email, password=password)
            if not user:
                msg = _('Unable to log in with provided credentials.')
                raise serializers.ValidationError(msg, code='authorization')

            # We'll handle unverified emails in the view, not as an error here
            # This allows the app to redirect to verification page
        else:
            msg = _('Must include "email" and "password".')
            raise serializers.ValidationError(msg, code='authorization')

        attrs['user'] = user
        return attrs


class VehicleSerializer(serializers.ModelSerializer):
    connector_type_display = serializers.SerializerMethodField()

    class Meta:
        model = Vehicle
        fields = (
            'id', 'name', 'make', 'model', 'year',
            'battery_capacity_kwh', 'connector_type',
            'connector_type_display', 'is_primary',
            'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at')

    def get_connector_type_display(self, obj):
        return obj.get_connector_type_display()

    def validate(self, attrs):
        # If this is a new vehicle and is_primary is True, or if is_primary is being set to True
        if (not self.instance and attrs.get('is_primary', False)) or \
           (self.instance and attrs.get('is_primary', False) and not self.instance.is_primary):
            # Set all other vehicles of this user to not primary
            Vehicle.objects.filter(user=self.context['request'].user, is_primary=True).update(is_primary=False)
        return attrs


class VehicleListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vehicle
        fields = ('id', 'name', 'make', 'model', 'year', 'is_primary')