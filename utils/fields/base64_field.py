"""
Custom DRF Serializer Fields for Base64 Image Handling

These fields automatically handle encoding/decoding of images
to/from Base64 strings in API requests and responses.
"""

import base64
import io
import uuid
from django.core.files.base import ContentFile
from django.core.exceptions import ValidationError
from rest_framework import serializers
from PIL import Image

from utils.base64_image import (
    encode_image_to_base64,
    decode_base64_to_bytes,
    is_valid_base64_image,
    get_base64_size_bytes,
    validate_image_size,
    DEFAULT_MAX_IMAGE_SIZE_MB,
    DEFAULT_COMPRESSION_QUALITY,
)


class Base64ImageField(serializers.Field):
    """
    A serializer field that handles Base64 encoded images.
    
    On write: Accepts Base64 string (with or without data URI prefix)
              and validates/compresses it before storing.
    On read: Returns the stored Base64 string.
    
    Usage:
        class MySerializer(serializers.ModelSerializer):
            image = Base64ImageField(required=False, allow_null=True)
    """
    
    def __init__(
        self,
        max_size_mb: float = DEFAULT_MAX_IMAGE_SIZE_MB,
        compress: bool = True,
        quality: int = DEFAULT_COMPRESSION_QUALITY,
        max_dimension: int = 1920,
        required: bool = False,
        allow_null: bool = True,
        **kwargs
    ):
        self.max_size_mb = max_size_mb
        self.compress = compress
        self.quality = quality
        self.max_dimension = max_dimension
        super().__init__(required=required, allow_null=allow_null, **kwargs)
    
    def to_internal_value(self, data):
        """
        Convert incoming data to internal representation.
        Handles both Base64 strings and file uploads.
        """
        if data is None or data == '':
            return None
        
        # If it's already a Base64 string
        if isinstance(data, str):
            # Handle data URI format
            if data.startswith('data:'):
                # Validate it's an image type
                if not data.startswith('data:image/'):
                    raise serializers.ValidationError(
                        "Invalid data URI. Must be an image type."
                    )
            
            # Validate it's a valid Base64 image
            if not is_valid_base64_image(data):
                raise serializers.ValidationError(
                    "Invalid Base64 image data."
                )
            
            # Check size
            size_bytes = get_base64_size_bytes(data)
            max_bytes = self.max_size_mb * 1024 * 1024
            
            if size_bytes > max_bytes:
                # Try to compress
                if self.compress:
                    try:
                        image_bytes = decode_base64_to_bytes(data)
                        from utils.base64_image import compress_image
                        compressed, fmt = compress_image(
                            io.BytesIO(image_bytes),
                            quality=self.quality,
                            max_dimension=self.max_dimension
                        )
                        data = encode_image_to_base64(
                            compressed,
                            compress=False,
                            include_data_uri=True
                        )
                    except Exception as e:
                        raise serializers.ValidationError(
                            f"Failed to compress image: {str(e)}"
                        )
                else:
                    raise serializers.ValidationError(
                        f"Image size exceeds maximum of {self.max_size_mb}MB"
                    )
            
            return data
        
        # If it's a file upload (InMemoryUploadedFile or similar)
        if hasattr(data, 'read'):
            try:
                # Validate size
                validate_image_size(data, self.max_size_mb)
                
                # Encode to Base64
                return encode_image_to_base64(
                    data,
                    compress=self.compress,
                    quality=self.quality,
                    max_dimension=self.max_dimension,
                    include_data_uri=True
                )
            except ValidationError as e:
                raise serializers.ValidationError(str(e))
            except Exception as e:
                raise serializers.ValidationError(
                    f"Failed to process image: {str(e)}"
                )
        
        raise serializers.ValidationError(
            "Invalid input. Expected a Base64 string or file upload."
        )
    
    def to_representation(self, value):
        """
        Convert internal value to external representation.
        Returns the Base64 string as-is.
        """
        if value is None or value == '':
            return None
        
        # If it's already a string (Base64), return it
        if isinstance(value, str):
            return value
        
        # If it's a file field (legacy data), encode it
        if hasattr(value, 'read'):
            try:
                return encode_image_to_base64(
                    value,
                    compress=False,
                    include_data_uri=True
                )
            except Exception:
                return None
        
        return None


