# Temporal Components README
## Nābr Workflows and Activities

This directory contains all Temporal workflow and activity implementations for the Nābr platform.

---

## 📁 Directory Structure

```
temporal/
├── __init__.py              # Package initialization
├── worker.py                # Worker process entry point (TO BE CREATED)
│
├── workflows/               # Workflow definitions (orchestration logic)
│   ├── __init__.py          # Workflow registry (TO BE CREATED)
│   ├── verification.py      # User verification workflow (TO BE CREATED)
│   ├── matching.py          # Request-volunteer matching (TO BE CREATED)
│   └── review.py            # Review submission workflow (TO BE CREATED)
│
└── activities/              # Activity implementations (work units)
    ├── __init__.py          # Activity registry ✅ CREATED
    ├── base.py              # Base classes and utilities ✅ CREATED
    ├── verification.py      # Verification activities ✅ CREATED
    ├── matching.py          # Matching activities ✅ CREATED
    ├── review.py            # Review activities ✅ CREATED
    └── notification.py      # Notification activities ✅ CREATED
```

---

## ✅ Completed Components

### Activities (20 total)

#### Verification Activities (5)
1. `generate_verification_qr_code` - Generate unique QR code for in-person verification
2. `validate_id_document` - Validate uploaded ID documents
3. `update_verification_status` - Update verification status in database
4. `log_verification_event` - Log verification events for audit trail
5. `hash_id_document` - Generate secure hash of ID document

#### Matching Activities (5)
1. `find_candidate_volunteers` - Find volunteers matching request criteria
2. `calculate_match_scores` - Calculate match scores using algorithm
3. `notify_volunteers` - Send notifications to candidate volunteers
4. `assign_request_to_volunteer` - Assign request to accepting volunteer
5. `log_matching_event` - Log matching events for audit trail

#### Review Activities (6)
1. `validate_review_eligibility` - Check if reviewer is eligible
2. `save_review` - Save review to database (idempotent)
3. `update_user_rating` - Recalculate and update user ratings
4. `check_for_moderation` - Check if review needs moderation
5. `notify_reviewee` - Notify user about received review
6. `log_review_event` - Log review events for audit trail

#### Notification Activities (4)
1. `send_email` - Send email notifications
2. `send_sms` - Send SMS notifications
3. `notify_user` - Send notification via user's preferred channel(s)
4. `send_batch_notifications` - Send multiple notifications efficiently

---

## 🚧 Next Steps

### 1. Create Workflows

Based on the patterns in `.github/temporal_guide.md`, create:

#### `workflows/verification.py`
```python
from datetime import timedelta
from temporalio import workflow
from nabr.temporal.activities import (
    generate_verification_qr_code,
    validate_id_document,
    update_verification_status,
    log_verification_event,
)

@workflow.defn
class UserVerificationWorkflow:
    """User verification workflow - see temporal_guide.md for template"""
    
    def __init__(self) -> None:
        self.verifications_received = 0
        self.verifier_ids = []
    
    @workflow.run
    async def run(self, request: VerificationRequest) -> VerificationResult:
        # See .github/temporal_guide.md for complete implementation
        pass
    
    @workflow.signal
    async def add_verifier(self, verifier_id: str) -> None:
        # Handle verifier confirmation signal
        pass
    
    @workflow.query
    def get_status(self) -> dict:
        # Return current status
        pass
```

#### `workflows/matching.py`
```python
@workflow.defn
class RequestMatchingWorkflow:
    """Request matching workflow - see temporal_guide.md for template"""
    # Implementation following guide patterns
    pass
```

#### `workflows/review.py`
```python
@workflow.defn
class ReviewSubmissionWorkflow:
    """Review submission workflow - see temporal_guide.md for template"""
    # Implementation following guide patterns
    pass
```

### 2. Create Worker

#### `worker.py`
```python
import asyncio
from temporalio.client import Client
from temporalio.worker import Worker

from nabr.core.config import get_settings
from nabr.temporal.workflows import all_workflows
from nabr.temporal.activities import all_activities

async def main():
    """Main worker entry point."""
    settings = get_settings()
    
    # Connect to Temporal
    client = await Client.connect(
        settings.temporal_host,
        namespace=settings.temporal_namespace,
    )
    
    # Create worker
    worker = Worker(
        client,
        task_queue=settings.temporal_task_queue,
        workflows=all_workflows,
        activities=all_activities,
    )
    
    # Run worker
    print(f"Starting worker on task queue: {settings.temporal_task_queue}")
    await worker.run()

if __name__ == "__main__":
    asyncio.run(main())
```

### 3. Update Configuration

Ensure `src/nabr/core/config.py` has Temporal settings:
```python
class Settings(BaseSettings):
    # Temporal configuration
    temporal_host: str = Field(default="localhost:7233")
    temporal_namespace: str = Field(default="default")
    temporal_task_queue: str = Field(default="nabr-task-queue")
```

---

## 🎯 Activity Design Principles

All activities follow these principles:

### 1. Idempotency
Activities can be safely retried without side effects:
```python
# Check if already exists before creating
existing = await db.query(...).first()
if existing:
    return existing.id  # Return existing instead of error

# Create new
new_record = await db.create(...)
return new_record.id
```

### 2. Comprehensive Logging
Every activity logs its operations:
```python
@activity.defn
@log_activity_execution  # Decorator adds automatic logging
async def my_activity(param: str) -> str:
    activity.logger.info(f"Processing {param}")
    # ... work ...
    activity.logger.info("Completed successfully")
    return result
```

