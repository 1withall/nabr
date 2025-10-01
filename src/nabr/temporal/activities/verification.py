"""
Verification activities.

Activities for user verification workflow including QR code generation,
document validation, and status updates.
"""

import secrets
import hashlib
from typing import Optional
from temporalio import activity
from sqlalchemy import select, update
from datetime import datetime, timedelta

from nabr.temporal.activities.base import ActivityBase, log_activity_execution
from nabr.models.user import User
from nabr.models.verification import Verification
from nabr.models.request import RequestEventLog


@activity.defn
@log_activity_execution
async def generate_verification_qr_code(user_id: str) -> str:
    """
    Generate unique QR code for user verification.
    
    Creates a secure, unique verification code that can be encoded
    into a QR code for in-person scanning by verifiers.
    
    Args:
        user_id: UUID of user requesting verification
        
    Returns:
        str: Unique verification code (e.g., "VERIFY-ABC123XYZ")
        
    Notes:
        - Code is cryptographically secure
        - Code format: "VERIFY-" + 12 uppercase alphanumeric characters
        - Idempotent: Returns existing code if verification already exists
    """
    from nabr.db.session import AsyncSessionLocal
    
    async with AsyncSessionLocal() as db:
        # Check if verification already exists
        result = await db.execute(
            select(Verification)
            .where(Verification.user_id == user_id)
            .where(Verification.status == "pending")
        )
        existing = result.scalar_one_or_none()
        
        if existing and existing.verification_code:
            activity.logger.info(f"Returning existing code for user {user_id}")
            return existing.verification_code
        
        # Generate new secure code
        random_bytes = secrets.token_bytes(16)
        code_suffix = secrets.token_hex(6).upper()  # 12 chars
        verification_code = f"VERIFY-{code_suffix}"
        
        # Create or update verification record
        if existing:
            existing.verification_code = verification_code
        else:
            verification = Verification(
                user_id=user_id,
                verification_code=verification_code,
                status="pending",
                expires_at=datetime.utcnow() + timedelta(days=365),
            )
            db.add(verification)
        
        await db.commit()
        
        activity.logger.info(f"Generated verification code for user {user_id}")
        return verification_code


@activity.defn
@log_activity_execution
async def validate_id_document(document_url: str) -> bool:
    """
    Validate uploaded ID document.
    
    Performs basic validation on uploaded ID document.
    In production, would integrate with document verification service.
    
    Args:
        document_url: URL to uploaded ID document
        
    Returns:
        bool: True if document is valid, False otherwise
        
    Notes:
        - Currently performs basic checks
        - TODO: Integrate with ID verification service (e.g., Jumio, Onfido)
        - Should check document authenticity, match user data
    """
    activity.logger.info(f"Validating document: {document_url}")
    
    # Basic validation
    if not document_url or len(document_url) < 10:
        activity.logger.warning("Invalid document URL")
        return False
    
    # Check URL format
    valid_extensions = [".jpg", ".jpeg", ".png", ".pdf"]
    if not any(document_url.lower().endswith(ext) for ext in valid_extensions):
        activity.logger.warning(f"Invalid document format: {document_url}")
        return False
    
    # TODO: Integrate with document verification service
    # For MVP, we'll accept all valid URLs
    activity.logger.info("Document validation passed")
    return True


@activity.defn
@log_activity_execution
async def update_verification_status(
    user_id: str,
    status: str,
    verifier1_id: Optional[str] = None,
    verifier2_id: Optional[str] = None,
) -> bool:
    """
    Update verification status in database.
    
    Updates both the verification record and user's verification status.
    Idempotent: Safe to call multiple times with same status.
    
    Args:
        user_id: UUID of user being verified
        status: New status (pending, verified, rejected, expired)
        verifier1_id: Optional first verifier UUID
        verifier2_id: Optional second verifier UUID
        
    Returns:
        bool: True if update successful
        
    Notes:
        - Updates both Verification and User tables
        - Sets verified_at timestamp if status is "verified"
        - Idempotent: Can be called multiple times safely
    """
    from nabr.db.session import AsyncSessionLocal
    
    async with AsyncSessionLocal() as db:
        # Update verification record
        verification_result = await db.execute(
            select(Verification)
            .where(Verification.user_id == user_id)
            .order_by(Verification.created_at.desc())
            .limit(1)
        )
        verification = verification_result.scalar_one_or_none()
        
        if not verification:
            activity.logger.error(f"No verification found for user {user_id}")
            return False
        
        # Update verification fields
        verification.status = status
        if verifier1_id:
            verification.verifier1_id = verifier1_id
        if verifier2_id:
            verification.verifier2_id = verifier2_id
        if status == "verified":
            verification.verified_at = datetime.utcnow()
        
        # Update user's verification status
        user_result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = user_result.scalar_one_or_none()
        
        if user:
            user.is_verified = (status == "verified")
            user.verification_status = status
        
        await db.commit()
        
        activity.logger.info(
            f"Updated verification status for user {user_id} to {status}"
        )
        return True


@activity.defn
@log_activity_execution
async def log_verification_event(
    user_id: str,
    event_type: str,
    event_data: Optional[dict] = None,
) -> str:
    """
    Log verification event for audit trail.
    
    Creates immutable event log entry for verification process.
    
    Args:
        user_id: UUID of user being verified
        event_type: Type of event (e.g., "qr_code_generated", "verifier_confirmed")
        event_data: Optional additional event data
        
    Returns:
        str: UUID of created event log entry
        
    Notes:
        - Creates immutable audit log
        - Used for compliance and transparency
        - Events are never deleted, only appended
    """
    from nabr.db.session import AsyncSessionLocal
    import uuid
    
    async with AsyncSessionLocal() as db:
        # For MVP, we'll create a simple event log
        # In production, might use separate events table
        event = {
            "event_type": event_type,
            "user_id": user_id,
            "event_data": event_data or {},
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        activity.logger.info(f"Logged event: {event}")
        
        # TODO: Store in dedicated events table
        # For now, just log it
        
        return str(uuid.uuid4())


@activity.defn
@log_activity_execution
async def hash_id_document(document_content: bytes) -> str:
    """
    Generate secure hash of ID document.
    
    Creates SHA-256 hash of document for verification without storing
    the actual document long-term.
    
    Args:
        document_content: Raw bytes of ID document
        
    Returns:
        str: SHA-256 hash of document (hex encoded)
        
    Notes:
        - Allows verification of document integrity
        - Doesn't store actual document (privacy)
        - Can verify same document used later
    """
    activity.logger.info("Hashing ID document")
    
    hash_obj = hashlib.sha256()
    hash_obj.update(document_content)
    document_hash = hash_obj.hexdigest()
    
    activity.logger.info(f"Generated document hash: {document_hash[:16]}...")
    return document_hash
