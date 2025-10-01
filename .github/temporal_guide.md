# Temporal Workflow Development Guide for AI Assistants
## Nābr Project - Comprehensive Reference

**Version:** 1.0  
**Last Updated:** October 1, 2025  
**For:** AI assistants co-developing the Nābr community volunteer coordination platform

---

## Table of Contents
1. [Introduction to Temporal](#introduction)
2. [Core Concepts](#core-concepts)
3. [Nābr-Specific Patterns](#nabr-patterns) (cut to save tokens)
4. [Workflow Development](#workflow-development)
5. [Activity Development](#activity-development)
6. [Worker Configuration](#worker-configuration)
7. [Testing Workflows](#testing)
8. [Error Handling & Retries](#error-handling)
9. [Best Practices](#best-practices)
10. [Common Patterns](#common-patterns)
11. [Troubleshooting](#troubleshooting)

---

## 1. Introduction to Temporal

### What is Temporal?

Temporal is a **durable execution platform** that guarantees workflow completion even in the face of failures. For Nābr, this means:

- **User verification workflows** will complete even if the server restarts
- **Request matching processes** are resilient to network failures
- **Review submission workflows** maintain state across interruptions
- **All processes are auditable** through immutable event logs

### Why Temporal for Nābr?

1. **Reliability**: Critical verification and matching processes never lose progress
2. **Observability**: Complete visibility into every step of every workflow
3. **Auditability**: Immutable execution history for security and compliance
4. **Transparency**: Users and administrators can track request lifecycles
5. **Scalability**: Distributed workers handle increased load automatically

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                      Temporal Server                            │
│  (Stores workflow state, schedules tasks, persists history)     │
└────────────────────┬──────────────────┬─────────────────────────┘
                     │                  │
          Save state │                  │ Schedule tasks
          Persist    │                  │ Resume workflows
                     │                  │
┌────────────────────▼──────────────────▼─────────────────────────┐
│                         Workers                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │            Workflow Code (Orchestration)                  │  │
│  │  - Verification workflows                                 │  │
│  │  - Matching workflows                                     │  │
│  │  - Review workflows                                       │  │
│  └──────────────┬───────────────┬──────────────┬─────────────┘  │
│                 │               │              │                 │
│  ┌──────────────▼───┐  ┌────────▼──────┐  ┌───▼─────────────┐  │
│  │  Activity:       │  │  Activity:    │  │  Activity:      │  │
│  │  Database Ops    │  │  QR Code Gen  │  │  Notifications  │  │
│  └──────────────────┘  └───────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                     │               │              │
                     ▼               ▼              ▼
            ┌──────────────┐  ┌──────────┐  ┌──────────────┐
            │  PostgreSQL  │  │  External│  │  Email/SMS   │
            │   Database   │  │  APIs    │  │   Services   │
            └──────────────┘  └──────────┘  └──────────────┘
```

---

## 2. Core Concepts

### Workflows

**Definition**: Durable functions that orchestrate activities and maintain state.

**Key Characteristics**:
- **Deterministic**: Must produce the same result given the same inputs
- **Durable**: State persists across failures
- **Long-running**: Can run for days, months, or years
- **Versioned**: Support workflow code evolution

**Nābr Examples**:
- User verification process (multi-step, requires human interaction)
- Request matching algorithm (complex logic, multiple attempts)
- Review submission and rating calculation

### Activities

**Definition**: Individual units of work that can have side effects.

**Key Characteristics**:
- **Non-deterministic**: Can interact with external systems
- **Retryable**: Automatic retry on failure
- **Short-lived**: Typically seconds to minutes
- **Idempotent**: Safe to retry without duplicating effects

**Nābr Examples**:
- Generate QR code for verification
- Query database for matching volunteers
- Send notification email
- Update user rating in database

### Workers

**Definition**: Processes that execute workflow and activity code.

**Key Characteristics**:
- **Scalable**: Run multiple workers for load distribution
- **Isolated**: Each worker is independent
- **Configurable**: Control concurrency and resource usage

### Signals and Queries

**Signals**: Asynchronous messages sent to running workflows
- Example: User submits verification document

**Queries**: Synchronous read-only operations on workflow state
- Example: Check current verification status

---

## 3. Nābr-Specific Patterns (#nabr-patterns) (cut to save tokens)

---
## 4. Workflow Development

### Workflow Structure

```python
from temporalio import workflow
from datetime import timedelta

@workflow.defn
class MyWorkflow:
    """Workflow description."""
    
    def __init__(self) -> None:
        """Initialize workflow state."""
        self.state_variable = None
    
    @workflow.run
    async def run(self, input_param: InputType) -> ReturnType:
        """Main workflow entry point."""
        # Workflow logic here
        result = await workflow.execute_activity(
            my_activity,
            args=[input_param],
            start_to_close_timeout=timedelta(seconds=30),
        )
        return result
    
    @workflow.signal
    async def my_signal(self, data: SignalData) -> None:
        """Handle async signals."""
        self.state_variable = data
    
    @workflow.query
    def my_query(self) -> QueryResult:
        """Handle sync queries."""
        return self.state_variable
```

### Determinism Rules

**✅ ALLOWED in Workflows:**
- Call activities
- Use Temporal time (`workflow.now()`)
- Use workflow sleep (`await asyncio.sleep()`)
- Use workflow random (`workflow.random()`)
- Store and read workflow state
- Use signals and queries
- Call child workflows

**❌ FORBIDDEN in Workflows:**
- Direct database access
- HTTP requests
- File I/O
- System time (`datetime.now()`)
- Random numbers (`random.random()`)
- Threading
- Global state mutation

### Activity Execution

```python
# Basic activity execution
result = await workflow.execute_activity(
    my_activity,
    args=[arg1, arg2],
    start_to_close_timeout=timedelta(seconds=30),
)

# With retry policy
result = await workflow.execute_activity(
    my_activity,
    args=[arg1],
    start_to_close_timeout=timedelta(seconds=30),
    retry_policy={
        "initial_interval": timedelta(seconds=1),
        "maximum_interval": timedelta(seconds=60),
        "maximum_attempts": 5,
        "backoff_coefficient": 2.0,
    },
)

# With heartbeat
result = await workflow.execute_activity(
    long_running_activity,
    args=[arg1],
    start_to_close_timeout=timedelta(minutes=10),
    heartbeat_timeout=timedelta(seconds=30),
)
```

### Signals and Queries

```python
# In workflow class
@workflow.signal
async def update_state(self, new_value: str) -> None:
    """Update workflow state via signal."""
    self.current_state = new_value
    self.state_updated.set()  # Event to trigger waiting condition

@workflow.query
def get_current_state(self) -> str:
    """Query current state."""
    return self.current_state

# Waiting for signals
await workflow.wait_condition(
    lambda: self.current_state == "expected_value",
    timeout=timedelta(hours=24)
)
```

### Child Workflows

```python
# Start child workflow
child_handle = await workflow.start_child_workflow(
    ChildWorkflow,
    args=[input_data],
    id=f"child-{workflow.info().workflow_id}",
)

# Wait for result
result = await child_handle

# Or execute and wait in one step
result = await workflow.execute_child_workflow(
    ChildWorkflow,
    args=[input_data],
    id=f"child-{workflow.info().workflow_id}",
)
```

---

## 5. Activity Development

### Activity Structure

```python
from temporalio import activity
from typing import Any
import asyncio

@activity.defn
async def my_async_activity(param: str) -> dict[str, Any]:
    """
    Async activity for I/O-bound operations.
    
    Activities can:
    - Access databases
    - Make HTTP requests
    - Perform file I/O
    - Call external APIs
    """
    activity.logger.info(f"Processing {param}")
    
    # Report progress (for long-running activities)
    activity.heartbeat("Starting processing")
    
    # Do actual work
    result = await some_async_operation(param)
    
    activity.heartbeat("Processing complete")
    
    return {"result": result, "status": "success"}

@activity.defn
def my_sync_activity(param: int) -> int:
    """
    Sync activity for CPU-bound operations.
    Runs in thread pool executor.
    """
    activity.logger.info(f"Computing {param}")
    
    # CPU-intensive work
    result = expensive_computation(param)
    
    return result
```

### Idempotency

Activities should be **idempotent** (safe to retry):

```python
@activity.defn
async def create_record(user_id: str, data: dict) -> str:
    """Idempotent record creation."""
    
    # Check if already exists
    existing = await db.get_record(user_id)
    if existing:
        return existing.id
    
    # Create new
    record = await db.create_record(user_id, data)
    return record.id
```

### Heartbeating

For long-running activities:

```python
@activity.defn
async def process_large_dataset(dataset_id: str) -> dict:
    """Long-running activity with heartbeat."""
    
    items = await load_dataset(dataset_id)
    processed = 0
    total = len(items)
    
    for item in items:
        # Check if activity is being cancelled
        if activity.is_cancelled():
            activity.logger.info("Activity cancelled, cleaning up...")
            await cleanup()
            raise activity.CancelledError("Processing cancelled")
        
        # Report progress
        activity.heartbeat(f"Processed {processed}/{total}")
        
        await process_item(item)
        processed += 1
    
    return {"processed": processed, "total": total}
```

### Error Handling

```python
from temporalio.exceptions import ApplicationError

@activity.defn
async def risky_operation(param: str) -> str:
    """Activity with error handling."""
    
    try:
        result = await external_api_call(param)
        return result
    
    except ValidationError as e:
        # Non-retryable error
        raise ApplicationError(
            f"Invalid parameter: {e}",
            non_retryable=True,
        )
    
    except TemporaryError as e:
        # Retryable error (will use workflow's retry policy)
        raise ApplicationError(
            f"Temporary failure: {e}",
            non_retryable=False,
        )
    
    except Exception as e:
        # Log and re-raise
        activity.logger.error(f"Unexpected error: {e}")
        raise
```

---

## 6. Worker Configuration

### Basic Worker Setup

```python
# src/nabr/temporal/worker.py

import asyncio
import signal
from temporalio.client import Client
from temporalio.worker import Worker
import concurrent.futures

from nabr.core.config import get_settings
from nabr.temporal.workflows.verification import UserVerificationWorkflow
from nabr.temporal.workflows.matching import RequestMatchingWorkflow
from nabr.temporal.workflows.review import ReviewSubmissionWorkflow
from nabr.temporal.activities import (
    verification_activities,
    matching_activities,
    review_activities,
)

settings = get_settings()

async def main():
    """Main worker entry point."""
    
    # Connect to Temporal server
    client = await Client.connect(
        settings.temporal_host,
        namespace=settings.temporal_namespace,
    )
    
    # Create thread pool for sync activities
    activity_executor = concurrent.futures.ThreadPoolExecutor(
        max_workers=100
    )
    
    # Create worker
    worker = Worker(
        client,
        task_queue=settings.temporal_task_queue,
        workflows=[
            UserVerificationWorkflow,
            RequestMatchingWorkflow,
            ReviewSubmissionWorkflow,
        ],
        activities=[
            *verification_activities,
            *matching_activities,
            *review_activities,
        ],
        activity_executor=activity_executor,
        max_concurrent_workflow_tasks=100,
        max_concurrent_activities=100,
    )
    
    # Setup graceful shutdown
    stop_event = asyncio.Event()
    
    def signal_handler(sig, frame):
        print(f"\nReceived signal {sig}, shutting down gracefully...")
        stop_event.set()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Run worker
    print(f"Starting worker on task queue: {settings.temporal_task_queue}")
    async with worker:
        await stop_event.wait()
    
    print("Worker stopped")
    activity_executor.shutdown(wait=True)

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 7. Testing Workflows

### Unit Testing Activities

```python
# tests/unit/test_activities.py

import pytest
from temporalio.testing import ActivityEnvironment

from nabr.temporal.activities.verification import generate_verification_qr_code

@pytest.mark.asyncio
async def test_generate_qr_code():
    """Test QR code generation activity."""
    
    env = ActivityEnvironment()
    
    # Run activity
    result = await env.run(
        generate_verification_qr_code,
        "user-123"
    )
    
    # Assert
    assert result is not None
    assert len(result) > 0
    assert result.startswith("VERIFY-")
```

### Integration Testing Workflows

```python
# tests/integration/test_verification_workflow.py

import pytest
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from nabr.temporal.workflows.verification import UserVerificationWorkflow
from nabr.temporal.activities import verification_activities
from nabr.schemas.verification import VerificationRequest, VerificationStatus

@pytest.mark.asyncio
async def test_verification_workflow_success():
    """Test successful verification flow."""
    
    async with await WorkflowEnvironment.start_time_skipping() as env:
        # Setup worker
        async with Worker(
            env.client,
            task_queue="test-queue",
            workflows=[UserVerificationWorkflow],
            activities=verification_activities,
        ):
            # Start workflow
            handle = await env.client.start_workflow(
                UserVerificationWorkflow.run,
                VerificationRequest(
                    user_id="test-user-123",
                    id_document_url=None,
                ),
                id="test-verification-1",
                task_queue="test-queue",
            )
            
            # Simulate verifier confirmations
            await handle.signal(
                UserVerificationWorkflow.add_verifier,
                "verifier-1"
            )
            await handle.signal(
                UserVerificationWorkflow.add_verifier,
                "verifier-2"
            )
            
            # Get result
            result = await handle.result()
            
            # Assert
            assert result.status == VerificationStatus.VERIFIED
            assert len(result.verifier_ids) == 2

@pytest.mark.asyncio
async def test_verification_workflow_timeout():
    """Test verification timeout."""
    
    async with await WorkflowEnvironment.start_time_skipping() as env:
        async with Worker(
            env.client,
            task_queue="test-queue",
            workflows=[UserVerificationWorkflow],
            activities=verification_activities,
        ):
            # Start workflow
            handle = await env.client.start_workflow(
                UserVerificationWorkflow.run,
                VerificationRequest(user_id="test-user-456"),
                id="test-verification-2",
                task_queue="test-queue",
            )
            
            # Skip time past timeout (30 days)
            await env.sleep(31 * 24 * 60 * 60)
            
            # Get result
            result = await handle.result()
            
            # Assert
            assert result.status == VerificationStatus.EXPIRED
```

### Mocking Activities in Tests

```python
@pytest.mark.asyncio
async def test_workflow_with_mocked_activities():
    """Test workflow with mocked activities."""
    
    async with await WorkflowEnvironment.start_time_skipping() as env:
        # Mock activity
        async def mock_generate_qr(user_id: str) -> str:
            return f"MOCKED-QR-{user_id}"
        
        # Register mock
        env.mock_activity(
            generate_verification_qr_code,
            mock_generate_qr
        )
        
        async with Worker(
            env.client,
            task_queue="test-queue",
            workflows=[UserVerificationWorkflow],
            activities=verification_activities,
        ):
            # Test workflow with mocked activity
            result = await env.client.execute_workflow(
                UserVerificationWorkflow.run,
                VerificationRequest(user_id="test-123"),
                id="test-mock-1",
                task_queue="test-queue",
            )
            
            # Mocked QR code was used
            status = await handle.query(
                UserVerificationWorkflow.get_status
            )
            assert status["verification_code"].startswith("MOCKED-QR-")
```

---

## 8. Error Handling & Retries

### Retry Policies

```python
from temporalio.common import RetryPolicy

# Default retry policy
default_retry = RetryPolicy(
    initial_interval=timedelta(seconds=1),
    maximum_interval=timedelta(seconds=60),
    backoff_coefficient=2.0,
    maximum_attempts=5,
)

# No retries
no_retry = RetryPolicy(maximum_attempts=1)

# Infinite retries (use with caution)
infinite_retry = RetryPolicy(maximum_attempts=0)

# Custom retry
custom_retry = RetryPolicy(
    initial_interval=timedelta(seconds=5),
    maximum_interval=timedelta(minutes=5),
    backoff_coefficient=1.5,
    maximum_attempts=10,
    non_retryable_error_types=["ValidationError"],
)
```

### Workflow Error Handling

```python
@workflow.defn
class RobustWorkflow:
    @workflow.run
    async def run(self, input: dict) -> dict:
        try:
            # Critical activity - retry many times
            result1 = await workflow.execute_activity(
                critical_activity,
                args=[input],
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=RetryPolicy(maximum_attempts=10),
            )
            
            # Non-critical activity - fail fast
            try:
                result2 = await workflow.execute_activity(
                    optional_activity,
                    args=[result1],
                    start_to_close_timeout=timedelta(seconds=10),
                    retry_policy=RetryPolicy(maximum_attempts=2),
                )
            except Exception as e:
                workflow.logger.warning(f"Optional activity failed: {e}")
                result2 = None
            
            return {"result1": result1, "result2": result2}
            
        except Exception as e:
            workflow.logger.error(f"Critical failure: {e}")
            raise ApplicationError(
                f"Workflow failed: {str(e)}",
                non_retryable=True,
            )
```

### Compensation (Saga Pattern)

```python
@workflow.defn
class SagaWorkflow:
    """Workflow with compensation for rollback."""
    
    def __init__(self):
        self.completed_steps = []
    
    @workflow.run
    async def run(self, input: dict) -> dict:
        try:
            # Step 1
            await workflow.execute_activity(
                step1_activity,
                args=[input],
                start_to_close_timeout=timedelta(seconds=30),
            )
            self.completed_steps.append("step1")
            
            # Step 2
            await workflow.execute_activity(
                step2_activity,
                args=[input],
                start_to_close_timeout=timedelta(seconds=30),
            )
            self.completed_steps.append("step2")
            
            # Step 3 (might fail)
            await workflow.execute_activity(
                step3_activity,
                args=[input],
                start_to_close_timeout=timedelta(seconds=30),
            )
            self.completed_steps.append("step3")
            
            return {"success": True}
            
        except Exception as e:
            # Rollback completed steps
            workflow.logger.error(f"Error occurred, rolling back: {e}")
            await self._rollback()
            raise
    
    async def _rollback(self):
        """Compensate completed steps."""
        for step in reversed(self.completed_steps):
            try:
                await workflow.execute_activity(
                    f"compensate_{step}",
                    start_to_close_timeout=timedelta(seconds=30),
                )
                workflow.logger.info(f"Compensated {step}")
            except Exception as e:
                workflow.logger.error(f"Compensation failed for {step}: {e}")
```

---

## 9. Best Practices

### 1. Workflow Design

**✅ DO:**
- Keep workflows focused on orchestration
- Use activities for all side effects
- Design for long-running scenarios
- Use signals for external events
- Use queries for real-time status
- Log important decisions

**❌ DON'T:**
- Put business logic in workflows
- Access databases directly
- Make HTTP calls
- Use non-deterministic functions
- Store large objects in workflow state

### 2. Activity Design

**✅ DO:**
- Make activities idempotent
- Use heartbeats for long operations
- Handle cancellation gracefully
- Return meaningful error messages
- Use appropriate timeouts

**❌ DON'T:**
- Store state between retries
- Assume single execution
- Ignore cancellation signals
- Use excessively long timeouts

### 3. Error Handling

**✅ DO:**
- Use appropriate retry policies
- Distinguish retryable vs non-retryable errors
- Log errors with context
- Implement compensation when needed
- Test failure scenarios

**❌ DON'T:**
- Swallow exceptions silently
- Retry indefinitely
- Use generic exception handlers
- Ignore partial failures

### 4. Testing

**✅ DO:**
- Test workflows in isolation
- Mock external dependencies
- Test timeout scenarios
- Test signal handling
- Use time-skipping for speed

**❌ DON'T:**
- Test against production Temporal
- Skip integration tests
- Ignore edge cases
- Test only happy paths

### 5. Monitoring

**✅ DO:**
- Use Temporal Web UI
- Monitor workflow metrics
- Set up alerts for failures
- Track workflow duration
- Review execution histories

**❌ DON'T:**
- Ignore failed workflows
- Disable history archiving
- Skip log analysis

---

## 10. Common Patterns

### Pattern: Polling Until Complete

```python
@workflow.defn
class PollingWorkflow:
    """Wait for external system to complete."""
    
    @workflow.run
    async def run(self, job_id: str) -> str:
        while True:
            status = await workflow.execute_activity(
                check_job_status,
                args=[job_id],
                start_to_close_timeout=timedelta(seconds=10),
            )
            
            if status == "complete":
                return "Job completed"
            
            if status == "failed":
                raise ApplicationError("Job failed")
            
            # Wait before next poll
            await asyncio.sleep(timedelta(seconds=30))
```

### Pattern: Fan-Out/Fan-In

```python
@workflow.defn
class FanOutWorkflow:
    """Execute multiple activities in parallel."""
    
    @workflow.run
    async def run(self, items: list[str]) -> list[str]:
        # Start all activities
        tasks = [
            workflow.execute_activity(
                process_item,
                args=[item],
                start_to_close_timeout=timedelta(seconds=30),
            )
            for item in items
        ]
        
        # Wait for all to complete
        results = await asyncio.gather(*tasks)
        
        return results
```

### Pattern: Human-in-the-Loop

```python
@workflow.defn
class ApprovalWorkflow:
    """Wait for human approval."""
    
    def __init__(self):
        self.approved = None
    
    @workflow.run
    async def run(self, request_id: str) -> str:
        # Send approval request
        await workflow.execute_activity(
            send_approval_request,
            args=[request_id],
            start_to_close_timeout=timedelta(seconds=30),
        )
        
        # Wait for approval (7 days timeout)
        try:
            await workflow.wait_condition(
                lambda: self.approved is not None,
                timeout=timedelta(days=7)
            )
        except asyncio.TimeoutError:
            return "Request expired"
        
        if self.approved:
            return "Approved"
        else:
            return "Rejected"
    
    @workflow.signal
    async def approve(self, approved: bool):
        self.approved = approved
```

### Pattern: Rate Limiting

```python
@workflow.defn
class RateLimitedWorkflow:
    """Process with rate limiting."""
    
    @workflow.run
    async def run(self, items: list[str]) -> list[str]:
        results = []
        
        for i, item in enumerate(items):
            # Rate limit: max 10 per second
            if i > 0 and i % 10 == 0:
                await asyncio.sleep(timedelta(seconds=1))
            
            result = await workflow.execute_activity(
                process_item,
                args=[item],
                start_to_close_timeout=timedelta(seconds=5),
            )
            results.append(result)
        
        return results
```

---

## 11. Troubleshooting

### Common Issues

#### Issue: Non-Determinism Error

**Symptom**: Workflow fails with non-determinism error during replay

**Causes:**
- Using `datetime.now()` instead of `workflow.now()`
- Using `random.random()` instead of `workflow.random()`
- Direct database calls in workflow code
- Reading files in workflow code

**Solution:**
```python
# ❌ WRONG
current_time = datetime.now()

# ✅ CORRECT
current_time = workflow.now()

# ❌ WRONG
random_value = random.random()

# ✅ CORRECT
random_value = workflow.random().random()
```

#### Issue: Activity Timeout

**Symptom**: Activities fail with timeout error

**Causes:**
- Too short timeout
- Activity doing too much work
- Network delays
- Database slow queries

**Solution:**
```python
# Increase timeout
result = await workflow.execute_activity(
    slow_activity,
    args=[input],
    start_to_close_timeout=timedelta(minutes=5),  # Increased
    heartbeat_timeout=timedelta(seconds=30),  # Add heartbeat
)

# Or split into multiple activities
result1 = await workflow.execute_activity(part1_activity, ...)
result2 = await workflow.execute_activity(part2_activity, ...)
```

#### Issue: Workflow Stuck

**Symptom**: Workflow never completes

**Causes:**
- Waiting for signal that never arrives
- Activity stuck without heartbeat
- Infinite loop without sleep
- Missing timeout on wait_condition

**Solution:**
```python
# Always use timeouts
try:
    await workflow.wait_condition(
        lambda: self.signal_received,
        timeout=timedelta(hours=24)  # Add timeout
    )
except asyncio.TimeoutError:
    # Handle timeout
    workflow.logger.warning("Timed out waiting for signal")
```

#### Issue: Memory Leak

**Symptom**: Worker memory usage grows over time

**Causes:**
- Storing too much in workflow state
- Not cleaning up completed child workflows
- Large activity results

**Solution:**
```python
# ❌ WRONG - storing large data
self.all_results = []  # Can grow unbounded
for item in items:
    result = await workflow.execute_activity(...)
    self.all_results.append(result)

# ✅ CORRECT - only store summary
self.result_count = 0
for item in items:
    await workflow.execute_activity(...)
    self.result_count += 1
```

### Debugging Tips

1. **Use Temporal Web UI**: View workflow execution history
2. **Check Worker Logs**: Activity errors appear here
3. **Use Workflow Logger**: Add debug logging
4. **Test with Time-Skipping**: Speed up timeout testing
5. **Replay Workflows**: Test non-determinism locally

---

## Quick Reference

### Workflow Decorators
- `@workflow.defn` - Define workflow class
- `@workflow.run` - Main workflow method
- `@workflow.signal` - Handle async signals
- `@workflow.query` - Handle sync queries

### Activity Decorators
- `@activity.defn` - Define activity function

### Common Imports
```python
from temporalio import workflow, activity
from temporalio.client import Client
from temporalio.worker import Worker
from temporalio.exceptions import ApplicationError
from datetime import timedelta
import asyncio
```

### Useful Functions
- `workflow.now()` - Get workflow time
- `workflow.random()` - Get deterministic random
- `workflow.logger` - Workflow logger
- `activity.logger` - Activity logger
- `activity.heartbeat()` - Report progress
- `activity.is_cancelled()` - Check cancellation

---

## Resources

- [Temporal Python SDK Docs](https://docs.temporal.io/dev-guide/python)
- [Temporal Concepts](https://docs.temporal.io/concepts)
- [Nābr Project Status](../PROJECT_STATUS.md)
- [Nābr Development Guide](../DEVELOPMENT.md)

---

**Remember**: Temporal workflows are the foundation of Nābr's reliability, transparency, and auditability. Every critical process should be a workflow!
