"""Two-party in-person verification workflow.

This is the CORE INCLUSIVE verification method that allows people WITHOUT
email, phone, ID, or home address to still verify their identity.

Two trusted community members confirm identity in person by scanning QR codes.
This workflow uses the Saga pattern for compensation if verification is revoked.

Workflow steps (Saga):
1. Generate QR codes for 2 verifiers
2. Wait for both verifier confirmations (signal)
3. Validate verifiers are authorized
4. Record confirmations in database
5. Award 150 points

Compensation (if revoked):
- Invalidate QR codes
- Revoke verifier confirmations
- Notify verifiers
"""

from datetime import timedelta, datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ApplicationError

with workflow.unsafe.imports_passed_through():
    from nabr.models.verification_types import VerificationMethod, METHOD_SCORES


@dataclass
class VerifierConfirmation:
    """Record of a verifier confirmation."""
    verifier_id: str
    confirmed_at: datetime
    location_lat: Optional[float] = None
    location_lon: Optional[float] = None
    device_fingerprint: Optional[str] = None


@dataclass
class TwoPartyState:
    """State for two-party verification saga."""
    user_id: str
    qr_code_1: Optional[str] = None
    qr_code_2: Optional[str] = None
    verifier_1: Optional[VerifierConfirmation] = None
    verifier_2: Optional[VerifierConfirmation] = None
    saga_step: int = 0
    completed: bool = False
    points_awarded: int = 0


