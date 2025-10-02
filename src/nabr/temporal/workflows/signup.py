"""
Signup Workflow for UN/PIN Authentication.

Implements a long-running, durable workflow for user registration with:
- Type-specific profile creation
- PIN authentication setup
- Automatic verification journey initiation
- Saga pattern for rollback on failure
"""

from datetime import timedelta
from typing import Optional
from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ApplicationError

# Import activity interfaces
with workflow.unsafe.imports_passed_through():
    from nabr.temporal.activities.auth_activities import (
        CreateUserAccountInput,
        CreateUserAccountResult,
        CreatePINAuthMethodInput,
        CreatePINAuthMethodResult,
        CreateProfileInput,
        CreateProfileResult,
        InitializeVerificationLevelInput,
        InitializeVerificationLevelResult,
        CreateSessionInput,
        CreateSessionResult,
        SendWelcomeMessageInput,
        RecordSignupEventInput,
        # Compensation activities
        DeleteUserAccountInput,
        DeactivateAuthMethodInput,
        DeleteProfileInput,
    )
    from nabr.temporal.workflows.verification.identity_verification import (
        IdentityVerificationWorkflow,
        IdentityVerificationInput,
    )


@workflow.defn
class SignupWorkflow:
    """
    User signup workflow with saga pattern for rollback.
    
    This workflow orchestrates the complete user registration process:
    1. Create user account
    2. Create PIN authentication method
    3. Create user type-specific profile
    4. Initialize verification level (TIER_0_UNVERIFIED)
    5. Create session for immediate login
    6. Send welcome message (if contact info provided)
    7. Record signup event for analytics
    8. Start verification workflow as child workflow
    
    On failure at any step, compensation activities rollback previous work.
    """
    
    def __init__(self) -> None:
        self._user_id: Optional[str] = None
        self._auth_method_id: Optional[str] = None
        self._profile_id: Optional[str] = None
        self._verification_level_id: Optional[str] = None
        self._session_token: Optional[str] = None
    
    @workflow.run
    async def run(
        self,
        username: str,
        pin: str,
        full_name: str,
        user_type: str,
        profile_data: dict,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        kiosk_id: Optional[str] = None,
        location: Optional[dict] = None,
    ) -> dict:
        """
        Execute signup workflow with saga compensation.
        
        Args:
            username: Unique username (3-20 chars)
            pin: 6-digit PIN (already validated by schema)
            full_name: User's full name
            user_type: INDIVIDUAL, BUSINESS, or ORGANIZATION
            profile_data: Type-specific profile fields
            email: Optional email address
            phone: Optional phone number
            kiosk_id: Optional kiosk identifier (for shared device login)
            location: Optional location data (IP, city, state)
        
        Returns:
            Dict with user_id, username, tokens, verification_level, workflow_id
        
        Raises:
            ApplicationError: If signup fails after retries and compensation
        """
        
        # Standard retry policy: 3 attempts with exponential backoff
        standard_retry = RetryPolicy(
            initial_interval=timedelta(seconds=1),
            maximum_interval=timedelta(seconds=10),
            maximum_attempts=3,
            backoff_coefficient=2.0,
        )
        
        try:
            # Step 1: Create user account
            workflow.logger.info(f"Creating user account for username: {username}")
            user_result: CreateUserAccountResult = await workflow.execute_activity(
                "create_user_account",
                CreateUserAccountInput(
                    username=username,
                    full_name=full_name,
                    user_type=user_type,
                    email=email,
                    phone=phone,
                ),
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=standard_retry,
            )
            self._user_id = user_result["user_id"]
            workflow.logger.info(f"User account created: {self._user_id}")
            
            # Step 2: Create PIN authentication method
            workflow.logger.info(f"Creating PIN auth method for user: {self._user_id}")
            auth_result: CreatePINAuthMethodResult = await workflow.execute_activity(
                "create_pin_auth_method",
                CreatePINAuthMethodInput(
                    user_id=self._user_id,
                    pin=pin,
                    is_primary=True,
                ),
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=standard_retry,
            )
            self._auth_method_id = auth_result["auth_method_id"]
            workflow.logger.info(f"PIN auth method created: {self._auth_method_id}")
            
            # Step 3: Create user type-specific profile
            workflow.logger.info(f"Creating {user_type} profile for user: {self._user_id}")
            profile_result: CreateProfileResult = await workflow.execute_activity(
                "create_user_profile",
                CreateProfileInput(
                    user_id=self._user_id,
                    user_type=user_type,
                    profile_data=profile_data,
                ),
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=standard_retry,
            )
            self._profile_id = profile_result["profile_id"]
            workflow.logger.info(f"Profile created: {self._profile_id}")
            
            # Step 4: Initialize verification level
            workflow.logger.info(f"Initializing verification level for user: {self._user_id}")
            verification_result: InitializeVerificationLevelResult = await workflow.execute_activity(
                "initialize_verification_level",
                InitializeVerificationLevelInput(
                    user_id=self._user_id,
                    user_type=user_type,
                ),
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=standard_retry,
            )
            self._verification_level_id = verification_result["verification_level_id"]
            workflow.logger.info(
                f"Verification level initialized: {verification_result['current_level']}"
            )
            
            # Step 5: Create session for immediate login
            workflow.logger.info(f"Creating session for user: {self._user_id}")
            session_result: CreateSessionResult = await workflow.execute_activity(
                "create_session",
                CreateSessionInput(
                    user_id=self._user_id,
                    auth_method_id=self._auth_method_id,
                    kiosk_id=kiosk_id,
                    location=location,
                ),
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=standard_retry,
            )
            self._session_token = session_result["session_token"]
            workflow.logger.info("Session created successfully")
            
            # Step 6: Send welcome message (optional, non-critical)
            if email or phone:
                workflow.logger.info(f"Sending welcome message to user: {self._user_id}")
                try:
                    await workflow.execute_activity(
                        "send_welcome_message",
                        SendWelcomeMessageInput(
                            user_id=self._user_id,
                            contact_method="email" if email else "sms",
                            recipient=email or phone,
                            username=username,
                        ),
                        start_to_close_timeout=timedelta(seconds=60),
                        retry_policy=RetryPolicy(maximum_attempts=2),  # Less critical
                    )
                    workflow.logger.info("Welcome message sent")
                except Exception as e:
                    # Non-critical failure - log and continue
                    workflow.logger.warning(f"Failed to send welcome message: {e}")
            
            # Step 7: Record signup event (fire-and-forget for analytics)
            workflow.logger.info(f"Recording signup event for user: {self._user_id}")
            try:
                await workflow.execute_activity(
                    "record_signup_event",
                    RecordSignupEventInput(
                        user_id=self._user_id,
                        username=username,
                        user_type=user_type,
                        signup_method="PIN",
                        location=location,
                        kiosk_id=kiosk_id,
                    ),
                    start_to_close_timeout=timedelta(seconds=30),
                    retry_policy=RetryPolicy(maximum_attempts=2),  # Less critical
                )
            except Exception as e:
                # Non-critical failure - log and continue
                workflow.logger.warning(f"Failed to record signup event: {e}")
            
            # Step 8: Start verification workflow as child workflow
            workflow.logger.info(f"Starting verification workflow for user: {self._user_id}")
            verification_workflow_id = f"verification_{self._user_id}_{workflow.info().workflow_id}"
            
            # Start child workflow (non-blocking)
            await workflow.start_child_workflow(
                IdentityVerificationWorkflow.run,
                IdentityVerificationInput(
                    user_id=self._user_id,
                    user_type=user_type,
                    current_level="TIER_0_UNVERIFIED",
                    target_level="TIER_1_IDENTITY",
                ),
                id=verification_workflow_id,
                task_queue="verification-tasks",
            )
            workflow.logger.info(f"Verification workflow started: {verification_workflow_id}")
            
            # Return success response
            return {
                "user_id": self._user_id,
                "username": username,
                "user_type": user_type,
                "full_name": full_name,
                "verification_level": verification_result["current_level"],
                "tokens": {
                    "access_token": session_result["access_token"],
                    "refresh_token": session_result["refresh_token"],
                    "token_type": "bearer",
                    "expires_in": session_result["expires_in"],
                },
                "session_id": session_result.get("session_id"),
                "session_expires_at": session_result.get("session_expires_at"),
                "workflow_id": workflow.info().workflow_id,
                "verification_workflow_id": verification_workflow_id,
                "next_steps": self._get_next_steps(user_type),
            }
        
        except Exception as e:
            # Saga compensation: Rollback all created resources
            workflow.logger.error(f"Signup failed, starting compensation: {e}")
            await self._compensate()
            raise ApplicationError(
                f"Signup failed: {str(e)}",
                non_retryable=True,  # Don't retry after compensation
            )
    
    async def _compensate(self) -> None:
        """
        Saga compensation: Rollback created resources in reverse order.
        
        This ensures cleanup even if workflow fails midway through execution.
        """
        workflow.logger.info("Starting saga compensation")
        
        # Compensation activities have shorter timeouts and fewer retries
        compensation_retry = RetryPolicy(
            initial_interval=timedelta(seconds=1),
            maximum_interval=timedelta(seconds=5),
            maximum_attempts=2,
        )
        
        # Delete profile (if created)
        if self._profile_id:
            try:
                workflow.logger.info(f"Compensating: Deleting profile {self._profile_id}")
                await workflow.execute_activity(
                    "delete_user_profile",
                    DeleteProfileInput(profile_id=self._profile_id),
                    start_to_close_timeout=timedelta(seconds=15),
                    retry_policy=compensation_retry,
                )
            except Exception as e:
                workflow.logger.error(f"Compensation failed for profile: {e}")
        
        # Deactivate auth method (if created)
        if self._auth_method_id:
            try:
                workflow.logger.info(f"Compensating: Deactivating auth method {self._auth_method_id}")
                await workflow.execute_activity(
                    "deactivate_auth_method",
                    DeactivateAuthMethodInput(auth_method_id=self._auth_method_id),
                    start_to_close_timeout=timedelta(seconds=15),
                    retry_policy=compensation_retry,
                )
            except Exception as e:
                workflow.logger.error(f"Compensation failed for auth method: {e}")
        
        # Delete user account (if created)
        if self._user_id:
            try:
                workflow.logger.info(f"Compensating: Deleting user account {self._user_id}")
                await workflow.execute_activity(
                    "delete_user_account",
                    DeleteUserAccountInput(user_id=self._user_id),
                    start_to_close_timeout=timedelta(seconds=15),
                    retry_policy=compensation_retry,
                )
            except Exception as e:
                workflow.logger.error(f"Compensation failed for user account: {e}")
        
        workflow.logger.info("Saga compensation completed")
    
    def _get_next_steps(self, user_type: str) -> list[str]:
        """Get user type-specific next steps."""
        if user_type == "INDIVIDUAL":
            return [
                "Complete your profile with skills and interests",
                "Start identity verification to unlock more features",
                "Browse community requests that match your skills",
            ]
        elif user_type == "BUSINESS":
            return [
                "Add business details and upload verification documents",
                "Complete business verification to gain trusted status",
                "Post your first resource offering",
            ]
        elif user_type == "ORGANIZATION":
            return [
                "Complete organization profile and upload IRS 501(c)(3) documentation",
                "Complete organization verification to coordinate volunteers",
                "Create your first community program",
            ]
        return ["Complete your profile", "Start verification"]
    
    @workflow.signal
    async def cancel_signup(self) -> None:
        """
        Signal to cancel signup workflow.
        
        Triggers compensation to rollback created resources.
        """
        workflow.logger.info("Signup cancellation requested")
        await self._compensate()
        raise ApplicationError("Signup cancelled by user", non_retryable=True)
    
    @workflow.query
    def get_status(self) -> dict:
        """Query current signup status."""
        return {
            "user_id": self._user_id,
            "auth_method_id": self._auth_method_id,
            "profile_id": self._profile_id,
            "verification_level_id": self._verification_level_id,
            "session_token": "***" if self._session_token else None,
        }
