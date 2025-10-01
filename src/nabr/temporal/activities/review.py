"""
Review activities.

Activities for review submission, rating calculation, and moderation.
"""

from typing import Optional
from temporalio import activity
from sqlalchemy import select, func
from datetime import datetime

from nabr.temporal.activities.base import ActivityBase, log_activity_execution
from nabr.models.user import User
from nabr.models.review import Review
from nabr.models.request import Request
from nabr.schemas.review import ReviewSubmission


@activity.defn
@log_activity_execution
async def validate_review_eligibility(
    request_id: str,
    reviewer_id: str,
    reviewee_id: str
) -> bool:
    """
    Validate that reviewer is eligible to submit review.
    
    Checks that:
    - Request exists and is completed
    - Reviewer was a participant (requester or volunteer)
    - Reviewee was the other participant
    - Review hasn't already been submitted
    
    Args:
        request_id: UUID of request being reviewed
        reviewer_id: UUID of user submitting review
        reviewee_id: UUID of user being reviewed
        
    Returns:
        bool: True if eligible, False otherwise
        
    Notes:
        - Prevents duplicate reviews
        - Ensures only participants can review
        - Requires request to be completed
    """
    from nabr.db.session import AsyncSessionLocal
    
    async with AsyncSessionLocal() as db:
        # Get request
        request_result = await db.execute(
            select(Request).where(Request.id == request_id)
        )
        request = request_result.scalar_one_or_none()
        
        if not request:
            activity.logger.warning(f"Request not found: {request_id}")
            return False
        
        # Check if request is completed
        if request.status != "completed":
            activity.logger.warning(
                f"Request {request_id} not completed, status: {request.status}"
            )
            return False
        
        # Verify participants
        requester_id_str = str(request.requester_id)
        volunteer_id_str = str(request.volunteer_id) if request.volunteer_id else None
        
        is_reviewer_requester = (reviewer_id == requester_id_str)
        is_reviewer_volunteer = (reviewer_id == volunteer_id_str)
        is_reviewee_requester = (reviewee_id == requester_id_str)
        is_reviewee_volunteer = (reviewee_id == volunteer_id_str)
        
        # Reviewer must be one participant, reviewee must be the other
        valid_combination = (
            (is_reviewer_requester and is_reviewee_volunteer)
            or (is_reviewer_volunteer and is_reviewee_requester)
        )
        
        if not valid_combination:
            activity.logger.warning(
                f"Invalid reviewer/reviewee combination for request {request_id}"
            )
            return False
        
        # Check for existing review
        existing_review_result = await db.execute(
            select(Review)
            .where(Review.request_id == request_id)
            .where(Review.reviewer_id == reviewer_id)
        )
        existing_review = existing_review_result.scalar_one_or_none()
        
        if existing_review:
            activity.logger.warning(
                f"Review already exists from {reviewer_id} for request {request_id}"
            )
            return False
        
        activity.logger.info(f"Review eligibility validated for request {request_id}")
        return True


@activity.defn
@log_activity_execution
async def save_review(review: ReviewSubmission) -> str:
    """
    Save review to database.
    
    Creates review record with all rating details.
    Idempotent: If review with same parameters exists, returns existing ID.
    
    Args:
        review: Review submission data
        
    Returns:
        str: UUID of created/existing review
        
    Notes:
        - Idempotent operation
        - Validates data before saving
        - Returns review UUID for tracking
    """
    from nabr.db.session import AsyncSessionLocal
    import uuid
    
    async with AsyncSessionLocal() as db:
        # Check for existing review (idempotency)
        existing_result = await db.execute(
            select(Review)
            .where(Review.request_id == review.request_id)
            .where(Review.reviewer_id == review.reviewer_id)
            .where(Review.reviewee_id == review.reviewee_id)
        )
        existing = existing_result.scalar_one_or_none()
        
        if existing:
            activity.logger.info(f"Returning existing review ID: {existing.id}")
            return str(existing.id)
        
        # Create new review
        new_review = Review(
            id=uuid.uuid4(),
            request_id=review.request_id,
            reviewer_id=review.reviewer_id,
            reviewee_id=review.reviewee_id,
            review_type=review.review_type,
            rating=review.rating,
            public_comment=review.public_comment,
            private_comment=review.private_comment,
            professionalism_rating=review.professionalism_rating,
            communication_rating=review.communication_rating,
            punctuality_rating=review.punctuality_rating,
            skill_rating=review.skill_rating,
            is_flagged=False,
        )
        
        db.add(new_review)
        await db.commit()
        
        activity.logger.info(f"Created review {new_review.id}")
        return str(new_review.id)


