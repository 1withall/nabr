"""
Verification workflow for two-party user verification.

This workflow orchestrates the process of verifying a user's identity
through two independent verifiers who confirm identity in person.

Task Queue: verification-queue
"""

from datetime import timedelta
from typing import Optional
from uuid import UUID

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from nabr.schemas.verification import (
        VerificationRequest,
        VerificationResult,
        VerifierConfirmation,
    )
    from nabr.temporal.activities.verification import VerificationActivities

# Task queue for verification workflows
VERIFICATION_TASK_QUEUE = "verification-queue"


@workflow.defn(name="VerificationWorkflow")
class VerificationWorkflow:
    """
    Two-party verification workflow.
    
    Workflow steps:
    1. Create verification record
    2. Generate QR codes for verifiers
    3. Wait for first verifier confirmation
    4. Wait for second verifier confirmation
    5. Validate both confirmations
    6. Update user verification status
    7. Send confirmation notifications
    
    Signals:
    - verifier_confirmed: Signal when a verifier confirms identity
    
    Queries:
    - get_status: Get current verification status
    """
    
    def __init__(self) -> None:
        self._status = "pending"
        self._verifier1_confirmed = False
        self._verifier2_confirmed = False
        self._verifier1_id: Optional[UUID] = None
        self._verifier2_id: Optional[UUID] = None
    
    @workflow.run
    async def run(self, request: VerificationRequest) -> VerificationResult:
        """
        Execute the verification workflow.
        
        Args:
            request: Verification request with user_id and verification details
            
        Returns:
            VerificationResult: Final verification outcome
        """
        # Activity retry policy
        retry_policy = RetryPolicy(
            maximum_attempts=3,
            initial_interval=timedelta(seconds=1),
            maximum_interval=timedelta(seconds=10),
        )
        
        # Step 1: Create verification record in database
        verification_id = await workflow.execute_activity(
            VerificationActivities.create_verification_record,
            request,
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=retry_policy,
        )
        
        workflow.logger.info(f"Created verification record: {verification_id}")
        
        # Step 2: Generate QR codes for verifiers
        qr_codes = await workflow.execute_activity(
            VerificationActivities.generate_qr_codes,
            verification_id,
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=retry_policy,
        )
        
        workflow.logger.info("Generated QR codes for verification")
        
        # Step 3: Wait for verifier confirmations (with timeout)
        self._status = "awaiting_verifiers"
        
        try:
            # Wait for both verifiers (7 days timeout)
            await workflow.wait_condition(
                lambda: self._verifier1_confirmed and self._verifier2_confirmed,
                timeout=timedelta(days=7),
            )
            
            workflow.logger.info("Both verifiers confirmed")
            
            # Step 4: Validate confirmations
            self._status = "validating"
            
            is_valid = await workflow.execute_activity(
                VerificationActivities.validate_verifications,
                args=[verification_id, self._verifier1_id, self._verifier2_id],
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=retry_policy,
            )
            
            if not is_valid:
                self._status = "rejected"
                workflow.logger.warning("Verification validation failed")
                
                return VerificationResult(
                    verification_id=verification_id,
                    user_id=request.user_id,
                    status="rejected",
                    verified=False,
                    rejection_reason="Verification validation failed",
                )
            
            # Step 5: Update user verification status
            self._status = "approved"
            
            await workflow.execute_activity(
                VerificationActivities.approve_verification,
                verification_id,
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=retry_policy,
            )
            
            # Step 6: Send confirmation notifications
            await workflow.execute_activity(
                VerificationActivities.send_verification_notification,
                args=[request.user_id, "approved"],
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=retry_policy,
            )
            
            workflow.logger.info(f"Verification approved for user {request.user_id}")
            
            return VerificationResult(
                verification_id=verification_id,
                user_id=request.user_id,
                status="verified",
                verified=True,
                qr_codes=qr_codes,
            )
            
        except TimeoutError:
            # Verification expired - no verifiers responded in time
            self._status = "expired"
            workflow.logger.warning(f"Verification expired for user {request.user_id}")
            
            await workflow.execute_activity(
                VerificationActivities.expire_verification,
                verification_id,
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=retry_policy,
            )
            
            return VerificationResult(
                verification_id=verification_id,
                user_id=request.user_id,
                status="expired",
                verified=False,
                rejection_reason="Verification expired - no verifiers responded",
            )
    
    @workflow.signal
    async def verifier_confirmed(self, confirmation: VerifierConfirmation) -> None:
        """
        Signal handler for verifier confirmation.
        
        Args:
            confirmation: Verifier confirmation with verifier_id and details
        """
        if not self._verifier1_confirmed:
            self._verifier1_id = confirmation.verifier_id
            self._verifier1_confirmed = True
            workflow.logger.info(f"First verifier confirmed: {confirmation.verifier_id}")
        elif not self._verifier2_confirmed and confirmation.verifier_id != self._verifier1_id:
            # Ensure second verifier is different from first
            self._verifier2_id = confirmation.verifier_id
            self._verifier2_confirmed = True
            workflow.logger.info(f"Second verifier confirmed: {confirmation.verifier_id}")
        else:
            workflow.logger.warning(
                f"Duplicate verifier attempt: {confirmation.verifier_id}"
            )
    
    @workflow.query
    def get_status(self) -> dict:
        """
        Query handler for verification status.
        
        Returns:
            dict: Current status, verifier confirmation states
        """
        return {
            "status": self._status,
            "verifier1_confirmed": self._verifier1_confirmed,
            "verifier2_confirmed": self._verifier2_confirmed,
        }
