"""
Temporal worker configuration for Nābr.

This module sets up multiple workers for different task queues following Temporal best practices:
- Verification worker: Handles user verification workflows
- Matching worker: Handles request matching workflows  
- Review worker: Handles review submission workflows
- Notification worker: Handles notification activities

Architecture:
- Each worker polls a dedicated task queue
- Workers can be scaled independently (horizontal scaling)
- Thread pool executor for synchronous activities
- Graceful shutdown handling
- Production-ready configuration

Usage:
    # Run all workers:
    python -m nabr.temporal.worker
    
    # Run specific worker:
    python -m nabr.temporal.worker verification
"""

import asyncio
import concurrent.futures
import logging
import signal
from typing import List, Optional

from temporalio.client import Client
from temporalio.worker import Worker

from nabr.core.config import get_settings

# Import workflows
from nabr.temporal.workflows.verification import VerificationWorkflow
from nabr.temporal.workflows.matching import RequestMatchingWorkflow
from nabr.temporal.workflows.review import ReviewWorkflow

# Import activities
# These will be imported when activity implementations are complete
# from nabr.temporal.activities.verification import verification_activities
# from nabr.temporal.activities.matching import matching_activities
# from nabr.temporal.activities.review import review_activities
# from nabr.temporal.activities.notification import notification_activities

logger = logging.getLogger(__name__)
settings = get_settings()

# Task Queue Names - Domain-specific queues for workflow isolation
VERIFICATION_TASK_QUEUE = "verification-queue"
MATCHING_TASK_QUEUE = "matching-queue"
REVIEW_TASK_QUEUE = "review-queue"
NOTIFICATION_TASK_QUEUE = "notification-queue"


