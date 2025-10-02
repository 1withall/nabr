"""
Authentication routes for the Nābr API.

Provides endpoints for:
- User registration (all user types: individual, business, organization)
- UN/PIN authentication (username + 6-digit PIN)
- User login (JWT authentication)
- Token refresh
- Current user information
"""

import json
from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from temporalio.client import Client as TemporalClient

from nabr.core.config import get_settings
from nabr.core.security import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
    verify_password,
    decode_token,
)
from nabr.db.session import get_db
from nabr.models.user import User, UserType, IndividualProfile, BusinessProfile, OrganizationProfile
from nabr.api.dependencies.temporal import get_temporal_client

from nabr.api.dependencies.auth import get_current_user
from nabr.schemas.auth import (
    LoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
    Token,
    # UN/PIN authentication schemas
    PINLoginRequest,
    PINLoginResponse,
    PINLoginError,
    SignupRequest,
    SignupResponse,
)
from nabr.schemas.user import UserRead, UserResponse
from nabr.temporal.workflows.signup import SignupWorkflow
from nabr.temporal.activities.auth_activities import (
    ValidatePINLoginInput,
    validate_pin_login,
)

settings = get_settings()
router = APIRouter()


@router.post("/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: RegisterRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserResponse:
    """Register a new user account.
    
    Creates a new user with the specified type (individual, business, or organization).
    Each user type gets a corresponding profile with unique fields and workflows.
    
    Args:
        user_data: Registration details including email, password, and user type
        db: Database session
        
    Returns:
        UserResponse: The created user information
        
    Raises:
        HTTPException: 400 if email already exists
    """
    # Check if email already exists
    result = await db.execute(
        select(User).where(User.email == user_data.email)
    )
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    
    # Validate password length
    if len(user_data.password) < settings.password_min_length:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Password must be at least {settings.password_min_length} characters",
        )
    
    # Create new user
    new_user = User(
        email=user_data.email,
        username=user_data.email.split('@')[0],  # Generate username from email
        hashed_password=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        phone_number=user_data.phone_number,
        user_type=user_data.user_type,
        is_active=True,
        is_verified=False,
    )
    
    db.add(new_user)
    await db.flush()  # Flush to get the user ID
    
    # Create user-type-specific profile
    if user_data.user_type == UserType.INDIVIDUAL:
        profile = IndividualProfile(
            user_id=new_user.id,
            skills=json.dumps([]),
            interests=json.dumps([]),
            max_distance_km=25.0,
        )
        db.add(profile)
    elif user_data.user_type == UserType.BUSINESS:
        profile = BusinessProfile(
            user_id=new_user.id,
            business_name=user_data.full_name,  # Use full_name as business name initially
            services_offered=json.dumps([]),
            resources_available=json.dumps([]),
        )
        db.add(profile)
    elif user_data.user_type == UserType.ORGANIZATION:
        profile = OrganizationProfile(
            user_id=new_user.id,
            organization_name=user_data.full_name,  # Use full_name as org name initially
            programs_offered=json.dumps([]),
            service_areas=json.dumps([]),
        )
        db.add(profile)
    
    await db.commit()
    await db.refresh(new_user)
    
    return UserResponse(
        success=True,
        user=UserRead.model_validate(new_user),
    )


