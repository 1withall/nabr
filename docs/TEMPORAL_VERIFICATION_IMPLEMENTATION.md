# Temporal Verification Workflows - Technical Implementation

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    Parent Verification Workflow                 │
│  (IndividualVerificationWorkflow / BusinessVerificationWorkflow │
│   / OrganizationVerificationWorkflow)                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐   │
│  │  State Management                                       │   │
│  │  - Current trust score                                  │   │
│  │  - Completed methods (with counts for multipliers)      │   │
│  │  - Verification level                                   │   │
│  │  - Pending verifications                               │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐   │
│  │  Child Workflows (per verification method)             │   │
│  │                                                         │   │
│  │  ├─ EmailVerificationWorkflow                          │   │
│  │  ├─ PhoneVerificationWorkflow                          │   │
│  │  ├─ TwoPartyInPersonWorkflow (Saga)                    │   │
│  │  ├─ GovernmentIDWorkflow                               │   │
│  │  ├─ BiometricWorkflow                                  │   │
│  │  ├─ ReferenceVerificationWorkflow                      │   │
│  │  ├─ BusinessLicenseWorkflow                            │   │
│  │  ├─ TaxIDWorkflow                                      │   │
│  │  └─ ... (one per verification method)                  │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐   │
│  │  Signals                                                │   │
│  │  - start_verification_method(method, params)           │   │
│  │  - verifier_confirms(verifier_id, notes)               │   │
│  │  - community_attests(member_id, attestation)           │   │
│  │  - revoke_verification(method, reason)                 │   │
│  │  - update_contact_info(email, phone)                   │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐   │
│  │  Queries                                                │   │
│  │  - get_trust_score() -> int                            │   │
│  │  - get_verification_level() -> VerificationLevel       │   │
│  │  - get_completed_methods() -> Dict[Method, int]        │   │
│  │  - get_next_level_info() -> NextLevelInfo             │   │
│  │  - get_verification_status(method) -> MethodStatus    │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐   │
│  │  Activities                                             │   │
│  │  - calculate_trust_score()                             │   │
│  │  - validate_verifier_credentials()                     │   │
│  │  - check_method_expiry()                               │   │
│  │  - send_notification()                                 │   │
│  │  - record_verification_event()                         │   │
│  └────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## Parent Verification Workflow

### IndividualVerificationWorkflow

