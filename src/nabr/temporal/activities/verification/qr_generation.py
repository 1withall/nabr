"""
QR code generation activities for two-party verification.

Generates secure QR codes with unique tokens for verifiers to scan.
"""

import io
import base64
import secrets
from datetime import datetime, timedelta, timezone
from typing import Dict, Any
from uuid import UUID

import qrcode
from temporalio import activity

from nabr.db.session import AsyncSessionLocal
from nabr.models.verification import VerificationRecord, VerificationStatus


@activity.defn(name="generate_verification_qr_codes")
async def generate_verification_qr_codes(
    verification_id: str,
    user_id: str,
    user_name: str,
) -> Dict[str, Any]:
    """
    Generate unique QR codes for two-party verification.
    
    Creates two separate QR codes that verifiers scan to confirm identity.
    Each QR code contains:
    - Verification ID
    - Secure token (different for each verifier)
    - Timestamp
    - User information
    
    Args:
        verification_id: UUID of verification record
        user_id: UUID of user being verified
        user_name: Name to display in QR code
        
    Returns:
        Dictionary containing:
        - qr_code_1: Base64-encoded PNG image
        - qr_code_2: Base64-encoded PNG image
        - token_1: Secure token for verifier 1
        - token_2: Secure token for verifier 2
        - expires_at: When QR codes expire
    """
    activity.logger.info(f"Generating QR codes for verification {verification_id}")
    
    # Generate secure tokens for each verifier
    token_1 = secrets.token_urlsafe(32)
    token_2 = secrets.token_urlsafe(32)
    
    # QR codes expire in 7 days
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    
    # Create QR code data
    base_url = "https://nabr.app/verify"  # TODO: Get from config
    qr_data_1 = f"{base_url}/{verification_id}/{token_1}"
    qr_data_2 = f"{base_url}/{verification_id}/{token_2}"
    
    # Generate QR code images
    def generate_qr_image(data: str) -> str:
        """Generate QR code and return as base64-encoded PNG."""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.ERROR_CORRECT_H,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer, 'PNG')
        buffer.seek(0)
        img_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        return img_base64
    
    qr_code_1 = generate_qr_image(qr_data_1)
    qr_code_2 = generate_qr_image(qr_data_2)
    
    activity.logger.info(f"Generated QR codes for user {user_name}")
    
    # Store tokens in database for validation
    async with AsyncSessionLocal() as db:
        verification = await db.get(VerificationRecord, UUID(verification_id))
        if verification:
            verification.verifier1_token = token_1
            verification.verifier2_token = token_2
            verification.qr_expires_at = expires_at
            verification.status = VerificationStatus.PENDING
            await db.commit()
            activity.logger.info(f"Stored QR tokens in database for verification {verification_id}")
        else:
            activity.logger.warning(f"Verification record {verification_id} not found")
    
    return {
        "qr_code_1": qr_code_1,
        "qr_code_2": qr_code_2,
        "token_1": token_1,
        "token_2": token_2,
        "expires_at": expires_at.isoformat(),
        "qr_url_1": qr_data_1,
        "qr_url_2": qr_data_2,
    }
