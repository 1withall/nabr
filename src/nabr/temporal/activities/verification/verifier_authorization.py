"""
Verifier authorization and credential validation activities.

Checks whether users are authorized to verify others and validates their credentials.
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, Any
from uuid import UUID

from temporalio import activity
from sqlalchemy import select

from nabr.db.session import AsyncSessionLocal
from nabr.models.user import User
from nabr.models.verification import (
    UserVerificationLevel,
    VerifierProfile,
)
from nabr.models.verification_types import (
    VerificationLevel,
    VerifierCredential,
)


@activity.defn(name="check_verifier_authorization")
async def check_verifier_authorization(
    verifier_id: str,
    user_type: str,
) -> Dict[str, Any]:
    """
    Check if a user is authorized to verify others.
    
    Requirements to be a verifier:
    - Must be at STANDARD verification level or higher
    - Must have verifier credentials (notary, attorney, community leader, etc.)
    - Must not be revoked
    - Must have completed verification training (future)
    
    Args:
        verifier_id: UUID of potential verifier
        user_type: Type of user being verified (affects requirements)
        
    Returns:
        Dictionary with authorization status and details
    """
    activity.logger.info(f"Checking verifier authorization for {verifier_id}")
    
    # Auto-qualified credentials (notary, attorney, etc.)
    AUTO_VERIFIER_CREDENTIALS = {
        VerifierCredential.NOTARY_PUBLIC,
        VerifierCredential.ATTORNEY,
        VerifierCredential.GOVERNMENT_OFFICIAL,
    }
    
    async with AsyncSessionLocal() as db:
        # Get verifier user
        verifier = await db.get(User, UUID(verifier_id))
        if not verifier:
            return {
                "authorized": False,
                "reason": "Verifier not found",
            }
        
        # Get verifier's verification level
        level_record = await db.execute(
            select(UserVerificationLevel).where(
                UserVerificationLevel.user_id == UUID(verifier_id)
            )
        )
        level = level_record.scalar_one_or_none()
        
        # Check verification level (must be at least MINIMAL)
        if not level or level.current_level == VerificationLevel.UNVERIFIED:
            return {
                "authorized": False,
                "reason": "Verifier must be verified at MINIMAL level or higher",
            }
        
        # Check for verifier profile
        profile_result = await db.execute(
            select(VerifierProfile).where(
                VerifierProfile.user_id == UUID(verifier_id)
            )
        )
        verifier_profile = profile_result.scalar_one_or_none()
        
        if not verifier_profile:
            return {
                "authorized": False,
                "reason": "No verifier profile found. User must apply to become a verifier.",
            }
        
        # Check if revoked
        if verifier_profile.revoked:
            return {
                "authorized": False,
                "reason": "Verifier status has been revoked",
                "revoked_at": verifier_profile.revoked_at.isoformat() if verifier_profile.revoked_at else None,
                "revocation_reason": verifier_profile.revocation_reason,
            }
        
        # Check if explicitly authorized
        if not verifier_profile.is_authorized:
            return {
                "authorized": False,
                "reason": "Verifier authorization pending approval",
            }
        
        # Check credentials
        credentials = verifier_profile.credentials
        
        # Auto-qualified by professional credentials
        cred_enums = [VerifierCredential(c) for c in credentials if c in [e.value for e in VerifierCredential]]
        auto_qualified = any(cred in AUTO_VERIFIER_CREDENTIALS for cred in cred_enums)
        
        if auto_qualified or verifier_profile.auto_qualified:
            return {
                "authorized": True,
                "credentials": credentials,
                "auto_qualified": True,
                "verification_level": level.current_level.value,
                "verifications_performed": verifier_profile.total_verifications_performed,
            }
        
        # Check if trusted verifier (50+ successful verifications)
        if verifier_profile.total_verifications_performed >= 50:
            return {
                "authorized": True,
                "credentials": credentials + [VerifierCredential.TRUSTED_VERIFIER.value],
                "verification_count": verifier_profile.total_verifications_performed,
                "verification_level": level.current_level.value,
            }
        
        # Check if community leader with good rating
        if (VerifierCredential.COMMUNITY_LEADER.value in credentials and 
            verifier_profile.verifier_rating >= 4.0):
            return {
                "authorized": True,
                "credentials": credentials,
                "rating": verifier_profile.verifier_rating,
                "verification_level": level.current_level.value,
            }
        
        # Default: authorized if profile exists and is marked authorized
        return {
            "authorized": True,
            "credentials": credentials,
            "verification_level": level.current_level.value,
            "verifications_performed": verifier_profile.total_verifications_performed,
        }


@activity.defn(name="validate_verifier_credentials")
async def validate_verifier_credentials(
    verifier_id: str,
    credential_type: str,
    credential_data: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Validate verifier credentials (notary license, attorney bar number, etc.).
    
    Different credentials require different validation:
    - NOTARY_PUBLIC: Verify notary commission with state database
    - ATTORNEY: Verify bar membership
    - COMMUNITY_LEADER: Verify organization leadership role
    - etc.
    
    Args:
        verifier_id: UUID of verifier
        credential_type: Type of credential to validate
        credential_data: Credential information (license numbers, etc.)
        
    Returns:
        Dictionary with validation results
    """
    activity.logger.info(
        f"Validating {credential_type} credentials for verifier {verifier_id}"
    )
    
    # TODO: Implement actual credential validation
    # This would involve:
    # - API calls to state licensing databases
    # - Bar association lookups
    # - Organization verification
    # - Document verification
    
    # Placeholder
    return {
        "valid": True,
        "credential_type": credential_type,
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=365)).isoformat(),
        "issuing_authority": "State of California",  # Example
    }


@activity.defn(name="revoke_verifier_status")
async def revoke_verifier_status(
    verifier_id: str,
    reason: str,
    revoked_by: str,
) -> Dict[str, Any]:
    """
    Revoke a user's verifier authorization.
    
    Reasons for revocation:
    - Credential expiration
    - Misconduct
    - False verification
    - User request
    - Administrative action
    
    Args:
        verifier_id: UUID of verifier to revoke
        reason: Reason for revocation
        revoked_by: UUID of admin/system revoking status
        
    Returns:
        Dictionary with revocation details
    """
    activity.logger.info(f"Revoking verifier status for {verifier_id}: {reason}")
    
    # TODO: Implement database update
    # async with AsyncSessionLocal() as db:
    #     verifier_profile = await db.get(VerifierProfile, UUID(verifier_id))
    #     verifier_profile.revoked = True
    #     verifier_profile.revoked_at = datetime.now(timezone.utc)
    #     verifier_profile.revocation_reason = reason
    #     verifier_profile.revoked_by = UUID(revoked_by)
    #     await db.commit()
    #     
    #     # Notify verifier
    #     await send_notification(
    #         user_id=verifier_id,
    #         type="verifier_status_revoked",
    #         data={"reason": reason}
    #     )
    
    return {
        "revoked": True,
        "verifier_id": verifier_id,
        "reason": reason,
        "revoked_at": datetime.now(timezone.utc).isoformat(),
        "revoked_by": revoked_by,
    }
