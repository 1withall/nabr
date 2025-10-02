"""
Verification activities for progressive trust identity verification.

Activities for user verification workflow including QR code generation,
multi-method verification, verifier authorization, and trust score calculation.

Progressive Trust System:
- Point-based trust accumulation (not hard requirements)
- Tiered levels: Unverified → Minimal (100+) → Standard (250+) → Enhanced (400+) → Complete (600+)
- Multiple verification methods per user type
- Authorized verifiers with credentials
- Method expiry and renewal
- Email/phone are OPTIONAL (30 points each)
"""

import io
import base64
import secrets
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
from uuid import UUID

import qrcode
from temporalio import activity
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

# Database imports
from nabr.db.session import AsyncSessionLocal
from nabr.models.user import User, UserType
from nabr.models.verification import (
    VerificationRecord,
    VerificationStatus,
    UserVerificationLevel,
    VerifierProfile,
    VerifierCredentialValidation,
    VerificationMethodCompletion,
    VerificationEvent,
)
from nabr.models.verification_types import (
    VerificationLevel,
    VerificationMethod,
    VerifierCredential,
    calculate_trust_score,
    calculate_verification_level as calc_level_from_score,
    METHOD_SCORES,
)


# ============================================================================
# QR Code Generation Activities
# ============================================================================

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


# ============================================================================
# Verifier Authorization Activities
# ============================================================================

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


# ============================================================================
# Verification Level Management Activities
# ============================================================================

@activity.defn(name="calculate_verification_level")
async def calculate_verification_level(
    user_id: str,
    user_type: str,
    completed_methods: List[str],
) -> Dict[str, Any]:
    """
    Calculate user's verification level based on completed methods.
    
    UNIQUE REQUIREMENTS PER USER TYPE:
    
    INDIVIDUAL (per original spec):
      - MINIMAL: Email + Phone + TWO-PARTY IN-PERSON (baseline to use platform)
      - STANDARD: Minimal + Government ID
      - ENHANCED: Standard + Personal references
      - COMPLETE: All methods including notary verification
    
    BUSINESS:
      - MINIMAL: Email + Phone + Business License + Tax ID (prove legitimacy)
      - STANDARD: Minimal + Business Address + Owner Verification
      - ENHANCED: Standard + Insurance + Notarized docs
      - COMPLETE: All methods including professional licenses
    
    ORGANIZATION:
      - MINIMAL: Email + Phone + 501(c)(3) Status + Tax ID (prove legitimacy)
      - STANDARD: Minimal + Bylaws + Board Verification
      - ENHANCED: Standard + Mission Alignment + Community Endorsement
      - COMPLETE: All methods including notarized docs
    
    Args:
        user_id: UUID of user
        user_type: Type of user (individual, business, organization)
        completed_methods: List of completed verification methods
        
    Returns:
        Dictionary with calculated verification level and requirements
    """
    activity.logger.info(
        f"Calculating verification level for {user_type} user {user_id}"
    )
    
    # TODO: Implement actual level calculation based on VERIFICATION_REQUIREMENTS
    # from nabr.models.verification_types import VERIFICATION_REQUIREMENTS
    # 
    # requirements = VERIFICATION_REQUIREMENTS.get(user_type, {})
    # completed_set = set(completed_methods)
    # 
    # # Check each level from highest to lowest
    # for level in reversed(list(VerificationLevel)):
    #     required_methods = set(requirements.get(level, []))
    #     if required_methods.issubset(completed_set):
    #         return {
    #             "level": level,
    #             "completed_methods": completed_methods,
    #             "next_level": get_next_level(level),
    #             "next_requirements": get_next_requirements(level, user_type),
    #         }
    
    # Placeholder
    return {
        "level": "basic",
        "completed_methods": completed_methods,
        "next_level": "standard",
        "next_requirements": ["government_id", "in_person_two_party"],
        "progress_percentage": 60,
    }


