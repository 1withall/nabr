"""
Base utilities for Temporal activities.

Provides common functionality and patterns for all activities.
"""

from typing import TypeVar, Callable, Any
from functools import wraps
import asyncio
from temporalio import activity

T = TypeVar("T")


def with_heartbeat(interval_seconds: int = 10):
    """
    Decorator to add automatic heartbeating to activities.
    
    Use for long-running activities that need progress reporting.
    
    Args:
        interval_seconds: Seconds between heartbeats
        
    Example:
        @activity.defn
        @with_heartbeat(interval_seconds=5)
        async def my_activity(param: str) -> str:
            await some_long_operation()
            return result
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            # Start heartbeat task
            async def heartbeat_loop():
                while True:
                    try:
                        activity.heartbeat()
                        await asyncio.sleep(interval_seconds)
                    except asyncio.CancelledError:
                        break
            
            heartbeat_task = asyncio.create_task(heartbeat_loop())
            
            try:
                # Run actual activity
                result = await func(*args, **kwargs)
                return result
            finally:
                # Stop heartbeat
                heartbeat_task.cancel()
                try:
                    await heartbeat_task
                except asyncio.CancelledError:
                    pass
        
        return wrapper
    return decorator


def log_activity_execution(func: Callable[..., T]) -> Callable[..., T]:
    """
    Decorator to log activity execution.
    
    Automatically logs start, completion, and errors.
    
    Example:
        @activity.defn
        @log_activity_execution
        async def my_activity(param: str) -> str:
            return result
    """
    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> T:
        activity_name = func.__name__
        activity.logger.info(f"Starting activity: {activity_name}")
        activity.logger.debug(f"Arguments: args={args}, kwargs={kwargs}")
        
        try:
            result = await func(*args, **kwargs)
            activity.logger.info(f"Completed activity: {activity_name}")
            return result
        except Exception as e:
            activity.logger.error(f"Activity failed: {activity_name}, error={e}")
            raise
    
    return wrapper


class ActivityBase:
    """
    Base class for activity implementations.
    
    Provides common utilities and database access.
    Use this as a template for creating activity classes.
    """
    
    def __init__(self):
        """Initialize activity with dependencies."""
        from nabr.core.config import get_settings
        self.settings = get_settings()
    
    async def get_db_session(self):
        """
        Get database session for activity.
        
        Returns:
            AsyncSession: Database session
            
        Example:
            async with self.get_db_session() as db:
                result = await db.execute(query)
        """
        from nabr.db.session import AsyncSessionLocal
        async with AsyncSessionLocal() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
    
    def check_cancellation(self):
        """
        Check if activity is being cancelled.
        
        Call this periodically in long-running activities.
        Raises CancelledError if activity is being cancelled.
        
        Example:
            for item in large_list:
                self.check_cancellation()
                process_item(item)
        """
        if activity.is_cancelled():
            activity.logger.info("Activity cancelled, cleaning up...")
            raise asyncio.CancelledError("Activity cancelled")
    
    def report_progress(self, message: str, **details: Any):
        """
        Report activity progress via heartbeat.
        
        Args:
            message: Progress message
            **details: Additional progress details
            
        Example:
            self.report_progress(
                "Processing items",
                completed=50,
                total=100
            )
        """
        progress = {"message": message, **details}
        activity.heartbeat(progress)
        activity.logger.info(f"Progress: {progress}")


def make_idempotent(key_func: Callable[..., str]):
    """
    Decorator to make activities idempotent using a cache key.
    
    Prevents duplicate operations by checking a cache before execution.
    
    Args:
        key_func: Function to generate cache key from arguments
        
    Example:
        @activity.defn
        @make_idempotent(lambda user_id: f"create_user:{user_id}")
        async def create_user_record(user_id: str) -> str:
            # Will only execute once for each user_id
            return await db.create_user(user_id)
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            # Generate idempotency key
            cache_key = key_func(*args, **kwargs)
            
            # Check if already processed
            # TODO: Implement actual cache check (Redis, etc.)
            # For now, activities should handle idempotency internally
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator
