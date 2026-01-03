"""
Base64 Image Utility Functions

This module provides utilities for encoding, decoding, compressing,
and validating images as Base64 strings for storage in the database.
"""

import base64
import io
from typing import Optional, Tuple
from PIL import Image
from django.conf import settings
from django.core.exceptions import ValidationError


# Default settings
DEFAULT_MAX_IMAGE_SIZE_MB = getattr(settings, 'MAX_IMAGE_SIZE_MB', 1)
DEFAULT_COMPRESSION_QUALITY = getattr(settings, 'IMAGE_COMPRESSION_QUALITY', 85)
DEFAULT_MAX_DIMENSION = getattr(settings, 'MAX_IMAGE_DIMENSION', 1920)


def get_image_format(filename: str) -> str:
    """Get image format from filename extension."""
    ext = filename.lower().split('.')[-1] if '.' in filename else 'jpeg'
    format_map = {
        'jpg': 'JPEG',
        'jpeg': 'JPEG',
        'png': 'PNG',
        'gif': 'GIF',
        'webp': 'WEBP',
        'bmp': 'BMP',
    }
    return format_map.get(ext, 'JPEG')


def get_mime_type(image_format: str) -> str:
    """Get MIME type from image format."""
    mime_map = {
        'JPEG': 'image/jpeg',
        'PNG': 'image/png',
        'GIF': 'image/gif',
        'WEBP': 'image/webp',
        'BMP': 'image/bmp',
    }
    return mime_map.get(image_format.upper(), 'image/jpeg')


def validate_image_size(file, max_size_mb: float = DEFAULT_MAX_IMAGE_SIZE_MB) -> None:
    """
    Validate that the image file is within the size limit.
    
    Args:
        file: The uploaded file object
        max_size_mb: Maximum allowed size in megabytes
        
    Raises:
        ValidationError: If image exceeds size limit
    """
    max_bytes = max_size_mb * 1024 * 1024
    
    if hasattr(file, 'size'):
        file_size = file.size
    elif hasattr(file, 'seek') and hasattr(file, 'tell'):
        file.seek(0, 2)  # Seek to end
        file_size = file.tell()
        file.seek(0)  # Reset to beginning
    else:
        return  # Cannot determine size
    
    if file_size > max_bytes:
        raise ValidationError(
            f"Image size ({file_size / (1024 * 1024):.2f}MB) exceeds maximum allowed size ({max_size_mb}MB)"
        )


def compress_image(
    file,
    quality: int = DEFAULT_COMPRESSION_QUALITY,
    max_dimension: int = DEFAULT_MAX_DIMENSION,
    output_format: str = 'JPEG'
) -> Tuple[io.BytesIO, str]:
    """
    Compress and optionally resize an image.
    
    Args:
        file: The uploaded file object
        quality: JPEG quality (1-100)
        max_dimension: Maximum width or height
        output_format: Output format (JPEG, PNG, WEBP)
        
    Returns:
        Tuple of (compressed image BytesIO, format string)
    """
    # Read the image
    if hasattr(file, 'read'):
        file.seek(0)
        img = Image.open(file)
    else:
        img = Image.open(io.BytesIO(file))
    
    # Convert to RGB if necessary (for JPEG)
    if output_format == 'JPEG' and img.mode in ('RGBA', 'P', 'LA'):
        # Create a white background
        background = Image.new('RGB', img.size, (255, 255, 255))
        if img.mode == 'P':
            img = img.convert('RGBA')
        background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
        img = background
    elif output_format == 'JPEG' and img.mode != 'RGB':
        img = img.convert('RGB')
    
    # Resize if necessary
    if max(img.size) > max_dimension:
        ratio = max_dimension / max(img.size)
        new_size = tuple(int(dim * ratio) for dim in img.size)
        img = img.resize(new_size, Image.Resampling.LANCZOS)
    
    # Save to BytesIO
    output = io.BytesIO()
    
    if output_format in ('JPEG', 'WEBP'):
        img.save(output, format=output_format, quality=quality, optimize=True)
    elif output_format == 'PNG':
        img.save(output, format=output_format, optimize=True)
    else:
        img.save(output, format=output_format)
    
    output.seek(0)
    return output, output_format


