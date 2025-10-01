"""
Base schemas for common patterns.

Provides base classes and utilities for all Pydantic schemas.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    """
    Base schema with common configuration.
    
    All schemas inherit from this to ensure consistent behavior.
    """
    
    model_config = ConfigDict(
        from_attributes=True,  # Enable ORM mode for SQLAlchemy models
        populate_by_name=True,  # Allow population by field name
        json_schema_extra={
            "example": {}  # Subclasses can override
        }
    )


class TimestampSchema(BaseSchema):
    """
    Schema with timestamp fields.
    
    Use this for models that track creation and modification times.
    """
    
    created_at: datetime
    updated_at: datetime


class ResponseSchema(BaseSchema):
    """
    Schema for API responses.
    
    Provides consistent structure for all API responses.
    """
    
    success: bool = True
    message: Optional[str] = None


class ErrorResponse(ResponseSchema):
    """
    Schema for error responses.
    
    Provides detailed error information for API consumers.
    """
    
    success: bool = False
    error_code: Optional[str] = None
    details: Optional[dict] = None
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": False,
                "message": "Resource not found",
                "error_code": "NOT_FOUND",
                "details": {"resource_type": "User", "resource_id": "123"}
            }
        }
    )


class PaginationParams(BaseSchema):
    """
    Schema for pagination parameters.
    
    Use this for list endpoints that support pagination.
    """
    
    skip: int = 0
    limit: int = 100
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "skip": 0,
                "limit": 50
            }
        }
    )


class PaginatedResponse(ResponseSchema):
    """
    Schema for paginated responses.
    
    Wraps list results with pagination metadata.
    """
    
    items: list
    total: int
    skip: int
    limit: int
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "items": [],
                "total": 100,
                "skip": 0,
                "limit": 50
            }
        }
    )
