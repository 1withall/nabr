"""Phone verification workflow.

Simple child workflow that sends a verification code via SMS to the user's phone
and waits for confirmation. Awards 30 points on success.

This method is OPTIONAL - not required for any verification level.
"""

from datetime import timedelta, datetime
from typing import Dict, Optional, Any
import secrets

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ApplicationError

with workflow.unsafe.imports_passed_through():
    from nabr.models.verification_types import VerificationMethod, METHOD_SCORES


@workflow.defn
class PhoneVerificationWorkflow:
    """Child workflow for phone verification.
    
    Workflow:
    1. Generate verification code
    2. Send SMS with code
    3. Wait for user confirmation (signal)
    4. Validate code
    5. Award 30 points
    """
    
    def __init__(self) -> None:
        self.phone: Optional[str] = None
        self.verification_code: Optional[str] = None
        self.user_submitted_code: Optional[str] = None
        self.attempts: int = 0
        self.max_attempts: int = 3
    
    @workflow.run
    async def run(
        self,
        user_id: str,
        phone: str,
        timeout_hours: int = 24
    ) -> Dict[str, Any]:
        """Execute phone verification.
        
        Args:
            user_id: User being verified
            phone: Phone number to verify (E.164 format)
            timeout_hours: Hours to wait for confirmation (default 24)
        
        Returns:
            Dict with points_awarded, phone, verified_at
        """
        self.phone = phone
        
        workflow.logger.info(
            f"Starting phone verification for {phone}",
            extra={"user_id": user_id, "phone": phone}
        )
        
        retry_policy = RetryPolicy(
            maximum_attempts=3,
            initial_interval=timedelta(seconds=1),
            maximum_interval=timedelta(seconds=10),
        )
        
        # Step 1: Generate verification code (6 digits)
        self.verification_code = "".join([str(secrets.randbelow(10)) for _ in range(6)])
        
        workflow.logger.info(
            f"Generated verification code",
            extra={"user_id": user_id, "phone": phone}
        )
        
        # Step 2: Send SMS
        await workflow.execute_activity(
            "send_verification_sms",
            args=[user_id, phone, self.verification_code],
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=retry_policy,
        )
        
        workflow.logger.info(
            f"Sent verification SMS",
            extra={"user_id": user_id, "phone": phone}
        )
        
        # Step 3: Wait for user confirmation (with timeout)
        timeout = timedelta(hours=timeout_hours)
        
        try:
            await workflow.wait_condition(
                lambda: self.user_submitted_code is not None,
                timeout=timeout
            )
        except TimeoutError:
            workflow.logger.warning(
                f"Phone verification timed out",
                extra={"user_id": user_id, "phone": phone}
            )
            raise ApplicationError(
                f"Phone verification timed out - no code submitted within {timeout_hours} hours",
                non_retryable=True
            )
        
        # Step 4: Validate code
        if self.user_submitted_code != self.verification_code:
            workflow.logger.warning(
                f"Invalid verification code",
                extra={"user_id": user_id, "phone": phone, "attempts": self.attempts}
            )
            raise ApplicationError(
                "Invalid verification code",
                non_retryable=True
            )
        
        # Step 5: Award points
        score_info = METHOD_SCORES[VerificationMethod.PHONE]
        points_awarded = score_info.points
        
        workflow.logger.info(
            f"Phone verification completed successfully",
            extra={
                "user_id": user_id,
                "phone": phone,
                "points_awarded": points_awarded
            }
        )
        
        return {
            "completed": True,
            "points_awarded": points_awarded,
            "phone": phone,
            "verified_at": datetime.now().isoformat(),
        }
    
    @workflow.signal
    async def submit_code(self, code: str) -> None:
        """Signal when user submits verification code.
        
        Args:
            code: 6-digit verification code
        """
        self.attempts += 1
        self.user_submitted_code = code
        
        workflow.logger.info(
            f"User submitted verification code (attempt {self.attempts})",
            extra={"phone": self.phone, "attempts": self.attempts}
        )
    
    @workflow.query
    def get_status(self) -> Dict[str, Any]:
        """Get current verification status."""
        return {
            "phone": self.phone,
            "code_sent": self.verification_code is not None,
            "code_submitted": self.user_submitted_code is not None,
            "attempts": self.attempts,
            "max_attempts": self.max_attempts,
        }
