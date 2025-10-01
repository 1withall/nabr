"""Request and matching models."""

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


class RequestStatus(str, PyEnum):
    """Request status enumeration."""

    PENDING = "pending"
    MATCHED = "matched"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class RequestPriority(str, PyEnum):
    """Request priority enumeration."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class RequestType(str, PyEnum):
    """Request type enumeration."""

    PHYSICAL_LABOR = "physical_labor"
    TECHNICAL_SUPPORT = "technical_support"
    TRANSPORTATION = "transportation"
    COMPANIONSHIP = "companionship"
    EDUCATION_TUTORING = "education_tutoring"
    FOOD_ASSISTANCE = "food_assistance"
    HEALTHCARE_SUPPORT = "healthcare_support"
    HOME_REPAIRS = "home_repairs"
    ADMINISTRATIVE = "administrative"
    OTHER = "other"


class Request(Base):
    """Volunteer assistance request model."""

    __tablename__ = "requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    requester_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    volunteer_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    
    # Request details
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    request_type = Column(Enum(RequestType), nullable=False)
    priority = Column(Enum(RequestPriority), default=RequestPriority.MEDIUM)
    status = Column(Enum(RequestStatus), default=RequestStatus.PENDING, nullable=False)
    
    # Location
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    address = Column(Text, nullable=False)
    city = Column(String(100), nullable=False)
    state = Column(String(50), nullable=False)
    postal_code = Column(String(20), nullable=True)
    
    # Requirements
    required_skills = Column(Text, nullable=True)  # JSON array
    required_certifications = Column(Text, nullable=True)  # JSON array
    estimated_duration_hours = Column(Float, nullable=True)
    num_volunteers_needed = Column(Integer, default=1)
    
    # Scheduling
    requested_start_date = Column(DateTime, nullable=False)
    requested_end_date = Column(DateTime, nullable=True)
    flexible_schedule = Column(Boolean, default=False)
    
    # Matching
    matching_score = Column(Float, nullable=True)
    matched_at = Column(DateTime, nullable=True)
    
    # Privacy
    is_anonymous = Column(Boolean, default=False)
    share_contact_info = Column(Boolean, default=True)
    
    # Temporal workflow tracking
    workflow_id = Column(String(255), nullable=True, index=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    
    # Relationships
    requester = relationship("User", foreign_keys=[requester_id], back_populates="requests_created")
    volunteer = relationship("User", foreign_keys=[volunteer_id], back_populates="requests_claimed")
    reviews = relationship("Review", back_populates="request", cascade="all, delete-orphan")
    event_logs = relationship("RequestEventLog", back_populates="request", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Request(id={self.id}, title={self.title}, status={self.status})>"


class RequestEventLog(Base):
    """Immutable event log for requests."""

    __tablename__ = "request_event_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id = Column(
        UUID(as_uuid=True),
        ForeignKey("requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Event details
    event_type = Column(String(100), nullable=False, index=True)
    event_data = Column(Text, nullable=True)  # JSON data
    actor_id = Column(UUID(as_uuid=True), nullable=True)  # User who triggered event
    
    # Temporal tracking
    workflow_id = Column(String(255), nullable=True, index=True)
    activity_id = Column(String(255), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    request = relationship("Request", back_populates="event_logs")

    def __repr__(self) -> str:
        return f"<RequestEventLog(request_id={self.request_id}, event_type={self.event_type})>"
