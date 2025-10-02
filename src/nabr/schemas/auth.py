"""
Authentication and authorization schemas.

Defines all schemas related to user authentication, token management,
and authorization scopes. Supports UN/PIN authentication with user type-specific
signup forms.
"""

from typing import Optional, Literal, Union, Annotated
from datetime import date, datetime
from pydantic import EmailStr, Field, ConfigDict, field_validator, Discriminator
import re

from nabr.schemas.base import BaseSchema


# ========================
# PIN Authentication Schemas
# ========================

class PINLoginRequest(BaseSchema):
    """
    Schema for PIN-based login.
    
    Used by /auth/login/pin endpoint for UN/PIN authentication.
    """
    username: str = Field(
        ...,
        min_length=3,
        max_length=20,
        description="Username (3-20 alphanumeric + underscores)",
        examples=["john_doe"]
    )
    pin: str = Field(
        ...,
        pattern=r"^\d{6}$",
        description="6-digit PIN",
        examples=["123456"]
    )
    kiosk_id: Optional[str] = Field(
        None,
        description="Optional kiosk identifier for shared device login",
        examples=["kiosk_001_main_library"]
    )
    
    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        """Validate username format."""
        if not re.match(r"^[a-zA-Z0-9_]{3,20}$", v):
            raise ValueError(
                "Username must be 3-20 characters, alphanumeric and underscores only"
            )
        return v.lower()
    
    @field_validator("pin")
    @classmethod
    def validate_pin_strength(cls, v: str) -> str:
        """Validate PIN is not sequential or repeated."""
        # Check for sequential numbers
        if any(
            v[i:i+3] in ["012", "123", "234", "345", "456", "567", "678", "789"]
            for i in range(len(v) - 2)
        ):
            raise ValueError("PIN cannot contain sequential numbers")
        
        # Check for repeated digits
        if len(set(v)) == 1:
            raise ValueError("PIN cannot be all the same digit")
        
        return v


# ========================
# User Type-Specific Signup Schemas
# ========================

class BaseSignupData(BaseSchema):
    """
    Base schema for all user signup forms.
    
    Contains common fields required by all user types.
    """
    username: str = Field(
        ...,
        min_length=3,
        max_length=20,
        description="Unique username (primary identifier)",
        examples=["john_doe"]
    )
    pin: str = Field(
        ...,
        pattern=r"^\d{6}$",
        description="6-digit PIN for authentication",
        examples=["456789"]
    )
    pin_confirm: str = Field(
        ...,
        pattern=r"^\d{6}$",
        description="PIN confirmation (must match)",
        examples=["456789"]
    )
    full_name: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Full legal name",
        examples=["Jane Doe"]
    )
    email: Optional[EmailStr] = Field(
        None,
        description="Optional email for notifications",
        examples=["jane@example.com"]
    )
    phone: Optional[str] = Field(
        None,
        description="Optional phone number",
        examples=["+1234567890"]
    )
    
    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        """Validate username format."""
        if not re.match(r"^[a-zA-Z0-9_]{3,20}$", v):
            raise ValueError(
                "Username must be 3-20 characters, alphanumeric and underscores only"
            )
        return v.lower()
    
    @field_validator("pin")
    @classmethod
    def validate_pin_strength(cls, v: str) -> str:
        """Validate PIN is not sequential or repeated."""
        # Check for sequential numbers
        if any(
            v[i:i+3] in ["012", "123", "234", "345", "456", "567", "678", "789"]
            for i in range(len(v) - 2)
        ):
            raise ValueError("PIN cannot contain sequential numbers")
        
        # Check for repeated digits
        if len(set(v)) == 1:
            raise ValueError("PIN cannot be all the same digit")
        
        return v


