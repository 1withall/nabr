"""
Verification activities package - Modularized structure.

This package contains all verification-related Temporal activities,
organized by concern:

- qr_generation: QR code generation for two-party verification
- verifier_authorization: Verifier authorization and credential validation
- progressive_trust: Trust score calculation and points awarding
- events: Verification event recording for audit trail
- notifications: Notification sending for verification events
- saga_compensation: Rollback activities for failed verifications
- document_validation: Document validation and human review queueing
"""

# QR Code Generation
from nabr.temporal.activities.verification.qr_generation import (
    generate_verification_qr_codes,
)

# Verifier Authorization
from nabr.temporal.activities.verification.verifier_authorization import (
    check_verifier_authorization,
    validate_verifier_credentials,
    revoke_verifier_status,
)

# Progressive Trust
from nabr.temporal.activities.verification.progressive_trust import (
    calculate_trust_score_activity,
    award_verification_points,
)

# Events
from nabr.temporal.activities.verification.events import (
    record_verification_event,
)

# Notifications
from nabr.temporal.activities.verification.notifications import (
    send_level_change_notification,
    send_verification_email,
    send_verification_sms,
    send_verification_notifications,
)

# Saga Compensation
from nabr.temporal.activities.verification.saga_compensation import (
    invalidate_qr_codes,
    revoke_confirmations,
)

# Document Validation
from nabr.temporal.activities.verification.document_validation import (
    validate_id_document,
    queue_for_human_review,
)

__all__ = [
    # QR Generation
    "generate_verification_qr_codes",
    
    # Verifier Authorization
    "check_verifier_authorization",
    "validate_verifier_credentials",
    "revoke_verifier_status",
    
    # Progressive Trust
    "calculate_trust_score_activity",
    "award_verification_points",
    
    # Events
    "record_verification_event",
    
    # Notifications
    "send_level_change_notification",
    "send_verification_email",
    "send_verification_sms",
    "send_verification_notifications",
    
    # Saga Compensation
    "invalidate_qr_codes",
    "revoke_confirmations",
    
    # Document Validation
    "validate_id_document",
    "queue_for_human_review",
]