@router.post("/auth/login", response_model=Token)
async def login(
    credentials: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Token:
    """Authenticate user and return access/refresh tokens.
    
    Args:
        credentials: Login credentials (email and password)
        db: Database session
        
    Returns:
        Token: Access and refresh tokens
        
    Raises:
        HTTPException: 401 if credentials are invalid
    """
    # Find user by email
    result = await db.execute(
        select(User).where(User.email == credentials.email)
    )
    user = result.scalar_one_or_none()
    
    # Verify user exists and password is correct
    if not user or not verify_password(credentials.password, str(user.hashed_password)):  # type: ignore
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:  # type: ignore
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )
    
    # Create tokens
    access_token = create_access_token(
        subject=str(user.id),
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )
    refresh_token = create_refresh_token(subject=str(user.id))
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/auth/refresh", response_model=Token)
async def refresh_token(
    token_data: RefreshTokenRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Token:
    """Refresh access token using refresh token.
    
    Args:
        token_data: Refresh token
        db: Database session
        
    Returns:
        Token: New access and refresh tokens
        
    Raises:
        HTTPException: 401 if refresh token is invalid
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Decode refresh token
        payload = decode_token(token_data.refresh_token)
        
        # Verify token type
        token_type = payload.get("type")
        if token_type != "refresh":
            raise credentials_exception
        
        # Extract user ID
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise credentials_exception
            
    except Exception:
        raise credentials_exception
    
    # Verify user exists
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user or not user.is_active:  # type: ignore
        raise credentials_exception
    
    # Create new tokens
    access_token = create_access_token(
        subject=user_id,
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )
    new_refresh_token = create_refresh_token(subject=user_id)
    
    return Token(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.get("/auth/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserResponse:
    """Get current authenticated user information.
    
    Args:
        current_user: The authenticated user from JWT token
        
    Returns:
        UserResponse: Current user information
    """
    return UserResponse(
        success=True,
        user=UserRead.model_validate(current_user),
    )


# ========================
# UN/PIN Authentication Endpoints
# ========================


@router.post("/auth/signup", response_model=SignupResponse, status_code=status.HTTP_201_CREATED)
async def signup_with_pin(
    signup_data: SignupRequest,
    temporal_client: Annotated[TemporalClient, Depends(get_temporal_client)],
    db: Annotated[AsyncSession, Depends(get_db)],
    background_tasks: BackgroundTasks,
) -> SignupResponse:
    """
    Register a new user with UN/PIN authentication.
    
    This endpoint accepts type-specific signup data (INDIVIDUAL, BUSINESS, or ORGANIZATION)
    and initiates a Temporal SignupWorkflow to handle the complete registration process.
    
    The workflow will:
    1. Create user account with username as primary identifier
    2. Hash and store PIN using Argon2
    3. Create user type-specific profile
    4. Initialize verification level at TIER_0_UNVERIFIED
    5. Generate session tokens for immediate login
    6. Send optional welcome message (if email/phone provided)
    7. Record signup event for analytics
    8. Start verification workflow as child workflow
    
    Args:
        signup_data: Discriminated union (IndividualSignupData | BusinessSignupData | OrganizationSignupData)
        temporal_client: Temporal client for workflow execution
        db: Database session (for validation)
        background_tasks: FastAPI background tasks
        
    Returns:
        SignupResponse: User info, tokens, verification level, next steps
        
    Raises:
        HTTPException: 400 if username already exists or PIN mismatch
        HTTPException: 500 if workflow fails
    """
    # Validate PIN confirmation
    if signup_data.pin != signup_data.pin_confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PIN and confirmation PIN do not match",
        )
    
    # Check if username already exists
    result = await db.execute(
        select(User).where(User.username == signup_data.username)
    )
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Username '{signup_data.username}' is already taken",
        )
    
    # Check if email already exists (if provided)
    if signup_data.email:
        result = await db.execute(
            select(User).where(User.email == signup_data.email)
        )
        existing_email = result.scalar_one_or_none()
        
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Email '{signup_data.email}' is already registered",
            )
    
    # Prepare profile data based on user type
    profile_data = {}
    if signup_data.user_type == "INDIVIDUAL":
        profile_data = {
            "date_of_birth": signup_data.date_of_birth.isoformat() if hasattr(signup_data, 'date_of_birth') else None,
            "city": getattr(signup_data, "city", None),
            "state": getattr(signup_data, "state", None),
            "bio": getattr(signup_data, "bio", None),
            "skills": getattr(signup_data, "skills", []),
            "interests": getattr(signup_data, "interests", []),
            "languages": getattr(signup_data, "languages", []),
            "availability": getattr(signup_data, "availability", None),
        }
    elif signup_data.user_type == "BUSINESS":
        profile_data = {
            "business_name": getattr(signup_data, "business_name"),
            "business_type": getattr(signup_data, "business_type"),
            "street_address": getattr(signup_data, "street_address"),
            "city": getattr(signup_data, "city"),
            "state": getattr(signup_data, "state"),
            "zip_code": getattr(signup_data, "zip_code"),
            "website": getattr(signup_data, "website", None),
            "tax_id": getattr(signup_data, "tax_id", None),
            "services": getattr(signup_data, "services", []),
            "business_hours": getattr(signup_data, "business_hours", None),
        }
    elif signup_data.user_type == "ORGANIZATION":
        profile_data = {
            "organization_name": getattr(signup_data, "organization_name"),
            "organization_type": getattr(signup_data, "organization_type"),
            "mission_statement": getattr(signup_data, "mission_statement"),
            "street_address": getattr(signup_data, "street_address"),
            "city": getattr(signup_data, "city"),
            "state": getattr(signup_data, "state"),
            "zip_code": getattr(signup_data, "zip_code"),
            "website": getattr(signup_data, "website", None),
            "tax_id": getattr(signup_data, "tax_id", None),
            "programs": getattr(signup_data, "programs", []),
            "staff_count": getattr(signup_data, "staff_count", None),
            "is_501c3": getattr(signup_data, "is_501c3", False),
        }
    
    # Generate unique workflow ID
    workflow_id = f"signup_{signup_data.username}_{int(timedelta(seconds=1).total_seconds())}"
    
    try:
        # Start SignupWorkflow
        workflow_handle = await temporal_client.start_workflow(
            SignupWorkflow.run,
            args=[
                signup_data.username,
                signup_data.pin,
                signup_data.full_name,
                signup_data.user_type,
                profile_data,
                signup_data.email,
                signup_data.phone,
                None,  # kiosk_id (None for web signup)
                None,  # location (could be populated from request headers)
            ],
            id=workflow_id,
            task_queue="auth-tasks",
        )
        
        # Wait for workflow result (with timeout)
        result = await workflow_handle.result()
        
        # Return signup response
        return SignupResponse(**result)
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Signup workflow failed: {str(e)}",
        )


@router.post("/auth/login/pin", response_model=PINLoginResponse)
async def login_with_pin(
    login_data: PINLoginRequest,
    temporal_client: Annotated[TemporalClient, Depends(get_temporal_client)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PINLoginResponse:
    """
    Authenticate user with UN/PIN (Username + 6-digit PIN).
    
    This endpoint validates the username and PIN, with built-in security features:
    - Rate limiting: 5 attempts per 15 minutes
    - Account lockout: 30 minutes after 5 failed attempts
    - Timing attack protection: Random delay for invalid usernames
    
    Args:
        login_data: Username, PIN, and optional kiosk_id
        temporal_client: Temporal client for activity execution
        db: Database session
        
    Returns:
        PINLoginResponse: User info, tokens, session details
        
    Raises:
        HTTPException: 401 for invalid credentials
        HTTPException: 423 for locked accounts
        HTTPException: 429 for rate limit exceeded
    """
    # Execute validate_pin_login activity
    try:
        # For now, we'll call the activity directly
        # TODO: Consider running as a workflow for better observability
        from nabr.temporal.activities.auth_activities import validate_pin_login
        
        login_result = await validate_pin_login(
            ValidatePINLoginInput(
                username=login_data.username,
                pin=login_data.pin,
                kiosk_id=login_data.kiosk_id,
                ip_address=None,  # TODO: Extract from request
                user_agent=None,  # TODO: Extract from request headers
            )
        )
        
        if not login_result["success"]:
            error_code = login_result["error_code"]
            
            if error_code == "ACCOUNT_LOCKED":
                raise HTTPException(
                    status_code=status.HTTP_423_LOCKED,
                    detail=login_result["error_message"],
                    headers={
                        "X-Locked-Until": login_result["locked_until"] or "",
                    },
                )
            elif error_code == "INVALID_CREDENTIALS":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=login_result["error_message"],
                    headers={
                        "X-Attempts-Remaining": str(login_result.get("attempts_remaining", "")),
                    },
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=login_result["error_message"],
                )
        
        # Get user details
        result = await db.execute(
            select(User).where(User.id == login_result["user_id"])
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        
        # Create session tokens using create_session activity
        from nabr.temporal.activities.auth_activities import create_session, CreateSessionInput
        
        session_result = await create_session(
            CreateSessionInput(
                user_id=str(user.id),
                auth_method_id="",  # TODO: Get from login_result
                kiosk_id=login_data.kiosk_id,
                location=None,  # TODO: Extract from request
            )
        )
        
        # Get verification level
        from nabr.models.verification import UserVerificationLevel
        from nabr.schemas.auth import AuthTokens
        from datetime import datetime
        
        result = await db.execute(
            select(UserVerificationLevel).where(UserVerificationLevel.user_id == user.id)
        )
        verification_level = result.scalar_one_or_none()
        
        # Parse session_expires_at if it's a string
        session_expires_at = session_result.get("session_expires_at")
        session_expires_at_dt = None
        if session_expires_at and isinstance(session_expires_at, str):
            session_expires_at_dt = datetime.fromisoformat(session_expires_at)
        elif isinstance(session_expires_at, datetime):
            session_expires_at_dt = session_expires_at
        
        return PINLoginResponse(
            user_id=str(user.id),
            username=str(user.username),  # type: ignore
            user_type=user.user_type.value,  # type: ignore
            full_name=str(user.full_name),  # type: ignore
            verification_level=str(verification_level.current_level) if verification_level else "TIER_0_UNVERIFIED",  # type: ignore
            tokens=AuthTokens(
                access_token=session_result["access_token"],
                refresh_token=session_result["refresh_token"],
                token_type=session_result.get("token_type", "bearer"),
                expires_in=session_result["expires_in"],
            ),
            session_id=session_result.get("session_id"),
            session_expires_at=session_expires_at_dt,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}",
        )

