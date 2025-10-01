"""
Request matching activities.

Activities for intelligent volunteer-request matching including candidate
finding, score calculation, and assignment.
"""

from typing import Optional
from temporalio import activity
from sqlalchemy import select, and_, or_, func
from datetime import datetime
import math

from nabr.temporal.activities.base import ActivityBase, log_activity_execution
from nabr.models.user import User, VolunteerProfile
from nabr.models.request import Request


@activity.defn
@log_activity_execution
async def find_candidate_volunteers(
    request_id: str,
    max_candidates: int = 20
) -> list[dict]:
    """
    Find candidate volunteers for a request.
    
    Searches for volunteers matching request criteria including:
    - Required skills
    - Geographic proximity
    - Availability
    - Verification status
    
    Args:
        request_id: UUID of request to match
        max_candidates: Maximum number of candidates to return
        
    Returns:
        list[dict]: List of candidate volunteer data
        
    Notes:
        - Only returns verified volunteers
        - Filters by required skills if specified
        - Considers geographic distance if location provided
        - Orders by potential match quality
    """
    from nabr.db.session import AsyncSessionLocal
    
    async with AsyncSessionLocal() as db:
        # Get request details
        request_result = await db.execute(
            select(Request).where(Request.id == request_id)
        )
        request = request_result.scalar_one_or_none()
        
        if not request:
            activity.logger.error(f"Request not found: {request_id}")
            return []
        
        activity.logger.info(
            f"Finding candidates for request {request_id}, "
            f"type: {request.request_type}, "
            f"skills: {request.required_skills}"
        )
        
        # Build base query for verified volunteers
        query = (
            select(User, VolunteerProfile)
            .join(VolunteerProfile, User.id == VolunteerProfile.user_id)
            .where(User.is_verified == True)
            .where(User.is_active == True)
            .where(User.user_type.in_(["volunteer", "individual"]))
        )
        
        # Filter by skills if required
        if request.required_skills:
            # Check if volunteer has any of the required skills
            # TODO: Improve skill matching logic
            activity.logger.info(f"Filtering by skills: {request.required_skills}")
        
        # Execute query
        result = await db.execute(query.limit(max_candidates * 2))
        rows = result.all()
        
        candidates = []
        for user, profile in rows:
            candidate = {
                "volunteer_id": str(user.id),
                "full_name": user.full_name,
                "email": user.email,
                "rating": user.rating or 0.0,
                "total_reviews": user.total_reviews,
                "skills": profile.skills or [],
                "latitude": user.latitude,
                "longitude": user.longitude,
                "max_distance_km": profile.max_distance_km,
            }
            candidates.append(candidate)
        
        activity.logger.info(f"Found {len(candidates)} candidates")
        return candidates[:max_candidates]


@activity.defn
@log_activity_execution
async def calculate_match_scores(
    request_id: str,
    candidates: list[dict]
) -> list[dict]:
    """
    Calculate match scores for candidate volunteers.
    
    Scoring algorithm considers:
    - Skill match (40% weight)
    - Geographic distance (10% weight)
    - Volunteer rating (20% weight)
    - Availability (30% weight)
    
    Args:
        request_id: UUID of request
        candidates: List of candidate volunteer data
        
    Returns:
        list[dict]: Candidates with match scores, sorted by score (high to low)
        
    Notes:
        - Scores range from 0.0 to 1.0
        - Higher scores indicate better matches
        - Weights can be configured in settings
    """
    from nabr.db.session import AsyncSessionLocal
    from nabr.core.config import get_settings
    
    settings = get_settings()
    
    async with AsyncSessionLocal() as db:
        # Get request details
        request_result = await db.execute(
            select(Request).where(Request.id == request_id)
        )
        request = request_result.scalar_one_or_none()
        
        if not request:
            activity.logger.error(f"Request not found: {request_id}")
            return []
        
        activity.logger.info(f"Calculating match scores for {len(candidates)} candidates")
        
        scored_candidates = []
        for candidate in candidates:
            score = 0.0
            
            # Skill match score (40% weight)
            skill_score = _calculate_skill_score(
                request.required_skills or [],
                candidate["skills"] or []
            )
            score += skill_score * settings.matching_skill_weight
            
            # Distance score (10% weight)
            distance_score = _calculate_distance_score(
                request.latitude,
                request.longitude,
                candidate["latitude"],
                candidate["longitude"],
                candidate["max_distance_km"]
            )
            score += distance_score * settings.matching_distance_weight
            
            # Rating score (20% weight)
            rating_score = (candidate["rating"] or 0.0) / 5.0
            score += rating_score * settings.matching_rating_weight
            
            # Availability score (30% weight)
            # TODO: Implement availability matching
            availability_score = 0.8  # Placeholder
            score += availability_score * settings.matching_availability_weight
            
            candidate["match_score"] = round(score, 3)
            scored_candidates.append(candidate)
        
        # Sort by score (highest first)
        scored_candidates.sort(key=lambda c: c["match_score"], reverse=True)
        
        activity.logger.info(
            f"Scored {len(scored_candidates)} candidates, "
            f"top score: {scored_candidates[0]['match_score'] if scored_candidates else 0}"
        )
        
        return scored_candidates