class IndividualSignupData(BaseSignupData):
    """
    Signup schema for INDIVIDUAL user type.
    
    Personal users offering or seeking help within their community.
    """
    user_type: Literal["INDIVIDUAL"] = "INDIVIDUAL"
    date_of_birth: date = Field(
        ...,
        description="Date of birth (required for age verification)",
        examples=["1990-01-15"]
    )
    city: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="City of residence",
        examples=["Seattle"]
    )
    state: str = Field(
        ...,
        min_length=2,
        max_length=50,
        description="State/province of residence",
        examples=["WA"]
    )
    bio: Optional[str] = Field(
        None,
        max_length=500,
        description="Short personal bio",
        examples=["Community volunteer passionate about helping neighbors"]
    )
    skills: Optional[list[str]] = Field(
        None,
        description="Skills to offer",
        examples=[["gardening", "tutoring", "handyman"]]
    )
    interests: Optional[list[str]] = Field(
        None,
        description="Areas of interest",
        examples=[["education", "environment", "seniors"]]
    )
    languages: Optional[list[str]] = Field(
        None,
        description="Languages spoken",
        examples=[["English", "Spanish"]]
    )
    availability: Optional[str] = Field(
        None,
        description="General availability",
        examples=["Weekends and evenings"]
    )
    
    @field_validator("date_of_birth")
    @classmethod
    def validate_age(cls, v: date) -> date:
        """Ensure user is at least 13 years old."""
        today = date.today()
        age = today.year - v.year - ((today.month, today.day) < (v.month, v.day))
        if age < 13:
            raise ValueError("User must be at least 13 years old")
        return v


class BusinessSignupData(BaseSignupData):
    """
    Signup schema for BUSINESS user type.
    
    Local businesses contributing resources or services to the community.
    """
    user_type: Literal["BUSINESS"] = "BUSINESS"
    business_name: str = Field(
        ...,
        min_length=2,
        max_length=200,
        description="Legal business name",
        examples=["Joe's Hardware Store"]
    )
    business_type: str = Field(
        ...,
        description="Type of business",
        examples=["retail", "restaurant", "service", "professional"]
    )
    street_address: str = Field(
        ...,
        description="Physical street address",
        examples=["123 Main St"]
    )
    city: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="City",
        examples=["Seattle"]
    )
    state: str = Field(
        ...,
        min_length=2,
        max_length=50,
        description="State/province",
        examples=["WA"]
    )
    zip_code: str = Field(
        ...,
        pattern=r"^\d{5}(-\d{4})?$",
        description="ZIP code",
        examples=["98101"]
    )
    website: Optional[str] = Field(
        None,
        description="Business website",
        examples=["https://joeshardware.com"]
    )
    tax_id: Optional[str] = Field(
        None,
        description="Employer Identification Number (EIN) - optional for verification",
        examples=["12-3456789"]
    )
    services: Optional[list[str]] = Field(
        None,
        description="Services or resources offered",
        examples=[["tools", "supplies", "workspace"]]
    )
    business_hours: Optional[str] = Field(
        None,
        description="Operating hours",
        examples=["Mon-Fri 9am-6pm, Sat 10am-4pm"]
    )


class OrganizationSignupData(BaseSignupData):
    """
    Signup schema for ORGANIZATION user type.
    
    Non-profits, community groups, or government agencies coordinating community support.
    """
    user_type: Literal["ORGANIZATION"] = "ORGANIZATION"
    organization_name: str = Field(
        ...,
        min_length=2,
        max_length=200,
        description="Legal organization name",
        examples=["Seattle Community Network"]
    )
    organization_type: str = Field(
        ...,
        description="Type of organization",
        examples=["nonprofit", "community_group", "government", "religious"]
    )
    mission_statement: str = Field(
        ...,
        min_length=10,
        max_length=1000,
        description="Organization's mission or purpose",
        examples=["Connecting neighbors to build stronger communities through mutual aid"]
    )
    street_address: str = Field(
        ...,
        description="Physical street address",
        examples=["456 Community Blvd"]
    )
    city: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="City",
        examples=["Seattle"]
    )
    state: str = Field(
        ...,
        min_length=2,
        max_length=50,
        description="State/province",
        examples=["WA"]
    )
    zip_code: str = Field(
        ...,
        pattern=r"^\d{5}(-\d{4})?$",
        description="ZIP code",
        examples=["98102"]
    )
    website: Optional[str] = Field(
        None,
        description="Organization website",
        examples=["https://seattlecommunity.org"]
    )
    tax_id: Optional[str] = Field(
        None,
        description="EIN or nonprofit ID - optional for verification",
        examples=["12-3456789"]
    )
    programs: Optional[list[str]] = Field(
        None,
        description="Programs or services offered",
        examples=[["food bank", "job training", "housing assistance"]]
    )
    staff_count: Optional[int] = Field(
        None,
        ge=1,
        description="Number of staff members",
        examples=[25]
    )
    is_501c3: Optional[bool] = Field(
        None,
        description="Whether organization has 501(c)(3) tax-exempt status",
        examples=[True]
    )


