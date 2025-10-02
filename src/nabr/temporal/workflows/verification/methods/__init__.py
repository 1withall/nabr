"""Child workflows for individual verification methods.

Each verification method is implemented as a separate child workflow that:
- Runs independently of the parent
- Returns points awarded on success
- Handles method-specific logic and validations
- Can be cancelled/compensated if needed
"""

from .email_verification import EmailVerificationWorkflow
from .phone_verification import PhoneVerificationWorkflow
from .two_party_in_person import TwoPartyInPersonWorkflow
from .government_id import GovernmentIDWorkflow

__all__ = [
    "EmailVerificationWorkflow",
    "PhoneVerificationWorkflow",
    "TwoPartyInPersonWorkflow",
    "GovernmentIDWorkflow",
]