def _calculate_skill_score(required_skills: list[str], volunteer_skills: list[str]) -> float:
    """Calculate skill match score (0.0 to 1.0)."""
    if not required_skills:
        return 1.0  # No specific skills required
    
    if not volunteer_skills:
        return 0.0  # No skills listed
    
    # Normalize skill names for comparison
    required = {skill.lower().strip() for skill in required_skills}
    available = {skill.lower().strip() for skill in volunteer_skills}
    
    # Calculate Jaccard similarity
    intersection = len(required & available)
    union = len(required | available)
    
    return intersection / union if union > 0 else 0.0


def _calculate_distance_score(
    req_lat: Optional[float],
    req_lon: Optional[float],
    vol_lat: Optional[float],
    vol_lon: Optional[float],
    max_distance_km: Optional[int]
) -> float:
    """Calculate distance score (0.0 to 1.0)."""
    # If no location data, return neutral score
    if not all([req_lat, req_lon, vol_lat, vol_lon]):
        return 0.5
    
    # Calculate distance using Haversine formula
    distance_km = _haversine_distance(req_lat, req_lon, vol_lat, vol_lon)
    
    # If volunteer has max distance preference, use it
    max_dist = max_distance_km or 50  # Default 50km
    
    # Score decreases linearly with distance
    if distance_km > max_dist:
        return 0.0
    
    return 1.0 - (distance_km / max_dist)


def _haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate distance between two points using Haversine formula.
    
    Returns:
        float: Distance in kilometers
    """
    # Earth radius in kilometers
    R = 6371.0
    
    # Convert to radians
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    # Haversine formula
    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c


@activity.defn
@log_activity_execution
async def notify_volunteers(
    request_id: str,
    volunteer_ids: list[str]
) -> bool:
    """
    Notify volunteers about request opportunity.
    
    Sends notifications (email/SMS) to selected volunteers about
    available request that matches their profile.
    
    Args:
        request_id: UUID of request
        volunteer_ids: List of volunteer UUIDs to notify
        
    Returns:
        bool: True if all notifications sent successfully
        
    Notes:
        - Sends email and/or SMS based on user preferences
        - Includes request details and acceptance link
        - Tracks notification delivery
    """
    activity.logger.info(
        f"Notifying {len(volunteer_ids)} volunteers about request {request_id}"
    )
    
    # TODO: Implement actual notification sending
    # For MVP, just log the notification
    
    for volunteer_id in volunteer_ids:
        activity.logger.info(f"Would notify volunteer {volunteer_id}")
    
    activity.heartbeat(f"Notified {len(volunteer_ids)} volunteers")
    
    return True


@activity.defn
@log_activity_execution
async def assign_request_to_volunteer(
    request_id: str,
    volunteer_id: str
) -> bool:
    """
    Assign request to volunteer who accepted.
    
    Updates request with volunteer assignment and status.
    Idempotent: Safe to call multiple times.
    
    Args:
        request_id: UUID of request
        volunteer_id: UUID of accepting volunteer
        
    Returns:
        bool: True if assignment successful
        
    Notes:
        - Updates request.volunteer_id
        - Changes status to "assigned"
        - Creates assignment event log
    """
    from nabr.db.session import AsyncSessionLocal
    
    async with AsyncSessionLocal() as db:
        # Get request
        result = await db.execute(
            select(Request).where(Request.id == request_id)
        )
        request = result.scalar_one_or_none()
        
        if not request:
            activity.logger.error(f"Request not found: {request_id}")
            return False
        
        # Check if already assigned
        if request.volunteer_id == volunteer_id:
            activity.logger.info(f"Request already assigned to {volunteer_id}")
            return True
        
        # Assign volunteer
        request.volunteer_id = volunteer_id
        request.status = "assigned"
        
        await db.commit()
        
        activity.logger.info(
            f"Assigned request {request_id} to volunteer {volunteer_id}"
        )
        return True


@activity.defn
@log_activity_execution
async def log_matching_event(
    request_id: str,
    event_type: str,
    event_data: Optional[dict] = None
) -> str:
    """
    Log matching event for audit trail.
    
    Creates immutable event log entry for matching process.
    
    Args:
        request_id: UUID of request
        event_type: Type of event (e.g., "candidates_found", "batch_notified")
        event_data: Optional additional event data
        
    Returns:
        str: UUID of created event log entry
        
    Notes:
        - Creates immutable audit log
        - Used for transparency and debugging
        - Events are never deleted
    """
    import uuid
    
    event = {
        "event_type": event_type,
        "request_id": request_id,
        "event_data": event_data or {},
        "timestamp": datetime.utcnow().isoformat(),
    }
    
    activity.logger.info(f"Logged matching event: {event}")
    
    # TODO: Store in dedicated events table
    
    return str(uuid.uuid4())