# Discriminated union for signup requests
SignupRequest = Annotated[
    Union[
        IndividualSignupData,
        BusinessSignupData,
        OrganizationSignupData,
    ],
    Field(discriminator="user_type")
]


class AuthTokens(BaseSchema):
    """Authentication tokens returned after successful login."""
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Seconds until access token expires")


class SignupResponse(BaseSchema):
    """
    Response after successful user signup.
    
    Contains user info, authentication tokens, and next steps.
    """
    user_id: str = Field(..., description="Unique user ID")
    username: str = Field(..., description="User's username")
    user_type: Literal["INDIVIDUAL", "BUSINESS", "ORGANIZATION"] = Field(
        ..., description="Type of user account"
    )
    full_name: str = Field(..., description="User's full name")
    verification_level: str = Field(..., description="Current verification level")
    tokens: AuthTokens = Field(..., description="Authentication tokens for immediate login")
    next_steps: list[str] = Field(
        ...,
        description="Suggested next actions",
        examples=[[
            "Complete your profile",
            "Start identity verification",
            "Browse available requests"
        ]]
    )
    workflow_id: str = Field(..., description="Temporal workflow ID for signup process")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": "user_12345",
                "username": "john_doe",
                "user_type": "INDIVIDUAL",
                "full_name": "John Doe",
                "verification_level": "TIER_0_UNVERIFIED",
                "tokens": {
                    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
                    "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
                    "token_type": "bearer",
                    "expires_in": 1800
                },
                "next_steps": [
                    "Complete your profile",
                    "Start identity verification",
                    "Browse available requests"
                ],
                "workflow_id": "signup_workflow_12345"
            }
        }
    )


class PINLoginResponse(BaseSchema):
    """
    Response after successful PIN login.
    
    Contains user info and authentication tokens.
    """
    user_id: str = Field(..., description="Unique user ID")
    username: str = Field(..., description="User's username")
    user_type: Literal["INDIVIDUAL", "BUSINESS", "ORGANIZATION"] = Field(
        ..., description="Type of user account"
    )
    full_name: str = Field(..., description="User's full name")
    verification_level: str = Field(..., description="Current verification level")
    tokens: AuthTokens = Field(..., description="Authentication tokens")
    session_id: Optional[str] = Field(
        None,
        description="Kiosk session ID (if logging in from shared device)"
    )
    session_expires_at: Optional[datetime] = Field(
        None,
        description="When kiosk session expires (UTC)"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": "user_12345",
                "username": "john_doe",
                "user_type": "INDIVIDUAL",
                "full_name": "John Doe",
                "verification_level": "TIER_1_IDENTITY",
                "tokens": {
                    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
                    "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
                    "token_type": "bearer",
                    "expires_in": 1800
                },
                "session_id": "kiosk_session_67890",
                "session_expires_at": "2025-01-02T12:30:00Z"
            }
        }
    )


