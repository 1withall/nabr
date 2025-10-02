"""Business verification workflow - lifetime verification management.

This parent workflow manages the entire verification lifecycle for business
users, spawning child workflows for each verification method, tracking trust
scores, handling expiry, and providing real-time status via queries.

Similar structure to IndividualVerificationWorkflow but with business-specific
verification methods and baseline paths.
"""

from datetime import timedelta
from typing import Dict, Optional, Any

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from nabr.models.verification_types import UserType
    from .individual_verification import (
        IndividualVerificationWorkflow,
        VerificationState,
    )


@workflow.defn
class BusinessVerificationWorkflow(IndividualVerificationWorkflow):
    """Parent workflow managing lifetime verification for business users.
    
    Inherits from IndividualVerificationWorkflow and overrides user_type.
    Business-specific paths:
    - BASELINE: Business license OR Tax ID (120 points)
    - Uses business-specific methods (license, tax ID, address, owner verification)
    """
    
    @workflow.run
    async def run(self, user_id: str, user_type: str = "BUSINESS", state_dict: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute the business verification workflow.
        
        Args:
            user_id: The business being verified
            user_type: Fixed to BUSINESS
            state_dict: Previous state (for Continue-As-New)
        
        Returns:
            Final state dictionary
        """
        # Call parent with BUSINESS user type
        return await super().run(user_id, "BUSINESS", state_dict)
