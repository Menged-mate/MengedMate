
import qrcode
from io import BytesIO
import base64
import uuid
import hashlib

def generate_qr_code_base64(data: str) -> str:
    """
    Generate a QR code for the given data and return it as a Base64 encoded string.
    """
    if not data:
        return None

    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        base64_image = base64.b64encode(buffer.read()).decode('utf-8')
        return f"data:image/png;base64,{base64_image}"
    except Exception as e:
        print(f"Error generating QR code: {e}")
        return None

def generate_unique_token(unique_string: str) -> str:
    """
    Generate a unique SHA256 token based on the input string.
    """
    if not unique_string:
         unique_string = str(uuid.uuid4())
    else:
         unique_string = f"{unique_string}-{uuid.uuid4()}"
         
    return hashlib.sha256(unique_string.encode()).hexdigest()[:32]