@activity.defn(name="update_user_verification_level")
async def update_user_verification_level(
    user_id: str,
    new_level: str,
    method_completed: str,
) -> Dict[str, Any]:
    """
    Update user's verification level after completing a method.
    
    Args:
        user_id: UUID of user
        new_level: New verification level to set
        method_completed: Verification method that was just completed
        
    Returns:
        Dictionary with update status
    """
    activity.logger.info(
        f"Updating user {user_id} to level {new_level} (completed: {method_completed})"
    )
    
    # TODO: Implement database update
    # async with AsyncSessionLocal() as db:
    #     user = await db.get(User, UUID(user_id))
    #     old_level = user.verification_level
    #     user.verification_level = new_level
    #     user.verification_updated_at = datetime.now(timezone.utc)
    #     
    #     # Record the verification method completion
    #     method_record = VerificationMethodRecord(
    #         user_id=UUID(user_id),
    #         method=method_completed,
    #         completed_at=datetime.now(timezone.utc),
    #     )
    #     db.add(method_record)
    #     await db.commit()
    #     
    #     # Send notification
    #     await send_notification(
    #         user_id=user_id,
    #         type="verification_level_increased",
    #         data={
    #             "old_level": old_level,
    #             "new_level": new_level,
    #             "method": method_completed,
    #         }
    #     )
    
    return {
        "updated": True,
        "user_id": user_id,
        "new_level": new_level,
        "method_completed": method_completed,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


# ============================================================================
# Two-Party Verification Activities
# ============================================================================

@activity.defn(name="record_verifier_confirmation")
async def record_verifier_confirmation(
    verification_id: str,
    verifier_id: str,
    verifier_number: int,  # 1 or 2
    confirmation_data: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Record a verifier's confirmation of identity.
    
    Stores:
    - Which verifier confirmed (1 or 2)
    - When confirmation occurred
    - Location of confirmation (if provided)
    - Any notes from verifier
    
    Args:
        verification_id: UUID of verification record
        verifier_id: UUID of verifier
        verifier_number: 1 for first verifier, 2 for second
        confirmation_data: Additional data (location, notes, etc.)
        
    Returns:
        Dictionary with confirmation details
    """
    activity.logger.info(
        f"Recording confirmation from verifier {verifier_number} "
        f"for verification {verification_id}"
    )
    
    # TODO: Implement database update
    # async with AsyncSessionLocal() as db:
    #     verification = await db.get(Verification, UUID(verification_id))
    #     
    #     if verifier_number == 1:
    #         verification.verifier1_id = UUID(verifier_id)
    #         verification.verifier1_confirmed_at = datetime.now(timezone.utc)
    #         verification.verifier1_location = confirmation_data.get("location")
    #         verification.verifier1_notes = confirmation_data.get("notes")
    #     else:
    #         verification.verifier2_id = UUID(verifier_id)
    #         verification.verifier2_confirmed_at = datetime.now(timezone.utc)
    #         verification.verifier2_location = confirmation_data.get("location")
    #         verification.verifier2_notes = confirmation_data.get("notes")
    #     
    #     await db.commit()
    #     
    #     # Increment verifier's count
    #     verifier = await db.get(User, UUID(verifier_id))
    #     verifier.total_verifications_performed += 1
    #     await db.commit()
    
    return {
        "recorded": True,
        "verification_id": verification_id,
        "verifier_id": verifier_id,
        "verifier_number": verifier_number,
        "confirmed_at": datetime.now(timezone.utc).isoformat(),
        "location": confirmation_data.get("location"),
    }


@activity.defn(name="check_verification_complete")
async def check_verification_complete(
    verification_id: str,
) -> Dict[str, Any]:
    """
    Check if verification is complete (both verifiers confirmed).
    
    Args:
        verification_id: UUID of verification record
        
    Returns:
        Dictionary with completion status
    """
    activity.logger.info(f"Checking if verification {verification_id} is complete")
    
    # TODO: Implement database query
    # async with AsyncSessionLocal() as db:
    #     verification = await db.get(Verification, UUID(verification_id))
    #     
    #     complete = (
    #         verification.verifier1_id is not None and
    #         verification.verifier2_id is not None and
    #         verification.verifier1_confirmed_at is not None and
    #         verification.verifier2_confirmed_at is not None
    #     )
    #     
    #     return {
    #         "complete": complete,
    #         "verifier1_confirmed": verification.verifier1_id is not None,
    #         "verifier2_confirmed": verification.verifier2_id is not None,
    #     }
    
    # Placeholder
    return {
        "complete": False,
        "verifier1_confirmed": True,
        "verifier2_confirmed": False,
    }


# ============================================================================
# Notification Activities
# ============================================================================

@activity.defn(name="send_verification_notifications")
async def send_verification_notifications(
    user_id: str,
    notification_type: str,
    data: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Send notifications related to verification process.
    
    Notification types:
    - verification_started: QR codes generated
    - verifier_confirmed: One verifier confirmed
    - verification_complete: Both verifiers confirmed
    - level_increased: Verification level upgraded
    - verifier_authorized: User authorized as verifier
    - verifier_revoked: Verifier status revoked
    
    Args:
        user_id: UUID of user to notify
        notification_type: Type of notification
        data: Notification data
        
    Returns:
        Dictionary with notification status
    """
    activity.logger.info(
        f"Sending {notification_type} notification to user {user_id}"
    )
    
    # TODO: Implement actual notification sending
    # This would involve:
    # - In-app notifications
    # - Email notifications
    # - Push notifications
    # - SMS notifications (for critical events)
    
    return {
        "sent": True,
        "user_id": user_id,
        "notification_type": notification_type,
        "sent_at": datetime.now(timezone.utc).isoformat(),
        "channels": ["in_app", "email"],
    }


# ============================================================================
# Progressive Trust System Activities (Phase 2C Extended)
# ============================================================================

@activity.defn(name="calculate_trust_score_activity")
async def calculate_trust_score_activity(
    user_id: str,
    completed_methods: Dict[str, int],
    user_type: str,
) -> Dict[str, Any]:
    """
    Calculate total trust score from completed verification methods.
    
    Uses the progressive trust scoring model from verification_types.py.
    
    Args:
        user_id: UUID of user
        completed_methods: Dict mapping method name to count (for multipliers)
        user_type: Type of user (INDIVIDUAL, BUSINESS, ORGANIZATION)
        
    Returns:
        Dictionary with trust_score, verification_level, next_level_info
    """
    activity.logger.info(
        f"Calculating trust score for {user_type} user {user_id}"
    )
    
    # TODO: Import and use actual calculation functions
    # from nabr.models.verification_types import (
    #     calculate_trust_score,
    #     calculate_verification_level,
    #     get_next_level_requirements,
    #     VerificationMethod,
    #     UserType,
    # )
    # 
    # # Convert string keys to VerificationMethod enum
    # method_dict = {
    #     VerificationMethod(method): count
    #     for method, count in completed_methods.items()
    # }
    # 
    # trust_score = calculate_trust_score(method_dict, UserType(user_type))
    # level = calculate_verification_level(trust_score)
    # next_level, points_needed, suggested = get_next_level_requirements(
    #     trust_score, UserType(user_type), set(method_dict.keys())
    # )
    
    # Placeholder calculation
    total_score = sum(completed_methods.values()) * 30  # Rough estimate
    
    return {
        "trust_score": total_score,
        "verification_level": "minimal" if total_score >= 100 else "unverified",
        "completed_methods": completed_methods,
        "next_level": "standard",
        "points_needed": max(0, 250 - total_score),
        "calculated_at": datetime.now(timezone.utc).isoformat(),
    }


@activity.defn(name="validate_verifier_credentials")
async def validate_verifier_credentials_activity(
    verifier_ids: List[str],
    method: str,
) -> Dict[str, Any]:
    """
    Validate that verifiers are authorized for a specific verification method.
    
    Args:
        verifier_ids: List of verifier UUIDs to validate
        method: Verification method they're performing
        
    Returns:
        Dictionary with all_valid flag and invalid_verifiers list
    """
    activity.logger.info(
        f"Validating {len(verifier_ids)} verifiers for method {method}"
    )
    
    # TODO: Implement actual validation
    # async with AsyncSessionLocal() as db:
    #     invalid_verifiers = []
    #     for verifier_id in verifier_ids:
    #         verifier = await db.get(User, UUID(verifier_id))
    #         verifier_profile = await db.get(VerifierProfile, UUID(verifier_id))
    #         
    #         # Check level requirement
    #         if verifier.verification_level < VERIFIER_MINIMUM_LEVEL:
    #             invalid_verifiers.append({
    #                 "verifier_id": verifier_id,
    #                 "reason": "Insufficient verification level"
    #             })
    #             continue
    #         
    #         # Check credentials
    #         if not verifier_profile or verifier_profile.revoked:
    #             invalid_verifiers.append({
    #                 "verifier_id": verifier_id,
    #                 "reason": "No valid verifier profile"
    #             })
    #             continue
    #     
    #     return {
    #         "all_valid": len(invalid_verifiers) == 0,
    #         "invalid_verifiers": invalid_verifiers,
    #         "validated_count": len(verifier_ids) - len(invalid_verifiers),
    #     }
    
    # Placeholder
    return {
        "all_valid": True,
        "invalid_verifiers": [],
        "validated_count": len(verifier_ids),
        "validated_at": datetime.now(timezone.utc).isoformat(),
    }


@activity.defn(name="record_verifier_confirmations")
async def record_verifier_confirmations(
    user_id: str,
    confirmations: List[Dict[str, Any]],
    method: str,
) -> Dict[str, Any]:
    """
    Record multiple verifier confirmations in database.
    
    Args:
        user_id: UUID of user being verified
        confirmations: List of confirmation dicts with verifier_id, confirmed_at, location
        method: Verification method (e.g., IN_PERSON_TWO_PARTY)
        
    Returns:
        Dictionary with recorded confirmation IDs
    """
    activity.logger.info(
        f"Recording {len(confirmations)} verifier confirmations for user {user_id}"
    )
    
    # TODO: Implement database storage
    # async with AsyncSessionLocal() as db:
    #     confirmation_ids = []
    #     for conf in confirmations:
    #         record = VerificationEvent(
    #             user_id=UUID(user_id),
    #             method=method,
    #             event_type="verifier_confirmation",
    #             verifier_id=UUID(conf["verifier_id"]),
    #             confirmed_at=datetime.fromisoformat(conf["confirmed_at"]),
    #             location_lat=conf.get("location_lat"),
    #             location_lon=conf.get("location_lon"),
    #         )
    #         db.add(record)
    #         confirmation_ids.append(str(record.id))
    #     
    #     await db.commit()
    #     return {
    #         "recorded": True,
    #         "confirmation_ids": confirmation_ids,
    #         "count": len(confirmations),
    #     }
    
    # Placeholder
    return {
        "recorded": True,
        "confirmation_ids": [f"conf-{i}" for i in range(len(confirmations))],
        "count": len(confirmations),
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }


@activity.defn(name="invalidate_qr_codes")
async def invalidate_qr_codes(
    qr_codes: List[str],
) -> Dict[str, Any]:
    """
    Invalidate QR codes (compensation for saga).
    
    Args:
        qr_codes: List of QR code tokens to invalidate
        
    Returns:
        Dictionary with invalidation status
    """
    activity.logger.info(f"Invalidating {len(qr_codes)} QR codes")
    
    # TODO: Implement database update
    # async with AsyncSessionLocal() as db:
    #     for qr_code in qr_codes:
    #         # Mark QR code as invalid in database
    #         await db.execute(
    #             update(QRCode)
    #             .where(QRCode.token == qr_code)
    #             .values(invalidated=True, invalidated_at=datetime.now(timezone.utc))
    #         )
    #     await db.commit()
    
    return {
        "invalidated": True,
        "count": len(qr_codes),
        "invalidated_at": datetime.now(timezone.utc).isoformat(),
    }


@activity.defn(name="revoke_verifier_confirmations")
async def revoke_verifier_confirmations(
    user_id: str,
    verifier_ids: List[str],
) -> Dict[str, Any]:
    """
    Revoke verifier confirmations (compensation for saga).
    
    Args:
        user_id: UUID of user whose confirmations to revoke
        verifier_ids: List of verifier IDs whose confirmations to revoke
        
    Returns:
        Dictionary with revocation status
    """
    activity.logger.info(
        f"Revoking confirmations from {len(verifier_ids)} verifiers for user {user_id}"
    )
    
    # TODO: Implement database update
    # async with AsyncSessionLocal() as db:
    #     revoked_count = 0
    #     for verifier_id in verifier_ids:
    #         result = await db.execute(
    #             update(VerificationEvent)
    #             .where(
    #                 VerificationEvent.user_id == UUID(user_id),
    #                 VerificationEvent.verifier_id == UUID(verifier_id)
    #             )
    #             .values(revoked=True, revoked_at=datetime.now(timezone.utc))
    #         )
    #         revoked_count += result.rowcount
    #     await db.commit()
    
    return {
        "revoked": True,
        "count": len(verifier_ids),
        "revoked_at": datetime.now(timezone.utc).isoformat(),
    }


@activity.defn(name="send_level_change_notification")
async def send_level_change_notification(
    user_id: str,
    old_level: str,
    new_level: str,
    trust_score: int,
) -> Dict[str, Any]:
    """
    Send notification when user's verification level changes.
    
    Args:
        user_id: UUID of user
        old_level: Previous verification level
        new_level: New verification level
        trust_score: Current trust score
        
    Returns:
        Dictionary with notification status
    """
    activity.logger.info(
        f"Sending level change notification to {user_id}: {old_level} → {new_level}"
    )
    
    # TODO: Implement actual notification
    # await send_notification(
    #     user_id=user_id,
    #     type="verification_level_changed",
    #     data={
    #         "old_level": old_level,
    #         "new_level": new_level,
    #         "trust_score": trust_score,
    #     },
    #     channels=["in_app", "email", "push"]
    # )
    
    return {
        "sent": True,
        "user_id": user_id,
        "old_level": old_level,
        "new_level": new_level,
        "trust_score": trust_score,
        "sent_at": datetime.now(timezone.utc).isoformat(),
    }


@activity.defn(name="send_verification_email")
async def send_verification_email(
    user_id: str,
    email: str,
    verification_code: str,
) -> Dict[str, Any]:
    """
    Send email verification code to user.
    
    Args:
        user_id: UUID of user
        email: Email address to send to
        verification_code: 6-digit verification code
        
    Returns:
        Dictionary with send status
    """
    activity.logger.info(f"Sending email verification code to {email}")
    
    # TODO: Implement actual email sending
    # await send_email(
    #     to=email,
    #     subject="Verify your email - Nābr",
    #     template="email_verification",
    #     data={"code": verification_code, "user_id": user_id}
    # )
    
    return {
        "sent": True,
        "email": email,
        "sent_at": datetime.now(timezone.utc).isoformat(),
    }


@activity.defn(name="send_verification_sms")
async def send_verification_sms(
    user_id: str,
    phone: str,
    verification_code: str,
) -> Dict[str, Any]:
    """
    Send SMS verification code to user.
    
    Args:
        user_id: UUID of user
        phone: Phone number to send to (E.164 format)
        verification_code: 6-digit verification code
        
    Returns:
        Dictionary with send status
    """
    activity.logger.info(f"Sending SMS verification code to {phone}")
    
    # TODO: Implement actual SMS sending (Twilio, etc.)
    # await send_sms(
    #     to=phone,
    #     message=f"Your Nābr verification code is: {verification_code}"
    # )
    
    return {
        "sent": True,
        "phone": phone,
        "sent_at": datetime.now(timezone.utc).isoformat(),
    }


@activity.defn(name="validate_id_document")
async def validate_id_document(
    document_url: str,
    document_type: str,
) -> Dict[str, Any]:
    """
    Validate government ID document upload.
    
    Checks:
    - File format is valid (JPG, PNG, PDF)
    - File size is reasonable
    - Document is readable
    - Basic fraud detection (not a screenshot of a screenshot)
    
    Args:
        document_url: URL to uploaded document
        document_type: Type of ID (passport, drivers_license, etc.)
        
    Returns:
        Dictionary with validation result
    """
    activity.logger.info(f"Validating {document_type} document at {document_url[:50]}...")
    
    # TODO: Implement actual validation
    # - Download file
    # - Check format
    # - Run fraud detection
    # - Extract text for verification
    
    # Placeholder
    return {
        "valid": True,
        "document_type": document_type,
        "validated_at": datetime.now(timezone.utc).isoformat(),
    }


@activity.defn(name="queue_for_human_review")
async def queue_for_human_review(
    user_id: str,
    method: str,
    review_data: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Queue verification method for human review.
    
    Args:
        user_id: UUID of user
        method: Verification method requiring review
        review_data: Data for reviewer (document URLs, etc.)
        
    Returns:
        Dictionary with queue status
    """
    activity.logger.info(f"Queuing {method} for human review (user {user_id})")
    
    # TODO: Implement review queue
    # async with AsyncSessionLocal() as db:
    #     review = ReviewQueue(
    #         user_id=UUID(user_id),
    #         method=method,
    #         data=review_data,
    #         queued_at=datetime.now(timezone.utc),
    #         status="pending",
    #     )
    #     db.add(review)
    #     await db.commit()
    #     
    #     # Notify reviewers
    #     await notify_reviewers(method_type=method)
    
    return {
        "queued": True,
        "user_id": user_id,
        "method": method,
        "queued_at": datetime.now(timezone.utc).isoformat(),
        "estimated_review_time_hours": 48,
    }
