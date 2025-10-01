"""
Authentication and authorization schemas.

Defines all schemas related to user authentication, token management,
and authorization scopes.
"""

from typing import Optional
from pydantic import EmailStr, Field, ConfigDict

from nabr.schemas.base import BaseSchema


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
