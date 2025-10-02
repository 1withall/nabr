"""
Notification activities for verification events.

Sends notifications when verification levels change or verification events occur.
"""

from datetime import datetime, timezone
from typing import Dict, Any

from temporalio import activity


@activity.defn(name="send_level_change_notification")
async def send_level_change_notification(
    user_id: str,
    old_level: str,
    new_level: str,
    score: int,
) -> Dict[str, Any]:
    """
    Send notification when user's verification level increases.
    
    Args:
        user_id: UUID of user
        old_level: Previous verification level
        new_level: New verification level
        score: Current trust score
        
    Returns:
        Dictionary with notification status
    """
    activity.logger.info(
        f"Sending level change notification: {old_level} → {new_level} "
        f"(score: {score})"
    )
    
    # TODO: Implement actual notification sending
    # - Email notification
    # - In-app notification
    # - Push notification (if mobile app exists)
    
    return {
        "sent": True,
        "user_id": user_id,
        "old_level": old_level,
        "new_level": new_level,
        "score": score,
        "sent_at": datetime.now(timezone.utc).isoformat(),
    }


@activity.defn(name="send_verification_email")
async def send_verification_email(
    user_id: str,
    email: str,
    verification_code: str,
) -> Dict[str, Any]:
    """
    Send email verification code to user.
    
    Args:
        user_id: UUID of user
        email: Email address to send to
        verification_code: 6-digit verification code
        
    Returns:
        Dictionary with send status
    """
    activity.logger.info(f"Sending email verification code to {email}")
    
    # TODO: Implement actual email sending
    # await send_email(
    #     to=email,
    #     subject="Verify your email - Nābr",
    #     template="email_verification",
    #     data={"code": verification_code, "user_id": user_id}
    # )
    
    return {
        "sent": True,
        "email": email,
        "sent_at": datetime.now(timezone.utc).isoformat(),
    }


@activity.defn(name="send_verification_sms")
async def send_verification_sms(
    user_id: str,
    phone: str,
    verification_code: str,
) -> Dict[str, Any]:
    """
    Send SMS verification code to user.
    
    Args:
        user_id: UUID of user
        phone: Phone number to send to (E.164 format)
        verification_code: 6-digit verification code
        
    Returns:
        Dictionary with send status
    """
    activity.logger.info(f"Sending SMS verification code to {phone}")
    
    # TODO: Implement actual SMS sending (Twilio, etc.)
    # await send_sms(
    #     to=phone,
    #     message=f"Your Nābr verification code is: {verification_code}"
    # )
    
    return {
        "sent": True,
        "phone": phone,
        "sent_at": datetime.now(timezone.utc).isoformat(),
    }


@activity.defn(name="send_verification_notifications")
async def send_verification_notifications(
    user_id: str,
    notification_type: str,
    data: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Send notifications related to verification process.
    
    Notification types:
    - verification_started: QR codes generated
    - verifier_confirmed: One verifier confirmed
    - verification_complete: Both verifiers confirmed
    - level_increased: Verification level upgraded
    - verifier_authorized: User authorized as verifier
    - verifier_revoked: Verifier status revoked
    
    Args:
        user_id: UUID of user to notify
        notification_type: Type of notification
        data: Notification data
        
    Returns:
        Dictionary with notification status
    """
    activity.logger.info(
        f"Sending {notification_type} notification to user {user_id}"
    )
    
    # TODO: Implement actual notification sending
    # This would involve:
    # - In-app notifications
    # - Email notifications
    # - Push notifications
    # - SMS notifications (for critical events)
    
    return {
        "sent": True,
        "user_id": user_id,
        "notification_type": notification_type,
        "sent_at": datetime.now(timezone.utc).isoformat(),
        "channels": ["in_app", "email"],
    }
