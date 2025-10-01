"""Authentication routes for user registration, login, and token management.

This module provides endpoints for:
- User registration (both requesters and volunteers)
- Login with email/password
- Token refresh
- Current user information
"""

import json

from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nabr.api.dependencies.auth import get_current_user
from nabr.core.config import get_settings
from nabr.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from nabr.db.session import get_db
from nabr.models.user import User, UserType, VolunteerProfile
from nabr.schemas.auth import (
    LoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
    Token,
)
from nabr.schemas.user import UserRead, UserResponse

settings = get_settings()
router = APIRouter()


@router.post("/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: RegisterRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserResponse:
    """Register a new user account.
    
    Creates a new user with the specified type (requester or volunteer).
    For volunteers, also creates an empty VolunteerProfile.
    
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
    
    # If volunteer, create empty profile
    if user_data.user_type == UserType.VOLUNTEER:
        volunteer_profile = VolunteerProfile(
            user_id=new_user.id,
            skills=json.dumps([]),  # Store as JSON string
            certifications=json.dumps([]),  # Store as JSON string
            max_distance_km=10.0,
        )
        db.add(volunteer_profile)
    
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
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
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
    
    if not user or not user.is_active:
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
