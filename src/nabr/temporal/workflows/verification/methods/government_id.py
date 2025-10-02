"""Government ID verification workflow.

Child workflow for document-based identity verification. Requires human review.
Awards 100 points on success.

This method is OPTIONAL - not required for verification (two-party is sufficient).
"""

from datetime import timedelta, datetime
from typing import Dict, Optional, Any

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ApplicationError

with workflow.unsafe.imports_passed_through():
    from nabr.models.verification_types import VerificationMethod, METHOD_SCORES


@workflow.defn
class GovernmentIDWorkflow:
    """Child workflow for government ID verification with human review.
    
    Workflow:
    1. User uploads ID document
    2. Store document securely
    3. Queue for human review
    4. Wait for reviewer decision (signal)
    5. Award 100 points if approved
    """
    
    def __init__(self) -> None:
        self.document_url: Optional[str] = None
        self.document_type: Optional[str] = None
        self.reviewer_id: Optional[str] = None
        self.review_decision: Optional[str] = None  # "approved" or "rejected"
        self.review_notes: Optional[str] = None
    
    @workflow.run
    async def run(
        self,
        user_id: str,
        document_url: str,
        document_type: str,
        timeout_hours: int = 168  # 7 days
    ) -> Dict[str, Any]:
        """Execute government ID verification.
        
        Args:
            user_id: User being verified
            document_url: URL to uploaded ID document
            document_type: Type of ID (passport, drivers_license, national_id, etc.)
            timeout_hours: Hours to wait for review (default 168 = 7 days)
        
        Returns:
            Dict with points_awarded, document_type, reviewed_at
        """
        self.document_url = document_url
        self.document_type = document_type
        
        workflow.logger.info(
            f"Starting government ID verification",
            extra={
                "user_id": user_id,
                "document_type": document_type,
                "document_url": document_url[:50] + "..."
            }
        )
        
        retry_policy = RetryPolicy(
            maximum_attempts=3,
            initial_interval=timedelta(seconds=1),
            maximum_interval=timedelta(seconds=10),
        )
        
        # Step 1: Validate document upload
        validation_result = await workflow.execute_activity(
            "validate_id_document",
            args=[document_url, document_type],
            start_to_close_timeout=timedelta(seconds=60),
            retry_policy=retry_policy,
        )
        
        if not validation_result["valid"]:
            workflow.logger.error(
                f"ID document validation failed",
                extra={
                    "user_id": user_id,
                    "reason": validation_result.get("reason")
                }
            )
            raise ApplicationError(
                f"ID document validation failed: {validation_result.get('reason')}",
                non_retryable=True
            )
        
        workflow.logger.info(
            f"ID document validated",
            extra={"user_id": user_id, "document_type": document_type}
        )
        
        # Step 2: Queue for human review
        await workflow.execute_activity(
            "queue_for_human_review",
            args=[
                user_id,
                VerificationMethod.GOVERNMENT_ID.value,
                {
                    "document_url": document_url,
                    "document_type": document_type,
                    "uploaded_at": datetime.now().isoformat(),
                }
            ],
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=retry_policy,
        )
        
        workflow.logger.info(
            f"Queued ID for human review",
            extra={"user_id": user_id, "document_type": document_type}
        )
        
        # Step 3: Wait for reviewer decision (with timeout)
        timeout = timedelta(hours=timeout_hours)
        
        try:
            await workflow.wait_condition(
                lambda: self.review_decision is not None,
                timeout=timeout
            )
        except TimeoutError:
            workflow.logger.warning(
                f"ID verification timed out - no review within {timeout_hours} hours",
                extra={"user_id": user_id, "document_type": document_type}
            )
            raise ApplicationError(
                f"ID verification timed out - no review completed within {timeout_hours} hours",
                non_retryable=True
            )
        
        # Step 4: Check reviewer decision
        if self.review_decision != "approved":
            workflow.logger.info(
                f"ID verification rejected by reviewer",
                extra={
                    "user_id": user_id,
                    "reviewer_id": self.reviewer_id,
                    "reason": self.review_notes
                }
            )
            raise ApplicationError(
                f"ID verification rejected: {self.review_notes}",
                non_retryable=True
            )
        
        # Step 5: Award points
        score_info = METHOD_SCORES[VerificationMethod.GOVERNMENT_ID]
        points_awarded = score_info.points
        
        workflow.logger.info(
            f"Government ID verification completed successfully",
            extra={
                "user_id": user_id,
                "document_type": document_type,
                "reviewer_id": self.reviewer_id,
                "points_awarded": points_awarded
            }
        )
        
        return {
            "completed": True,
            "points_awarded": points_awarded,
            "document_type": document_type,
            "reviewer_id": self.reviewer_id,
            "verified_at": datetime.now().isoformat(),
        }
    
    @workflow.signal
    async def reviewer_decision(
        self,
        reviewer_id: str,
        decision: str,
        notes: Optional[str] = None
    ) -> None:
        """Signal when reviewer makes a decision.
        
        Args:
            reviewer_id: ID of the reviewer
            decision: "approved" or "rejected"
            notes: Optional reviewer notes/reason
        """
        self.reviewer_id = reviewer_id
        self.review_decision = decision
        self.review_notes = notes
        
        workflow.logger.info(
            f"Reviewer decision received: {decision}",
            extra={
                "reviewer_id": reviewer_id,
                "decision": decision,
                "document_type": self.document_type
            }
        )
    
    @workflow.query
    def get_status(self) -> Dict[str, Any]:
        """Get current verification status."""
        return {
            "document_type": self.document_type,
            "document_uploaded": self.document_url is not None,
            "in_review": self.review_decision is None,
            "decision": self.review_decision,
            "reviewer_id": self.reviewer_id,
        }
