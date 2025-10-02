"""
Request matching workflow for connecting requests with appropriate acceptors.

This workflow implements an algorithm-based matching system that considers:
- User type capabilities (individual, business, organization)
- Skills and requirements
- Geographic proximity
- Availability
- User ratings and history

Task Queue: matching-queue
"""

from datetime import timedelta
from typing import List, Optional
from uuid import UUID

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from nabr.schemas.request import RequestMatchingInput, MatchingResult
    from nabr.temporal.activities.matching import MatchingActivities

# Task queue for matching workflows
MATCHING_TASK_QUEUE = "matching-queue"


@workflow.defn(name="RequestMatchingWorkflow")
class RequestMatchingWorkflow:
    """
    Request matching workflow.
    
    Workflow steps:
    1. Validate request and requester
    2. Calculate matching scores for potential acceptors
    3. Rank and filter candidates
    4. Notify top candidates
    5. Wait for acceptance (with timeout and fallback)
    6. Assign request to acceptor
    7. Send notifications
    
    The workflow ensures fairness and prevents exploitation by:
    - Not showing all requests publicly
    - Using algorithm-based matching only
    - Considering user ratings and history
    - Enforcing reasonable time limits
    """
    
    def __init__(self) -> None:
        self._status = "pending"
        self._matched_acceptor_id: Optional[UUID] = None
        self._notified_candidates: List[UUID] = []
    
    @workflow.run
    async def run(self, request: RequestMatchingInput) -> MatchingResult:
        """
        Execute the request matching workflow.
        
        Args:
            request: Request matching input with request_id and preferences
            
        Returns:
            MatchingResult: Matching outcome with acceptor_id if successful
        """
        retry_policy = RetryPolicy(
            maximum_attempts=3,
            initial_interval=timedelta(seconds=1),
            maximum_interval=timedelta(seconds=10),
        )
        
        workflow.logger.info(f"Starting matching for request {request.request_id}")
        
        # Step 1: Validate request
        self._status = "validating"
        
        is_valid = await workflow.execute_activity(
            MatchingActivities.validate_request,
            request.request_id,
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=retry_policy,
        )
        
        if not is_valid:
            workflow.logger.warning(f"Request {request.request_id} is invalid")
            return MatchingResult(
                request_id=request.request_id,
                status="failed",
                reason="Request validation failed",
            )
        
        # Step 2: Find potential acceptors
        self._status = "finding_candidates"
        
        candidates = await workflow.execute_activity(
            MatchingActivities.find_potential_acceptors,
            request,
            start_to_close_timeout=timedelta(seconds=60),
            retry_policy=retry_policy,
        )
        
        if not candidates:
            workflow.logger.info(f"No candidates found for request {request.request_id}")
            return MatchingResult(
                request_id=request.request_id,
                status="no_match",
                reason="No suitable acceptors found",
            )
        
        workflow.logger.info(f"Found {len(candidates)} candidates")
        
        # Step 3: Calculate matching scores
        self._status = "calculating_scores"
        
        scored_candidates = await workflow.execute_activity(
            MatchingActivities.calculate_matching_scores,
            args=[request, candidates],
            start_to_close_timeout=timedelta(seconds=60),
            retry_policy=retry_policy,
        )
        
        # Step 4: Notify top candidates (batch of 3-5 at a time)
        self._status = "notifying_candidates"
        
        top_candidates = scored_candidates[:5]  # Top 5 candidates
        self._notified_candidates = [c.user_id for c in top_candidates]
        
        await workflow.execute_activity(
            MatchingActivities.notify_candidates,
            args=[request.request_id, top_candidates],
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=retry_policy,
        )
        
        # Step 5: Wait for acceptance (24 hours timeout)
        self._status = "awaiting_acceptance"
        
        try:
            await workflow.wait_condition(
                lambda: self._matched_acceptor_id is not None,
                timeout=timedelta(hours=24),
            )
            
            workflow.logger.info(
                f"Request {request.request_id} accepted by {self._matched_acceptor_id}"
            )
            
            # Step 6: Assign request
            self._status = "assigning"
            
            await workflow.execute_activity(
                MatchingActivities.assign_request,
                args=[request.request_id, self._matched_acceptor_id],
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=retry_policy,
            )
            
            # Step 7: Send confirmation notifications
            await workflow.execute_activity(
                MatchingActivities.send_match_notifications,
                args=[request.request_id, self._matched_acceptor_id],
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=retry_policy,
            )
            
            self._status = "matched"
            
            return MatchingResult(
                request_id=request.request_id,
                acceptor_id=self._matched_acceptor_id,
                status="matched",
                matching_score=next(
                    (c.score for c in scored_candidates if c.user_id == self._matched_acceptor_id),
                    0.0,
                ),
            )
            
        except TimeoutError:
            # No one accepted in time - try next batch or mark as unmatched
            workflow.logger.warning(f"Request {request.request_id} matching timeout")
            
            self._status = "timeout"
            
            # Could extend this to try another batch of candidates
            # For now, mark as unmatched
            
            await workflow.execute_activity(
                MatchingActivities.mark_request_unmatched,
                request.request_id,
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=retry_policy,
            )
            
            return MatchingResult(
                request_id=request.request_id,
                status="timeout",
                reason="No acceptors responded within timeout period",
            )
    
    @workflow.signal
    async def request_accepted(self, acceptor_id: UUID) -> None:
        """
        Signal handler for request acceptance.
        
        Args:
            acceptor_id: UUID of the user accepting the request
        """
        if acceptor_id in self._notified_candidates and self._matched_acceptor_id is None:
            self._matched_acceptor_id = acceptor_id
            workflow.logger.info(f"Request accepted by {acceptor_id}")
        else:
            workflow.logger.warning(
                f"Invalid acceptance attempt by {acceptor_id} "
                f"(not in candidates or already matched)"
            )
    
    @workflow.query
    def get_status(self) -> dict:
        """
        Query handler for matching status.
        
        Returns:
            dict: Current status and matching progress
        """
        return {
            "status": self._status,
            "notified_count": len(self._notified_candidates),
            "matched": self._matched_acceptor_id is not None,
            "acceptor_id": str(self._matched_acceptor_id) if self._matched_acceptor_id else None,
        }
