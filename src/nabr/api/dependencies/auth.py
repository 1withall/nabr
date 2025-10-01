"""Authentication dependencies for FastAPI routes.

These dependencies provide user authentication and authorization
for protected endpoints using JWT tokens.
"""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nabr.core.security import decode_token
from nabr.db.session import get_db
from nabr.models.user import User, UserType
from nabr.schemas.user import UserRead

# HTTP Bearer token security scheme
security = HTTPBearer()


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Get the current authenticated user from JWT token.
    
    Args:
        credentials: Bearer token from Authorization header
        db: Database session
        
    Returns:
        User: The authenticated user
        
    Raises:
        HTTPException: 401 if token is invalid or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Decode JWT token
        payload = decode_token(credentials.credentials)
        
        # Verify token type
        token_type = payload.get("type")
        if token_type != "access":
            raise credentials_exception
        
        # Extract user ID
        user_id_str: str | None = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
        
        user_id = UUID(user_id_str)
        
    except (JWTError, ValueError):
        raise credentials_exception
    
    # Fetch user from database
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if user is None:
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )
    
    return user


async def get_current_verified_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Get the current user and verify they have completed verification.
    
    Args:
        current_user: The authenticated user
        
    Returns:
        User: The verified user
        
    Raises:
        HTTPException: 403 if user is not verified
    """
    if not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User verification required. Please complete the verification process.",
        )
    
    return current_user


def require_user_type(*allowed_types: UserType):
    """Create a dependency that requires specific user types.
    
    This is a dependency factory that creates a dependency function
    requiring the user to have one of the specified user types.
    
    Args:
        *allowed_types: UserType values that are allowed
        
    Returns:
        A dependency function that validates user type
        
    Example:
        ```python
        @router.post("/admin-only")
        async def admin_endpoint(
            user: Annotated[User, Depends(require_user_type(UserType.ADMIN))]
        ):
            # Only admins can access this
            pass
        ```
    """
    async def check_user_type(
        current_user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        if current_user.user_type not in allowed_types:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This endpoint requires one of these user types: {', '.join(t.value for t in allowed_types)}",
            )
        return current_user
    
    return check_user_type
