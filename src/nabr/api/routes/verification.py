"""
Verification API routes for progressive trust system.

Endpoints for:
- Starting verification methods
- Getting trust score and verification level
- Checking verification status
- Getting next level requirements
- Verifier confirmations
- Revoking verifications
"""

from typing import Dict, List, Optional, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from temporalio.client import Client as TemporalClient

from nabr.api.dependencies.auth import get_current_user
from nabr.schemas.user import UserRead
from nabr.schemas.verification import (
    VerificationMethodStart,
    VerificationStatus,
    NextLevelInfo,
    VerifierConfirmationRequest,
    VerificationRevocation,
)
from nabr.models.verification_types import (
    VerificationMethod,
    UserType,
    get_applicable_methods,
    get_method_details,
    METHOD_SCORES,
)

router = APIRouter(prefix="/verification", tags=["verification"])


# ============================================================================
# Verification Workflow Management
# ============================================================================

@router.post("/start", response_model=Dict[str, Any])
async def start_verification_method(
    request: VerificationMethodStart,
    current_user: UserRead = Depends(get_current_user),
    temporal_client: TemporalClient = Depends(),  # TODO: Add temporal client dependency
) -> Dict[str, Any]:
    """
    Start a verification method for the current user.
    
    This signals the parent verification workflow to spawn a child workflow
    for the requested verification method.
    
    Available methods depend on user type:
    - INDIVIDUAL: email, phone, two-party, government_id, biometric, references, etc.
    - BUSINESS: email, phone, business_license, tax_id, address, owner, etc.
    - ORGANIZATION: email, phone, 501c3, tax_id, bylaws, board, etc.
    
    Args:
        request: Method to start and method-specific parameters
        current_user: Authenticated user
        temporal_client: Temporal client for signaling workflows
    
    Returns:
        Dictionary with workflow_id, method, status
    """
    try:
        method = VerificationMethod(request.method)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid verification method: {request.method}"
        )
    
    # Check if method is applicable for user type
    applicable = get_applicable_methods(UserType(current_user.user_type))
    if method not in applicable:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Method {request.method} not applicable for user type {current_user.user_type}"
        )
    
    # Get parent workflow handle
    workflow_id = f"verification-{current_user.id}"
    
    # TODO: Signal parent workflow to start verification method
    # handle = temporal_client.get_workflow_handle(workflow_id)
    # await handle.signal(
    #     "start_verification_method",
    #     method=request.method,
    #     params=request.params
    # )
    
    return {
        "workflow_id": workflow_id,
        "method": request.method,
        "status": "started",
        "message": f"Verification method {request.method} started successfully"
    }


@router.get("/status", response_model=VerificationStatus)
async def get_verification_status(
    current_user: UserRead = Depends(get_current_user),
    temporal_client: TemporalClient = Depends(),
) -> VerificationStatus:
    """
    Get current trust score, verification level, and completed methods.
    
    Uses Temporal workflow queries for instant status without blocking.
    
    Args:
        current_user: Authenticated user
        temporal_client: Temporal client for querying workflows
    
    Returns:
        VerificationStatus with trust_score, level, completed_methods, active_verifications
    """
    workflow_id = f"verification-{current_user.id}"
    
    # TODO: Query parent workflow for status
    # handle = temporal_client.get_workflow_handle(workflow_id)
    # 
    # trust_score = await handle.query("get_trust_score")
    # level = await handle.query("get_verification_level")
    # completed = await handle.query("get_completed_methods")
    # active = await handle.query("get_active_verifications")
    
    # Placeholder
    return VerificationStatus(
        user_id=str(current_user.id),
        trust_score=150,
        verification_level="minimal",
        completed_methods={
            "IN_PERSON_TWO_PARTY": {
                "points": 150,
                "completed_at": "2025-10-01T12:00:00Z",
                "expires_at": None,
                "is_expired": False,
            }
        },
        active_verifications=[],
    )


