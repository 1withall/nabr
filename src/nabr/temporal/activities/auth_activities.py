"""
Authentication Activities for Temporal Workflows.

Implements activities for user signup, PIN authentication, and session management.
All activities follow OWASP security best practices and include proper error handling.
"""

import asyncio
import secrets
from datetime import datetime, timedelta
from typing import Optional, TypedDict
from passlib.hash import argon2
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from temporalio import activity

from nabr.db.session import AsyncSessionLocal
from nabr.models.user import User, UserType
from nabr.models.auth_methods import (
    UserAuthenticationMethod,
    AuthMethodType,
    KioskSession,
)
from nabr.models.user import (
    IndividualProfile,
    BusinessProfile,
    OrganizationProfile,
)
from nabr.models.verification import UserVerificationLevel
from nabr.core.security import create_access_token, create_refresh_token


# ========================
# Activity Input/Output Types
# ========================

class CreateUserAccountInput(TypedDict):
    """Input for create_user_account activity."""
    username: str
    full_name: str
    user_type: str
    email: Optional[str]
    phone: Optional[str]


class CreateUserAccountResult(TypedDict):
    """Output from create_user_account activity."""
    user_id: str
    username: str
    created_at: str


class CreatePINAuthMethodInput(TypedDict):
    """Input for create_pin_auth_method activity."""
    user_id: str
    pin: str
    is_primary: bool


class CreatePINAuthMethodResult(TypedDict):
    """Output from create_pin_auth_method activity."""
    auth_method_id: str
    method_type: str
    created_at: str


class CreateProfileInput(TypedDict):
    """Input for create_user_profile activity."""
    user_id: str
    user_type: str
    profile_data: dict


class CreateProfileResult(TypedDict):
    """Output from create_user_profile activity."""
    profile_id: str
    user_type: str


class InitializeVerificationLevelInput(TypedDict):
    """Input for initialize_verification_level activity."""
    user_id: str
    user_type: str


class InitializeVerificationLevelResult(TypedDict):
    """Output from initialize_verification_level activity."""
    verification_level_id: str
    current_level: str


class CreateSessionInput(TypedDict):
    """Input for create_session activity."""
    user_id: str
    auth_method_id: str
    kiosk_id: Optional[str]
    location: Optional[dict]


class CreateSessionResult(TypedDict):
    """Output from create_session activity."""
    session_token: str
    access_token: str
    refresh_token: str
    expires_in: int
    session_id: Optional[str]
    session_expires_at: Optional[str]


class SendWelcomeMessageInput(TypedDict):
    """Input for send_welcome_message activity."""
    user_id: str
    contact_method: str
    recipient: str
    username: str


class RecordSignupEventInput(TypedDict):
    """Input for record_signup_event activity."""
    user_id: str
    username: str
    user_type: str
    signup_method: str
    location: Optional[dict]
    kiosk_id: Optional[str]


class ValidatePINLoginInput(TypedDict):
    """Input for validate_pin_login activity."""
    username: str
    pin: str
    kiosk_id: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]


class ValidatePINLoginResult(TypedDict):
    """Output from validate_pin_login activity."""
    success: bool
    user_id: Optional[str]
    error_code: Optional[str]
    error_message: Optional[str]
    attempts_remaining: Optional[int]
    locked_until: Optional[str]


# Compensation activity inputs
class DeleteUserAccountInput(TypedDict):
    """Input for delete_user_account compensation activity."""
    user_id: str


class DeactivateAuthMethodInput(TypedDict):
    """Input for deactivate_auth_method compensation activity."""
    auth_method_id: str


class DeleteProfileInput(TypedDict):
    """Input for delete_user_profile compensation activity."""
    profile_id: str


# ========================
# Signup Activities
# ========================