```python
from temporalio import workflow
from temporalio.common import RetryPolicy
from datetime import timedelta
from typing import Dict, Set
import asyncio

from nabr.models.verification_types import (
    VerificationMethod,
    VerificationLevel,
    UserType,
    calculate_trust_score,
    calculate_verification_level,
    get_next_level_requirements,
    METHOD_SCORES,
)
from nabr.temporal.workflows.verification_methods import (
    EmailVerificationWorkflow,
    PhoneVerificationWorkflow,
    TwoPartyInPersonWorkflow,
    GovernmentIDWorkflow,
    ReferenceVerificationWorkflow,
)
from nabr.temporal.activities.verification import (
    calculate_trust_score_activity,
    record_verification_event,
    send_level_change_notification,
    check_verifier_authorization,
)


@workflow.defn
class IndividualVerificationWorkflow:
    """
    Parent workflow managing lifetime verification for an individual user.
    
    Uses Continue-As-New to support indefinite lifetime (years).
    Uses Child Workflows for each verification method.
    Uses Signals for real-time updates.
    Uses Queries for instant status checks.
    """
    
    def __init__(self) -> None:
        self.user_id: str = ""
        self.user_type = UserType.INDIVIDUAL
        
        # Completed methods with counts (for multipliers)
        self.completed_methods: Dict[VerificationMethod, int] = {}
        
        # Current trust score and level
        self.trust_score: int = 0
        self.verification_level: VerificationLevel = VerificationLevel.UNVERIFIED
        
        # Active child workflows
        self.active_verifications: Dict[VerificationMethod, workflow.ChildWorkflowHandle] = {}
        
        # Completion timestamps for expiry tracking
        self.completion_timestamps: Dict[VerificationMethod, str] = {}
        
        # Events for signal handling
        self.method_started = asyncio.Event()
        self.verifier_confirmed = asyncio.Event()
        
    @workflow.run
    async def run(self, user_id: str, initial_methods: Set[VerificationMethod] = None) -> None:
        """
        Main workflow execution.
        
        Args:
            user_id: User being verified
            initial_methods: Optional set of methods to start immediately
        """
        self.user_id = user_id
        
        workflow.logger.info(
            f"Starting individual verification workflow for user {user_id}",
            extra={"user_id": user_id, "user_type": "individual"}
        )
        
        # Start initial verification methods if provided
        if initial_methods:
            for method in initial_methods:
                await self._start_verification_method(method, {})
        
        # Main loop: Wait for signals and process verifications
        iteration = 0
        max_iterations = 1000  # Continue-As-New after 1000 iterations
        
        while iteration < max_iterations:
            iteration += 1
            
            # Wait for events (signals) with timeout
            try:
                await workflow.wait_condition(
                    lambda: self.method_started.is_set() or self.verifier_confirmed.is_set(),
                    timeout=timedelta(days=30)  # Check every 30 days for expiry
                )
            except asyncio.TimeoutError:
                # Timeout reached - check for expired methods
                await self._check_and_renew_expired_methods()
                continue
            
            # Process events
            if self.method_started.is_set():
                self.method_started.clear()
                # Method start handled in signal
                
            if self.verifier_confirmed.is_set():
                self.verifier_confirmed.clear()
                # Recalculate trust score
                await self._recalculate_trust_score()
        
        # Continue as new to prevent event history growth
        workflow.logger.info(f"Continue-As-New after {iteration} iterations")
        await workflow.continue_as_new(user_id, None)
    
    # ========================================================================
    # SIGNALS
    # ========================================================================
    
    @workflow.signal
    async def start_verification_method(
        self,
        method: VerificationMethod,
        params: Dict
    ) -> None:
        """
        Signal to start a new verification method.
        
        Args:
            method: Verification method to start
            params: Method-specific parameters
        """
        workflow.logger.info(
            f"Signal received: start_verification_method({method})",
            extra={"user_id": self.user_id, "method": method}
        )
        
        await self._start_verification_method(method, params)
        self.method_started.set()
    
    @workflow.signal
    async def verifier_confirms_identity(
        self,
        verifier_id: str,
        method: VerificationMethod,
        notes: str
    ) -> None:
        """
        Signal from authorized verifier confirming user identity.
        
        Args:
            verifier_id: ID of verifier
            method: Which verification method this confirms
            notes: Verifier notes
        """
        workflow.logger.info(
            f"Signal received: verifier_confirms_identity from {verifier_id}",
            extra={"user_id": self.user_id, "verifier_id": verifier_id, "method": method}
        )
        
        # Validate verifier authorization
        is_authorized = await workflow.execute_activity(
            check_verifier_authorization,
            args=[verifier_id, method],
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=RetryPolicy(maximum_attempts=3)
        )
        
        if not is_authorized:
            workflow.logger.warning(
                f"Unauthorized verifier attempt: {verifier_id}",
                extra={"user_id": self.user_id, "verifier_id": verifier_id}
            )
            return
        
        # Signal the appropriate child workflow
        if method in self.active_verifications:
            handle = self.active_verifications[method]
            await handle.signal("verifier_confirmation", verifier_id, notes)
        
        self.verifier_confirmed.set()
    
    @workflow.signal
    async def community_attests(
        self,
        member_id: str,
        attestation: str
    ) -> None:
        """
        Signal from community member attesting to user's identity.
        
        Args:
            member_id: ID of community member
            attestation: Attestation text
        """
        workflow.logger.info(
            f"Signal received: community_attests from {member_id}",
            extra={"user_id": self.user_id, "member_id": member_id}
        )
        
        # Start community attestation verification
        await self._start_verification_method(
            VerificationMethod.COMMUNITY_ATTESTATION,
            {"member_id": member_id, "attestation": attestation}
        )
    
    @workflow.signal
    async def revoke_verification(
        self,
        method: VerificationMethod,
        reason: str
    ) -> None:
        """
        Signal to revoke a verification method (e.g., fraud detected).
        
        Args:
            method: Method to revoke
            reason: Reason for revocation
        """
        workflow.logger.warning(
            f"Signal received: revoke_verification({method})",
            extra={"user_id": self.user_id, "method": method, "reason": reason}
        )
        
        # Remove from completed methods
        if method in self.completed_methods:
            del self.completed_methods[method]
        
        # Cancel active child workflow if running
        if method in self.active_verifications:
            handle = self.active_verifications[method]
            await handle.cancel()
            del self.active_verifications[method]
        
        # Recalculate trust score
        await self._recalculate_trust_score()
        
        # Record revocation event
        await workflow.execute_activity(
            record_verification_event,
            args=[self.user_id, method, "revoked", {"reason": reason}],
            start_to_close_timeout=timedelta(seconds=10)
        )
    
    # ========================================================================
    # QUERIES
    # ========================================================================
    
    @workflow.query
    def get_trust_score(self) -> int:
        """Query current trust score."""
        return self.trust_score
    
    @workflow.query
    def get_verification_level(self) -> str:
        """Query current verification level."""
        return self.verification_level.value
    
    @workflow.query
    def get_completed_methods(self) -> Dict[str, int]:
        """Query completed verification methods with counts."""
        return {method.value: count for method, count in self.completed_methods.items()}
    
    @workflow.query
    def get_next_level_info(self) -> Dict:
        """Query what's needed to reach next level."""
        next_level, points_needed, suggested_paths = get_next_level_requirements(
            self.trust_score,
            self.user_type,
            set(self.completed_methods.keys())
        )
        
        return {
            "next_level": next_level.value,
            "points_needed": points_needed,
            "current_score": self.trust_score,
            "suggested_paths": [
                [method.value for method in path]
                for path in suggested_paths
            ]
        }
    
    @workflow.query
    def get_verification_status(self, method: VerificationMethod) -> Dict:
        """Query status of specific verification method."""
        return {
            "completed": method in self.completed_methods,
            "count": self.completed_methods.get(method, 0),
            "active": method in self.active_verifications,
            "timestamp": self.completion_timestamps.get(method),
        }
    
    # ========================================================================
    # INTERNAL METHODS
    # ========================================================================
    
    async def _start_verification_method(
        self,
        method: VerificationMethod,
        params: Dict
    ) -> None:
        """Start a child workflow for specific verification method."""
        
        # Don't start if already running
        if method in self.active_verifications:
            workflow.logger.info(f"Verification {method} already active, skipping")
            return
        
        # Select appropriate child workflow
        workflow_class = self._get_workflow_class_for_method(method)
        if not workflow_class:
            workflow.logger.error(f"No workflow class for method {method}")
            return
        
        # Start child workflow
        workflow.logger.info(f"Starting child workflow for {method}")
        
        handle = await workflow.start_child_workflow(
            workflow_class,
            args=[self.user_id, params],
            id=f"verification-{self.user_id}-{method.value}-{workflow.now().timestamp()}",
            parent_close_policy=workflow.ParentClosePolicy.ABANDON,  # Keep running if parent restarts
            retry_policy=RetryPolicy(
                maximum_attempts=3,
                initial_interval=timedelta(seconds=1),
                maximum_interval=timedelta(minutes=1),
            )
        )
        
        self.active_verifications[method] = handle
        
        # Await completion in background
        asyncio.create_task(self._await_verification_completion(method, handle))
    
    async def _await_verification_completion(
        self,
        method: VerificationMethod,
        handle: workflow.ChildWorkflowHandle
    ) -> None:
        """Wait for child workflow completion and update state."""
        try:
            result = await handle.result()
            
            workflow.logger.info(
                f"Verification {method} completed successfully",
                extra={"user_id": self.user_id, "method": method, "result": result}
            )
            
            # Update completed methods (increment count for multipliers)
            current_count = self.completed_methods.get(method, 0)
            score_info = METHOD_SCORES.get(method)
            
            if score_info and current_count < score_info.max_multiplier:
                self.completed_methods[method] = current_count + 1
                self.completion_timestamps[method] = workflow.now().isoformat()
                
                # Recalculate trust score
                await self._recalculate_trust_score()
            else:
                workflow.logger.info(
                    f"Method {method} already at max multiplier, not counting again"
                )
            
        except Exception as e:
            workflow.logger.error(
                f"Verification {method} failed: {e}",
                extra={"user_id": self.user_id, "method": method, "error": str(e)}
            )
        finally:
            # Remove from active verifications
            if method in self.active_verifications:
                del self.active_verifications[method]
    
    async def _recalculate_trust_score(self) -> None:
        """Recalculate trust score and check for level changes."""
        
        # Calculate new score using activity
        new_score = await workflow.execute_activity(
            calculate_trust_score_activity,
            args=[dict(self.completed_methods), self.user_type.value],
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=RetryPolicy(maximum_attempts=3)
        )
        
        old_score = self.trust_score
        old_level = self.verification_level
        
        self.trust_score = new_score
        self.verification_level = calculate_verification_level(new_score)
        
        workflow.logger.info(
            f"Trust score updated: {old_score} -> {new_score} (level: {self.verification_level})",
            extra={
                "user_id": self.user_id,
                "old_score": old_score,
                "new_score": new_score,
                "level": self.verification_level.value
            }
        )
        
        # Check for level change
        if self.verification_level != old_level:
            workflow.logger.info(
                f"Verification level changed: {old_level} -> {self.verification_level}",
                extra={"user_id": self.user_id, "new_level": self.verification_level.value}
            )
            
            # Send notification
            await workflow.execute_activity(
                send_level_change_notification,
                args=[self.user_id, old_level.value, self.verification_level.value, new_score],
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=RetryPolicy(maximum_attempts=3)
            )
            
            # Record event
            await workflow.execute_activity(
                record_verification_event,
                args=[
                    self.user_id,
                    None,  # Not specific to one method
                    "level_changed",
                    {
                        "old_level": old_level.value,
                        "new_level": self.verification_level.value,
                        "trust_score": new_score
                    }
                ],
                start_to_close_timeout=timedelta(seconds=10)
            )
    
    async def _check_and_renew_expired_methods(self) -> None:
        """Check for expired methods and trigger renewal workflows."""
        from nabr.models.verification_types import is_method_expired
        
        for method, timestamp in list(self.completion_timestamps.items()):
            if is_method_expired(method, timestamp):
                workflow.logger.info(
                    f"Method {method} expired, removing from completed list",
                    extra={"user_id": self.user_id, "method": method}
                )
                
                # Remove from completed (will reduce trust score)
                if method in self.completed_methods:
                    del self.completed_methods[method]
                
                del self.completion_timestamps[method]
                
                # Recalculate score
                await self._recalculate_trust_score()
    
    def _get_workflow_class_for_method(self, method: VerificationMethod):
        """Map verification method to child workflow class."""
        method_to_workflow = {
            VerificationMethod.EMAIL: EmailVerificationWorkflow,
            VerificationMethod.PHONE: PhoneVerificationWorkflow,
            VerificationMethod.IN_PERSON_TWO_PARTY: TwoPartyInPersonWorkflow,
            VerificationMethod.GOVERNMENT_ID: GovernmentIDWorkflow,
            VerificationMethod.PERSONAL_REFERENCE: ReferenceVerificationWorkflow,
            # Add more mappings...
        }
        
        return method_to_workflow.get(method)
```

