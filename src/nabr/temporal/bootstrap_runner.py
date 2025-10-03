"""
Bootstrap workflow executor.

This module provides a simple way to run the system bootstrap workflow
from the command line or startup script.
"""

import asyncio
import logging
from temporalio.client import Client
from nabr.core.config import get_settings
from nabr.temporal.workflows.bootstrap import SystemBootstrapWorkflow

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

settings = get_settings()


async def run_bootstrap() -> dict:
    """
    Execute the bootstrap workflow.
    
    Returns:
        Dictionary with bootstrap results
    """
    logger.info("Connecting to Temporal server...")
    
    # Connect to Temporal
    client = await Client.connect(
        settings.temporal_host,
        namespace=settings.temporal_namespace,
    )
    
    logger.info(f"Connected to Temporal at {settings.temporal_host}")
    
    # Execute bootstrap workflow
    workflow_id = "system-bootstrap"
    
    try:
        logger.info(f"Starting bootstrap workflow: {workflow_id}")
        
        result = await client.execute_workflow(
            SystemBootstrapWorkflow.run,
            id=workflow_id,
            task_queue="bootstrap-queue",
            execution_timeout=timedelta(minutes=10),
        )
        
        logger.info("Bootstrap workflow completed successfully")
        logger.info(f"Result: {result}")
        
        return result
        
    except Exception as e:
        logger.error(f"Bootstrap workflow failed: {e}", exc_info=True)
        raise


async def main():
    """Main entry point."""
    try:
        result = await run_bootstrap()
        
        if result.get("success"):
            logger.info("✓ System bootstrap completed successfully")
            return 0
        else:
            logger.error("✗ System bootstrap completed with errors")
            logger.error(f"Errors: {result.get('errors', [])}")
            return 1
            
    except Exception as e:
        logger.error(f"✗ Bootstrap failed: {e}")
        return 1


if __name__ == "__main__":
    from datetime import timedelta
    exit_code = asyncio.run(main())
    exit(exit_code)
