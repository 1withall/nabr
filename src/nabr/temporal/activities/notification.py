"""
Notification activities.

Activities for sending notifications via email, SMS, and push notifications.
"""

from typing import Optional, Any
from temporalio import activity

from nabr.temporal.activities.base import ActivityBase, log_activity_execution


@activity.defn
@log_activity_execution
async def send_email(
    to_email: str,
    subject: str,
    body: str,
    template: Optional[str] = None,
    template_data: Optional[dict] = None
) -> bool:
    """
    Send email notification.
    
    Args:
        to_email: Recipient email address
        subject: Email subject line
        body: Email body (plain text or HTML)
        template: Optional email template name
        template_data: Optional data for template rendering
        
    Returns:
        bool: True if email sent successfully
        
    Notes:
        - Uses configured email service (SendGrid, AWS SES, etc.)
        - Supports HTML and plain text
        - Tracks delivery status
        - Retryable on failure
    """
    activity.logger.info(f"Sending email to {to_email}: {subject}")
    
    # TODO: Implement actual email sending
    # For MVP, just log the email
    
    activity.logger.debug(f"Email body: {body[:100]}...")
    
    # Simulate sending
    activity.heartbeat("Email sent")
    
    return True


@activity.defn
@log_activity_execution
async def send_sms(
    phone_number: str,
    message: str
) -> bool:
    """
    Send SMS notification.
    
    Args:
        phone_number: Recipient phone number (E.164 format)
        message: SMS message (max 160 chars recommended)
        
    Returns:
        bool: True if SMS sent successfully
        
    Notes:
        - Uses configured SMS service (Twilio, AWS SNS, etc.)
        - Validates phone number format
        - Tracks delivery status
        - Retryable on failure
    """
    activity.logger.info(f"Sending SMS to {phone_number}")
    
    # TODO: Implement actual SMS sending
    # For MVP, just log the SMS
    
    activity.logger.debug(f"SMS message: {message}")
    
    # Simulate sending
    activity.heartbeat("SMS sent")
    
    return True


@activity.defn
@log_activity_execution
async def notify_user(
    user_id: str,
    notification_type: str,
    data: dict[str, Any]
) -> bool:
    """
    Send notification to user via their preferred channel(s).
    
    Determines user's notification preferences and sends via
    appropriate channel (email, SMS, push, or multiple).
    
    Args:
        user_id: UUID of user to notify
        notification_type: Type of notification (e.g., "verification_complete")
        data: Notification data for rendering
        
    Returns:
        bool: True if notification sent successfully
        
    Notes:
        - Checks user notification preferences
        - Sends via all enabled channels
        - Uses templates for consistent messaging
        - Tracks delivery across all channels
    """
    from nabr.db.session import AsyncSessionLocal
    from nabr.models.user import User
    from sqlalchemy import select
    
    activity.logger.info(
        f"Sending {notification_type} notification to user {user_id}"
    )
    
    async with AsyncSessionLocal() as db:
        # Get user preferences
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            activity.logger.error(f"User not found: {user_id}")
            return False
        
        # TODO: Get notification preferences from user settings
        # For MVP, send email notifications
        
        # Render notification based on type
        subject, body = _render_notification(notification_type, data, user)
        
        # Send email
        if user.email:
            await send_email(
                to_email=user.email,
                subject=subject,
                body=body
            )
        
        # TODO: Send SMS if user has phone and preference enabled
        # TODO: Send push notification if user has mobile app
        
        activity.logger.info(f"Notification sent to user {user_id}")
        return True


def _render_notification(
    notification_type: str,
    data: dict[str, Any],
    user: Any
) -> tuple[str, str]:
    """
    Render notification content based on type.
    
    Args:
        notification_type: Type of notification
        data: Data for rendering
        user: User object
        
    Returns:
        tuple: (subject, body)
        
    Notes:
        - Uses templates for each notification type
        - Personalizes with user data
        - TODO: Move to dedicated templates system
    """
    # Simple template system for MVP
    templates = {
        "verification_complete": (
            "Nābr: Verification Complete",
            f"Hi {user.full_name},\n\n"
            f"Your account has been successfully verified!\n\n"
            f"You can now access all Nābr features.\n\n"
            f"Best regards,\nThe Nābr Team"
        ),
        "request_matched": (
            "Nābr: New Request Opportunity",
            f"Hi {user.full_name},\n\n"
            f"A new volunteer request matches your profile:\n\n"
            f"{data.get('request_title', 'Request')}\n\n"
            f"View details and accept: {data.get('accept_url', '')}\n\n"
            f"Best regards,\nThe Nābr Team"
        ),
        "review_received": (
            "Nābr: You received a review",
            f"Hi {user.full_name},\n\n"
            f"You received a {data.get('rating', 'N/A')}-star review!\n\n"
            f"View your reviews: {data.get('reviews_url', '')}\n\n"
            f"Best regards,\nThe Nābr Team"
        ),
    }
    
    if notification_type in templates:
        return templates[notification_type]
    
    # Default template
    return (
        f"Nābr: {notification_type}",
        f"Hi {user.full_name},\n\nYou have a new notification.\n\n"
        f"Best regards,\nThe Nābr Team"
    )


@activity.defn
@log_activity_execution
async def send_batch_notifications(
    notifications: list[dict[str, Any]]
) -> dict[str, Any]:
    """
    Send multiple notifications in batch.
    
    More efficient than sending individual notifications when
    you need to notify many users at once.
    
    Args:
        notifications: List of notification dicts with keys:
            - user_id: str
            - notification_type: str
            - data: dict
            
    Returns:
        dict: Summary of results (successful, failed counts)
        
    Notes:
        - Sends all notifications concurrently
        - Returns summary of successes/failures
        - Individual failures don't stop batch
    """
    import asyncio
    
    activity.logger.info(f"Sending batch of {len(notifications)} notifications")
    
    # Send all notifications concurrently
    tasks = [
        notify_user(
            user_id=notif["user_id"],
            notification_type=notif["notification_type"],
            data=notif["data"]
        )
        for notif in notifications
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Count successes and failures
    successful = sum(1 for r in results if r is True)
    failed = len(results) - successful
    
    activity.logger.info(
        f"Batch notification complete: {successful} successful, {failed} failed"
    )
    
    return {
        "total": len(notifications),
        "successful": successful,
        "failed": failed
    }