### 3. Error Handling
Activities distinguish retryable vs non-retryable errors:
```python
from temporalio.exceptions import ApplicationError

try:
    result = await operation()
except ValidationError as e:
    # Non-retryable
    raise ApplicationError(str(e), non_retryable=True)
except NetworkError as e:
    # Retryable - will use workflow's retry policy
    raise
```

### 4. Heartbeating
Long-running activities report progress:
```python
@activity.defn
async def process_large_dataset(data_id: str) -> dict:
    items = await load_items(data_id)
    
    for i, item in enumerate(items):
        # Check cancellation
        if activity.is_cancelled():
            raise asyncio.CancelledError()
        
        # Report progress
        activity.heartbeat(f"Processed {i}/{len(items)}")
        
        await process_item(item)
    
    return {"processed": len(items)}
```

---

## 📖 Usage Examples

### Starting a Verification Workflow

```python
from temporalio.client import Client
from nabr.temporal.workflows import UserVerificationWorkflow
from nabr.schemas.verification import VerificationRequest

# Connect to Temporal
client = await Client.connect("localhost:7233")

# Start workflow
handle = await client.start_workflow(
    UserVerificationWorkflow.run,
    VerificationRequest(
        user_id="550e8400-e29b-41d4-a716-446655440000",
        id_document_url="https://storage.nabr.app/docs/id.jpg"
    ),
    id=f"verification-{user_id}",
    task_queue="nabr-task-queue",
)

# Get result (waits for completion)
result = await handle.result()
print(f"Verification status: {result.status}")
```

### Sending a Signal to Workflow

```python
# Get workflow handle
handle = client.get_workflow_handle(workflow_id="verification-123")

# Send signal (verifier confirmed)
await handle.signal(
    UserVerificationWorkflow.add_verifier,
    "verifier-user-id-456"
)
```

### Querying Workflow State

```python
# Get workflow handle
handle = client.get_workflow_handle(workflow_id="verification-123")

# Query current status
status = await handle.query(UserVerificationWorkflow.get_status)
print(f"Verifications received: {status['verifications_received']}")
```

---

## 🧪 Testing

### Unit Testing Activities

```python
import pytest
from temporalio.testing import ActivityEnvironment

from nabr.temporal.activities import generate_verification_qr_code

@pytest.mark.asyncio
async def test_generate_qr_code():
    """Test QR code generation."""
    env = ActivityEnvironment()
    
    # Run activity
    code = await env.run(
        generate_verification_qr_code,
        "user-123"
    )
    
    # Assert
    assert code.startswith("VERIFY-")
    assert len(code) == 19  # "VERIFY-" + 12 chars
```

### Integration Testing Workflows

```python
import pytest
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

@pytest.mark.asyncio
async def test_verification_workflow():
    """Test complete verification workflow."""
    
    async with await WorkflowEnvironment.start_time_skipping() as env:
        # Create worker with workflows and activities
        async with Worker(
            env.client,
            task_queue="test-queue",
            workflows=[UserVerificationWorkflow],
            activities=verification_activities,
        ):
            # Start workflow
            handle = await env.client.start_workflow(
                UserVerificationWorkflow.run,
                VerificationRequest(user_id="test-user-123"),
                id="test-verification",
                task_queue="test-queue",
            )
            
            # Send signals
            await handle.signal(UserVerificationWorkflow.add_verifier, "verifier-1")
            await handle.signal(UserVerificationWorkflow.add_verifier, "verifier-2")
            
            # Get result
            result = await handle.result()
            
            # Assert
            assert result.status == "verified"
            assert len(result.verifier_ids) == 2
```

---

## 🔍 Monitoring and Debugging

### Temporal Web UI
Access at `http://localhost:8080` (when running via Docker Compose)

### Viewing Workflow History
1. Navigate to Temporal Web UI
2. Search for workflow by ID
3. View complete execution history
4. Inspect each activity execution
5. Review any errors or retries

### Common Issues

**Issue:** Activity not found
- Check activity is imported in `activities/__init__.py`
- Verify activity is in `all_activities` list
- Restart worker

**Issue:** Workflow not starting
- Check workflow is imported in `workflows/__init__.py`
- Verify workflow is in `all_workflows` list
- Check Temporal server is running
- Verify task queue name matches

**Issue:** Activity timing out
- Increase `start_to_close_timeout`
- Add heartbeat for long operations
- Check database connection pool size

---

## 📚 Additional Resources

- **Temporal Guide:** `.github/temporal_guide.md` - Complete Temporal reference
- **AI Dev Guide:** `.github/AI_DEVELOPMENT_GUIDE.md` - Adding new features
- **Config:** `src/nabr/core/config.py` - Temporal configuration
- **Official Docs:** https://docs.temporal.io/dev-guide/python

---

## 🎓 Key Concepts Refresher

**Workflow:** Durable function that orchestrates activities. Must be deterministic.

**Activity:** Unit of work that can have side effects. Can be retried.

**Signal:** Asynchronous message sent to running workflow.

**Query:** Synchronous read of workflow state.

**Task Queue:** Named queue where workers poll for work.

**Worker:** Process that executes workflows and activities.

---

**All activities are ready to use. Workflows are ready to be created following the patterns in the Temporal guide!** 🚀
