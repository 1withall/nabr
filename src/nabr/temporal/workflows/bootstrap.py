"""
Bootstrap Workflow for Nābr System Initialization.

This workflow orchestrates all system startup tasks through Temporal,
leveraging its retry logic, error handling, and observability features.

Tasks performed:
1. Database migrations (Alembic)
2. Database health checks
3. Schema validation
4. Default data initialization
5. Service connectivity tests
6. Configuration validation

Benefits of using Temporal for bootstrap:
- Automatic retries with exponential backoff
- Full observability in Temporal UI
- Activity-level error handling
- Workflow history for debugging
- Ability to pause/resume initialization
- Coordination of distributed initialization tasks
"""

from datetime import timedelta
from typing import Any, Dict, List

from temporalio import workflow
from temporalio.common import RetryPolicy


@workflow.defn(name="SystemBootstrapWorkflow")
class SystemBootstrapWorkflow:
    """
    Main bootstrap workflow for system initialization.
    
    This workflow runs once at system startup to ensure all services
    are properly initialized before accepting user requests.
    
    Workflow Steps:
    1. Run database migrations
    2. Verify database connectivity and schema
    3. Check Temporal connectivity
    4. Initialize default data (if needed)
    5. Validate all configuration
    6. Run health checks on all services
    
    Each step is implemented as an activity with proper retry logic.
    """
    
    def __init__(self) -> None:
        self._current_step = "initializing"
        self._completed_steps: List[str] = []
        self._failed_steps: List[str] = []
    
    @workflow.run
    async def run(self) -> Dict[str, Any]:
        """
        Execute the complete bootstrap sequence.
        
        Returns:
            Dictionary with bootstrap results and status
        """
        workflow.logger.info("Starting system bootstrap workflow")
        
        # Define retry policy for all activities
        retry_policy = RetryPolicy(
            initial_interval=timedelta(seconds=1),
            maximum_interval=timedelta(seconds=30),
            maximum_attempts=5,
            backoff_coefficient=2.0,
        )
        
        results = {
            "success": False,
            "steps": {},
            "errors": [],
            "warnings": [],
        }
        
        try:
            # Step 1: Run Database Migrations
            self._current_step = "database_migrations"
            workflow.logger.info("Step 1: Running database migrations")
            
            migration_result = await workflow.execute_activity(
                "run_database_migrations",
                start_to_close_timeout=timedelta(minutes=5),
                retry_policy=retry_policy,
            )
            
            self._completed_steps.append("database_migrations")
            results["steps"]["database_migrations"] = migration_result
            workflow.logger.info(f"Migrations completed: {migration_result}")
            
            # Step 2: Verify Database Health
            self._current_step = "database_health"
            workflow.logger.info("Step 2: Verifying database health")
            
            db_health = await workflow.execute_activity(
                "check_database_health",
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=retry_policy,
            )
            
            self._completed_steps.append("database_health")
            results["steps"]["database_health"] = db_health
            workflow.logger.info(f"Database health: {db_health}")
            
            # Step 3: Verify Schema Integrity
            self._current_step = "schema_validation"
            workflow.logger.info("Step 3: Validating database schema")
            
            schema_validation = await workflow.execute_activity(
                "validate_database_schema",
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=retry_policy,
            )
            
            self._completed_steps.append("schema_validation")
            results["steps"]["schema_validation"] = schema_validation
            
            if not schema_validation.get("valid"):
                raise RuntimeError(f"Schema validation failed: {schema_validation}")
            
            workflow.logger.info("Schema validation passed")
            
            # Step 4: Initialize Default Data
            self._current_step = "default_data"
            workflow.logger.info("Step 4: Initializing default data")
            
            default_data = await workflow.execute_activity(
                "initialize_default_data",
                start_to_close_timeout=timedelta(minutes=2),
                retry_policy=retry_policy,
            )
            
            self._completed_steps.append("default_data")
            results["steps"]["default_data"] = default_data
            workflow.logger.info(f"Default data initialized: {default_data}")
            
            # Step 5: Validate Configuration
            self._current_step = "config_validation"
            workflow.logger.info("Step 5: Validating system configuration")
            
            config_validation = await workflow.execute_activity(
                "validate_configuration",
                start_to_close_timeout=timedelta(seconds=10),
                retry_policy=retry_policy,
            )
            
            self._completed_steps.append("config_validation")
            results["steps"]["config_validation"] = config_validation
            
            if not config_validation.get("valid"):
                results["warnings"].append("Configuration has warnings")
                workflow.logger.warning(f"Configuration warnings: {config_validation}")
            else:
                workflow.logger.info("Configuration validation passed")
            
            # Step 6: Service Health Checks
            self._current_step = "service_health"
            workflow.logger.info("Step 6: Running service health checks")
            
            health_checks = await workflow.execute_activity(
                "run_service_health_checks",
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=retry_policy,
            )
            
            self._completed_steps.append("service_health")
            results["steps"]["service_health"] = health_checks
            workflow.logger.info(f"Service health checks: {health_checks}")
            
            # All steps completed successfully
            results["success"] = True
            results["completed_steps"] = self._completed_steps
            workflow.logger.info("Bootstrap workflow completed successfully")
            
            return results
            
        except Exception as e:
            workflow.logger.error(f"Bootstrap workflow failed at step: {self._current_step}")
            workflow.logger.error(f"Error: {str(e)}")
            
            results["success"] = False
            results["failed_step"] = self._current_step
            results["completed_steps"] = self._completed_steps
            results["errors"].append(str(e))
            
            return results
    
    @workflow.query
    def get_current_step(self) -> str:
        """Query current bootstrap step."""
        return self._current_step
    
    @workflow.query
    def get_completed_steps(self) -> List[str]:
        """Query list of completed steps."""
        return self._completed_steps
    
    @workflow.query
    def get_progress(self) -> Dict[str, Any]:
        """Query detailed progress information."""
        return {
            "current_step": self._current_step,
            "completed_steps": self._completed_steps,
            "failed_steps": self._failed_steps,
            "total_steps": 6,
            "completion_percentage": len(self._completed_steps) / 6 * 100,
        }
