"""
Review-related schemas.

Defines all schemas for review submission and rating management.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import Field, ConfigDict

from nabr.schemas.base import BaseSchema, TimestampSchema


class ReviewBase(BaseSchema):
    """
    Base review schema with common fields.
    
    Other review schemas inherit from this.
    """
    
    rating: int = Field(
        ...,
        ge=1,
        le=5,
        description="Overall rating (1-5)"
    )
    public_comment: Optional[str] = Field(
        None,
        max_length=1000,
        description="Public review comment"
    )
    private_comment: Optional[str] = Field(
        None,
        max_length=1000,
        description="Private feedback (visible only to participant and admins)"
    )


class ReviewCreate(ReviewBase):
    """
    Schema for creating a new review.
    
    Used by the /reviews endpoint (POST).
    """
    
    request_id: UUID = Field(
        ...,
        description="Request being reviewed"
    )
    reviewee_id: UUID = Field(
        ...,
        description="User being reviewed"
    )
    review_type: str = Field(
        ...,
        description="Type of review (requester_to_volunteer or volunteer_to_requester)"
    )
    professionalism_rating: Optional[int] = Field(
        None,
        ge=1,
        le=5,
        description="Professionalism rating (1-5)"
    )
    communication_rating: Optional[int] = Field(
        None,
        ge=1,
        le=5,
        description="Communication rating (1-5)"
    )
    punctuality_rating: Optional[int] = Field(
        None,
        ge=1,
        le=5,
        description="Punctuality rating (1-5)"
    )
    skill_rating: Optional[int] = Field(
        None,
        ge=1,
        le=5,
        description="Skill rating (1-5)"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "request_id": "770e8400-e29b-41d4-a716-446655440000",
                "reviewee_id": "660e8400-e29b-41d4-a716-446655440000",
                "review_type": "requester_to_volunteer",
                "rating": 5,
                "public_comment": "Excellent volunteer! Very helpful and professional.",
                "professionalism_rating": 5,
                "communication_rating": 5,
                "punctuality_rating": 5,
                "skill_rating": 5
            }
        }
    )


class ReviewRead(ReviewBase, TimestampSchema):
    """
    Schema for reading review data.
    
    Returned by review endpoints. Private comments excluded unless authorized.
    """
    
    id: UUID
    request_id: UUID
    reviewer_id: UUID
    reviewee_id: UUID
    review_type: str
    professionalism_rating: Optional[int] = None
    communication_rating: Optional[int] = None
    punctuality_rating: Optional[int] = None
    skill_rating: Optional[int] = None
    is_flagged: bool = False
    flagged_reason: Optional[str] = None
    verification_id: Optional[UUID] = None
    temporal_workflow_id: Optional[str] = None
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "880e8400-e29b-41d4-a716-446655440000",
                "request_id": "770e8400-e29b-41d4-a716-446655440000",
                "reviewer_id": "550e8400-e29b-41d4-a716-446655440000",
                "reviewee_id": "660e8400-e29b-41d4-a716-446655440000",
                "review_type": "requester_to_volunteer",
                "rating": 5,
                "public_comment": "Excellent volunteer!",
                "professionalism_rating": 5,
                "communication_rating": 5,
                "punctuality_rating": 5,
                "skill_rating": 5,
                "is_flagged": False,
                "created_at": "2025-10-01T18:00:00Z",
                "updated_at": "2025-10-01T18:00:00Z"
            }
        }
    )


class ReviewResponse(BaseSchema):
    """
    Schema for review response wrapper.
    
    Wraps review data with success indicator.
    """
    
    success: bool = True
    review: ReviewRead
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "review": {
                    "id": "880e8400-e29b-41d4-a716-446655440000",
                    "rating": 5
                }
            }
        }
    )


class ReviewSubmission(BaseSchema):
    """
    Schema for review submission workflow input.
    
    Used internally by Temporal workflows.
    """
    
    request_id: str
    reviewer_id: str
    reviewee_id: str
    review_type: str
    rating: int = Field(ge=1, le=5)
    public_comment: Optional[str] = None
    private_comment: Optional[str] = None
    professionalism_rating: Optional[int] = Field(None, ge=1, le=5)
    communication_rating: Optional[int] = Field(None, ge=1, le=5)
    punctuality_rating: Optional[int] = Field(None, ge=1, le=5)
    skill_rating: Optional[int] = Field(None, ge=1, le=5)


class ReviewResult(BaseSchema):
    """
    Schema for review submission workflow result.
    
    Returned by review submission workflow.
    """
    
    success: bool
    review_id: Optional[str] = None
    new_rating: Optional[float] = None
    needs_moderation: bool = False
    reason: Optional[str] = None
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "review_id": "880e8400-e29b-41d4-a716-446655440000",
                "new_rating": 4.8,
                "needs_moderation": False
            }
        }
    )