@activity.defn
async def create_user_account(input: CreateUserAccountInput) -> CreateUserAccountResult:
    """
    Create a new user account with UN/PIN authentication.
    
    Args:
        input: User account data
    
    Returns:
        Created user ID and metadata
    
    Raises:
        ValueError: If username already exists
    """
    activity.logger.info(f"Creating user account for username: {input['username']}")
    
    async with AsyncSessionLocal() as db:
        try:
            # Check if username already exists
            result = await db.execute(
                select(User).filter(User.username == input["username"])
            )
            existing_user = result.scalar_one_or_none()
            if existing_user:
                raise ValueError(f"Username '{input['username']}' is already taken")
            
            # Check if email already exists (if provided)
            if input.get("email"):
                result = await db.execute(
                    select(User).filter(User.email == input["email"])
                )
                existing_email = result.scalar_one_or_none()
                if existing_email:
                    raise ValueError(f"Email '{input['email']}' is already registered")
            
            # Create user
            user = User(
                username=input["username"],
                full_name=input["full_name"],
                user_type=UserType[input["user_type"]],
                email=input.get("email"),
                phone_number=input.get("phone"),
                hashed_password=None,  # UN/PIN auth doesn't use password field
                is_active=True,
            )
            
            db.add(user)
            await db.commit()
            await db.refresh(user)
            
            activity.logger.info(f"User account created successfully: {user.id}")
            
            return CreateUserAccountResult(
                user_id=str(user.id),
                username=str(user.username),
                created_at=user.created_at.isoformat(),
            )
        
        except IntegrityError as e:
            await db.rollback()
            activity.logger.error(f"Database integrity error: {e}")
            raise ValueError("Username or email already exists")
        except Exception as e:
            await db.rollback()
            activity.logger.error(f"Failed to create user account: {e}")
            raise


@activity.defn
async def create_pin_auth_method(
    input: CreatePINAuthMethodInput
) -> CreatePINAuthMethodResult:
    """
    Create PIN authentication method with Argon2 hashing.
    
    Args:
        input: PIN auth method data
    
    Returns:
        Created auth method ID and metadata
    """
    activity.logger.info(f"Creating PIN auth method for user: {input['user_id']}")
    
    async with AsyncSessionLocal() as db:
        try:
            # Hash PIN using Argon2 (OWASP recommended)
            hashed_pin = argon2.using(
                time_cost=3,  # Iterations
                memory_cost=65536,  # 64 MB
                parallelism=4,  # Threads
                salt_size=16,
            ).hash(input["pin"])
            
            # Create authentication method
            auth_method = UserAuthenticationMethod(
                user_id=input["user_id"],
                method_type=AuthMethodType.PIN,
                method_identifier=input["user_id"],  # PIN is user-specific
                hashed_secret=hashed_pin,
                is_active=True,
                is_primary=input["is_primary"],
                failed_attempts=0,
            )
            
            db.add(auth_method)
            await db.commit()
            await db.refresh(auth_method)
            
            activity.logger.info(f"PIN auth method created successfully: {auth_method.id}")
            
            return CreatePINAuthMethodResult(
                auth_method_id=str(auth_method.id),
                method_type=auth_method.method_type.value,
                created_at=auth_method.created_at.isoformat(),
            )
        
        except Exception as e:
            await db.rollback()
            activity.logger.error(f"Failed to create PIN auth method: {e}")
            raise


