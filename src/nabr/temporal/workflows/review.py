"""
Review workflow for event-linked feedback submission.

This workflow ensures reviews are properly validated, moderated if needed,
and only submitted for completed, verified events.

Task Queue: review-queue
"""

from datetime import timedelta
from typing import Optional

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from nabr.schemas.review import ReviewSubmission, ReviewResult
    from nabr.temporal.activities.review import ReviewActivities

# Task queue for review workflows
REVIEW_TASK_QUEUE = "review-queue"


@workflow.defn(name="ReviewWorkflow")
class ReviewWorkflow:
    """
    Review submission workflow.
    
    Workflow steps:
    1. Validate request is completed
    2. Verify reviewer is a participant
    3. Check for duplicate reviews
    4. Moderate review content (if flagged)
    5. Save review to database
    6. Update user ratings
    7. Send notifications
    
    Safeguards:
    - Only participants can review
    - One review per user per request
    - Content moderation for inappropriate content
    - Immutable once submitted
    """
    
    def __init__(self) -> None:
        self._status = "pending"
        self._moderation_required = False
        self._moderation_result: Optional[str] = None
    
    @workflow.run
    async def run(self, submission: ReviewSubmission) -> ReviewResult:
        """
        Execute the review submission workflow.
        
        Args:
            submission: Review submission with request_id, reviewer_id, rating, comment
            
        Returns:
            ReviewResult: Review submission outcome
        """
        retry_policy = RetryPolicy(
            maximum_attempts=3,
            initial_interval=timedelta(seconds=1),
            maximum_interval=timedelta(seconds=10),
        )
        
        workflow.logger.info(
            f"Processing review for request {submission.request_id} "
            f"by user {submission.reviewer_id}"
        )
        
        # Step 1: Validate request is completed
        self._status = "validating_request"
        
        request_valid = await workflow.execute_activity(
            ReviewActivities.validate_request_completed,
            submission.request_id,
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=retry_policy,
        )
        
        if not request_valid:
            workflow.logger.warning(f"Request {submission.request_id} not completed")
            return ReviewResult(
                review_id=None,
                success=False,
                error="Request is not completed or does not exist",
            )
        
        # Step 2: Verify reviewer is a participant
        self._status = "verifying_participant"
        
        is_participant = await workflow.execute_activity(
            ReviewActivities.verify_participant,
            args=[submission.request_id, submission.reviewer_id],
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=retry_policy,
        )
        
        if not is_participant:
            workflow.logger.warning(
                f"User {submission.reviewer_id} is not a participant in request {submission.request_id}"
            )
            return ReviewResult(
                review_id=None,
                success=False,
                error="Only participants can submit reviews",
            )
        
        # Step 3: Check for duplicate reviews
        self._status = "checking_duplicates"
        
        has_reviewed = await workflow.execute_activity(
            ReviewActivities.check_existing_review,
            args=[submission.request_id, submission.reviewer_id],
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=retry_policy,
        )
        
        if has_reviewed:
            workflow.logger.warning(
                f"User {submission.reviewer_id} already reviewed request {submission.request_id}"
            )
            return ReviewResult(
                review_id=None,
                success=False,
                error="You have already submitted a review for this request",
            )
        
        # Step 4: Moderate content if needed
        if submission.comment:
            self._status = "moderating"
            
            moderation_result = await workflow.execute_activity(
                ReviewActivities.moderate_content,
                submission.comment,
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=retry_policy,
            )
            
            if moderation_result.get("flagged", False):
                self._moderation_required = True
                self._moderation_result = moderation_result.get("reason")
                workflow.logger.warning(
                    f"Review content flagged: {self._moderation_result}"
                )
                
                # For now, reject flagged content
                # Could extend this to allow manual moderation
                return ReviewResult(
                    review_id=None,
                    success=False,
                    error=f"Review content was flagged: {self._moderation_result}",
                )
        
        # Step 5: Create review record
        self._status = "creating_review"
        
        review_id = await workflow.execute_activity(
            ReviewActivities.create_review,
            submission,
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=retry_policy,
        )
        
        workflow.logger.info(f"Created review {review_id}")
        
        # Step 6: Update user ratings
        self._status = "updating_ratings"
        
        await workflow.execute_activity(
            ReviewActivities.update_user_rating,
            args=[submission.reviewee_id, submission.rating],
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=retry_policy,
        )
        
        # Step 7: Send notifications
        self._status = "sending_notifications"
        
        await workflow.execute_activity(
            ReviewActivities.send_review_notification,
            args=[submission.reviewee_id, review_id],
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=retry_policy,
        )
        
        self._status = "completed"
        workflow.logger.info(f"Review workflow completed for review {review_id}")
        
        return ReviewResult(
            review_id=review_id,
            success=True,
        )
    
    @workflow.query
    def get_status(self) -> dict:
        """
        Query handler for review workflow status.
        
        Returns:
            dict: Current status and moderation info
        """
        return {
            "status": self._status,
            "moderation_required": self._moderation_required,
            "moderation_result": self._moderation_result,
        }
