"""
Bootstrap CLI - Execute system initialization workflow.

This module provides a command-line interface to run the bootstrap workflow
that initializes the system at startup.

Usage:
    python -m nabr.temporal.bootstrap
"""

import asyncio
import logging
import sys
from datetime import timedelta

from temporalio.client import Client
from temporalio.worker import Worker

from nabr.core.config import get_settings
from nabr.temporal.workflows.bootstrap import SystemBootstrapWorkflow
from nabr.temporal.activities import bootstrap as bootstrap_activities

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

settings = get_settings()

# Task queue for bootstrap workflow
BOOTSTRAP_TASK_QUEUE = "bootstrap-queue"


async def run_bootstrap_workflow() -> bool:
    """
    Execute the bootstrap workflow.
    
    Returns:
        True if bootstrap succeeded, False otherwise
    """
    logger.info("Connecting to Temporal server...")
    
    try:
        # Connect to Temporal
        client = await Client.connect(
            settings.temporal_host,
            namespace=settings.temporal_namespace,
        )
        logger.info(f"Connected to Temporal at {settings.temporal_host}")
        
        # Start a worker for the bootstrap workflow
        logger.info("Starting bootstrap worker...")
        
        # Get all bootstrap activities
        activities = [
            bootstrap_activities.run_database_migrations,
            bootstrap_activities.check_database_health,
            bootstrap_activities.validate_database_schema,
            bootstrap_activities.initialize_default_data,
            bootstrap_activities.validate_configuration,
            bootstrap_activities.run_service_health_checks,
        ]
        
        # Create worker
        worker = Worker(
            client,
            task_queue=BOOTSTRAP_TASK_QUEUE,
            workflows=[SystemBootstrapWorkflow],
            activities=activities,
        )
        
        # Start worker in background
        async with worker:
            logger.info("Bootstrap worker started")
            logger.info("Executing bootstrap workflow...")
            
            # Execute the workflow
            result = await client.execute_workflow(
                SystemBootstrapWorkflow.run,
                id="system-bootstrap",
                task_queue=BOOTSTRAP_TASK_QUEUE,
                execution_timeout=timedelta(minutes=10),
            )
            
            # Check result
            if result.get("success"):
                logger.info("✓ Bootstrap workflow completed successfully!")
                logger.info(f"Completed steps: {result.get('completed_steps', [])}")
                
                if result.get("warnings"):
                    logger.warning("Warnings:")
                    for warning in result["warnings"]:
                        logger.warning(f"  • {warning}")
                
                return True
            else:
                logger.error("✗ Bootstrap workflow failed!")
                logger.error(f"Failed at step: {result.get('failed_step')}")
                logger.error(f"Completed steps: {result.get('completed_steps', [])}")
                
                if result.get("errors"):
                    logger.error("Errors:")
                    for error in result["errors"]:
                        logger.error(f"  • {error}")
                
                return False
    
    except Exception as e:
        logger.error(f"Bootstrap failed with exception: {e}", exc_info=True)
        return False


async def main():
    """Main entry point."""
    logger.info("=" * 60)
    logger.info("Nābr System Bootstrap")
    logger.info("=" * 60)
    logger.info("")
    
    success = await run_bootstrap_workflow()
    
    logger.info("")
    logger.info("=" * 60)
    
    if success:
        logger.info("Bootstrap completed successfully ✓")
        logger.info("System is ready to accept requests")
        logger.info("=" * 60)
        sys.exit(0)
    else:
        logger.error("Bootstrap failed ✗")
        logger.error("Check logs above for details")
        logger.error("View workflow in Temporal UI: http://localhost:8080")
        logger.info("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
