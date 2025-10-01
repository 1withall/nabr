# AI-First Development Guide for Nābr
## Modular Architecture for AI-Assisted Development

**Version:** 1.0  
**Last Updated:** October 1, 2025  
**Purpose:** Enable AI agents to easily understand, navigate, and extend the Nābr codebase

---

## Table of Contents

1. [Philosophy: Why AI-First?](#philosophy)
2. [Project Structure](#structure)
3. [Quick Navigation Guide](#navigation)
4. [Adding New Features](#adding-features)
5. [Modular Patterns](#patterns)
6. [Common Tasks](#common-tasks)
7. [Testing Strategy](#testing)
8. [Troubleshooting](#troubleshooting)

---

## <a name="philosophy"></a>1. Philosophy: Why AI-First?

### Core Principles

**Extreme Modularity**: Every component is in its own file with a single, clear purpose.

**Self-Documenting Code**: 
- Every module has a comprehensive docstring explaining its purpose
- Every function has docstrings with Args, Returns, and Notes
- Type hints on all parameters and return values
- Example usage in docstrings where helpful

**Convention Over Configuration**:
- Predictable file locations
- Consistent naming patterns
- Standard import structures

**Template-Based Extension**:
- Copy-paste-modify approach for new features
- Registry patterns for easy additions
- Clear examples to follow

**AI-Readable Organization**:
- Flat when possible (avoid deep nesting)
- Domain-driven structure (group by concept, not technology)
- Explicit over implicit

---

## <a name="structure"></a>2. Project Structure

```
nabr/
├── .github/
│   └── temporal_guide.md          # Temporal reference for AI agents
│
├── src/nabr/
│   ├── __init__.py                # Package initialization
│   │
│   ├── core/                      # Core utilities (RARELY CHANGE)
│   │   ├── __init__.py
│   │   ├── config.py              # Centralized configuration
│   │   └── security.py            # Security utilities (JWT, hashing)
│   │
│   ├── db/                        # Database setup (RARELY CHANGE)
│   │   ├── __init__.py
│   │   └── session.py             # SQLAlchemy async session
│   │
│   ├── models/                    # Database models (MODIFY CAREFULLY)
│   │   ├── __init__.py
│   │   ├── user.py                # User, VolunteerProfile, enums
│   │   ├── request.py             # Request, RequestEventLog
│   │   └── review.py              # Review model
│   │
│   ├── schemas/                   # API schemas (ADD NEW OFTEN)
│   │   ├── __init__.py            # Central export point
│   │   ├── base.py                # Base classes for schemas
│   │   ├── auth.py                # Authentication schemas
│   │   ├── user.py                # User schemas
│   │   ├── request.py             # Request schemas
│   │   ├── review.py              # Review schemas
│   │   └── verification.py        # Verification schemas
│   │
│   ├── api/                       # API routes (ADD NEW OFTEN)
│   │   ├── dependencies/          # FastAPI dependencies
│   │   │   ├── __init__.py
│   │   │   └── auth.py            # Auth dependencies
│   │   └── routes/                # API route modules
│   │       ├── __init__.py
│   │       ├── auth.py            # Authentication endpoints
│   │       ├── users.py           # User management endpoints
│   │       ├── requests.py        # Request endpoints
│   │       ├── reviews.py         # Review endpoints
│   │       └── verification.py    # Verification endpoints
│   │
│   ├── services/                  # Business logic (ADD NEW OFTEN)
│   │   ├── __init__.py
│   │   ├── auth_service.py        # Authentication business logic
│   │   ├── user_service.py        # User management logic
│   │   └── request_service.py     # Request management logic
│   │
│   ├── temporal/                  # Temporal workflows (ADD NEW OFTEN)
│   │   ├── __init__.py
│   │   │
│   │   ├── workflows/             # Workflow definitions
│   │   │   ├── __init__.py        # Central workflow registry
│   │   │   ├── verification.py    # Verification workflow
│   │   │   ├── matching.py        # Request matching workflow
│   │   │   └── review.py          # Review submission workflow
│   │   │
│   │   ├── activities/            # Activity implementations
│   │   │   ├── __init__.py        # Central activity registry
│   │   │   ├── base.py            # Base classes and utilities
│   │   │   ├── verification.py    # Verification activities
│   │   │   ├── matching.py        # Matching activities
│   │   │   ├── review.py          # Review activities
│   │   │   └── notification.py    # Notification activities
│   │   │
│   │   └── worker.py              # Worker process entry point
│   │
│   └── main.py                    # FastAPI application entry point
│
├── tests/                         # Test suite
│   ├── unit/                      # Unit tests
│   │   ├── test_security.py
│   │   ├── test_activities.py
│   │   └── ...
│   └── integration/               # Integration tests
│       ├── test_workflows.py
│       ├── test_api.py
│       └── ...
│
├── alembic/                       # Database migrations
│   ├── versions/                  # Migration files
│   └── env.py
│
├── docker/                        # Docker configurations
│   ├── backend/
│   ├── worker/
│   └── ...
│
├── scripts/                       # Utility scripts
│
├── docker-compose.yml             # Local development stack
├── pyproject.toml                 # Python dependencies and config
├── DEVELOPMENT.md                 # Developer quick-start guide
├── PROJECT_STATUS.md              # Current project status
└── CHANGELOG.md                   # Comprehensive change history
```

---

## <a name="navigation"></a>3. Quick Navigation Guide

### "I need to understand..."

**...how configuration works**
→ Read `src/nabr/core/config.py`

**...how authentication works**
→ Read `src/nabr/core/security.py` then `src/nabr/api/dependencies/auth.py`

**...database models**
→ Read `src/nabr/models/` (start with `user.py`)

**...API endpoints**
→ Read `src/nabr/api/routes/` (each file is one domain)

**...API request/response formats**
→ Read `src/nabr/schemas/` (each file matches a model)

**...Temporal workflows**
→ Read `.github/temporal_guide.md` first, then `src/nabr/temporal/workflows/`

**...Temporal activities**
→ Read `src/nabr/temporal/activities/` (start with `base.py`)

**...how to run the app**
→ Read `DEVELOPMENT.md`

**...project status**
→ Read `PROJECT_STATUS.md`

**...what changed recently**
→ Read `CHANGELOG.md`

### "I need to add..."

**...a new API endpoint**
→ Go to [Adding New Features](#adding-features) → "New API Endpoint"

**...a new Temporal workflow**
→ Go to [Adding New Features](#adding-features) → "New Temporal Workflow"

**...a new database model**
→ Go to [Adding New Features](#adding-features) → "New Database Model"

---

## <a name="adding-features"></a>4. Adding New Features

### Adding a New API Endpoint

**Example: Add "Get User Statistics" endpoint**

#### Step 1: Create/Update Schema

File: `src/nabr/schemas/user.py`

```python
class UserStatistics(BaseSchema):
    """User statistics response."""
    
    total_requests: int = Field(..., description="Total requests created")
    completed_requests: int = Field(..., description="Completed requests")
    average_rating: float = Field(..., description="Average rating")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total_requests": 10,
                "completed_requests": 8,
                "average_rating": 4.5
            }
        }
    )
```

Then add to `__init__.py`:
```python
from nabr.schemas.user import UserStatistics
__all__ = [..., "UserStatistics"]
```

#### Step 2: Create Service Function (Optional)

File: `src/nabr/services/user_service.py`

```python
async def get_user_statistics(db: AsyncSession, user_id: str) -> UserStatistics:
    """
    Get statistics for a user.
    
    Args:
        db: Database session
        user_id: UUID of user
        
    Returns:
        UserStatistics: User statistics
    """
    # Query database
    # Calculate statistics
    # Return schema
    pass
```

#### Step 3: Add Route

File: `src/nabr/api/routes/users.py`

```python
@router.get("/{user_id}/statistics", response_model=UserStatistics)
async def get_user_statistics(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get user statistics.
    
    Returns statistics about user's activity.
    """
    return await user_service.get_user_statistics(db, user_id)
```

#### Step 4: Test

File: `tests/integration/test_users.py`

```python
async def test_get_user_statistics():
    """Test getting user statistics."""
    # Test implementation
    pass
```

### Adding a New Temporal Workflow

**Example: Add "Request Cancellation" workflow**

#### Step 1: Define Workflow Schema

File: `src/nabr/schemas/request.py`

```python
class RequestCancellationInput(BaseSchema):
    """Input for request cancellation workflow."""
    request_id: str
    cancelled_by: str
    reason: str

class CancellationResult(BaseSchema):
    """Result of cancellation workflow."""
    success: bool
    refund_amount: Optional[float] = None
```

#### Step 2: Create Activities

File: `src/nabr/temporal/activities/request.py` (new file)

```python
"""Request management activities."""

from temporalio import activity
from nabr.temporal.activities.base import log_activity_execution

@activity.defn
@log_activity_execution
async def cancel_request_in_db(request_id: str) -> bool:
    """
    Cancel request in database.
    
    Args:
        request_id: UUID of request to cancel
        
    Returns:
        bool: True if successful
    """
    # Implementation
    pass

@activity.defn
@log_activity_execution
async def notify_participants(request_id: str, reason: str) -> bool:
    """
    Notify participants of cancellation.
    
    Args:
        request_id: UUID of request
        reason: Cancellation reason
        
    Returns:
        bool: True if successful
    """
    # Implementation
    pass
```

#### Step 3: Create Workflow

File: `src/nabr/temporal/workflows/cancellation.py` (new file)

```python
"""Request cancellation workflow."""

from datetime import timedelta
from temporalio import workflow

from nabr.temporal.activities.request import (
    cancel_request_in_db,
    notify_participants,
)
from nabr.schemas.request import (
    RequestCancellationInput,
    CancellationResult,
)

@workflow.defn
class RequestCancellationWorkflow:
    """
    Orchestrates request cancellation.
    
    Process:
    1. Cancel request in database
    2. Notify participants
    3. Process any refunds
    4. Log cancellation event
    """
    
    @workflow.run
    async def run(self, input: RequestCancellationInput) -> CancellationResult:
        """Main workflow entry point."""
        
        # Step 1: Cancel in database
        cancelled = await workflow.execute_activity(
            cancel_request_in_db,
            args=[input.request_id],
            start_to_close_timeout=timedelta(seconds=30),
        )
        
        if not cancelled:
            return CancellationResult(success=False)
        
        # Step 2: Notify participants
        await workflow.execute_activity(
            notify_participants,
            args=[input.request_id, input.reason],
            start_to_close_timeout=timedelta(seconds=30),
        )
        
        return CancellationResult(success=True)
```

#### Step 4: Register with Worker

File: `src/nabr/temporal/workflows/__init__.py`

```python
from nabr.temporal.workflows.cancellation import RequestCancellationWorkflow

# Add to all_workflows list
all_workflows = [
    ...,
    RequestCancellationWorkflow,
]
```

File: `src/nabr/temporal/activities/__init__.py`

```python
from nabr.temporal.activities.request import (
    cancel_request_in_db,
    notify_participants,
)

# Add to all_activities list
```

#### Step 5: Test

File: `tests/integration/test_cancellation_workflow.py`

```python
async def test_cancellation_workflow():
    """Test request cancellation workflow."""
    # Test implementation
    pass
```

### Adding a New Database Model

**Example: Add "Message" model for user messaging**

#### Step 1: Create Model

File: `src/nabr/models/message.py` (new file)

```python
"""Message model for user-to-user communication."""

from sqlalchemy import Column, String, Text, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID
import uuid

from nabr.db.session import Base, TimestampMixin

class Message(Base, TimestampMixin):
    """
    Message model for user communication.
    
    Attributes:
        id: Unique message identifier
        sender_id: User who sent the message
        recipient_id: User who receives the message
        subject: Message subject
        body: Message content
        is_read: Whether message has been read
        request_id: Optional related request
    """
    __tablename__ = "messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sender_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    recipient_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    subject = Column(String(200), nullable=False)
    body = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False, nullable=False)
    request_id = Column(UUID(as_uuid=True), ForeignKey("requests.id"), nullable=True)
```

#### Step 2: Create Migration

```bash
uv run alembic revision --autogenerate -m "Add message model"
uv run alembic upgrade head
```

#### Step 3: Create Schemas

File: `src/nabr/schemas/message.py` (new file)

```python
"""Message schemas."""

from uuid import UUID
from typing import Optional
from pydantic import Field

from nabr.schemas.base import BaseSchema, TimestampSchema

class MessageCreate(BaseSchema):
    """Schema for creating a message."""
    recipient_id: UUID
    subject: str = Field(..., min_length=1, max_length=200)
    body: str = Field(..., min_length=1, max_length=5000)
    request_id: Optional[UUID] = None

class MessageRead(MessageCreate, TimestampSchema):
    """Schema for reading a message."""
    id: UUID
    sender_id: UUID
    is_read: bool
```

#### Step 4: Create Routes

File: `src/nabr/api/routes/messages.py` (new file)

```python
"""Message API routes."""

from fastapi import APIRouter, Depends
from nabr.schemas.message import MessageCreate, MessageRead

router = APIRouter(prefix="/messages", tags=["messages"])

@router.post("/", response_model=MessageRead)
async def send_message(message: MessageCreate):
    """Send a message to another user."""
    pass

@router.get("/{message_id}", response_model=MessageRead)
async def get_message(message_id: str):
    """Get a message by ID."""
    pass
```

---

## <a name="patterns"></a>5. Modular Patterns

### Pattern 1: Registry Pattern

**Use for:** Workflows, Activities, Routes

**Purpose:** Easy registration of new components without modifying core code

**Example:** Activity Registry

```python
# In activities/__init__.py

from nabr.temporal.activities.verification import verification_activities
from nabr.temporal.activities.matching import matching_activities
from nabr.temporal.activities.review import review_activities

# Easy to add new activity modules
from nabr.temporal.activities.messaging import messaging_activities  # NEW!

# Combine all
all_activities = (
    verification_activities
    + matching_activities
    + review_activities
    + messaging_activities  # NEW!
)
```

### Pattern 2: Base Class Pattern

**Use for:** Activities, Schemas

**Purpose:** Share common functionality across similar components

**Example:** Activity Base Class

```python
# All activities can inherit from ActivityBase
class ActivityBase:
    def get_db_session(self): ...
    def check_cancellation(self): ...
    def report_progress(self, message: str): ...

# Usage in new activity
@activity.defn
async def my_new_activity(param: str) -> str:
    base = ActivityBase()
    base.check_cancellation()  # Use shared functionality
    async with base.get_db_session() as db:
        # Do work
        pass
```

### Pattern 3: Template Pattern

**Use for:** Anything repetitive

**Purpose:** Copy-paste-modify to create new instances

**Example:** New Workflow Template

```python
# Template workflow structure
@workflow.defn
class MyNewWorkflow:
    """
    Brief description.
    
    Process:
    1. Step 1
    2. Step 2
    3. Step 3
    """
    
    def __init__(self) -> None:
        self.state_var = None
    
    @workflow.run
    async def run(self, input: InputSchema) -> ResultSchema:
        """Main workflow entry point."""
        
        # Execute activities
        result = await workflow.execute_activity(
            my_activity,
            args=[input.param],
            start_to_close_timeout=timedelta(seconds=30),
        )
        
        return ResultSchema(success=True)
    
    @workflow.signal
    async def my_signal(self, data: Any):
        """Handle signal."""
        self.state_var = data
    
    @workflow.query
    def get_status(self) -> dict:
        """Query current status."""
        return {"state": self.state_var}
```

---

## <a name="common-tasks"></a>6. Common Tasks

### Task: Add Validation to Existing Endpoint

**Location:** `src/nabr/schemas/[domain].py`

**Steps:**
1. Find the schema used by endpoint
2. Add validation to field using Pydantic validators

```python
from pydantic import validator

class MySchema(BaseSchema):
    email: str
    
    @validator('email')
    def validate_email_domain(cls, v):
        if not v.endswith('@nabr.app'):
            raise ValueError('Must use nabr.app email')
        return v
```

### Task: Add Error Handling to Activity

**Location:** `src/nabr/temporal/activities/[domain].py`

**Steps:**
1. Find the activity function
2. Wrap risky operations in try-except
3. Use ApplicationError for non-retryable errors

```python
from temporalio.exceptions import ApplicationError

@activity.defn
async def my_activity(param: str) -> str:
    try:
        result = await risky_operation(param)
        return result
    except ValidationError as e:
        # Non-retryable error
        raise ApplicationError(
            f"Invalid input: {e}",
            non_retryable=True
        )
    except NetworkError as e:
        # Retryable error (will use retry policy)
        raise
```

### Task: Add Logging to Any Function

**Pattern:**

```python
import logging

logger = logging.getLogger(__name__)

async def my_function(param: str) -> str:
    logger.info(f"Starting operation for {param}")
    
    try:
        result = await do_work(param)
        logger.info(f"Operation completed successfully")
        return result
    except Exception as e:
        logger.error(f"Operation failed: {e}", exc_info=True)
        raise
```

### Task: Add Database Query

**Location:** Service functions or activities

**Pattern:**

```python
from sqlalchemy import select
from nabr.models.user import User

async def my_function(db: AsyncSession, user_id: str):
    # Query
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise ValueError(f"User not found: {user_id}")
    
    # Update
    user.some_field = "new value"
    await db.commit()
    
    return user
```

---

## <a name="testing"></a>7. Testing Strategy

### Unit Tests

**Test:** Individual functions in isolation

**Location:** `tests/unit/`

**Example:**

```python
# tests/unit/test_security.py
from nabr.core.security import validate_password_strength

def test_password_validation():
    """Test password strength validation."""
    # Valid password
    assert validate_password_strength("SecurePass123!") is True
    
    # Too short
    assert validate_password_strength("Short1!") is False
```

### Integration Tests

**Test:** Components working together

**Location:** `tests/integration/`

**Example:**

```python
# tests/integration/test_verification_workflow.py
import pytest
from temporalio.testing import WorkflowEnvironment

@pytest.mark.asyncio
async def test_verification_workflow():
    """Test complete verification workflow."""
    async with await WorkflowEnvironment.start_time_skipping() as env:
        # Setup worker
        # Start workflow
        # Send signals
        # Assert results
        pass
```

---

## <a name="troubleshooting"></a>8. Troubleshooting

### Issue: Import Errors

**Symptom:** `ModuleNotFoundError` or `ImportError`

**Solution:**
1. Check file exists at expected location
2. Verify `__init__.py` files exist in all directories
3. Check imports in `__init__.py` files match module exports

### Issue: Type Errors

**Symptom:** Pylance/mypy complaining about types

**Solution:**
1. Add type hints to function signatures
2. Import types from `typing` module
3. For SQLAlchemy columns, use proper column access patterns

### Issue: Activity Not Found

**Symptom:** Temporal worker can't find activity

**Solution:**
1. Check activity is decorated with `@activity.defn`
2. Verify activity is imported in `activities/__init__.py`
3. Confirm activity is in `all_activities` list
4. Restart worker

### Issue: Workflow Not Found

**Symptom:** Cannot start workflow

**Solution:**
1. Check workflow is decorated with `@workflow.defn`
2. Verify workflow is imported in `workflows/__init__.py`
3. Confirm workflow is in `all_workflows` list
4. Restart worker

---

## Quick Reference

### File Templates

**New Activity:**
```python
@activity.defn
@log_activity_execution
async def my_activity(param: str) -> str:
    """
    Brief description.
    
    Args:
        param: Description
        
    Returns:
        str: Description
        
    Notes:
        - Important note 1
        - Important note 2
    """
    activity.logger.info(f"Processing {param}")
    # Implementation
    return result
```

**New Schema:**
```python
class MySchema(BaseSchema):
    """Brief description."""
    
    field: str = Field(..., description="Field description")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {"field": "example value"}
        }
    )
```

**New Route:**
```python
@router.get("/endpoint", response_model=ResponseSchema)
async def my_endpoint(
    param: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Brief description.
    
    Detailed description of what endpoint does.
    """
    # Implementation
    return result
```

---

## Remember

1. **Every file has a single, clear purpose**
2. **Every function has comprehensive docstrings**
3. **Every new feature follows existing patterns**
4. **Test everything you add**
5. **When in doubt, check similar existing code**

---

**This guide is a living document. Update it when you add new patterns or discover better approaches!**