## Child Workflow Example: Two-Party In-Person Verification (Saga)

This is the most complex child workflow, demonstrating the Saga pattern:

```python
from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ApplicationError
from datetime import timedelta
from typing import Dict, List
import asyncio

from nabr.temporal.activities.verification import (
    generate_qr_codes,
    validate_verifier_credentials,
    record_verifier_confirmation,
    send_verifier_notification,
    award_verification_points,
)


@workflow.defn
class TwoPartyInPersonWorkflow:
    """
    Child workflow for two-party in-person verification.
    
    Uses SAGA PATTERN for multi-step verification with compensation.
    
    Steps:
    1. Generate QR codes for both verifiers
    2. Wait for first verifier confirmation (via signal)
    3. Wait for second verifier confirmation (via signal)
    4. Validate both verifications
    5. Award points
    
    Compensation (on failure):
    - Revoke any partial confirmations
    - Notify verifiers of cancellation
    - Clean up QR codes
    """
    
    def __init__(self) -> None:
        self.user_id: str = ""
        self.qr_codes: Dict[str, str] = {}
        self.confirmations: Dict[str, Dict] = {}  # verifier_id -> confirmation details
        self.confirmation_received = asyncio.Event()
        self.compensations: List[callable] = []  # Compensation functions
        
    @workflow.run
    async def run(self, user_id: str, params: Dict) -> Dict:
        """
        Execute two-party verification saga.
        
        Args:
            user_id: User being verified
            params: Optional parameters (e.g., preferred verifier IDs)
            
        Returns:
            Verification result with points awarded
        """
        self.user_id = user_id
        
        workflow.logger.info(
            f"Starting two-party in-person verification for {user_id}",
            extra={"user_id": user_id}
        )
        
        try:
            # ============================================================
            # STEP 1: Generate QR codes
            # ============================================================
            workflow.logger.info("Saga Step 1: Generate QR codes")
            
            self.qr_codes = await workflow.execute_activity(
                generate_qr_codes,
                args=[user_id, 2],  # 2 verifiers needed
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=RetryPolicy(maximum_attempts=3)
            )
            
            # Register compensation: Clean up QR codes
            self.compensations.append(self._compensate_qr_codes)
            
            # ============================================================
            # STEP 2: Wait for verifier confirmations
            # ============================================================
            workflow.logger.info("Saga Step 2: Wait for verifier confirmations")
            
            # Wait for 2 confirmations with timeout
            timeout_hours = params.get("timeout_hours", 72)  # 3 days default
            
            await workflow.wait_condition(
                lambda: len(self.confirmations) >= 2,
                timeout=timedelta(hours=timeout_hours)
            )
            
            workflow.logger.info(
                f"Received {len(self.confirmations)} confirmations",
                extra={"user_id": user_id, "verifier_count": len(self.confirmations)}
            )
            
            # ============================================================
            # STEP 3: Validate verifier credentials
            # ============================================================
            workflow.logger.info("Saga Step 3: Validate verifier credentials")
            
            validation_results = []
            for verifier_id, confirmation in self.confirmations.items():
                is_valid = await workflow.execute_activity(
                    validate_verifier_credentials,
                    args=[verifier_id, confirmation],
                    start_to_close_timeout=timedelta(seconds=30),
                    retry_policy=RetryPolicy(maximum_attempts=3)
                )
                validation_results.append((verifier_id, is_valid))
            
            # Check if both are valid
            invalid_verifiers = [vid for vid, valid in validation_results if not valid]
            if invalid_verifiers:
                raise ApplicationError(
                    f"Invalid verifiers: {invalid_verifiers}",
                    non_retryable=True
                )
            
            # ============================================================
            # STEP 4: Record confirmations (compensatable)
            # ============================================================
            workflow.logger.info("Saga Step 4: Record confirmations")
            
            for verifier_id, confirmation in self.confirmations.items():
                await workflow.execute_activity(
                    record_verifier_confirmation,
                    args=[user_id, verifier_id, confirmation],
                    start_to_close_timeout=timedelta(seconds=10),
                    retry_policy=RetryPolicy(maximum_attempts=3)
                )
            
            # Register compensation: Revoke confirmations
            self.compensations.append(self._compensate_confirmations)
            
            # ============================================================
            # STEP 5: Award points (final step, no compensation needed)
            # ============================================================
            workflow.logger.info("Saga Step 5: Award verification points")
            
            points_awarded = await workflow.execute_activity(
                award_verification_points,
                args=[user_id, "IN_PERSON_TWO_PARTY", 150],
                start_to_close_timeout=timedelta(seconds=10),
                retry_policy=RetryPolicy(maximum_attempts=3)
            )
            
            workflow.logger.info(
                "Two-party verification completed successfully",
                extra={"user_id": user_id, "points": points_awarded}
            )
            
            return {
                "success": True,
                "points_awarded": points_awarded,
                "verifiers": list(self.confirmations.keys())
            }
            
        except asyncio.TimeoutError:
            workflow.logger.warning(
                f"Two-party verification timed out for {user_id}",
                extra={"user_id": user_id}
            )
            # Compensation will run automatically
            raise ApplicationError(
                "Verification timeout - insufficient confirmations",
                non_retryable=True
            )
            
        except Exception as e:
            workflow.logger.error(
                f"Two-party verification failed: {e}",
                extra={"user_id": user_id, "error": str(e)}
            )
            # Compensation will run automatically
            raise
        
        finally:
            # If we're here due to exception, run compensations
            if workflow.current_history_length() > 0:  # Check if we're in failure path
                await self._run_compensations()
    
    # ========================================================================
    # SIGNALS
    # ========================================================================
    
    @workflow.signal
    async def verifier_confirmation(
        self,
        verifier_id: str,
        confirmation_data: Dict
    ) -> None:
        """
        Signal from verifier confirming they've verified the user.
        
        Args:
            verifier_id: ID of verifier
            confirmation_data: Confirmation details (notes, location, etc.)
        """
        workflow.logger.info(
            f"Verifier confirmation received from {verifier_id}",
            extra={"user_id": self.user_id, "verifier_id": verifier_id}
        )
        
        self.confirmations[verifier_id] = confirmation_data
        self.confirmation_received.set()
    
    # ========================================================================
    # COMPENSATION FUNCTIONS (Saga Pattern)
    # ========================================================================
    
    async def _run_compensations(self) -> None:
        """Execute all registered compensation functions in reverse order."""
        workflow.logger.info("Running saga compensations")
        
        for compensation_fn in reversed(self.compensations):
            try:
                await compensation_fn()
            except Exception as e:
                workflow.logger.error(
                    f"Compensation failed: {e}",
                    extra={"error": str(e)}
                )
    
    async def _compensate_qr_codes(self) -> None:
        """Compensation: Invalidate generated QR codes."""
        workflow.logger.info("Compensating: Invalidating QR codes")
        
        from nabr.temporal.activities.verification import invalidate_qr_codes
        
        await workflow.execute_activity(
            invalidate_qr_codes,
            args=[self.qr_codes],
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=RetryPolicy(maximum_attempts=3)
        )
    
    async def _compensate_confirmations(self) -> None:
        """Compensation: Revoke recorded confirmations."""
        workflow.logger.info("Compensating: Revoking confirmations")
        
        from nabr.temporal.activities.verification import revoke_confirmations
        
        for verifier_id in self.confirmations.keys():
            await workflow.execute_activity(
                revoke_confirmations,
                args=[self.user_id, verifier_id],
                start_to_close_timeout=timedelta(seconds=10),
                retry_policy=RetryPolicy(maximum_attempts=3)
            )
        
        # Notify verifiers
        for verifier_id in self.confirmations.keys():
            await workflow.execute_activity(
                send_verifier_notification,
                args=[verifier_id, "Verification cancelled - compensation executed"],
                start_to_close_timeout=timedelta(seconds=10)
            )
```

