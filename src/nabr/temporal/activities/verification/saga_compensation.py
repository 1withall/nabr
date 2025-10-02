"""
Saga compensation activities for verification rollback.

These activities are called when verification workflows fail and need to be rolled back.
"""

from datetime import datetime, timezone
from typing import Dict, Any, List
from uuid import UUID

from temporalio import activity
from sqlalchemy import select

from nabr.db.session import AsyncSessionLocal
from nabr.models.verification import VerificationRecord, VerificationStatus


@activity.defn(name="invalidate_qr_codes")
async def invalidate_qr_codes(
    qr_codes: List[str],
) -> Dict[str, Any]:
    """
    Invalidate QR codes (saga compensation function).
    
    Called when a two-party verification fails or is cancelled.
    
    Args:
        qr_codes: List of QR code tokens to invalidate
        
    Returns:
        Dictionary with invalidation status
    """
    activity.logger.info(f"Invalidating {len(qr_codes)} QR codes")
    
    async with AsyncSessionLocal() as db:
        for token in qr_codes:
            # Find verification record by token
            result = await db.execute(
                select(VerificationRecord).where(
                    (VerificationRecord.verifier1_token == token) |
                    (VerificationRecord.verifier2_token == token)
                )
            )
            verification = result.scalar_one_or_none()
            
            if verification:
                verification.status = VerificationStatus.EXPIRED
                verification.qr_expires_at = datetime.now(timezone.utc)
                activity.logger.info(f"Invalidated QR code for verification {verification.id}")
        
        await db.commit()
    
    return {
        "invalidated": True,
        "count": len(qr_codes),
        "invalidated_at": datetime.now(timezone.utc).isoformat(),
    }


@activity.defn(name="revoke_confirmations")
async def revoke_confirmations(
    user_id: str,
    verifier_ids: List[str],
) -> Dict[str, Any]:
    """
    Revoke verifier confirmations (saga compensation function).
    
    Called when a two-party verification is rolled back.
    
    Args:
        user_id: UUID of user whose verifications should be revoked
        verifier_ids: List of verifier UUIDs whose confirmations should be revoked
        
    Returns:
        Dictionary with revocation status
    """
    activity.logger.info(f"Revoking confirmations from {len(verifier_ids)} verifiers for user {user_id}")
    
    async with AsyncSessionLocal() as db:
        # Find all verification records for this user with these verifiers
        result = await db.execute(
            select(VerificationRecord).where(
                (VerificationRecord.user_id == UUID(user_id)) &
                (
                    (VerificationRecord.verifier1_id.in_([UUID(v) for v in verifier_ids])) |
                    (VerificationRecord.verifier2_id.in_([UUID(v) for v in verifier_ids]))
                )
            )
        )
        verifications = result.scalars().all()
        
        for verification in verifications:
            verification.status = VerificationStatus.REVOKED
            activity.logger.info(f"Revoked verification {verification.id}")
        
        await db.commit()
        
        # Record event (imported to avoid circular dependency)
        from nabr.temporal.activities.verification.events import record_verification_event
        await record_verification_event(
            user_id=user_id,
            event_type="confirmations_revoked",
            data={
                "verifier_ids": verifier_ids,
                "count": len(verifications),
            },
        )
    
    return {
        "revoked": True,
        "user_id": user_id,
        "verifier_count": len(verifier_ids),
        "verification_count": len(verifications),
        "revoked_at": datetime.now(timezone.utc).isoformat(),
    }
