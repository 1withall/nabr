"""Organization verification workflow - lifetime verification management.

This parent workflow manages the entire verification lifecycle for organization
users, spawning child workflows for each verification method, tracking trust
scores, handling expiry, and providing real-time status via queries.

Similar structure to IndividualVerificationWorkflow but with organization-specific
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
class OrganizationVerificationWorkflow(IndividualVerificationWorkflow):
    """Parent workflow managing lifetime verification for organization users.
    
    Inherits from IndividualVerificationWorkflow and overrides user_type.
    Organization-specific paths:
    - BASELINE: 501(c)(3) status OR Tax ID (120 points)
    - Uses organization-specific methods (501c3, tax ID, bylaws, board verification)
    """
    
    @workflow.run
    async def run(self, user_id: str, user_type: str = "ORGANIZATION", state_dict: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute the organization verification workflow.
        
        Args:
            user_id: The organization being verified
            user_type: Fixed to ORGANIZATION
            state_dict: Previous state (for Continue-As-New)
        
        Returns:
            Final state dictionary
        """
        # Call parent with ORGANIZATION user type
        return await super().run(user_id, "ORGANIZATION", state_dict)
