from rest_framework import serializers
from django.contrib.auth import get_user_model, authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from rest_framework.authtoken.models import Token
from django.utils.crypto import get_random_string
import random
import string
import uuid

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Serializer for the custom user model."""

    class Meta:
        model = User
        fields = ('id', 'email', 'first_name', 'last_name', 'is_verified')
        read_only_fields = ('id', 'is_verified')


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for the user profile."""
    ev_connector_type_display = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id', 'email', 'first_name', 'last_name',
            'phone_number', 'address', 'city', 'state', 'zip_code',
            'profile_picture', 'is_verified', 'ev_battery_capacity_kwh',
            'ev_connector_type', 'ev_connector_type_display'
        )
        read_only_fields = ('id', 'email', 'is_verified', 'ev_connector_type_display')

    def get_ev_connector_type_display(self, obj):
        """Return the display name for the EV connector type."""
        return obj.get_ev_connector_type_display() if obj.ev_connector_type else None


class RegisterSerializer(serializers.ModelSerializer):
    """Serializer for user registration."""
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
        # Generate a 6-digit verification code
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
    """Serializer for email verification."""
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
    """Serializer for user login."""
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, style={'input_type': 'password'})


class ResendVerificationSerializer(serializers.Serializer):
    """Serializer for resending verification code."""
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
    """Serializer for changing password."""
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
    """Serializer for requesting a password reset email."""
    email = serializers.EmailField(required=True)

    def validate_email(self, value):
        User = get_user_model()
        try:
            user = User.objects.get(email=value)
        except User.DoesNotExist:
            # We don't want to reveal if a user exists or not for security reasons
            # So we'll just pass validation and handle it in the view
            pass
        return value


class ResetPasswordSerializer(serializers.Serializer):
    """Serializer for resetting password with token."""
    token = serializers.CharField(required=True)
    email = serializers.EmailField(required=True)
    new_password = serializers.CharField(required=True, style={'input_type': 'password'})

    def validate(self, attrs):
        User = get_user_model()

        try:
            user = User.objects.get(email=attrs.get('email'))
        except User.DoesNotExist:
            raise serializers.ValidationError({"email": "User with this email does not exist."})

        # Check if the reset token is valid
        if not hasattr(user, 'password_reset_token') or user.password_reset_token != attrs.get('token'):
            raise serializers.ValidationError({"token": "Invalid or expired token."})

        # Validate the new password
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
            # Clear the reset token after use
            user.password_reset_token = None
            user.save()
            return user
        except User.DoesNotExist:
            raise serializers.ValidationError({"email": "User with this email does not exist."})
