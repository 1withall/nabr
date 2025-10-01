"""Review and feedback models."""

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


class ReviewType(str, PyEnum):
    """Review type enumeration.
    
    Reviews are bidirectional - both parties can review each other
    after a completed interaction.
    """

    REQUESTER_TO_ACCEPTOR = "requester_to_acceptor"
    ACCEPTOR_TO_REQUESTER = "acceptor_to_requester"


class Review(Base):
    """Event-linked review model."""

    __tablename__ = "reviews"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    request_id = Column(
        UUID(as_uuid=True),
        ForeignKey("requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reviewer_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reviewee_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Review details
    review_type = Column(Enum(ReviewType), nullable=False)
    rating = Column(Integer, nullable=False)  # 1-5 stars
    
    # Public review (visible to all)
    public_comment = Column(Text, nullable=True)
    
    # Private review (only visible to participants and admins)
    private_comment = Column(Text, nullable=True)
    
    # Specific feedback categories
    professionalism_rating = Column(Integer, nullable=True)  # 1-5
    communication_rating = Column(Integer, nullable=True)  # 1-5
    punctuality_rating = Column(Integer, nullable=True)  # 1-5
    skill_rating = Column(Integer, nullable=True)  # 1-5
    
    # Flags for moderation
    is_flagged = Column(Boolean, default=False)
    flag_reason = Column(Text, nullable=True)
    is_verified_review = Column(Boolean, default=True)  # Linked to completed request
    
    # Temporal workflow tracking
    workflow_id = Column(String(255), nullable=True, index=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    request = relationship("Request", back_populates="reviews")
    reviewer = relationship("User", foreign_keys=[reviewer_id], back_populates="reviews_given")
    reviewee = relationship("User", foreign_keys=[reviewee_id], back_populates="reviews_received")

    def __repr__(self) -> str:
        return f"<Review(id={self.id}, request_id={self.request_id}, rating={self.rating})>"