@router.get("/next-level", response_model=NextLevelInfo)
async def get_next_level_requirements(
    current_user: UserRead = Depends(get_current_user),
    temporal_client: TemporalClient = Depends(),
) -> NextLevelInfo:
    """
    Get points needed and suggested paths to reach next verification level.
    
    Shows multiple possible method combinations to reach the next level,
    allowing users to choose their preferred path.
    
    Args:
        current_user: Authenticated user
        temporal_client: Temporal client for querying workflows
    
    Returns:
        NextLevelInfo with current_score, current_level, next_level, points_needed, suggested_paths
    """
    workflow_id = f"verification-{current_user.id}"
    
    # TODO: Query parent workflow for next level info
    # handle = temporal_client.get_workflow_handle(workflow_id)
    # next_level_info = await handle.query("get_next_level_info")
    
    # Placeholder
    return NextLevelInfo(
        current_score=150,
        current_level="minimal",
        next_level="standard",
        points_needed=100,
        suggested_paths=[
            {
                "methods": ["EMAIL", "PHONE", "GOVERNMENT_ID"],
                "total_points": 160,
                "description": "Email (30) + Phone (30) + Government ID (100)"
            },
            {
                "methods": ["BIOMETRIC", "PERSONAL_REFERENCE", "PERSONAL_REFERENCE", "PERSONAL_REFERENCE"],
                "total_points": 230,
                "description": "Biometric (80) + 3 Personal References (150)"
            }
        ]
    )


# ============================================================================
# Verifier Operations
# ============================================================================

@router.post("/verifier/confirm", response_model=Dict[str, Any])
async def verifier_confirm_identity(
    confirmation: VerifierConfirmationRequest,
    current_user: UserRead = Depends(get_current_user),
    temporal_client: TemporalClient = Depends(),
) -> Dict[str, Any]:
    """
    Confirm a user's identity as a verifier (for two-party verification).
    
    Verifiers scan the user's QR code and submit this confirmation.
    The workflow validates the verifier's authorization before accepting.
    
    Args:
        confirmation: QR code data, user_id being verified, location, etc.
        current_user: Authenticated verifier
        temporal_client: Temporal client for signaling workflows
    
    Returns:
        Dictionary with confirmation status
    """
    # Get the user's verification workflow
    workflow_id = f"verification-{confirmation.user_id}"
    
    # TODO: Signal the workflow with verifier confirmation
    # handle = temporal_client.get_workflow_handle(workflow_id)
    # await handle.signal(
    #     "verifier_confirms_identity",
    #     verifier_id=str(current_user.id),
    #     method=confirmation.method,
    #     confirmation_data={
    #         "qr_code": confirmation.qr_code,
    #         "location_lat": confirmation.location_lat,
    #         "location_lon": confirmation.location_lon,
    #         "device_fingerprint": confirmation.device_fingerprint,
    #     }
    # )
    
    return {
        "confirmed": True,
        "verifier_id": str(current_user.id),
        "user_id": confirmation.user_id,
        "method": confirmation.method,
        "confirmed_at": "2025-10-01T12:00:00Z",
    }


@router.post("/revoke", response_model=Dict[str, Any])
async def revoke_verification_method(
    revocation: VerificationRevocation,
    current_user: UserRead = Depends(get_current_user),
    temporal_client: TemporalClient = Depends(),
) -> Dict[str, Any]:
    """
    Revoke a verification method (removes points, may lower level).
    
    Reasons for revocation:
    - Method expired
    - Information changed (email, phone, address)
    - User request
    - Administrative action
    - Fraud detected
    
    Args:
        revocation: Method to revoke and reason
        current_user: Authenticated user
        temporal_client: Temporal client for signaling workflows
    
    Returns:
        Dictionary with revocation status
    """
    workflow_id = f"verification-{current_user.id}"
    
    # TODO: Signal workflow to revoke method
    # handle = temporal_client.get_workflow_handle(workflow_id)
    # await handle.signal(
    #     "revoke_verification",
    #     method=revocation.method,
    #     reason=revocation.reason
    # )
    
    return {
        "revoked": True,
        "method": revocation.method,
        "reason": revocation.reason,
        "revoked_at": "2025-10-01T12:00:00Z",
    }