class WorkerManager:
    """
    Manages multiple Temporal workers for different task queues.
    
    Architecture follows Temporal best practices:
    - Separate workers for different domains (verification, matching, review)
    - Thread pool executor for synchronous activities
    - Each worker can be started/stopped independently
    - Graceful shutdown handling
    - Context manager support for proper resource cleanup
    
    Workers can scale independently:
    - Run all workers in one process (development)
    - Run each worker in separate process (production, better isolation)
    - Scale specific workers based on load (e.g., more matching workers)
    """
    
    def __init__(self):
        self.client: Optional[Client] = None
        self.workers: List[Worker] = []
        self.activity_executor: Optional[concurrent.futures.ThreadPoolExecutor] = None
        self.running = False
    
    async def connect(self) -> Client:
        """
        Connect to Temporal server.
        
        Returns:
            Connected Temporal client
        """
        self.client = await Client.connect(
            settings.temporal_host,
            namespace=settings.temporal_namespace,
        )
        logger.info(
            f"Connected to Temporal at {settings.temporal_host} "
            f"(namespace: {settings.temporal_namespace})"
        )
        return self.client
    
    def _create_activity_executor(self, max_workers: int = 100) -> concurrent.futures.ThreadPoolExecutor:
        """
        Create thread pool executor for synchronous activities.
        
        Per Temporal best practices:
        - Use ThreadPoolExecutor for sync activities
        - Max 100 workers is a good default for most applications
        - Async activities run in the event loop (no executor needed)
        
        Args:
            max_workers: Maximum number of thread pool workers
            
        Returns:
            ThreadPoolExecutor instance
        """
        if not self.activity_executor:
            self.activity_executor = concurrent.futures.ThreadPoolExecutor(
                max_workers=max_workers,
                thread_name_prefix="temporal-activity-"
            )
            logger.info(f"Created activity executor with {max_workers} max workers")
        return self.activity_executor
    
    async def create_verification_worker(self) -> Worker:
        """
        Create worker for verification workflows.
        
        Handles:
        - Two-party user verification
        - QR code generation
        - Verification status updates
        
        Configuration:
        - Task queue: verification-queue
        - Max concurrent workflow tasks: 10
        - Uses shared activity executor for sync activities
        """
        if not self.client:
            raise RuntimeError("Client not connected. Call connect() first.")
        
        executor = self._create_activity_executor()
        
        worker = Worker(
            self.client,
            task_queue=VERIFICATION_TASK_QUEUE,
            workflows=[VerificationWorkflow],
            activities=[],  # verification_activities will be added
            activity_executor=executor,
            max_concurrent_workflow_tasks=10,
        )
        
        logger.info(f"Created verification worker on queue: {VERIFICATION_TASK_QUEUE}")
        return worker
    
    async def create_matching_worker(self) -> Worker:
        """
        Create worker for matching workflows.
        
        Handles:
        - Request-to-acceptor matching algorithms
        - Score calculation
        - Candidate notification
        - Request assignment
        
        Configuration:
        - Task queue: matching-queue
        - Max concurrent workflow tasks: 20 (higher load expected)
        - Uses shared activity executor for sync activities
        """
        if not self.client:
            raise RuntimeError("Client not connected. Call connect() first.")
        
        executor = self._create_activity_executor()
        
        worker = Worker(
            self.client,
            task_queue=MATCHING_TASK_QUEUE,
            workflows=[RequestMatchingWorkflow],
            activities=[],  # matching_activities will be added
            activity_executor=executor,
            max_concurrent_workflow_tasks=20,  # Higher concurrency for matching
        )
        
        logger.info(f"Created matching worker on queue: {MATCHING_TASK_QUEUE}")
        return worker
    
    async def create_review_worker(self) -> Worker:
        """
        Create worker for review workflows.
        
        Handles:
        - Review submission
        - Content moderation
        - Rating calculations
        - Review notifications
        
        Configuration:
        - Task queue: review-queue
        - Max concurrent workflow tasks: 15
        - Uses shared activity executor for sync activities
        """
        if not self.client:
            raise RuntimeError("Client not connected. Call connect() first.")
        
        executor = self._create_activity_executor()
        
        worker = Worker(
            self.client,
            task_queue=REVIEW_TASK_QUEUE,
            workflows=[ReviewWorkflow],
            activities=[],  # review_activities will be added
            activity_executor=executor,
            max_concurrent_workflow_tasks=15,
        )
        
        logger.info(f"Created review worker on queue: {REVIEW_TASK_QUEUE}")
        return worker
    
    async def create_notification_worker(self) -> Worker:
        """
        Create worker for notification activities.
        
        Handles:
        - Email notifications
        - SMS notifications
        - Push notifications
        - In-app notifications
        
        Configuration:
        - Task queue: notification-queue
        - No workflows (activity-only worker)
        - Uses shared activity executor for sync activities
        
        Note: This worker only handles activities (no workflows).
        Notifications can be triggered from any workflow using the notification queue.
        """
        if not self.client:
            raise RuntimeError("Client not connected. Call connect() first.")
        
        executor = self._create_activity_executor()
        
        worker = Worker(
            self.client,
            task_queue=NOTIFICATION_TASK_QUEUE,
            workflows=[],  # No workflows, only activities
            activities=[],  # notification_activities will be added
            activity_executor=executor,
        )
        
        logger.info(f"Created notification worker on queue: {NOTIFICATION_TASK_QUEUE}")
        return worker
    
    async def start_all_workers(self):
        """
        Start all workers for the Nābr platform.
        
        Per Temporal best practices:
        - All workers share the same client connection
        - Each worker polls its dedicated task queue
        - Workers run concurrently using asyncio.gather
        - Graceful shutdown on signal handling
        """
        await self.connect()
        
        # Create all workers
        verification_worker = await self.create_verification_worker()
        matching_worker = await self.create_matching_worker()
        review_worker = await self.create_review_worker()
        notification_worker = await self.create_notification_worker()
        
        self.workers = [
            verification_worker,
            matching_worker,
            review_worker,
            notification_worker,
        ]
        
        logger.info("Starting all workers concurrently...")
        self.running = True
        
        # Run all workers concurrently
        # Each worker.run() is a long-running coroutine
        await asyncio.gather(
            *[worker.run() for worker in self.workers]
        )
    
    async def start_worker(self, worker_type: str):
        """
        Start a single worker by type.
        
        Useful for:
        - Scaling specific workers independently
        - Development/testing of specific workflows
        - Running workers in separate processes for isolation
        
        Args:
            worker_type: One of 'verification', 'matching', 'review', 'notification'
        """
        await self.connect()
        
        worker_map = {
            "verification": self.create_verification_worker,
            "matching": self.create_matching_worker,
            "review": self.create_review_worker,
            "notification": self.create_notification_worker,
        }
        
        if worker_type not in worker_map:
            raise ValueError(
                f"Unknown worker type: {worker_type}. "
                f"Must be one of: {', '.join(worker_map.keys())}"
            )
        
        worker = await worker_map[worker_type]()
        self.workers.append(worker)
        
        logger.info(f"Starting {worker_type} worker...")
        self.running = True
        
        await worker.run()
    
    async def shutdown(self):
        """
        Gracefully shutdown all workers.
        
        Per Temporal best practices:
        - Workers gracefully complete in-progress tasks
        - No new tasks are accepted during shutdown
        - Activity executor is shut down cleanly
        """
        logger.info("Shutting down workers...")
        self.running = False
        
        # Shutdown activity executor
        if self.activity_executor:
            logger.info("Shutting down activity executor...")
            self.activity_executor.shutdown(wait=True)
            logger.info("Activity executor shut down")
        
        # Workers will shut down when their run() tasks are cancelled
        logger.info("Workers shut down gracefully")