class Base64FileField(serializers.Field):
    """
    A serializer field that handles Base64 encoded files (PDFs, documents, etc).
    
    Similar to Base64ImageField but without image-specific processing.
    """
    
    ALLOWED_MIME_TYPES = [
        'application/pdf',
        'image/jpeg',
        'image/png',
        'image/gif',
        'image/webp',
    ]
    
    def __init__(
        self,
        max_size_mb: float = 5.0,
        allowed_mime_types: list = None,
        required: bool = False,
        allow_null: bool = True,
        **kwargs
    ):
        self.max_size_mb = max_size_mb
        self.allowed_mime_types = allowed_mime_types or self.ALLOWED_MIME_TYPES
        super().__init__(required=required, allow_null=allow_null, **kwargs)
    
    def to_internal_value(self, data):
        """Convert incoming data to internal representation."""
        if data is None or data == '':
            return None
        
        if isinstance(data, str):
            # Validate data URI format
            if data.startswith('data:'):
                # Extract MIME type
                try:
                    header = data.split(',', 1)[0]
                    mime_type = header.replace('data:', '').replace(';base64', '')
                    
                    if mime_type not in self.allowed_mime_types:
                        raise serializers.ValidationError(
                            f"File type '{mime_type}' is not allowed. "
                            f"Allowed types: {', '.join(self.allowed_mime_types)}"
                        )
                except IndexError:
                    raise serializers.ValidationError("Invalid data URI format.")
            
            # Check size
            try:
                if data.startswith('data:'):
                    base64_data = data.split(',', 1)[1]
                else:
                    base64_data = data
                
                decoded = base64.b64decode(base64_data)
                size_bytes = len(decoded)
                max_bytes = self.max_size_mb * 1024 * 1024
                
                if size_bytes > max_bytes:
                    raise serializers.ValidationError(
                        f"File size exceeds maximum of {self.max_size_mb}MB"
                    )
            except Exception as e:
                if isinstance(e, serializers.ValidationError):
                    raise
                raise serializers.ValidationError(
                    f"Invalid Base64 data: {str(e)}"
                )
            
            return data
        
        # Handle file upload
        if hasattr(data, 'read'):
            try:
                data.seek(0)
                file_content = data.read()
                
                # Check size
                if len(file_content) > self.max_size_mb * 1024 * 1024:
                    raise serializers.ValidationError(
                        f"File size exceeds maximum of {self.max_size_mb}MB"
                    )
                
                # Determine MIME type
                mime_type = getattr(data, 'content_type', 'application/octet-stream')
                
                # Encode to Base64
                base64_string = base64.b64encode(file_content).decode('utf-8')
                return f"data:{mime_type};base64,{base64_string}"
            except Exception as e:
                if isinstance(e, serializers.ValidationError):
                    raise
                raise serializers.ValidationError(
                    f"Failed to process file: {str(e)}"
                )
        
        raise serializers.ValidationError(
            "Invalid input. Expected a Base64 string or file upload."
        )
    
    def to_representation(self, value):
        """Convert internal value to external representation."""
        if value is None or value == '':
            return None
        
        if isinstance(value, str):
            return value
        
        if hasattr(value, 'read'):
            try:
                value.seek(0)
                file_content = value.read()
                mime_type = getattr(value, 'content_type', 'application/octet-stream')
                base64_string = base64.b64encode(file_content).decode('utf-8')
                return f"data:{mime_type};base64,{base64_string}"
            except Exception:
                return None
        
        return None
