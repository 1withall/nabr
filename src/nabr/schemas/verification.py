"""
Verification-related schemas.

Defines all schemas for user verification, QR codes, and verification workflows.
Includes schemas for progressive trust system (Phase 2C Extended).
"""

from datetime import datetime
from typing import Optional, Dict, List, Any
from uuid import UUID
from pydantic import Field, ConfigDict

from nabr.schemas.base import BaseSchema, TimestampSchema


class VerificationRequest(BaseSchema):
    """
    Schema for verification workflow input.
    
    Used to initiate verification workflow.
    """
    
    user_id: str = Field(
        ...,
        description="UUID of user to verify"
    )
    id_document_url: Optional[str] = Field(
        None,
        description="URL to uploaded ID document"
    )
    location_latitude: Optional[float] = Field(
        None,
        ge=-90,
        le=90,
        description="Verification location latitude"
    )
    location_longitude: Optional[float] = Field(
        None,
        ge=-180,
        le=180,
        description="Verification location longitude"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "id_document_url": "https://storage.nabr.app/docs/user-123-id.jpg",
                "location_latitude": 37.7749,
                "location_longitude": -122.4194
            }
        }
    )


class VerificationResult(BaseSchema):
    """
    Schema for verification workflow result.
    
    Returned by verification workflow.
    """
    
    user_id: str
    status: str = Field(
        ...,
        description="Verification status (verified, rejected, expired)"
    )
    verifier_ids: list[str] = Field(
        default_factory=list,
        description="List of verifier user IDs"
    )
    rejection_reason: Optional[str] = Field(
        None,
        description="Reason for rejection if status is rejected"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "verified",
                "verifier_ids": [
                    "660e8400-e29b-41d4-a716-446655440000",
                    "770e8400-e29b-41d4-a716-446655440000"
                ]
            }
        }
    )


class VerificationStatusResponse(BaseSchema):
    """
    Schema for verification status query response.
    
    Returned by workflow status queries.
    """
    
    status: str
    verifications_received: int
    verification_code: Optional[str] = None
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "pending",
                "verifications_received": 1,
                "verification_code": "VERIFY-ABC123"
            }
        }
    )


class VerificationRead(TimestampSchema):
    """
    Schema for reading verification data.
    
    Returned by verification detail endpoints.
    """
    
    id: UUID
    user_id: UUID
    verifier1_id: Optional[UUID] = None
    verifier2_id: Optional[UUID] = None
    verification_code: str
    status: str
    expires_at: datetime
    verified_at: Optional[datetime] = None
    id_document_hash: Optional[str] = None
    location_latitude: Optional[float] = None
    location_longitude: Optional[float] = None
    temporal_workflow_id: Optional[str] = None
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "990e8400-e29b-41d4-a716-446655440000",
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "verifier1_id": "660e8400-e29b-41d4-a716-446655440000",
                "verifier2_id": "770e8400-e29b-41d4-a716-446655440000",
                "verification_code": "VERIFY-ABC123",
                "status": "verified",
                "verified_at": "2025-10-01T15:30:00Z",
                "expires_at": "2026-10-01T15:30:00Z",
                "created_at": "2025-10-01T12:00:00Z",
                "updated_at": "2025-10-01T15:30:00Z"
            }
        }
    )


class VerifierConfirmation(BaseSchema):
    """
    Schema for verifier confirmation signal.
    
    Used to signal verification workflow.
    """
    
    verification_code: str = Field(
        ...,
        description="Verification code from QR scan"
    )
    verifier_id: UUID = Field(
        ...,
        description="ID of user performing verification"
    )
    location_latitude: Optional[float] = Field(
        None,
        ge=-90,
        le=90
    )
    location_longitude: Optional[float] = Field(
        None,
        ge=-180,
        le=180
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "verification_code": "VERIFY-ABC123",
                "verifier_id": "660e8400-e29b-41d4-a716-446655440000",
                "location_latitude": 37.7749,
                "location_longitude": -122.4194
            }
        }
    )


# ============================================================================
# Progressive Trust System Schemas (Phase 2C Extended)
# ============================================================================

class VerificationMethodStart(BaseSchema):
    """Schema for starting a verification method."""
    
    method: str = Field(..., description="Verification method to start")
    params: Dict[str, Any] = Field(default_factory=dict, description="Method-specific parameters")


class VerificationStatus(BaseSchema):
    """Schema for current verification status."""
    
    user_id: str
    trust_score: int
    verification_level: str
    completed_methods: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    active_verifications: List[str] = Field(default_factory=list)


class NextLevelInfo(BaseSchema):
    """Schema for next verification level information."""
    
    current_score: int
    current_level: str
    next_level: Optional[str] = None
    points_needed: int
    suggested_paths: List[Dict[str, Any]] = Field(default_factory=list)


class VerifierConfirmationRequest(BaseSchema):
    """Schema for verifier confirmation of identity."""
    
    user_id: str
    method: str
    qr_code: str
    location_lat: Optional[float] = None
    location_lon: Optional[float] = None
    device_fingerprint: Optional[str] = None


class VerificationRevocation(BaseSchema):
    """Schema for revoking a verification method."""
    
    method: str
    reason: str
