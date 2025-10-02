"""Individual verification workflow - lifetime verification management.

This parent workflow manages the entire verification lifecycle for individual
users, spawning child workflows for each verification method, tracking trust
scores, handling expiry, and providing real-time status via queries.

Uses Temporal advanced patterns:
- Child workflows for modularity (each method is independent)
- Signals for real-time updates (verifier confirmations, revocations)
- Queries for instant status checks (trust score, level, next steps)
- Continue-As-New for indefinite lifetime (can run for years)
"""

from datetime import timedelta, datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ApplicationError

with workflow.unsafe.imports_passed_through():
    from nabr.models.verification_types import (
        VerificationLevel,
        VerificationMethod,
        UserType,
        calculate_trust_score,
        calculate_verification_level,
        get_next_level_requirements,
        is_method_expired,
        get_applicable_methods,
        METHOD_SCORES,
    )


@dataclass
class MethodCompletion:
    """Record of a completed verification method."""
    method: VerificationMethod
    completed_at: datetime
    points_awarded: int
    count: int = 1  # For methods with multipliers (e.g., 3 references)
    metadata: Dict[str, Any] = field(default_factory=dict)
    expires_at: Optional[datetime] = None


@dataclass
class VerificationState:
    """Current state of user's verification."""
    user_id: str
    user_type: UserType
    trust_score: int = 0
    verification_level: VerificationLevel = VerificationLevel.UNVERIFIED
    completed_methods: Dict[str, MethodCompletion] = field(default_factory=dict)
    active_verifications: List[str] = field(default_factory=list)  # Child workflow IDs
    last_expiry_check: Optional[datetime] = None
    iteration_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dict for Continue-As-New."""
        return {
            "user_id": self.user_id,
            "user_type": self.user_type.value,
            "trust_score": self.trust_score,
            "verification_level": self.verification_level.value,
            "completed_methods": {
                k: {
                    "method": v.method.value,
                    "completed_at": v.completed_at.isoformat(),
                    "points_awarded": v.points_awarded,
                    "count": v.count,
                    "metadata": v.metadata,
                    "expires_at": v.expires_at.isoformat() if v.expires_at else None,
                }
                for k, v in self.completed_methods.items()
            },
            "active_verifications": self.active_verifications,
            "last_expiry_check": self.last_expiry_check.isoformat() if self.last_expiry_check else None,
            "iteration_count": self.iteration_count,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VerificationState":
        """Reconstruct state from Continue-As-New."""
        state = cls(
            user_id=data["user_id"],
            user_type=UserType(data["user_type"]),
            trust_score=data["trust_score"],
            verification_level=VerificationLevel(data["verification_level"]),
            active_verifications=data["active_verifications"],
            iteration_count=data["iteration_count"],
        )
        
        # Reconstruct completed methods
        for key, method_data in data["completed_methods"].items():
            state.completed_methods[key] = MethodCompletion(
                method=VerificationMethod(method_data["method"]),
                completed_at=datetime.fromisoformat(method_data["completed_at"]),
                points_awarded=method_data["points_awarded"],
                count=method_data["count"],
                metadata=method_data["metadata"],
                expires_at=datetime.fromisoformat(method_data["expires_at"]) if method_data["expires_at"] else None,
            )
        
        if data["last_expiry_check"]:
            state.last_expiry_check = datetime.fromisoformat(data["last_expiry_check"])
        
        return state


@workflow.defn
class IndividualVerificationWorkflow:
    """Parent workflow managing lifetime verification for individual users.
    
    This workflow:
    1. Maintains verification state (trust score, level, completed methods)
    2. Spawns child workflows for each verification method
    3. Receives signals for real-time updates (confirmations, revocations)
    4. Provides queries for instant status checks
    5. Handles method expiry and renewal
    6. Uses Continue-As-New for indefinite lifetime
    """
    
    def __init__(self) -> None:
        self.state: Optional[VerificationState] = None
    
    @workflow.run
    async def run(self, user_id: str, user_type: str = "INDIVIDUAL", state_dict: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute the verification workflow.
        
        Args:
            user_id: The user being verified
            user_type: Type of user (INDIVIDUAL, BUSINESS, ORGANIZATION)
            state_dict: Previous state (for Continue-As-New)
        
        Returns:
            Final state dictionary
        """
        # Initialize or restore state
        if state_dict:
            self.state = VerificationState.from_dict(state_dict)
        else:
            self.state = VerificationState(
                user_id=user_id,
                user_type=UserType(user_type)
            )
        
        workflow.logger.info(
            f"Individual verification workflow started for user {user_id}",
            extra={
                "user_id": user_id,
                "user_type": self.state.user_type.value,
                "trust_score": self.state.trust_score,
                "level": self.state.verification_level.value,
                "iteration": self.state.iteration_count,
            }
        )
        
        # Main workflow loop
        while True:
            self.state.iteration_count += 1
            
            # Check for expiry every 30 days
            if (
                not self.state.last_expiry_check
                or workflow.now() - self.state.last_expiry_check > timedelta(days=30)
            ):
                await self._check_and_handle_expiry()
                self.state.last_expiry_check = workflow.now()
            
            # Continue-As-New after 1000 iterations to avoid history growth
            if self.state.iteration_count >= 1000:
                workflow.logger.info(
                    f"Continuing workflow as new (iteration {self.state.iteration_count})",
                    extra={"user_id": self.state.user_id}
                )
                workflow.continue_as_new(
                    args=[self.state.user_id, self.state.user_type.value, self.state.to_dict()]
                )
            
            # Wait for signals (verification start, confirmation, revocation)
            # This allows the workflow to be long-running without consuming resources
            await workflow.wait_condition(lambda: False, timeout=timedelta(days=30))
        
        return self.state.to_dict()
    
    @workflow.signal
    async def start_verification_method(
        self,
        method: str,
        params: Optional[Dict[str, Any]] = None
    ) -> None:
        """Start a verification method (spawns child workflow).
        
        Args:
            method: Verification method to start (e.g., "EMAIL", "TWO_PARTY_IN_PERSON")
            params: Method-specific parameters
        """
        if not self.state:
            workflow.logger.error("Workflow state not initialized")
            return
        
        try:
            method_enum = VerificationMethod(method)
            params = params or {}
            
            # Check if method is applicable for user type
            applicable = get_applicable_methods(self.state.user_type)
            if method_enum not in applicable:
                workflow.logger.warning(
                    f"Method {method} not applicable for user type {self.state.user_type.value}",
                    extra={"user_id": self.state.user_id, "method": method}
                )
                return
            
            # Check if method is already completed and not expired
            method_key = method_enum.value
            if method_key in self.state.completed_methods:
                completion = self.state.completed_methods[method_key]
                if not is_method_expired(method_enum, completion.completed_at.isoformat()):
                    workflow.logger.info(
                        f"Method {method} already completed and not expired",
                        extra={"user_id": self.state.user_id, "method": method}
                    )
                    return
            
            # Spawn child workflow for this method
            child_workflow_id = f"verification-{self.state.user_id}-{method}-{workflow.now().isoformat()}"
            
            workflow.logger.info(
                f"Starting child workflow for method {method}",
                extra={
                    "user_id": self.state.user_id,
                    "method": method,
                    "child_workflow_id": child_workflow_id
                }
            )
            
            # Track active verification
            self.state.active_verifications.append(child_workflow_id)
            
            # TODO: Implement child workflow spawning based on method type
            # This will be implemented in the next phase with actual child workflows
            # For now, log the intent
            workflow.logger.info(
                f"Child workflow {child_workflow_id} would be started here",
                extra={"method": method, "params": params}
            )
            
        except ValueError as e:
            workflow.logger.error(
                f"Invalid verification method: {method}",
                extra={"user_id": self.state.user_id, "error": str(e)}
            )
    
    @workflow.signal
    async def verifier_confirms_identity(
        self,
        verifier_id: str,
        method: str,
        confirmation_data: Dict[str, Any]
    ) -> None:
        """Handle verifier confirmation signal.
        
        Args:
            verifier_id: ID of the verifier
            method: Verification method confirmed
            confirmation_data: Method-specific confirmation data
        """
        if not self.state:
            workflow.logger.error("Workflow state not initialized")
            return
        
        workflow.logger.info(
            f"Verifier {verifier_id} confirmed {method}",
            extra={
                "user_id": self.state.user_id,
                "verifier_id": verifier_id,
                "method": method,
            }
        )
        
        # This will trigger appropriate child workflow via signal
        # Implementation will be completed when child workflows are added
    
    @workflow.signal
    async def community_attests(
        self,
        attestor_id: str,
        attestation_data: Dict[str, Any]
    ) -> None:
        """Handle community attestation signal.
        
        Args:
            attestor_id: ID of the community member attesting
            attestation_data: Attestation details
        """
        if not self.state:
            workflow.logger.error("Workflow state not initialized")
            return
        
        workflow.logger.info(
            f"Community attestation from {attestor_id}",
            extra={
                "user_id": self.state.user_id,
                "attestor_id": attestor_id,
            }
        )
        
        # Award points for community attestation
        await self._complete_method(
            method=VerificationMethod.COMMUNITY_ATTESTATION,
            metadata={"attestor_id": attestor_id, **attestation_data}
        )
    
    @workflow.signal
    async def revoke_verification(
        self,
        method: str,
        reason: str
    ) -> None:
        """Revoke a verification method.
        
        Args:
            method: Method to revoke
            reason: Reason for revocation
        """
        if not self.state:
            workflow.logger.error("Workflow state not initialized")
            return
        
        method_enum = VerificationMethod(method)
        method_key = method_enum.value
        
        if method_key not in self.state.completed_methods:
            workflow.logger.warning(
                f"Cannot revoke {method} - not completed",
                extra={"user_id": self.state.user_id, "method": method}
            )
            return
        
        workflow.logger.info(
            f"Revoking verification method {method}",
            extra={
                "user_id": self.state.user_id,
                "method": method,
                "reason": reason
            }
        )
        
        # Remove method and recalculate trust score
        del self.state.completed_methods[method_key]
        await self._recalculate_trust_score()
    
    @workflow.query
    def get_trust_score(self) -> int:
        """Get current trust score."""
        return self.state.trust_score if self.state else 0
    
    @workflow.query
    def get_verification_level(self) -> str:
        """Get current verification level."""
        return self.state.verification_level.value if self.state else VerificationLevel.UNVERIFIED.value
    
    @workflow.query
    def get_completed_methods(self) -> Dict[str, Dict[str, Any]]:
        """Get all completed verification methods."""
        if not self.state:
            return {}
        
        return {
            k: {
                "method": v.method.value,
                "completed_at": v.completed_at.isoformat(),
                "points_awarded": v.points_awarded,
                "count": v.count,
                "expires_at": v.expires_at.isoformat() if v.expires_at else None,
                "is_expired": is_method_expired(v.method, v.completed_at.isoformat()),
            }
            for k, v in self.state.completed_methods.items()
        }
    
    @workflow.query
    def get_next_level_info(self) -> Dict[str, Any]:
        """Get information about next verification level."""
        if not self.state:
            return {}
        
        # Convert completed method keys to VerificationMethod enum set
        completed_method_enums = {
            VerificationMethod(key) for key in self.state.completed_methods.keys()
        }
        
        next_level, points_needed, suggested = get_next_level_requirements(
            current_score=self.state.trust_score,
            user_type=self.state.user_type,
            completed_methods=completed_method_enums
        )
        
        return {
            "current_score": self.state.trust_score,
            "current_level": self.state.verification_level.value,
            "next_level": next_level.value if next_level else None,
            "points_needed": points_needed,
            "suggested_paths": suggested,
        }
    
    @workflow.query
    def get_active_verifications(self) -> List[str]:
        """Get list of active verification workflow IDs."""
        return self.state.active_verifications if self.state else []
    
    async def _check_and_handle_expiry(self) -> None:
        """Check for expired methods and handle renewal."""
        if not self.state:
            return
        
        expired_methods = []
        
        for method_key, completion in self.state.completed_methods.items():
            if is_method_expired(completion.method, completion.completed_at.isoformat()):
                expired_methods.append(method_key)
                workflow.logger.info(
                    f"Method {method_key} has expired",
                    extra={
                        "user_id": self.state.user_id,
                        "method": method_key,
                        "completed_at": completion.completed_at.isoformat()
                    }
                )
        
        # Remove expired methods
        for method_key in expired_methods:
            del self.state.completed_methods[method_key]
        
        # Recalculate trust score if any expired
        if expired_methods:
            await self._recalculate_trust_score()
    
    async def _complete_method(
        self,
        method: VerificationMethod,
        count: int = 1,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Mark a verification method as complete and award points.
        
        Args:
            method: The verification method completed
            count: Number of times completed (for multipliers)
            metadata: Additional method-specific data
        """
        if not self.state:
            return
        
        method_key = method.value
        score_info = METHOD_SCORES.get(method)
        
        if not score_info:
            workflow.logger.error(
                f"No score info for method {method_key}",
                extra={"user_id": self.state.user_id, "method": method_key}
            )
            return
        
        # Calculate points (respecting max multiplier)
        effective_count = min(count, int(score_info.max_multiplier))
        points_awarded = score_info.points * effective_count
        
        # Calculate expiry
        expires_at = None
        if score_info.decay_days > 0:
            expires_at = workflow.now() + timedelta(days=score_info.decay_days)
        
        # Record completion
        completion = MethodCompletion(
            method=method,
            completed_at=workflow.now(),
            points_awarded=points_awarded,
            count=effective_count,
            metadata=metadata or {},
            expires_at=expires_at
        )
        
        self.state.completed_methods[method_key] = completion
        
        workflow.logger.info(
            f"Method {method_key} completed",
            extra={
                "user_id": self.state.user_id,
                "method": method_key,
                "points": points_awarded,
                "count": effective_count,
            }
        )
        
        # Recalculate trust score and level
        await self._recalculate_trust_score()
    
    async def _recalculate_trust_score(self) -> None:
        """Recalculate trust score and verification level from completed methods."""
        if not self.state:
            return
        
        old_score = self.state.trust_score
        old_level = self.state.verification_level
        
        # Convert completed methods to Dict[VerificationMethod, int] format
        method_counts = {
            completion.method: completion.count
            for completion in self.state.completed_methods.values()
        }
        
        # Calculate new trust score
        self.state.trust_score = calculate_trust_score(
            completed_methods=method_counts,
            user_type=self.state.user_type
        )
        
        # Calculate new verification level
        self.state.verification_level = calculate_verification_level(self.state.trust_score)
        
        workflow.logger.info(
            f"Trust score recalculated",
            extra={
                "user_id": self.state.user_id,
                "old_score": old_score,
                "new_score": self.state.trust_score,
                "old_level": old_level.value,
                "new_level": self.state.verification_level.value,
            }
        )
        
        # Log level change if it occurred
        if old_level != self.state.verification_level:
            workflow.logger.info(
                f"Verification level changed: {old_level.value} → {self.state.verification_level.value}",
                extra={
                    "user_id": self.state.user_id,
                    "old_level": old_level.value,
                    "new_level": self.state.verification_level.value,
                    "score": self.state.trust_score,
                }
            )
            
            # TODO: Send notification activity
            # await workflow.execute_activity(
            #     send_level_change_notification,
            #     args=[self.state.user_id, old_level, self.state.verification_level, self.state.trust_score],
            #     start_to_close_timeout=timedelta(seconds=30)
            # )
