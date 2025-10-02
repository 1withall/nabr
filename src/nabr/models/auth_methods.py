"""
Authentication method models for multi-modal authentication.

Supports PIN, biometric, email, and phone-based authentication methods.
Each user can have multiple authentication methods.
"""
import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, INET
from sqlalchemy.orm import relationship

from nabr.db.session import Base


class AuthMethodType(str, PyEnum):
    """Authentication method types."""
    
    PIN = "pin"  # 6-digit PIN (primary for kiosks)
    BIOMETRIC = "biometric"  # Device biometric (fingerprint, face)
    EMAIL = "email"  # Email + password
    PHONE = "phone"  # Phone + SMS code
    HELPER_ASSISTED = "helper_assisted"  # Community helper authentication


class UserAuthenticationMethod(Base):
    """
    User authentication methods table.
    
    Stores multiple authentication methods per user:
    - PIN: 6-digit PIN for kiosk/shared device access
    - Biometric: Device-specific biometric authentication
    - Email: Traditional email + password
    - Phone: Phone number + SMS verification
    
    Security features:
    - Argon2 hashed secrets
    - Rate limiting tracking
    - Account lockout support
    - Audit trail
    """
    
    __tablename__ = "user_authentication_methods"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Method type and identifier
    method_type = Column(Enum(AuthMethodType), nullable=False, index=True)
    method_identifier = Column(Text, nullable=True)  # Device ID, phone, email, etc.
    
    # Security metadata
    hashed_secret = Column(Text, nullable=True)  # Argon2 hashed PIN/password
    public_key = Column(Text, nullable=True)  # For device keys (future feature)
    
    # Status flags
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    is_primary = Column(Boolean, default=False, nullable=False)  # Primary auth method
    
    # Security tracking
    failed_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime, nullable=True)  # Account lockout timestamp
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_used_at = Column(DateTime, nullable=True)
    deactivated_at = Column(DateTime, nullable=True)
    deactivation_reason = Column(Text, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="authentication_methods")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "method_type",
            "method_identifier",
            name="uq_user_auth_method",
        ),
    )
    
    def __repr__(self) -> str:
        return (
            f"<UserAuthenticationMethod("
            f"user_id={self.user_id}, "
            f"method_type={self.method_type}, "
            f"is_active={self.is_active}"
            f")>"
        )


class KioskSession(Base):
    """
    Kiosk session tracking for shared device authentication.
    
    Tracks user sessions on public kiosks at community centers,
    libraries, and partner locations. Features:
    - Limited session duration (30 minutes default)
    - Inactivity timeout (5 minutes)
    - Location tracking
    - Security audit trail
    """
    
    __tablename__ = "kiosk_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Kiosk identification
    kiosk_id = Column(String(100), nullable=True)  # e.g., "oakland-library-kiosk-1"
    location = Column(Text, nullable=True)  # Human-readable location
    
    # Session details
    session_token = Column(String(255), unique=True, nullable=False, index=True)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)  # 30 minutes from start
    last_activity_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    ended_at = Column(DateTime, nullable=True)  # When user logged out or session expired
    
    # Authentication method used
    auth_method = Column(String(50), nullable=False)  # 'pin', 'biometric', 'helper_assisted'
    
    # Security tracking
    ip_address = Column(INET, nullable=True)
    user_agent = Column(Text, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="kiosk_sessions")
    
    def __repr__(self) -> str:
        return (
            f"<KioskSession("
            f"user_id={self.user_id}, "
            f"kiosk_id={self.kiosk_id}, "
            f"started_at={self.started_at}, "
            f"expires_at={self.expires_at}"
            f")>"
        )
    
    @property
    def is_active(self) -> bool:
        """Check if session is still active."""
        now = datetime.utcnow()
        # Type ignore for SQLAlchemy column comparisons
        return bool(
            self.ended_at is None
            and self.expires_at > now  # type: ignore
            and (now - self.last_activity_at).total_seconds() < 300  # type: ignore # 5 min inactivity
        )
    
    @property
    def time_remaining(self) -> int:
        """Get seconds remaining until session expires."""
        if self.ended_at is not None:
            return 0
        remaining = (self.expires_at - datetime.utcnow()).total_seconds()  # type: ignore
        return max(0, int(remaining))