@workflow.defn
class TwoPartyInPersonWorkflow:
    """Child workflow for two-party in-person verification using Saga pattern.
    
    This workflow:
    1. Generates QR codes for 2 verifiers
    2. Waits for both confirmations via signals
    3. Validates verifier authorization
    4. Records confirmations
    5. Awards 150 points
    
    Uses Saga pattern for automatic compensation if revoked.
    """
    
    def __init__(self) -> None:
        self.state: Optional[TwoPartyState] = None
    
    @workflow.run
    async def run(
        self,
        user_id: str,
        timeout_hours: int = 72,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute the two-party verification saga.
        
        Args:
            user_id: User being verified
            timeout_hours: Hours to wait for confirmations (default 72)
            metadata: Additional verification metadata
        
        Returns:
            Dict with points_awarded, verifier_ids, completed status
        """
        self.state = TwoPartyState(user_id=user_id)
        metadata = metadata or {}
        
        workflow.logger.info(
            f"Starting two-party verification for user {user_id}",
            extra={"user_id": user_id, "timeout_hours": timeout_hours}
        )
        
        retry_policy = RetryPolicy(
            maximum_attempts=3,
            initial_interval=timedelta(seconds=1),
            maximum_interval=timedelta(seconds=10),
        )
        
        try:
            # SAGA STEP 1: Generate QR codes
            self.state.saga_step = 1
            qr_codes = await workflow.execute_activity(
                "generate_verification_qr_codes",
                args=[user_id, 2],  # Generate 2 QR codes
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=retry_policy,
            )
            
            self.state.qr_code_1 = qr_codes["qr_code_1"]
            self.state.qr_code_2 = qr_codes["qr_code_2"]
            
            workflow.logger.info(
                f"Generated QR codes for two-party verification",
                extra={"user_id": user_id, "qr_codes": list(qr_codes.keys())}
            )
            
            # SAGA STEP 2: Wait for verifier confirmations (with timeout)
            self.state.saga_step = 2
            timeout = timedelta(hours=timeout_hours)
            
            try:
                # Wait for both verifiers to confirm
                await workflow.wait_condition(
                    lambda: self.state.verifier_1 is not None and self.state.verifier_2 is not None,
                    timeout=timeout
                )
            except TimeoutError:
                workflow.logger.warning(
                    f"Two-party verification timed out after {timeout_hours} hours",
                    extra={"user_id": user_id}
                )
                # Compensate: Invalidate QR codes
                await self._compensate_qr_codes()
                raise ApplicationError(
                    f"Verification timed out - no confirmations received within {timeout_hours} hours",
                    non_retryable=True
                )
            
            workflow.logger.info(
                f"Received both verifier confirmations",
                extra={
                    "user_id": user_id,
                    "verifier_1": self.state.verifier_1.verifier_id if self.state.verifier_1 else None,
                    "verifier_2": self.state.verifier_2.verifier_id if self.state.verifier_2 else None,
                }
            )
            
            # SAGA STEP 3: Validate verifiers are authorized
            self.state.saga_step = 3
            verifier_ids = [
                self.state.verifier_1.verifier_id,
                self.state.verifier_2.verifier_id
            ]
            
            validation_result = await workflow.execute_activity(
                "validate_verifier_credentials",
                args=[verifier_ids, VerificationMethod.IN_PERSON_TWO_PARTY.value],
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=retry_policy,
            )
            
            if not validation_result["all_valid"]:
                workflow.logger.error(
                    f"Verifier validation failed",
                    extra={
                        "user_id": user_id,
                        "invalid_verifiers": validation_result.get("invalid_verifiers", [])
                    }
                )
                # Compensate: Invalidate QR codes and confirmations
                await self._compensate_qr_codes()
                await self._compensate_confirmations()
                raise ApplicationError(
                    f"One or more verifiers not authorized: {validation_result.get('invalid_verifiers')}",
                    non_retryable=True
                )
            
            workflow.logger.info(
                f"Verifiers validated successfully",
                extra={"user_id": user_id, "verifier_ids": verifier_ids}
            )
            
            # SAGA STEP 4: Record verifier confirmations in database
            self.state.saga_step = 4
            await workflow.execute_activity(
                "record_verifier_confirmations",
                args=[
                    user_id,
                    [
                        {
                            "verifier_id": self.state.verifier_1.verifier_id,
                            "confirmed_at": self.state.verifier_1.confirmed_at.isoformat(),
                            "location_lat": self.state.verifier_1.location_lat,
                            "location_lon": self.state.verifier_1.location_lon,
                        },
                        {
                            "verifier_id": self.state.verifier_2.verifier_id,
                            "confirmed_at": self.state.verifier_2.confirmed_at.isoformat(),
                            "location_lat": self.state.verifier_2.location_lat,
                            "location_lon": self.state.verifier_2.location_lon,
                        }
                    ],
                    VerificationMethod.IN_PERSON_TWO_PARTY.value
                ],
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=retry_policy,
            )
            
            workflow.logger.info(
                f"Recorded verifier confirmations",
                extra={"user_id": user_id}
            )
            
            # SAGA STEP 5: Award points
            self.state.saga_step = 5
            score_info = METHOD_SCORES[VerificationMethod.IN_PERSON_TWO_PARTY]
            self.state.points_awarded = score_info.points
            self.state.completed = True
            
            workflow.logger.info(
                f"Two-party verification completed successfully",
                extra={
                    "user_id": user_id,
                    "points_awarded": self.state.points_awarded,
                    "verifier_ids": verifier_ids,
                }
            )
            
            return {
                "completed": True,
                "points_awarded": self.state.points_awarded,
                "verifier_1_id": self.state.verifier_1.verifier_id,
                "verifier_2_id": self.state.verifier_2.verifier_id,
                "confirmed_at": datetime.now().isoformat(),
            }
            
        except Exception as e:
            workflow.logger.error(
                f"Two-party verification failed at step {self.state.saga_step}",
                extra={
                    "user_id": user_id,
                    "saga_step": self.state.saga_step,
                    "error": str(e)
                }
            )
            # Compensate based on saga step
            await self._compensate_saga()
            raise
    
    @workflow.signal
    async def verifier_confirmation(
        self,
        verifier_id: str,
        qr_code: str,
        location_lat: Optional[float] = None,
        location_lon: Optional[float] = None,
        device_fingerprint: Optional[str] = None
    ) -> None:
        """Signal when a verifier confirms identity.
        
        Args:
            verifier_id: ID of the verifier
            qr_code: QR code that was scanned
            location_lat: Latitude of confirmation
            location_lon: Longitude of confirmation
            device_fingerprint: Device identifier for fraud detection
        """
        if not self.state:
            workflow.logger.error("Workflow state not initialized")
            return
        
        confirmation = VerifierConfirmation(
            verifier_id=verifier_id,
            confirmed_at=workflow.now(),
            location_lat=location_lat,
            location_lon=location_lon,
            device_fingerprint=device_fingerprint,
        )
        
        # Assign to first available verifier slot
        if qr_code == self.state.qr_code_1 and self.state.verifier_1 is None:
            self.state.verifier_1 = confirmation
            workflow.logger.info(
                f"Verifier 1 confirmed",
                extra={"user_id": self.state.user_id, "verifier_id": verifier_id}
            )
        elif qr_code == self.state.qr_code_2 and self.state.verifier_2 is None:
            self.state.verifier_2 = confirmation
            workflow.logger.info(
                f"Verifier 2 confirmed",
                extra={"user_id": self.state.user_id, "verifier_id": verifier_id}
            )
        else:
            workflow.logger.warning(
                f"Invalid QR code or slot already filled",
                extra={
                    "user_id": self.state.user_id,
                    "verifier_id": verifier_id,
                    "qr_code": qr_code[:10] + "..."
                }
            )
    
    @workflow.query
    def get_status(self) -> Dict[str, Any]:
        """Get current verification status."""
        if not self.state:
            return {"status": "not_started"}
        
        return {
            "saga_step": self.state.saga_step,
            "qr_code_1_generated": self.state.qr_code_1 is not None,
            "qr_code_2_generated": self.state.qr_code_2 is not None,
            "verifier_1_confirmed": self.state.verifier_1 is not None,
            "verifier_2_confirmed": self.state.verifier_2 is not None,
            "completed": self.state.completed,
            "points_awarded": self.state.points_awarded,
        }
    
    async def _compensate_saga(self) -> None:
        """Compensate saga based on which step failed."""
        if not self.state:
            return
        
        if self.state.saga_step >= 2:
            await self._compensate_qr_codes()
        
        if self.state.saga_step >= 4:
            await self._compensate_confirmations()
    
    async def _compensate_qr_codes(self) -> None:
        """Compensation: Invalidate generated QR codes."""
        if not self.state:
            return
        
        if self.state.qr_code_1 or self.state.qr_code_2:
            workflow.logger.info(
                f"Compensating: Invalidating QR codes",
                extra={"user_id": self.state.user_id}
            )
            
            try:
                await workflow.execute_activity(
                    "invalidate_qr_codes",
                    args=[[self.state.qr_code_1, self.state.qr_code_2]],
                    start_to_close_timeout=timedelta(seconds=30),
                )
            except Exception as e:
                workflow.logger.error(
                    f"Failed to invalidate QR codes",
                    extra={"user_id": self.state.user_id, "error": str(e)}
                )
    
    async def _compensate_confirmations(self) -> None:
        """Compensation: Revoke verifier confirmations."""
        if not self.state:
            return
        
        if self.state.verifier_1 or self.state.verifier_2:
            workflow.logger.info(
                f"Compensating: Revoking verifier confirmations",
                extra={"user_id": self.state.user_id}
            )
            
            verifier_ids = []
            if self.state.verifier_1:
                verifier_ids.append(self.state.verifier_1.verifier_id)
            if self.state.verifier_2:
                verifier_ids.append(self.state.verifier_2.verifier_id)
            
            try:
                await workflow.execute_activity(
                    "revoke_verifier_confirmations",
                    args=[self.state.user_id, verifier_ids],
                    start_to_close_timeout=timedelta(seconds=30),
                )
            except Exception as e:
                workflow.logger.error(
                    f"Failed to revoke confirmations",
                    extra={"user_id": self.state.user_id, "error": str(e)}
                )