def encode_image_to_base64(
    file,
    compress: bool = True,
    quality: int = DEFAULT_COMPRESSION_QUALITY,
    max_dimension: int = DEFAULT_MAX_DIMENSION,
    include_data_uri: bool = True
) -> str:
    """
    Encode an image file to a Base64 string.
    
    Args:
        file: The uploaded file object or bytes
        compress: Whether to compress the image
        quality: Compression quality (1-100)
        max_dimension: Maximum width or height for resizing
        include_data_uri: Whether to include the data URI prefix
        
    Returns:
        Base64 encoded string (optionally with data URI prefix)
    """
    # Determine the original format
    if hasattr(file, 'name'):
        original_format = get_image_format(file.name)
    else:
        original_format = 'JPEG'
    
    # Compress if requested
    if compress:
        compressed, output_format = compress_image(
            file, 
            quality=quality, 
            max_dimension=max_dimension,
            output_format=original_format if original_format in ('PNG', 'WEBP') else 'JPEG'
        )
        image_data = compressed.read()
    else:
        if hasattr(file, 'read'):
            file.seek(0)
            image_data = file.read()
        else:
            image_data = file
        output_format = original_format
    
    # Encode to Base64
    base64_string = base64.b64encode(image_data).decode('utf-8')
    
    if include_data_uri:
        mime_type = get_mime_type(output_format)
        return f"data:{mime_type};base64,{base64_string}"
    
    return base64_string


def decode_base64_to_bytes(base64_string: str) -> bytes:
    """
    Decode a Base64 string to bytes.
    
    Args:
        base64_string: Base64 encoded string (with or without data URI prefix)
        
    Returns:
        Decoded bytes
    """
    # Remove data URI prefix if present
    if base64_string.startswith('data:'):
        # Format: data:mime/type;base64,<data>
        base64_string = base64_string.split(',', 1)[1]
    
    return base64.b64decode(base64_string)


def decode_base64_to_image(base64_string: str) -> Image.Image:
    """
    Decode a Base64 string to a PIL Image.
    
    Args:
        base64_string: Base64 encoded string (with or without data URI prefix)
        
    Returns:
        PIL Image object
    """
    image_bytes = decode_base64_to_bytes(base64_string)
    return Image.open(io.BytesIO(image_bytes))


def get_base64_mime_type(base64_string: str) -> Optional[str]:
    """
    Extract MIME type from a Base64 data URI string.
    
    Args:
        base64_string: Base64 encoded string with data URI prefix
        
    Returns:
        MIME type string or None if not a data URI
    """
    if base64_string.startswith('data:'):
        # Format: data:mime/type;base64,<data>
        header = base64_string.split(',', 1)[0]
        mime_part = header.replace('data:', '').replace(';base64', '')
        return mime_part
    return None


def is_valid_base64_image(base64_string: str) -> bool:
    """
    Validate that a string is a valid Base64-encoded image.
    
    Args:
        base64_string: The string to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not base64_string:
        return False
    
    try:
        image_bytes = decode_base64_to_bytes(base64_string)
        img = Image.open(io.BytesIO(image_bytes))
        img.verify()  # Verify it's a valid image
        return True
    except Exception:
        return False


def get_base64_image_dimensions(base64_string: str) -> Optional[Tuple[int, int]]:
    """
    Get the dimensions of a Base64-encoded image.
    
    Args:
        base64_string: Base64 encoded image string
        
    Returns:
        Tuple of (width, height) or None if invalid
    """
    try:
        img = decode_base64_to_image(base64_string)
        return img.size
    except Exception:
        return None


def get_base64_size_bytes(base64_string: str) -> int:
    """
    Calculate the approximate size in bytes of a Base64 string.
    
    Args:
        base64_string: Base64 encoded string
        
    Returns:
        Approximate size in bytes
    """
    # Remove data URI prefix if present
    if base64_string.startswith('data:'):
        base64_string = base64_string.split(',', 1)[1]
    
    # Base64 encoding increases size by ~33%
    # Each Base64 character represents 6 bits, so 4 chars = 3 bytes
    padding = base64_string.count('=')
    return (len(base64_string) * 3 // 4) - padding