async def run_all_workers():
    """
    Main entry point to run all Temporal workers.
    
    This function:
    1. Connects to Temporal server
    2. Creates workers for each task queue
    3. Runs all workers concurrently
    4. Handles graceful shutdown on SIGINT/SIGTERM
    """
    manager = WorkerManager()
    
    # Setup signal handlers for graceful shutdown
    loop = asyncio.get_running_loop()
    
    def signal_handler():
        logger.info("Received shutdown signal")
        asyncio.create_task(manager.shutdown())
        loop.stop()
    
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, signal_handler)
    
    try:
        await manager.start_all_workers()
    except asyncio.CancelledError:
        logger.info("Workers cancelled")
    except Exception as e:
        logger.error(f"Worker error: {e}", exc_info=True)
        raise
    finally:
        # Client will be cleaned up automatically
        logger.info("All workers shut down")


async def run_specific_worker(worker_type: str):
    """
    Run a specific worker only.
    
    Args:
        worker_type: One of 'verification', 'matching', 'review', 'notification'
    
    Useful for:
    - Scaling specific workers independently
    - Development/testing of specific workflows
    - Isolating worker processes
    """
    manager = WorkerManager()
    
    # Setup signal handlers
    loop = asyncio.get_running_loop()
    
    def signal_handler():
        logger.info("Received shutdown signal")
        asyncio.create_task(manager.shutdown())
        loop.stop()
    
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, signal_handler)
    
    try:
        await manager.start_worker(worker_type)
    except asyncio.CancelledError:
        logger.info(f"{worker_type} worker cancelled")
    except Exception as e:
        logger.error(f"Worker error: {e}", exc_info=True)
        raise
    finally:
        # Client will be cleaned up automatically
        logger.info(f"{worker_type} worker shut down")


def main():
    """CLI entry point for running workers."""
    import sys
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Check for specific worker argument
    if len(sys.argv) > 1:
        worker_type = sys.argv[1]
        logger.info(f"Starting {worker_type} worker only")
        asyncio.run(run_specific_worker(worker_type))
    else:
        logger.info("Starting all workers")
        asyncio.run(run_all_workers())


if __name__ == "__main__":
    main()
