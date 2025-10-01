"""
Temporal activities package for Nābr workflows.

This package contains all activity implementations organized by domain.
Activities are the workhorses that perform actual work with side effects.

## Directory Structure:
- base.py: Base classes and utilities for all activities
- verification.py: Verification-related activities
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

# Import all activities for easy registration
from nabr.temporal.activities.verification import (
    generate_verification_qr_code,
    validate_id_document,
    update_verification_status,
    log_verification_event,
)
from nabr.temporal.activities.matching import (
    find_candidate_volunteers,
    calculate_match_scores,
    notify_volunteers,
    assign_request_to_volunteer,
    log_matching_event,
)
from nabr.temporal.activities.review import (
    validate_review_eligibility,
    save_review,
    update_user_rating,
    check_for_moderation,
    notify_reviewee,
    log_review_event,
)
from nabr.temporal.activities.notification import (
    send_email,
    send_sms,
    notify_user,
)

# Activity lists for worker registration
verification_activities = [
    generate_verification_qr_code,
    validate_id_document,
    update_verification_status,
    log_verification_event,
]

matching_activities = [
    find_candidate_volunteers,
    calculate_match_scores,
    notify_volunteers,
    assign_request_to_volunteer,
    log_matching_event,
]

review_activities = [
    validate_review_eligibility,
    save_review,
    update_user_rating,
    check_for_moderation,
    notify_reviewee,
    log_review_event,
]

notification_activities = [
    send_email,
    send_sms,
    notify_user,
]

# All activities combined
all_activities = (
    verification_activities
    + matching_activities
    + review_activities
    + notification_activities
)

__all__ = [
    # Lists
    "verification_activities",
    "matching_activities",
    "review_activities",
    "notification_activities",
    "all_activities",
    # Verification
    "generate_verification_qr_code",
    "validate_id_document",
    "update_verification_status",
    "log_verification_event",
    # Matching
    "find_candidate_volunteers",
    "calculate_match_scores",
    "notify_volunteers",
    "assign_request_to_volunteer",
    "log_matching_event",
    # Review
    "validate_review_eligibility",
    "save_review",
    "update_user_rating",
    "check_for_moderation",
    "notify_reviewee",
    "log_review_event",
    # Notification
    "send_email",
    "send_sms",
    "notify_user",
]
