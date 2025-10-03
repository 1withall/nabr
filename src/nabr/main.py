"""Nābr FastAPI Application.

This is the main application entry point for the Nābr platform.
It configures the FastAPI app with:
- CORS middleware
- API routers
- Exception handlers
- Lifespan events for startup/shutdown
- Health check endpoints
"""

from contextlib import asynccontextmanager
from typing import Any, Union

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from nabr.api.routes import auth, verification
from nabr.core.config import get_settings
from nabr.db.session import engine
from nabr.schemas.base import ErrorResponse

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events.
    
    Handles startup and shutdown tasks:
    - Database connection initialization
    - Temporal client connection (future)
    - Resource cleanup on shutdown
    """
    # Startup
    try:
        # Test database connection
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        print("✅ Database connection successful")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        raise
    
    yield
    
    # Shutdown
    await engine.dispose()
    print("✅ Database connections closed")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Nābr - Mutual aid and community support platform",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_hosts,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception Handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Handle validation errors with structured response."""
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(x) for x in error["loc"][1:]),
            "message": error["msg"],
            "type": error["type"],
        })
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "message": "Validation error",
            "errors": errors,
        },
    )


@app.exception_handler(SQLAlchemyError)
async def database_exception_handler(
    request: Request,
    exc: SQLAlchemyError,
) -> JSONResponse:
    """Handle database errors."""
    # Log the error for debugging (in production, use proper logging)
    print(f"Database error: {exc}")
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "message": "Database error occurred",
            "error": "An internal database error occurred. Please try again later.",
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Handle general exceptions."""
    # Log the error for debugging (in production, use proper logging)
    print(f"Unhandled error: {exc}")
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "message": "Internal server error",
            "error": str(exc) if settings.debug else "An unexpected error occurred",
        },
    )


# Health Check Endpoints
@app.get("/health", tags=["Health"])
async def health_check() -> dict[str, Any]:
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
    }


@app.get("/health/ready", tags=["Health"], response_model=None)
async def readiness_check() -> Union[dict[str, Any], JSONResponse]:
    """Readiness check - verifies database connectivity."""
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        return {
            "status": "ready",
            "database": "connected",
        }
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "not_ready",
                "database": "disconnected",
                "error": str(e) if settings.debug else "Database connection failed",
            },
        )


# API Router Registration
app.include_router(
    auth.router,
    prefix=settings.api_v1_prefix,
    tags=["Authentication"],
)

app.include_router(
    verification.router,
    prefix=settings.api_v1_prefix,
    tags=["Verification"],
)

# Additional routers will be added here:
# app.include_router(users.router, prefix=settings.api_v1_prefix, tags=["Users"])
# app.include_router(requests.router, prefix=settings.api_v1_prefix, tags=["Requests"])
# app.include_router(reviews.router, prefix=settings.api_v1_prefix, tags=["Reviews"])


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "nabr.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
    )
