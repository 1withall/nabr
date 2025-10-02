"""
Temporal activities package for Nābr workflows.

This package contains all activity implementations organized by domain.
Activities are the workhorses that perform actual work with side effects.

## Directory Structure:
- base.py: Base classes and utilities for all activities
- verification/: Modular verification activities (QR generation, authorization, trust scoring, etc.)
- matching.py: Request matching activities
- review.py: Review submission activities
- notification.py: Notification and communication activities
- database.py: Database operation activities

## Adding New Activities:
1. Create activity function with @activity.defn decorator
2. Add comprehensive docstring explaining purpose and parameters
3. Implement idempotent logic (safe to retry)
4. Add heartbeat for long-running operations
5. Handle cancellation gracefully
6. Return meaningful results
7. Add to appropriate module and __all__ list
"""

# Import all verification activities from modular package
from nabr.temporal.activities.verification import (
    # QR Generation
    generate_verification_qr_codes,
    # Verifier Authorization
    check_verifier_authorization,
    validate_verifier_credentials,
    revoke_verifier_status,
    # Progressive Trust
    calculate_trust_score_activity,
    award_verification_points,
    # Events
    record_verification_event,
    # Notifications
    send_level_change_notification,
    send_verification_email,
    send_verification_sms,
    send_verification_notifications,
    # Saga Compensation
    invalidate_qr_codes,
    revoke_confirmations,
    # Document Validation
    validate_id_document,
    queue_for_human_review,
)


# Activity lists for worker registration
verification_activities = [
    # QR Generation
    generate_verification_qr_codes,
    # Verifier Authorization
    check_verifier_authorization,
    validate_verifier_credentials,
    revoke_verifier_status,
    # Progressive Trust
    calculate_trust_score_activity,
    award_verification_points,
    # Events
    record_verification_event,
    # Notifications
    send_level_change_notification,
    send_verification_email,
    send_verification_sms,
    send_verification_notifications,
    # Saga Compensation
    invalidate_qr_codes,
    revoke_confirmations,
    # Document Validation
    validate_id_document,
    queue_for_human_review,
]

# All activities combined (add others as they're implemented)
all_activities = verification_activities

__all__ = [
    # Verification Activities
    "generate_verification_qr_codes",
    "check_verifier_authorization",
    "validate_verifier_credentials",
    "revoke_verifier_status",
    "calculate_trust_score_activity",
    "award_verification_points",
    "record_verification_event",
    "send_level_change_notification",
    "send_verification_email",
    "send_verification_sms",
    "send_verification_notifications",
    "invalidate_qr_codes",
    "revoke_confirmations",
    "validate_id_document",
    "queue_for_human_review",
    # Lists
    "verification_activities",
    "all_activities",
]