class PINLoginError(BaseSchema):
    """
    Error response for failed PIN login attempts.
    
    Provides security-conscious error messages with lockout info.
    """
    error: str = Field(..., description="Error code")
    message: str = Field(..., description="Human-readable error message")
    attempts_remaining: Optional[int] = Field(
        None,
        description="Number of attempts remaining before lockout"
    )
    locked_until: Optional[datetime] = Field(
        None,
        description="UTC timestamp when account will be unlocked"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error": "INVALID_CREDENTIALS",
                "message": "Invalid username or PIN",
                "attempts_remaining": 3,
                "locked_until": None
            }
        }
    )


# ========================
# Legacy Email/Password Schemas (kept for backward compatibility)
# ========================


class LoginRequest(BaseSchema):
    """
    Schema for user login request.
    
    Used by the /auth/login endpoint.
    """
    
    email: EmailStr = Field(
        ...,
        description="User's email address",
        examples=["user@example.com"]
    )
    password: str = Field(
        ...,
        min_length=8,
        description="User's password",
        examples=["SecurePass123!"]
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "volunteer@nabr.app",
                "password": "SecurePass123!"
            }
        }
    )


class RegisterRequest(BaseSchema):
    """
    Schema for user registration request.
    
    Used by the /auth/register endpoint.
    """
    
    email: EmailStr = Field(
        ...,
        description="User's email address",
        examples=["newuser@example.com"]
    )
    password: str = Field(
        ...,
        min_length=8,
        description="Strong password meeting requirements",
        examples=["SecurePass123!"]
    )
    full_name: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="User's full name",
        examples=["Jane Doe"]
    )
    phone_number: Optional[str] = Field(
        None,
        description="Optional phone number",
        examples=["+1234567890"]
    )
    user_type: str = Field(
        default="individual",
        description="Type of user account: individual, business, or organization",
        examples=["individual", "business", "organization"]
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "newuser@nabr.app",
                "password": "SecurePass123!",
                "full_name": "Jane Doe",
                "phone_number": "+1234567890",
                "user_type": "individual"
            }
        }
    )


class Token(BaseSchema):
    """
    Schema for JWT token response.
    
    Returned by login and token refresh endpoints.
    """
    
    access_token: str = Field(
        ...,
        description="JWT access token for API authentication"
    )
    refresh_token: str = Field(
        ...,
        description="JWT refresh token for obtaining new access tokens"
    )
    token_type: str = Field(
        default="bearer",
        description="Token type (always 'bearer')"
    )
    expires_in: int = Field(
        ...,
        description="Access token expiration time in seconds"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 1800
            }
        }
    )


class TokenData(BaseSchema):
    """
    Schema for decoded JWT token data.
    
    Used internally for token validation and user identification.
    """
    
    user_id: str = Field(
        ...,
        description="User's unique identifier"
    )
    email: Optional[str] = Field(
        None,
        description="User's email address"
    )
    scopes: list[str] = Field(
        default_factory=list,
        description="List of permission scopes"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "email": "user@nabr.app",
                "scopes": ["read:requests", "write:requests"]
            }
        }
    )


class RefreshTokenRequest(BaseSchema):
    """
    Schema for refresh token request.
    
    Used by the /auth/refresh endpoint.
    """
    
    refresh_token: str = Field(
        ...,
        description="Valid refresh token"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            }
        }
    )


class PasswordResetRequest(BaseSchema):
    """
    Schema for password reset request.
    
    Used to initiate password reset flow.
    """
    
    email: EmailStr = Field(
        ...,
        description="Email address of account to reset"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "user@nabr.app"
            }
        }
    )


class PasswordResetConfirm(BaseSchema):
    """
    Schema for password reset confirmation.
    
    Used to complete password reset with token.
    """
    
    token: str = Field(
        ...,
        description="Password reset token from email"
    )
    new_password: str = Field(
        ...,
        min_length=8,
        description="New password meeting requirements"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "token": "reset-token-from-email",
                "new_password": "NewSecurePass123!"
            }
        }
    )
