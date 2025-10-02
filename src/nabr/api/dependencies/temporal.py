"""
Temporal client dependency for API routes.

Provides a singleton Temporal client for workflow execution and management.
"""

from typing import Optional, AsyncGenerator
from temporalio.client import Client as TemporalClient

from nabr.core.config import get_settings

settings = get_settings()

# Global Temporal client instance (singleton)
_temporal_client: Optional[TemporalClient] = None


async def get_temporal_client() -> AsyncGenerator[TemporalClient, None]:
    """
    Dependency to get Temporal client for API routes.
    
    Creates a singleton client connection to Temporal server.
    Reuses the same connection across requests for efficiency.
    
    Yields:
        TemporalClient: Connected Temporal client
        
    Example:
        @router.post("/start")
        async def start_workflow(
            client: TemporalClient = Depends(get_temporal_client)
        ):
            await client.start_workflow(...)
    """
    global _temporal_client
    
    # Create client if it doesn't exist
    if _temporal_client is None:
        _temporal_client = await TemporalClient.connect(
            settings.temporal_host,
            namespace=settings.temporal_namespace,
        )
    
    yield _temporal_client


async def close_temporal_client():
    """
    Close the Temporal client connection.
    
    Should be called on application shutdown.
    """
    global _temporal_client
    
    if _temporal_client is not None:
        await _temporal_client.close()
        _temporal_client = None
