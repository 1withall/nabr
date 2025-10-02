"""
Enhanced verification models for tiered verification system.

Models for multi-level verification, verifier credentials, and method tracking.
"""

import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from nabr.db.session import Base
from nabr.models.verification_types import (
    VerificationLevel,
    VerificationMethod,
    VerifierCredential,
)


class VerificationStatus(str, PyEnum):
    """Overall verification record status."""

    PENDING = "pending"  # Verification initiated, awaiting completion
    IN_PROGRESS = "in_progress"  # At least one verifier has confirmed
    VERIFIED = "verified"  # Both verifiers confirmed, method complete
    REJECTED = "rejected"  # Verification rejected by verifier or system
    EXPIRED = "expired"  # QR codes or verification window expired
    REVOKED = "revoked"  # Verification revoked after completion


# ============================================================================
# Core Verification Models
# ============================================================================

class VerificationRecord(Base):
    """
    Individual verification attempt record.
    
    Tracks a single verification method attempt (e.g., one two-party verification,
    one government ID check, one notary verification, etc.).
    """

    __tablename__ = "verification_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # What method is being verified
    method = Column(Enum(VerificationMethod), nullable=False, index=True)
    
    # Status of this specific verification
    status = Column(
        Enum(VerificationStatus),
        nullable=False,
        default=VerificationStatus.PENDING,
        index=True,
    )
    
    # Two-party verification (for IN_PERSON_TWO_PARTY method)
    verifier1_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    verifier2_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    verifier1_confirmed_at = Column(DateTime, nullable=True)
    verifier2_confirmed_at = Column(DateTime, nullable=True)
    verifier1_location = Column(Text, nullable=True)
    verifier2_location = Column(Text, nullable=True)
    verifier1_notes = Column(Text, nullable=True)
    verifier2_notes = Column(Text, nullable=True)
    
    # QR code tokens for two-party verification
    verifier1_token = Column(String(255), nullable=True, unique=True, index=True)
    verifier2_token = Column(String(255), nullable=True, unique=True, index=True)
    qr_expires_at = Column(DateTime, nullable=True)
    
    # Document/credential data (stored securely, hashed where appropriate)
    document_hash = Column(String(255), nullable=True)  # Hash of ID/document
    document_type = Column(String(100), nullable=True)  # e.g., "passport", "drivers_license"
    credential_number = Column(String(255), nullable=True)  # License number, tax ID, etc.
    credential_data = Column(JSONB, nullable=True)  # Additional structured data
    
    # Location where verification occurred
    verification_location = Column(Text, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    
    # Status and notes
    notes = Column(Text, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    revocation_reason = Column(Text, nullable=True)
    revoked_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    # Temporal workflow tracking
    temporal_workflow_id = Column(String(255), nullable=True, index=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    verified_at = Column(DateTime, nullable=True)  # When verification completed
    expires_at = Column(DateTime, nullable=True)  # When this verification expires
    revoked_at = Column(DateTime, nullable=True)  # When revoked
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="verification_records")
    verifier1 = relationship("User", foreign_keys=[verifier1_id])
    verifier2 = relationship("User", foreign_keys=[verifier2_id])
    revoker = relationship("User", foreign_keys=[revoked_by])

    def __repr__(self) -> str:
        return (
            f"<VerificationRecord(id={self.id}, user_id={self.user_id}, "
            f"method={self.method}, status={self.status})>"
        )


class UserVerificationLevel(Base):
    """
    Tracks user's current verification level and progress.
    
    One record per user, updated as they complete verification methods.
    """

    __tablename__ = "user_verification_levels"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    
    # Current verification level
    current_level = Column(
        Enum(VerificationLevel),
        nullable=False,
        default=VerificationLevel.UNVERIFIED,
        index=True,
    )
    
    # Progress tracking
    completed_methods = Column(JSONB, nullable=False, default=list)  # List of completed method names
    in_progress_methods = Column(JSONB, nullable=False, default=list)  # List of in-progress methods
    
    # Statistics
    total_methods_completed = Column(Integer, default=0, nullable=False)
    level_progress_percentage = Column(Float, default=0.0, nullable=False)  # Progress to next level
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    level_achieved_at = Column(DateTime, nullable=True)  # When current level was achieved
    
    # Relationship
    user = relationship("User", back_populates="verification_level")

    def __repr__(self) -> str:
        return (
            f"<UserVerificationLevel(user_id={self.user_id}, "
            f"level={self.current_level})>"
        )


# ============================================================================
# Verifier Authorization Models
# ============================================================================

class VerifierProfile(Base):
    """
    Verifier authorization profile.
    
    Tracks who is authorized to verify others, their credentials,
    and verification statistics.
    """

    __tablename__ = "verifier_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    
    # Authorization status
    is_authorized = Column(Boolean, default=False, nullable=False, index=True)
    auto_qualified = Column(Boolean, default=False, nullable=False)  # Auto-qualified via credentials
    
    # Credentials (stored as list of VerifierCredential enum values)
    credentials = Column(JSONB, nullable=False, default=list)  # List of credential type names
    
    # Statistics
    total_verifications_performed = Column(Integer, default=0, nullable=False)
    successful_verifications = Column(Integer, default=0, nullable=False)
    rejected_verifications = Column(Integer, default=0, nullable=False)
    verifier_rating = Column(Float, default=0.0, nullable=False)  # Based on verification quality
    
    # Revocation tracking
    revoked = Column(Boolean, default=False, nullable=False, index=True)
    revoked_at = Column(DateTime, nullable=True)
    revocation_reason = Column(Text, nullable=True)
    revoked_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    # Training and compliance
    training_completed = Column(Boolean, default=False, nullable=False)
    training_completed_at = Column(DateTime, nullable=True)
    last_activity_check = Column(DateTime, nullable=True)  # Last time credentials were verified
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    authorized_at = Column(DateTime, nullable=True)  # When first authorized
    
    # Relationships
    user = relationship("User", back_populates="verifier_profile", foreign_keys=[user_id])
    revoker = relationship("User", foreign_keys=[revoked_by])
    credential_validations = relationship(
        "VerifierCredentialValidation",
        back_populates="verifier_profile",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<VerifierProfile(user_id={self.user_id}, authorized={self.is_authorized}, "
            f"verifications={self.total_verifications_performed})>"
        )


class VerifierCredentialValidation(Base):
    """
    Records of verifier credential validations.
    
    Tracks validation of notary licenses, attorney bar numbers, etc.
    """

    __tablename__ = "verifier_credential_validations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    verifier_profile_id = Column(
        UUID(as_uuid=True),
        ForeignKey("verifier_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Credential being validated
    credential_type = Column(Enum(VerifierCredential), nullable=False)
    
    # Validation status
    is_valid = Column(Boolean, default=False, nullable=False, index=True)
    validation_method = Column(String(100), nullable=True)  # e.g., "state_database", "manual_review"
    
    # Credential details
    credential_number = Column(String(255), nullable=True)  # License number, bar number, etc.
    issuing_authority = Column(String(255), nullable=True)  # State, organization, etc.
    credential_data = Column(JSONB, nullable=True)  # Additional structured data
    
    # Validation notes
    notes = Column(Text, nullable=True)
    validation_source = Column(String(255), nullable=True)  # API endpoint, manual verifier, etc.
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    validated_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)  # When credential expires
    last_checked_at = Column(DateTime, nullable=True)  # Last time validity was confirmed
    
    # Relationship
    verifier_profile = relationship("VerifierProfile", back_populates="credential_validations")

    def __repr__(self) -> str:
        return (
            f"<VerifierCredentialValidation(credential={self.credential_type}, "
            f"valid={self.is_valid}, profile_id={self.verifier_profile_id})>"
        )


# ============================================================================
# Method Completion Tracking
# ============================================================================

class VerificationMethodCompletion(Base):
    """
    Tracks completion of individual verification methods.
    
    One record per user per completed method, for audit trail.
    """

    __tablename__ = "verification_method_completions"
    __table_args__ = (
        UniqueConstraint("user_id", "method", name="uq_user_method"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Method completed
    method = Column(Enum(VerificationMethod), nullable=False, index=True)
    
    # Reference to the verification record
    verification_record_id = Column(
        UUID(as_uuid=True),
        ForeignKey("verification_records.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    # Completion details
    completed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    level_before = Column(Enum(VerificationLevel), nullable=True)  # Level before this completion
    level_after = Column(Enum(VerificationLevel), nullable=True)  # Level after this completion
    
    # Relationships
    user = relationship("User", back_populates="method_completions")
    verification_record = relationship("VerificationRecord")

    def __repr__(self) -> str:
        return (
            f"<VerificationMethodCompletion(user_id={self.user_id}, "
            f"method={self.method}, level={self.level_after})>"
        )


# ============================================================================
# Verification Events/Audit Trail
# ============================================================================

class VerificationEvent(Base):
    """
    Immutable audit trail of verification-related events.
    
    Tracks all significant events in the verification process.
    """

    __tablename__ = "verification_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    verification_record_id = Column(
        UUID(as_uuid=True),
        ForeignKey("verification_records.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    
    # Event details
    event_type = Column(String(100), nullable=False, index=True)  # e.g., "qr_generated", "verifier_confirmed", "level_increased"
    event_data = Column(JSONB, nullable=True)  # Additional structured event data
    
    # Actor (who caused this event)
    actor_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    # Context
    temporal_workflow_id = Column(String(255), nullable=True, index=True)
    ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6
    user_agent = Column(Text, nullable=True)
    
    # Timestamp (immutable)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    verification_record = relationship("VerificationRecord")
    actor = relationship("User", foreign_keys=[actor_id])

    def __repr__(self) -> str:
        return (
            f"<VerificationEvent(type={self.event_type}, user_id={self.user_id}, "
            f"created_at={self.created_at})>"
        )