@activity.defn
async def create_user_profile(input: CreateProfileInput) -> CreateProfileResult:
    """
    Create user type-specific profile.
    
    Args:
        input: Profile data with user_type discriminator
    
    Returns:
        Created profile ID
    """
    activity.logger.info(
        f"Creating {input['user_type']} profile for user: {input['user_id']}"
    )
    
    async with AsyncSessionLocal() as db:
        try:
            profile_data = input["profile_data"]
            
            if input["user_type"] == "INDIVIDUAL":
                profile = IndividualProfile(
                    user_id=input["user_id"],
                    date_of_birth=profile_data.get("date_of_birth"),
                    city=profile_data.get("city"),
                    state=profile_data.get("state"),
                    bio=profile_data.get("bio"),
                    skills=profile_data.get("skills", []),
                    interests=profile_data.get("interests", []),
                    languages=profile_data.get("languages", []),
                    availability=profile_data.get("availability"),
                )
            elif input["user_type"] == "BUSINESS":
                profile = BusinessProfile(
                    user_id=input["user_id"],
                    business_name=profile_data["business_name"],
                    business_type=profile_data["business_type"],
                    street_address=profile_data["street_address"],
                    city=profile_data["city"],
                    state=profile_data["state"],
                    zip_code=profile_data["zip_code"],
                    website=profile_data.get("website"),
                    tax_id=profile_data.get("tax_id"),
                    services_offered=profile_data.get("services", []),
                    business_hours=profile_data.get("business_hours"),
                )
            elif input["user_type"] == "ORGANIZATION":
                profile = OrganizationProfile(
                    user_id=input["user_id"],
                    organization_name=profile_data["organization_name"],
                    organization_type=profile_data["organization_type"],
                    mission_statement=profile_data["mission_statement"],
                    street_address=profile_data["street_address"],
                    city=profile_data["city"],
                    state=profile_data["state"],
                    zip_code=profile_data["zip_code"],
                    website=profile_data.get("website"),
                    tax_id=profile_data.get("tax_id"),
                    programs=profile_data.get("programs", []),
                    staff_count=profile_data.get("staff_count"),
                    is_501c3=profile_data.get("is_501c3", False),
                )
            else:
                raise ValueError(f"Unknown user type: {input['user_type']}")
            
            db.add(profile)
            await db.commit()
            await db.refresh(profile)
            
            activity.logger.info(f"Profile created successfully: {profile.id}")
            
            return CreateProfileResult(
                profile_id=str(profile.id),
                user_type=input["user_type"],
            )
        
        except Exception as e:
            await db.rollback()
            activity.logger.error(f"Failed to create profile: {e}")
            raise


@activity.defn
async def initialize_verification_level(
    input: InitializeVerificationLevelInput
) -> InitializeVerificationLevelResult:
    """
    Initialize verification level at TIER_0_UNVERIFIED.
    
    Args:
        input: User ID and type
    
    Returns:
        Created verification level record
    """
    activity.logger.info(f"Initializing verification level for user: {input['user_id']}")
    
    async with AsyncSessionLocal() as db:
        try:
            verification_level = UserVerificationLevel(
                user_id=input["user_id"],
                current_level="TIER_0_UNVERIFIED",
                verification_score=0,
            )
            
            db.add(verification_level)
            await db.commit()
            await db.refresh(verification_level)
            
            activity.logger.info(
                f"Verification level initialized: {str(verification_level.current_level)}"
            )
            
            return InitializeVerificationLevelResult(
                verification_level_id=str(verification_level.id),
                current_level=str(verification_level.current_level),
            )
        
        except Exception as e:
            await db.rollback()
            activity.logger.error(f"Failed to initialize verification level: {e}")
            raise


@activity.defn
async def create_session(input: CreateSessionInput) -> CreateSessionResult:
    """
    Create session and generate JWT tokens for immediate login.
    
    Args:
        input: Session creation data
    
    Returns:
        Session tokens and metadata
    """
    activity.logger.info(f"Creating session for user: {input['user_id']}")
    
    async with AsyncSessionLocal() as db:
        try:
            # Determine session expiry based on device type
            if input.get("kiosk_id"):
                # Kiosk (shared device): 30 minutes
                expires_in = 1800
                expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
            else:
                # Personal device: 7 days
                expires_in = 604800
                expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
            
            # Generate JWT tokens with correct function signatures
            access_token = create_access_token(
                subject=input["user_id"],
                expires_delta=timedelta(seconds=expires_in),
            )
            refresh_token = create_refresh_token(
                subject=input["user_id"],
            )
            
            result = CreateSessionResult(
                session_token=secrets.token_urlsafe(32),
                access_token=access_token,
                refresh_token=refresh_token,
                expires_in=expires_in,
                session_id=None,
                session_expires_at=None,
            )
            
            # Create kiosk session if kiosk_id provided
            if input.get("kiosk_id"):
                location = input.get("location") or {}
                kiosk_session = KioskSession(
                    user_id=input["user_id"],
                    kiosk_id=input["kiosk_id"],
                    location=location.get("city", "Unknown"),
                    session_token=result["session_token"],
                    started_at=datetime.utcnow(),
                    expires_at=expires_at,
                    last_activity_at=datetime.utcnow(),
                    auth_method=AuthMethodType.PIN.value,
                    ip_address=location.get("ip"),
                    user_agent=location.get("user_agent"),
                )
                
                db.add(kiosk_session)
                await db.commit()
                await db.refresh(kiosk_session)
                
                result["session_id"] = str(kiosk_session.id)
                result["session_expires_at"] = kiosk_session.expires_at.isoformat()
                
                activity.logger.info(f"Kiosk session created: {kiosk_session.id}")
            
            return result
        
        except Exception as e:
            await db.rollback()
            activity.logger.error(f"Failed to create session: {e}")
            raise


