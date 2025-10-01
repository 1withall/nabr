"""
Pydantic schemas package for Nābr API.

This package contains all request/response models for the API.
Each module corresponds to a domain concept.
"""

from nabr.schemas.user import (
    UserCreate,
    UserRead,
    UserUpdate,
    UserResponse,
)
from nabr.schemas.auth import (
    Token,
    TokenData,
    LoginRequest,
    RegisterRequest,
)
from nabr.schemas.request import (
    RequestCreate,
    RequestRead,
    RequestUpdate,
    RequestResponse,
)
from nabr.schemas.review import (
    ReviewCreate,
    ReviewRead,
    ReviewResponse,
)
from nabr.schemas.verification import (
    VerificationRequest,
    VerificationResult,
    VerificationStatusResponse,
)

__all__ = [
    # User schemas
    "UserCreate",
    "UserRead",
    "UserUpdate",
    "UserResponse",
    # Auth schemas
    "Token",
    "TokenData",
    "LoginRequest",
    "RegisterRequest",
    # Request schemas
    "RequestCreate",
    "RequestRead",
    "RequestUpdate",
    "RequestResponse",
    # Review schemas
    "ReviewCreate",
    "ReviewRead",
    "ReviewResponse",
    # Verification schemas
    "VerificationRequest",
    "VerificationResult",
    "VerificationStatusResponse",
]