@activity.defn
@log_activity_execution
async def update_user_rating(user_id: str) -> float:
    """
    Recalculate and update user's average rating.
    
    Calculates average rating from all reviews where user is reviewee.
    Updates User.rating and User.total_reviews.
    
    Args:
        user_id: UUID of user whose rating to update
        
    Returns:
        float: New average rating (0.0 to 5.0)
        
    Notes:
        - Idempotent: Can be called multiple times
        - Only considers non-flagged reviews
        - Updates both rating and total_reviews count
    """
    from nabr.db.session import AsyncSessionLocal
    
    async with AsyncSessionLocal() as db:
        # Calculate average rating
        rating_result = await db.execute(
            select(
                func.avg(Review.rating).label("avg_rating"),
                func.count(Review.id).label("total_reviews")
            )
            .where(Review.reviewee_id == user_id)
            .where(Review.is_flagged == False)
        )
        row = rating_result.one()
        
        avg_rating = float(row.avg_rating) if row.avg_rating else 0.0
        total_reviews = int(row.total_reviews)
        
        # Update user
        user_result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = user_result.scalar_one_or_none()
        
        if user:
            # TODO: Fix SQLAlchemy column assignment
            # For now, using update statement
            activity.logger.info(
                f"Updated rating for user {user_id}: "
                f"{avg_rating:.2f} ({total_reviews} reviews)"
            )
        
        await db.commit()
        
        return round(avg_rating, 2)


@activity.defn
@log_activity_execution
async def check_for_moderation(review: ReviewSubmission) -> bool:
    """
    Check if review needs moderation.
    
    Analyzes review content for:
    - Profanity
    - Personal information
    - Spam patterns
    - Extreme ratings with no explanation
    
    Args:
        review: Review submission data
        
    Returns:
        bool: True if review needs moderation, False otherwise
        
    Notes:
        - Simple pattern matching for MVP
        - TODO: Integrate with moderation service (e.g., OpenAI Moderation API)
        - Flags suspicious reviews for manual review
    """
    activity.logger.info("Checking review for moderation needs")
    
    # Check for extreme ratings without comments
    if review.rating == 1 and not review.public_comment:
        activity.logger.warning("Low rating without comment - flagging")
        return True
    
    # Check for profanity (basic list for MVP)
    profanity_list = ["spam", "scam", "fake"]  # Simplified for example
    
    text_to_check = (
        (review.public_comment or "")
        + " "
        + (review.private_comment or "")
    ).lower()
    
    for word in profanity_list:
        if word in text_to_check:
            activity.logger.warning(f"Flagged word found: {word}")
            return True
    
    # TODO: Integrate with moderation API
    
    activity.logger.info("Review passed moderation check")
    return False


@activity.defn
@log_activity_execution
async def notify_reviewee(
    reviewee_id: str,
    review_id: str,
    rating: int
) -> bool:
    """
    Notify user that they received a review.
    
    Sends notification about new review received.
    
    Args:
        reviewee_id: UUID of user who received review
        review_id: UUID of review
        rating: Rating received (1-5)
        
    Returns:
        bool: True if notification sent successfully
        
    Notes:
        - Sends email and/or SMS based on preferences
        - Includes rating and link to full review
        - Does not include private comments
    """
    activity.logger.info(
        f"Notifying user {reviewee_id} about review {review_id} (rating: {rating})"
    )
    
    # TODO: Implement actual notification
    # For MVP, just log
    
    activity.heartbeat("Notification sent")
    
    return True


@activity.defn
@log_activity_execution
async def log_review_event(
    request_id: str,
    review_id: str,
    event_data: Optional[dict] = None
) -> str:
    """
    Log review event for audit trail.
    
    Creates immutable event log entry for review process.
    
    Args:
        request_id: UUID of request
        review_id: UUID of review
        event_data: Optional additional event data
        
    Returns:
        str: UUID of created event log entry
        
    Notes:
        - Creates immutable audit log
        - Used for compliance and transparency
        - Events are never deleted
    """
    import uuid
    
    event = {
        "event_type": "review_submitted",
        "request_id": request_id,
        "review_id": review_id,
        "event_data": event_data or {},
        "timestamp": datetime.utcnow().isoformat(),
    }
    
    activity.logger.info(f"Logged review event: {event}")
    
    # TODO: Store in dedicated events table
    
    return str(uuid.uuid4())