## Next Steps

1. **Implement remaining child workflows** for each verification method
2. **Create BusinessVerificationWorkflow** and **OrganizationVerificationWorkflow** (similar structure)
3. **Implement activities** in `src/nabr/temporal/activities/verification.py`
4. **Update API routes** to use new scoring system
5. **Create UI components** showing trust scores and point values
6. **Write comprehensive tests** for all workflows

## Testing Strategy

### Unit Tests
- Test trust score calculation
- Test level determination
- Test method applicability
- Test expiry checking

### Integration Tests
- Test child workflow execution
- Test signal handling
- Test query responses
- Test saga compensation

### End-to-End Tests
- Test complete individual verification flow
- Test business verification flow
- Test organization verification flow
- Test level progression
- Test method expiry and renewal

## Deployment Strategy

1. **Phase 1**: Deploy new verification_types.py (backward compatible)
2. **Phase 2**: Deploy new workflows alongside old system
3. **Phase 3**: Migrate existing users to new system
4. **Phase 4**: Deprecate old workflows
5. **Phase 5**: Add new verification methods

## Monitoring & Observability

### Key Metrics
- Trust scores by user type
- Verification completion rates by method
- Time to complete verification by level
- Verifier activity and accuracy
- Method expiry and renewal rates

### Alerts
- High failure rate for specific method
- Suspicious rapid trust accumulation
- Verifier validation failures
- System overload (too many concurrent verifications)

## Security Considerations

### Threat Model
- **Sybil attacks**: Prevented by nullifier hashes
- **Verifier collusion**: Mitigated by requiring STANDARD+ level verifiers
- **Fraud**: Detected by anomaly monitoring and community flags
- **Data breaches**: Minimized by zero-knowledge proofs (future)

### Audit Trail
- All verification events recorded with timestamps
- Verifier confirmations permanently logged
- Trust score changes tracked
- Method revocations documented with reasons
