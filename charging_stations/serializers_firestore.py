from rest_framework import serializers
from utils.fields.base64_field import Base64ImageField, Base64FileField
from utils.firestore_repo import firestore_repo

class FirestoreStationOwnerSerializer(serializers.Serializer):
    """
    Serializer for Station Owner Profile in Firestore.
    """
    id = serializers.CharField(read_only=True)
    user_id = serializers.CharField(read_only=True)
    
    company_name = serializers.CharField(max_length=255, required=True)
    business_registration_number = serializers.CharField(max_length=100, required=False, allow_blank=True)
    
    # Status
    verification_status = serializers.ChoiceField(
        choices=[('pending', 'Pending'), ('verified', 'Verified'), ('rejected', 'Rejected')],
        default='pending',
        read_only=True
    )
    
    # Documents (Base64)
    business_document = Base64FileField(required=False, allow_null=True)
    business_license = Base64FileField(required=False, allow_null=True)
    id_proof = Base64FileField(required=False, allow_null=True)
    utility_bill = Base64FileField(required=False, allow_null=True)
    
    contact_phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    contact_email = serializers.EmailField(required=False, allow_blank=True)
    
    website = serializers.URLField(required=False, allow_blank=True)
    description = serializers.CharField(required=False, allow_blank=True)
    
    is_profile_completed = serializers.BooleanField(default=False)
    
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    verified_at = serializers.DateTimeField(read_only=True)

    def create(self, validated_data):
        # We generally won't use this directly for creation via API as it's tied to User Registration
        # But if we did:
        user_id = validated_data.pop('user_id', None)
        if not user_id:
            raise serializers.ValidationError("user_id required for StationOwner creation")
        
        return firestore_repo.create_station_owner(user_id, validated_data)

    def update(self, instance, validated_data):
        # instance is a dict here since it comes from Firestore
        user_id = instance.get('id')
        if not user_id:
             raise serializers.ValidationError("Instance has no ID")
             
        # Log completion
        if not instance.get('is_profile_completed') and validated_data.get('is_profile_completed'):
            pass # Logic handled in view usually

        return firestore_repo.update_station_owner(user_id, validated_data)

class FirestorePayoutMethodSerializer(serializers.Serializer):
    """Serializer for Payout Methods in Firestore."""
    id = serializers.CharField(read_only=True)
    method_type = serializers.ChoiceField(choices=[
        ('bank_account', 'Bank Account'), 
        ('mobile_money', 'Mobile Money'), 
        ('card', 'Credit/Debit Card'),
        ('paypal', 'PayPal')
    ])
    
    # Common fields
    account_holder_name = serializers.CharField(max_length=255)
    is_default = serializers.BooleanField(default=False)
    is_active = serializers.BooleanField(default=True)
    
    # Bank fields
    bank_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    account_number = serializers.CharField(max_length=50, required=False, allow_blank=True)
    routing_number = serializers.CharField(max_length=50, required=False, allow_blank=True)
    swift_code = serializers.CharField(max_length=50, required=False, allow_blank=True)

    # Mobile Money fields
    provider = serializers.CharField(max_length=50, required=False, allow_blank=True) # e.g. Telebirr
    phone_number = serializers.CharField(max_length=20, required=False, allow_blank=True)
    
    # Card fields/PayPal
    # (Simplified for now, add others if needed)
    
    created_at = serializers.DateTimeField(read_only=True)

    def validate(self, attrs):
        method = attrs.get('method_type')
        
        if method == 'bank_account':
            if not attrs.get('bank_name'):
                raise serializers.ValidationError({"bank_name": "Required for bank account."})
            if not attrs.get('account_number'):
                raise serializers.ValidationError({"account_number": "Required for bank account."})
                
        elif method == 'mobile_money':
            if not attrs.get('provider'):
                raise serializers.ValidationError({"provider": "Required for mobile money."})
            if not attrs.get('phone_number'):
                raise serializers.ValidationError({"phone_number": "Required for mobile money."})
                
        return attrs


class FirestoreWithdrawalRequestSerializer(serializers.Serializer):
    """Serializer for Withdrawal Requests"""
    id = serializers.CharField(read_only=True)
    owner_id = serializers.CharField(read_only=True)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    description = serializers.CharField(required=False, allow_blank=True)
    
    # Store snapshot of payout method
    payment_method_snapshot = serializers.DictField(read_only=True)
    payment_method_id = serializers.CharField(write_only=True)
    
    status = serializers.ChoiceField(choices=[
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('completed', 'Completed')
    ], default='pending', read_only=True)
    
    admin_note = serializers.CharField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be positive.")
        return value


    
    def create(self, validated_data):
        from utils.firestore_repo import firestore_repo
        from decimal import Decimal
        
        # Convert Decimal fields
        if 'amount' in validated_data and isinstance(validated_data['amount'], Decimal):
            validated_data['amount'] = float(validated_data['amount'])
            
        # Ensure station owner ID is available from context or validated data
        request = self.context.get('request')
        if request and request.user:
            station_owner = firestore_repo.get_station_owner(request.user.id)
            if not station_owner:
                 raise serializers.ValidationError("Station owner profile not found.")
            validated_data['owner_id'] = station_owner.get('id')
            
        return firestore_repo.create_withdrawal(validated_data)

    def update(self, instance, validated_data):
        from utils.firestore_repo import firestore_repo
        from decimal import Decimal
        
        # Convert Decimal fields
        if 'amount' in validated_data and isinstance(validated_data['amount'], Decimal):
            validated_data['amount'] = float(validated_data['amount'])
            
        request_id = instance.get('id')
        return firestore_repo.update_withdrawal(request_id, validated_data)
