"""
Verification event recording activities.

Records immutable audit trail events for all verification-related actions.
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional
from uuid import UUID

from temporalio import activity

from nabr.db.session import AsyncSessionLocal
from nabr.models.verification import VerificationEvent


@activity.defn(name="record_verification_event")
async def record_verification_event(
    user_id: str,
    event_type: str,
    method: Optional[str] = None,
    data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Record a verification event in the immutable audit trail.
    
    Args:
        user_id: UUID of user
        event_type: Type of event (e.g., "points_awarded", "method_completed")
        method: Verification method (if applicable)
        data: Additional structured event data
        
    Returns:
        Dictionary with event ID and timestamp
    """
    activity.logger.info(f"Recording event: {event_type} for user {user_id}")
    
    async with AsyncSessionLocal() as db:
        event = VerificationEvent(
            user_id=UUID(user_id),
            event_type=event_type,
            event_data={
                "method": method,
                **(data or {}),
            },
            temporal_workflow_id=activity.info().workflow_id,
            created_at=datetime.now(timezone.utc),
        )
        db.add(event)
        await db.commit()
        
        activity.logger.info(f"Recorded event {event.id} of type {event_type}")
        
        return {
            "event_id": str(event.id),
            "event_type": event_type,
            "created_at": event.created_at.isoformat(),
        }