@activity.defn
async def send_welcome_message(input: SendWelcomeMessageInput) -> bool:
    """
    Send welcome message to new user (email or SMS).
    
    Args:
        input: Recipient and message data
    
    Returns:
        Success status
    """
    activity.logger.info(
        f"Sending welcome {input['contact_method']} to user: {input['user_id']}"
    )
    
    # TODO: Implement email/SMS sending
    # For now, just log
    activity.logger.info(f"Welcome message would be sent to: {input['recipient']}")
    
    return True


@activity.defn
async def record_signup_event(input: RecordSignupEventInput) -> str:
    """
    Record signup event for analytics.
    
    Args:
        input: Event data
    
    Returns:
        Event ID
    """
    activity.logger.info(f"Recording signup event for user: {input['user_id']}")
    
    # TODO: Implement analytics event recording
    # For now, just log
    activity.logger.info(
        f"Signup event: {input['username']} ({input['user_type']}) via {input['signup_method']}"
    )
    
    return f"event_{input['user_id']}"


# ========================
# Authentication Activities
# ========================

@activity.defn
async def validate_pin_login(
    input: ValidatePINLoginInput
) -> ValidatePINLoginResult:
    """
    Validate PIN login with rate limiting and brute force protection.
    
    Args:
        input: Login credentials and metadata
    
    Returns:
        Login result with success status or error details
    """
    activity.logger.info(f"Validating PIN login for username: {input['username']}")
    
    async with AsyncSessionLocal() as db:
        try:
            # Find user by username
            result = await db.execute(
                select(User).filter(User.username == input["username"])
            )
            user = result.scalar_one_or_none()
            
            if not user:
                # Timing attack protection: Random sleep for invalid usernames
                await asyncio.sleep(secrets.randbelow(200) / 1000 + 0.1)  # 0.1-0.3s
                return ValidatePINLoginResult(
                    success=False,
                    user_id=None,
                    error_code="INVALID_CREDENTIALS",
                    error_message="Invalid username or PIN",
                    attempts_remaining=None,
                    locked_until=None,
                )
            
            # Get PIN auth method
            result = await db.execute(
                select(UserAuthenticationMethod)
                .filter(
                    UserAuthenticationMethod.user_id == user.id,
                    UserAuthenticationMethod.method_type == AuthMethodType.PIN,
                    UserAuthenticationMethod.is_active == True,
                )
            )
            auth_method = result.scalar_one_or_none()
            
            if not auth_method:
                return ValidatePINLoginResult(
                    success=False,
                    user_id=None,
                    error_code="NO_AUTH_METHOD",
                    error_message="No PIN authentication method configured",
                    attempts_remaining=None,
                    locked_until=None,
                )
            
            # Check if account is locked
            if auth_method.locked_until and auth_method.locked_until > datetime.utcnow():  # type: ignore
                return ValidatePINLoginResult(
                    success=False,
                    user_id=str(user.id),
                    error_code="ACCOUNT_LOCKED",
                    error_message="Account is temporarily locked due to too many failed attempts",
                    attempts_remaining=0,
                    locked_until=auth_method.locked_until.isoformat(),  # type: ignore
                )
            
            # Reset failed attempts if lock expired
            if auth_method.locked_until and auth_method.locked_until <= datetime.utcnow():  # type: ignore
                auth_method.failed_attempts = 0  # type: ignore
                auth_method.locked_until = None  # type: ignore
            
            # Verify PIN using timing-safe comparison
            pin_valid = argon2.verify(input["pin"], auth_method.hashed_secret)  # type: ignore
            
            if pin_valid:
                # Success: Reset failed attempts
                auth_method.failed_attempts = 0  # type: ignore
                auth_method.locked_until = None  # type: ignore
                auth_method.last_used_at = datetime.utcnow()  # type: ignore
                await db.commit()
                
                activity.logger.info(f"PIN login successful for user: {user.id}")
                
                return ValidatePINLoginResult(
                    success=True,
                    user_id=str(user.id),
                    error_code=None,
                    error_message=None,
                    attempts_remaining=None,
                    locked_until=None,
                )
            else:
                # Failed: Increment failed attempts
                auth_method.failed_attempts += 1  # type: ignore
                attempts_remaining = max(0, 5 - int(auth_method.failed_attempts))  # type: ignore
                
                # Lock account after 5 failed attempts
                if int(auth_method.failed_attempts) >= 5:  # type: ignore
                    auth_method.locked_until = datetime.utcnow() + timedelta(minutes=30)  # type: ignore
                    await db.commit()
                    
                    return ValidatePINLoginResult(
                        success=False,
                        user_id=str(user.id),
                        error_code="ACCOUNT_LOCKED",
                        error_message="Account locked due to too many failed attempts. Try again in 30 minutes.",
                        attempts_remaining=0,
                        locked_until=auth_method.locked_until.isoformat(),  # type: ignore
                    )
                
                await db.commit()
                
                return ValidatePINLoginResult(
                    success=False,
                    user_id=str(user.id),
                    error_code="INVALID_CREDENTIALS",
                    error_message="Invalid username or PIN",
                    attempts_remaining=attempts_remaining,
                    locked_until=None,
                )
        
        except Exception as e:
            await db.rollback()
            activity.logger.error(f"PIN validation failed: {e}")
            raise


