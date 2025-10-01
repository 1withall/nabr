"""
User-related schemas.

Defines all schemas for user management, profiles, and volunteer information.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import EmailStr, Field, ConfigDict

from nabr.schemas.base import BaseSchema, TimestampSchema


class UserBase(BaseSchema):
    """
    Base user schema with common fields.
    
    Other user schemas inherit from this.
    """
    
    email: EmailStr = Field(
        ...,
        description="User's email address"
    )
    full_name: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="User's full name"
    )
    phone_number: Optional[str] = Field(
        None,
        description="User's phone number"
    )
    user_type: str = Field(
        default="individual",
        description="Type of user account"
    )


class UserCreate(UserBase):
    """
    Schema for creating a new user.
    
    Used internally during registration.
    """
    
    password: str = Field(
        ...,
        min_length=8,
        description="User's password"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "newuser@nabr.app",
                "full_name": "Jane Doe",
                "phone_number": "+1234567890",
                "user_type": "volunteer",
                "password": "SecurePass123!"
            }
        }
    )


class UserUpdate(BaseSchema):
    """
    Schema for updating user information.
    
    All fields are optional for partial updates.
    """
    
    full_name: Optional[str] = Field(
        None,
        min_length=2,
        max_length=100,
        description="Updated full name"
    )
    phone_number: Optional[str] = Field(
        None,
        description="Updated phone number"
    )
    bio: Optional[str] = Field(
        None,
        max_length=500,
        description="User bio"
    )
    address: Optional[str] = Field(
        None,
        description="User address"
    )
    city: Optional[str] = Field(
        None,
        description="User city"
    )
    state: Optional[str] = Field(
        None,
        description="User state"
    )
    zip_code: Optional[str] = Field(
        None,
        description="User ZIP code"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "full_name": "Jane Smith",
                "bio": "Passionate about community service",
                "city": "San Francisco",
                "state": "CA"
            }
        }
    )


class UserRead(UserBase, TimestampSchema):
    """
    Schema for reading user data.
    
    Returned by user detail endpoints. Excludes sensitive data.
    """
    
    id: UUID = Field(
        ...,
        description="User's unique identifier"
    )
    is_active: bool = Field(
        ...,
        description="Whether user account is active"
    )
    is_verified: bool = Field(
        ...,
        description="Whether user is verified"
    )
    verification_status: str = Field(
        ...,
        description="Current verification status"
    )
    rating: Optional[float] = Field(
        None,
        ge=0.0,
        le=5.0,
        description="User's average rating"
    )
    total_reviews: int = Field(
        default=0,
        description="Total number of reviews received"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "email": "user@nabr.app",
                "full_name": "Jane Doe",
                "phone_number": "+1234567890",
                "user_type": "volunteer",
                "is_active": True,
                "is_verified": True,
                "verification_status": "verified",
                "rating": 4.8,
                "total_reviews": 25,
                "created_at": "2025-09-01T12:00:00Z",
                "updated_at": "2025-10-01T12:00:00Z"
            }
        }
    )


class UserResponse(BaseSchema):
    """
    Schema for user response wrapper.
    
    Wraps user data with success indicator.
    """
    
    success: bool = True
    user: UserRead
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "user": {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "email": "user@nabr.app",
                    "full_name": "Jane Doe"
                }
            }
        }
    )


class VolunteerProfileCreate(BaseSchema):
    """
    Schema for creating volunteer profile.
    
    Extends user with volunteer-specific information.
    """
    
    skills: list[str] = Field(
        default_factory=list,
        description="List of volunteer skills"
    )
    certifications: list[str] = Field(
        default_factory=list,
        description="List of certifications"
    )
    availability_schedule: Optional[dict] = Field(
        None,
        description="Availability schedule as JSON"
    )
    max_distance_km: Optional[int] = Field(
        None,
        ge=1,
        le=100,
        description="Maximum travel distance in kilometers"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "skills": ["First Aid", "Cooking", "Mentoring"],
                "certifications": ["CPR Certified"],
                "max_distance_km": 25,
                "availability_schedule": {
                    "monday": ["09:00-17:00"],
                    "wednesday": ["14:00-20:00"]
                }
            }
        }
    )


class VolunteerProfileRead(VolunteerProfileCreate, TimestampSchema):
    """
    Schema for reading volunteer profile.
    
    Returned by volunteer profile endpoints.
    """
    
    id: UUID
    user_id: UUID
    background_check_status: Optional[str] = None
    background_check_date: Optional[datetime] = None
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "660e8400-e29b-41d4-a716-446655440000",
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "skills": ["First Aid", "Cooking"],
                "certifications": ["CPR Certified"],
                "background_check_status": "approved",
                "background_check_date": "2025-08-15T12:00:00Z",
                "created_at": "2025-09-01T12:00:00Z",
                "updated_at": "2025-10-01T12:00:00Z"
            }
        }
    )
