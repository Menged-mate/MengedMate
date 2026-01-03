from rest_framework import serializers
from utils.fields.base64_field import Base64ImageField

class FirestoreSupportTicketSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    user_id = serializers.CharField(read_only=True) # Set in view
    email = serializers.EmailField()
    subject = serializers.CharField(max_length=255)
    description = serializers.CharField()
    
    priority = serializers.CharField(max_length=10, default='medium')
    status = serializers.CharField(read_only=True)
    
    screenshot = Base64ImageField(required=False, allow_null=True)
    phone_number = serializers.CharField(max_length=20, required=False, allow_blank=True)
    
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    resolved_at = serializers.DateTimeField(read_only=True)

class FirestoreFAQSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    category = serializers.CharField()
    question = serializers.CharField()
    answer = serializers.CharField()
    order = serializers.IntegerField(default=0)
    view_count = serializers.IntegerField(read_only=True)
