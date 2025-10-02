"""User and account models."""

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
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from nabr.db.session import Base


class UserType(str, PyEnum):
    """User account type enumeration.
    
    Each user type has unique workflows, profiles, and capabilities:
    - INDIVIDUAL: People seeking or offering assistance in the community
    - BUSINESS: Local businesses contributing resources or services
    - ORGANIZATION: Non-profits, community groups, and institutions
    """

    INDIVIDUAL = "individual"
    BUSINESS = "business"
    ORGANIZATION = "organization"


class VerificationStatus(str, PyEnum):
    """Verification status enumeration."""

    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"
    EXPIRED = "expired"


class User(Base):
    """User account model."""

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    user_type = Column(Enum(UserType), nullable=False, default=UserType.INDIVIDUAL)
    
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    verification_status = Column(
        Enum(VerificationStatus),
        nullable=False,
        default=VerificationStatus.PENDING,
    )
    
    # Location data for matching
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(50), nullable=True)
    postal_code = Column(String(20), nullable=True)
    country = Column(String(100), default="USA")
    
    # Profile
    bio = Column(Text, nullable=True)
    phone_number = Column(String(20), nullable=True)
    profile_image_url = Column(String(500), nullable=True)
    
    # Ratings and statistics
    rating = Column(Float, default=0.0)
    total_reviews = Column(Integer, default=0)  # Total reviews received
    total_requests_completed = Column(Integer, default=0)
    total_requests_received = Column(Integer, default=0)
    total_verifications_performed = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at = Column(DateTime, nullable=True)
    verified_at = Column(DateTime, nullable=True)
    
    # Relationships
    individual_profile = relationship(
        "IndividualProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    business_profile = relationship(
        "BusinessProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    organization_profile = relationship(
        "OrganizationProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    # Legacy verification relationship (will be deprecated)
    verifications_received = relationship(
        "Verification",
        foreign_keys="[Verification.user_id]",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    
    # New tiered verification relationships
    verification_records = relationship(
        "VerificationRecord",
        foreign_keys="[VerificationRecord.user_id]",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    verification_level = relationship(
        "UserVerificationLevel",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    verifier_profile = relationship(
        "VerifierProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    method_completions = relationship(
        "VerificationMethodCompletion",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    
    requests_created = relationship(
        "Request",
        foreign_keys="[Request.requester_id]",
        back_populates="requester",
        cascade="all, delete-orphan",
    )
    requests_accepted = relationship(
        "Request",
        foreign_keys="[Request.acceptor_id]",
        back_populates="acceptor",
    )
    reviews_given = relationship(
        "Review",
        foreign_keys="[Review.reviewer_id]",
        back_populates="reviewer",
        cascade="all, delete-orphan",
    )
    reviews_received = relationship(
        "Review",
        foreign_keys="[Review.reviewee_id]",
        back_populates="reviewee",
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username={self.username}, type={self.user_type})>"


class IndividualProfile(Base):
    """Extended profile for individual users.
    
    Individuals can both request and provide assistance within the community.
    They have the most flexible role in the platform.
    """

    __tablename__ = "individual_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    
    # Skills and capabilities (for offering help)
    skills = Column(Text, nullable=True)  # JSON array stored as text
    interests = Column(Text, nullable=True)  # JSON array of interests
    
    # Availability
    availability_schedule = Column(Text, nullable=True)  # JSON schedule
    max_distance_km = Column(Float, default=25.0)
    
    # Preferences
    preferred_assistance_types = Column(Text, nullable=True)  # JSON array
    languages_spoken = Column(Text, nullable=True)  # JSON array
    
    # Emergency contact
    emergency_contact_name = Column(String(100), nullable=True)
    emergency_contact_phone = Column(String(20), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="individual_profile")

    def __repr__(self) -> str:
        return f"<IndividualProfile(user_id={self.user_id})>"


class BusinessProfile(Base):
    """Extended profile for business users.
    
    Businesses can offer services, resources, or sponsorship to community members.
    They have unique workflows for resource allocation and impact tracking.
    """

    __tablename__ = "business_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    
    # Business information
    business_name = Column(String(200), nullable=False)
    business_type = Column(String(100), nullable=True)  # e.g., "Restaurant", "Retail"
    tax_id = Column(String(50), nullable=True)  # EIN or similar
    website = Column(String(255), nullable=True)
    
    # Services and resources
    services_offered = Column(Text, nullable=True)  # JSON array
    resources_available = Column(Text, nullable=True)  # JSON array
    
    # Operating details
    business_hours = Column(Text, nullable=True)  # JSON schedule
    service_area_radius_km = Column(Float, default=50.0)
    
    # Verification documents
    business_license_verified = Column(Boolean, default=False)
    insurance_verified = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="business_profile")

    def __repr__(self) -> str:
        return f"<BusinessProfile(user_id={self.user_id}, business={self.business_name})>"


class OrganizationProfile(Base):
    """Extended profile for organization users.
    
    Organizations (non-profits, community groups, institutions) coordinate
    larger-scale assistance efforts and have workflows for program management.
    """

    __tablename__ = "organization_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    
    # Organization information
    organization_name = Column(String(200), nullable=False)
    organization_type = Column(String(100), nullable=True)  # e.g., "Non-Profit", "Community Group"
    tax_id = Column(String(50), nullable=True)  # EIN for non-profits
    website = Column(String(255), nullable=True)
    mission_statement = Column(Text, nullable=True)
    
    # Programs and services
    programs_offered = Column(Text, nullable=True)  # JSON array
    service_areas = Column(Text, nullable=True)  # JSON array of geographic areas
    
    # Capacity
    staff_count = Column(Integer, nullable=True)
    volunteer_capacity = Column(Integer, nullable=True)
    
    # Verification
    nonprofit_status_verified = Column(Boolean, default=False)
    accreditation = Column(Text, nullable=True)  # JSON array of accreditations
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="organization_profile")

    def __repr__(self) -> str:
        return f"<OrganizationProfile(user_id={self.user_id}, org={self.organization_name})>"


class Verification(Base):
    """
    User verification records.
    
    Implements two-party verification system where each user must be
    verified by two other verified users.
    """

    __tablename__ = "verifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Two-party verification
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
    
    # Verification data
    verification_code = Column(String(255), nullable=True, unique=True, index=True)
    id_document_hash = Column(String(255), nullable=True)  # Hash of ID for verification
    
    # Location where verification occurred
    verification_location = Column(Text, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    
    # Status and notes
    status = Column(
        Enum(VerificationStatus),
        nullable=False,
        default=VerificationStatus.PENDING,
    )
    notes = Column(Text, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    
    # Temporal workflow ID for tracking
    temporal_workflow_id = Column(String(255), nullable=True, index=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    verified_at = Column(DateTime, nullable=True)  # When verification completed
    expires_at = Column(DateTime, nullable=True)   # When verification expires
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="verifications_received")
    verifier1 = relationship("User", foreign_keys=[verifier1_id])
    verifier2 = relationship("User", foreign_keys=[verifier2_id])

    def __repr__(self) -> str:
        return f"<Verification(id={self.id}, user_id={self.user_id}, status={self.status})>"