# ============================================================================
# Method Information
# ============================================================================

@router.get("/methods", response_model=List[Dict[str, Any]])
async def get_applicable_methods_for_user(
    current_user: UserRead = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    """
    Get all verification methods applicable to the current user's type.
    
    Returns method name, points, expiry period, and requirements for each.
    
    Args:
        current_user: Authenticated user
    
    Returns:
        List of applicable verification methods with details
    """
    user_type = UserType(current_user.user_type)
    applicable = get_applicable_methods(user_type)
    
    methods = []
    for method in applicable:
        score_info = METHOD_SCORES.get(method)
        if score_info:
            methods.append({
                "method": method.value,
                "points": score_info.points,
                "max_multiplier": score_info.max_multiplier,
                "decay_days": score_info.decay_days,
                "requires_human_review": score_info.requires_human_review,
                "description": _get_method_description(method),
            })
    
    return methods


@router.get("/method/{method}/details", response_model=Dict[str, Any])
async def get_method_details_endpoint(
    method: str,
    current_user: UserRead = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get detailed information about a specific verification method.
    
    Args:
        method: Verification method name
        current_user: Authenticated user
    
    Returns:
        Dictionary with method details, requirements, point value, expiry
    """
    try:
        method_enum = VerificationMethod(method)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Method {method} not found"
        )
    
    score_info = get_method_details(method_enum)
    if not score_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No details available for method {method}"
        )
    
    return {
        "method": method,
        "points": score_info.points,
        "max_multiplier": score_info.max_multiplier,
        "decay_days": score_info.decay_days,
        "requires_human_review": score_info.requires_human_review,
        "description": _get_method_description(method_enum),
        "requirements": _get_method_requirements(method_enum),
    }


# ============================================================================
# Helper Functions
# ============================================================================

def _get_method_description(method: VerificationMethod) -> str:
    """Get human-readable description of verification method."""
    descriptions = {
        VerificationMethod.EMAIL: "Verify your email address with a 6-digit code",
        VerificationMethod.PHONE: "Verify your phone number with an SMS code",
        VerificationMethod.IN_PERSON_TWO_PARTY: "Two trusted community members confirm your identity in person (CORE INCLUSIVE METHOD)",
        VerificationMethod.GOVERNMENT_ID: "Upload government-issued ID for human review",
        VerificationMethod.BIOMETRIC: "Biometric verification (facial recognition, fingerprint, etc.)",
        VerificationMethod.PERSONAL_REFERENCE: "Personal reference from verified community member",
        VerificationMethod.COMMUNITY_ATTESTATION: "Community attestation of identity",
        VerificationMethod.PLATFORM_HISTORY: "Accumulated platform activity history",
        VerificationMethod.TRANSACTION_HISTORY: "Verified transaction history",
    }
    return descriptions.get(method, f"Verification via {method.value}")


def _get_method_requirements(method: VerificationMethod) -> List[str]:
    """Get requirements list for verification method."""
    requirements = {
        VerificationMethod.EMAIL: ["Valid email address"],
        VerificationMethod.PHONE: ["Valid phone number (E.164 format)"],
        VerificationMethod.IN_PERSON_TWO_PARTY: ["Two authorized verifiers", "In-person meeting"],
        VerificationMethod.GOVERNMENT_ID: ["Government-issued ID document", "Clear photo/scan"],
        VerificationMethod.BIOMETRIC: ["Device with camera/biometric sensor"],
        VerificationMethod.PERSONAL_REFERENCE: ["Verified community member willing to vouch"],
    }
    return requirements.get(method, ["Contact support for requirements"])