# ========================
# Compensation Activities (Saga Pattern)
# ========================

@activity.defn
async def delete_user_account(input: DeleteUserAccountInput) -> bool:
    """
    Compensation: Delete user account if signup fails.
    
    Args:
        input: User ID to delete
    
    Returns:
        Success status
    """
    activity.logger.info(f"Compensating: Deleting user account {input['user_id']}")
    
    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(
                select(User).filter(User.id == input["user_id"])
            )
            user = result.scalar_one_or_none()
            if user:
                await db.delete(user)
                await db.commit()
                activity.logger.info(f"User account deleted: {input['user_id']}")
            return True
        except Exception as e:
            await db.rollback()
            activity.logger.error(f"Failed to delete user account: {e}")
            raise


@activity.defn
async def deactivate_auth_method(input: DeactivateAuthMethodInput) -> bool:
    """
    Compensation: Deactivate auth method if signup fails.
    
    Args:
        input: Auth method ID to deactivate
    
    Returns:
        Success status
    """
    activity.logger.info(
        f"Compensating: Deactivating auth method {input['auth_method_id']}"
    )
    
    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(
                select(UserAuthenticationMethod)
                .filter(UserAuthenticationMethod.id == input["auth_method_id"])
            )
            auth_method = result.scalar_one_or_none()
            if auth_method:
                auth_method.is_active = False  # type: ignore
                auth_method.deactivated_at = datetime.utcnow()  # type: ignore
                await db.commit()
                activity.logger.info(f"Auth method deactivated: {input['auth_method_id']}")
            return True
        except Exception as e:
            await db.rollback()
            activity.logger.error(f"Failed to deactivate auth method: {e}")
            raise


@activity.defn
async def delete_user_profile(input: DeleteProfileInput) -> bool:
    """
    Compensation: Delete user profile if signup fails.
    
    Args:
        input: Profile ID to delete
    
    Returns:
        Success status
    """
    activity.logger.info(f"Compensating: Deleting profile {input['profile_id']}")
    
    async with AsyncSessionLocal() as db:
        try:
            # Try all profile types
            for ProfileModel in [IndividualProfile, BusinessProfile, OrganizationProfile]:
                result = await db.execute(
                    select(ProfileModel).filter(ProfileModel.id == input["profile_id"])
                )
                profile = result.scalar_one_or_none()
                if profile:
                    await db.delete(profile)
                    await db.commit()
                    activity.logger.info(f"Profile deleted: {input['profile_id']}")
                    return True
            
            activity.logger.warning(f"Profile not found: {input['profile_id']}")
            return False
        except Exception as e:
            await db.rollback()
            activity.logger.error(f"Failed to delete profile: {e}")
            raise
