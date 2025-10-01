"""
Request-related schemas.

Defines all schemas for volunteer requests, matching, and request management.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import Field, ConfigDict

from nabr.schemas.base import BaseSchema, TimestampSchema


class RequestBase(BaseSchema):
    """
    Base request schema with common fields.
    
    Other request schemas inherit from this.
    """
    
    title: str = Field(
        ...,
        min_length=5,
        max_length=200,
        description="Request title"
    )
    description: str = Field(
        ...,
        min_length=10,
        max_length=2000,
        description="Detailed request description"
    )
    request_type: str = Field(
        ...,
        description="Type of volunteer request"
    )
    priority: str = Field(
        default="medium",
        description="Request priority level"
    )
    required_skills: list[str] = Field(
        default_factory=list,
        description="Skills required for this request"
    )


class RequestCreate(RequestBase):
    """
    Schema for creating a new request.
    
    Used by the /requests endpoint (POST).
    """
    
    address: Optional[str] = Field(
        None,
        description="Request location address"
    )
    city: Optional[str] = Field(
        None,
        description="Request location city"
    )
    state: Optional[str] = Field(
        None,
        description="Request location state"
    )
    zip_code: Optional[str] = Field(
        None,
        description="Request location ZIP code"
    )
    latitude: Optional[float] = Field(
        None,
        ge=-90,
        le=90,
        description="Location latitude"
    )
    longitude: Optional[float] = Field(
        None,
        ge=-180,
        le=180,
        description="Location longitude"
    )
    scheduled_start: Optional[datetime] = Field(
        None,
        description="Preferred start time"
    )
    scheduled_end: Optional[datetime] = Field(
        None,
        description="Preferred end time"
    )
    is_urgent: bool = Field(
        default=False,
        description="Whether this is an urgent request"
    )
    is_recurring: bool = Field(
        default=False,
        description="Whether this is a recurring request"
    )
    recurrence_pattern: Optional[str] = Field(
        None,
        description="Recurrence pattern (e.g., 'weekly', 'monthly')"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Help with grocery shopping",
                "description": "Need assistance with weekly grocery shopping for elderly parent",
                "request_type": "shopping_errands",
                "priority": "medium",
                "required_skills": ["Transportation"],
                "city": "San Francisco",
                "state": "CA",
                "scheduled_start": "2025-10-05T10:00:00Z",
                "is_urgent": False,
                "is_recurring": True,
                "recurrence_pattern": "weekly"
            }
        }
    )


class RequestUpdate(BaseSchema):
    """
    Schema for updating a request.
    
    All fields are optional for partial updates.
    """
    
    title: Optional[str] = Field(
        None,
        min_length=5,
        max_length=200
    )
    description: Optional[str] = Field(
        None,
        min_length=10,
        max_length=2000
    )
    priority: Optional[str] = None
    status: Optional[str] = None
    scheduled_start: Optional[datetime] = None
    scheduled_end: Optional[datetime] = None
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "priority": "high",
                "scheduled_start": "2025-10-06T10:00:00Z"
            }
        }
    )


class RequestRead(RequestBase, TimestampSchema):
    """
    Schema for reading request data.
    
    Returned by request endpoints.
    """
    
    id: UUID
    requester_id: UUID
    volunteer_id: Optional[UUID] = None
    status: str
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    scheduled_start: Optional[datetime] = None
    scheduled_end: Optional[datetime] = None
    actual_start: Optional[datetime] = None
    actual_end: Optional[datetime] = None
    is_urgent: bool
    is_recurring: bool
    match_score: Optional[float] = None
    temporal_workflow_id: Optional[str] = None
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "770e8400-e29b-41d4-a716-446655440000",
                "requester_id": "550e8400-e29b-41d4-a716-446655440000",
                "volunteer_id": None,
                "title": "Help with grocery shopping",
                "description": "Need assistance with weekly grocery shopping",
                "request_type": "shopping_errands",
                "priority": "medium",
                "status": "pending",
                "required_skills": ["Transportation"],
                "city": "San Francisco",
                "state": "CA",
                "is_urgent": False,
                "is_recurring": True,
                "created_at": "2025-10-01T12:00:00Z",
                "updated_at": "2025-10-01T12:00:00Z"
            }
        }
    )


class RequestResponse(BaseSchema):
    """
    Schema for request response wrapper.
    
    Wraps request data with success indicator.
    """
    
    success: bool = True
    request: RequestRead
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "request": {
                    "id": "770e8400-e29b-41d4-a716-446655440000",
                    "title": "Help with grocery shopping"
                }
            }
        }
    )


class RequestMatchingInput(BaseSchema):
    """
    Schema for request matching workflow input.
    
    Used internally by Temporal workflows.
    """
    
    request_id: str = Field(
        ...,
        description="UUID of request to match"
    )
    max_candidates: int = Field(
        default=20,
        ge=5,
        le=50,
        description="Maximum number of candidates to consider"
    )
    batch_size: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Number of volunteers to notify per batch"
    )
    timeout_hours: int = Field(
        default=24,
        ge=1,
        le=72,
        description="Hours to wait for volunteer acceptance"
    )


class MatchingResult(BaseSchema):
    """
    Schema for matching workflow result.
    
    Returned by matching workflow.
    """
    
    request_id: str
    matched: bool
    volunteer_id: Optional[str] = None
    reason: Optional[str] = None
    notified_count: int = 0
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "request_id": "770e8400-e29b-41d4-a716-446655440000",
                "matched": True,
                "volunteer_id": "660e8400-e29b-41d4-a716-446655440000",
                "notified_count": 8
            }
        }
    )
