"""
Progressive trust scoring and points awarding activities.

Core activities for calculating trust scores, awarding points, and updating
verification levels based on the progressive trust model.
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional
from uuid import UUID

from temporalio import activity
from sqlalchemy import select

from nabr.db.session import AsyncSessionLocal
from nabr.models.user import User, UserType
from nabr.models.verification import (
    UserVerificationLevel,
    VerificationEvent,
)
from nabr.models.verification_types import (
    VerificationLevel,
    VerificationMethod,
    calculate_trust_score,
    calculate_verification_level as calc_level_from_score,
)


@activity.defn(name="calculate_trust_score_activity")
async def calculate_trust_score_activity(
    completed_methods: Dict[str, int],
    user_type: str,
) -> int:
    """
    Calculate total trust score from completed verification methods.
    
    Args:
        completed_methods: Dict mapping method name to completion count
        user_type: Type of user account (INDIVIDUAL, BUSINESS, ORGANIZATION)
        
    Returns:
        Total trust score (points)
    """
    activity.logger.info(f"Calculating trust score for {user_type} with {len(completed_methods)} methods")
    
    # Convert method names to enum
    method_dict = {}
    for method_name, count in completed_methods.items():
        try:
            method = VerificationMethod(method_name)
            method_dict[method] = count
        except ValueError:
            activity.logger.warning(f"Unknown verification method: {method_name}")
            continue
    
    # Convert user type
    try:
        user_type_enum = UserType(user_type.lower())
    except ValueError:
        activity.logger.error(f"Invalid user type: {user_type}")
        return 0
    
    # Calculate score using verification_types function
    score = calculate_trust_score(method_dict, user_type_enum)
    
    activity.logger.info(f"Calculated trust score: {score} points")
    return score


@activity.defn(name="award_verification_points")
async def award_verification_points(
    user_id: str,
    method: str,
    points: int,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Award points for completing a verification method and update level.
    
    This is the CORE activity for progressive trust accumulation.
    
    Args:
        user_id: UUID of user
        method: Verification method completed
        points: Points to award
        metadata: Additional data about the verification
        
    Returns:
        Dictionary with updated trust score and level
    """
    activity.logger.info(f"Awarding {points} points to user {user_id} for {method}")
    
    async with AsyncSessionLocal() as db:
        # Get or create user verification level record
        level_result = await db.execute(
            select(UserVerificationLevel).where(
                UserVerificationLevel.user_id == UUID(user_id)
            )
        )
        level_record = level_result.scalar_one_or_none()
        
        if not level_record:
            # Create new level record
            level_record = UserVerificationLevel(
                user_id=UUID(user_id),
                current_level=VerificationLevel.UNVERIFIED,
                completed_methods=[],
                in_progress_methods=[],
                total_methods_completed=0,
            )
            db.add(level_record)
            await db.flush()
        
        old_level = level_record.current_level
        
        # Add method to completed_methods if not already there
        completed_list = level_record.completed_methods or []
        if method not in completed_list:
            completed_list.append(method)
            level_record.completed_methods = completed_list
            level_record.total_methods_completed = len(completed_list)
        
        # Calculate new trust score
        # Build method count dict
        method_counts = {}
        for m in completed_list:
            method_counts[m] = method_counts.get(m, 0) + 1
        
        # Get user type
        user = await db.get(User, UUID(user_id))
        if not user:
            activity.logger.error(f"User {user_id} not found")
            return {"error": "User not found"}
        
        user_type = user.user_type
        
        # Calculate trust score
        method_enum_dict = {}
        for method_name, count in method_counts.items():
            try:
                method_enum = VerificationMethod(method_name)
                method_enum_dict[method_enum] = count
            except ValueError:
                continue
        
        trust_score = calculate_trust_score(method_enum_dict, user_type)
        
        # Calculate new level
        new_level = calc_level_from_score(trust_score)
        
        # Update level record
        level_record.current_level = new_level
        if new_level != old_level:
            level_record.level_achieved_at = datetime.now(timezone.utc)
        
        # Calculate progress to next level
        level_thresholds = {
            VerificationLevel.MINIMAL: 100,
            VerificationLevel.STANDARD: 250,
            VerificationLevel.ENHANCED: 400,
            VerificationLevel.COMPLETE: 600,
        }
        
        current_threshold = level_thresholds.get(new_level, 0)
        next_threshold = None
        for level in [VerificationLevel.MINIMAL, VerificationLevel.STANDARD, 
                      VerificationLevel.ENHANCED, VerificationLevel.COMPLETE]:
            if level_thresholds[level] > trust_score:
                next_threshold = level_thresholds[level]
                break
        
        if next_threshold:
            progress = ((trust_score - current_threshold) / 
                       (next_threshold - current_threshold)) * 100
            level_record.level_progress_percentage = min(100.0, max(0.0, progress))
        else:
            level_record.level_progress_percentage = 100.0
        
        await db.commit()
        
        # Record event (imported from events module)
        from nabr.temporal.activities.verification.events import record_verification_event
        await record_verification_event(
            user_id=user_id,
            event_type="points_awarded",
            method=method,
            data={
                "points": points,
                "method": method,
                "trust_score": trust_score,
                "old_level": old_level.value,
                "new_level": new_level.value,
                "metadata": metadata or {},
            },
        )
        
        # Send notification if level changed (imported from notifications module)
        if new_level != old_level:
            from nabr.temporal.activities.verification.notifications import send_level_change_notification
            await send_level_change_notification(
                user_id=user_id,
                old_level=old_level.value,
                new_level=new_level.value,
                score=trust_score,
            )
        
        activity.logger.info(
            f"Awarded {points} points. Trust score: {trust_score}, "
            f"Level: {old_level.value} → {new_level.value}"
        )
        
        return {
            "user_id": user_id,
            "points_awarded": points,
            "trust_score": trust_score,
            "old_level": old_level.value,
            "new_level": new_level.value,
            "level_changed": new_level != old_level,
            "progress_to_next": level_record.level_progress_percentage,
        }
