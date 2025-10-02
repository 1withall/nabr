"""
Verification types and requirements for tiered verification system.

UNIVERSAL IDENTITY VERIFICATION - CORE MISSION:
  "Some people may not have access to reliable internet or cellular service at home.
   Some may not have a home address or state-issued ID. This app will give them an
   opportunity to prove that they are who they say they are, even if they don't have
   any of those things."

PROGRESSIVE TRUST ACCUMULATION MODEL:
  Instead of hard requirements, this system uses a SCORING MODEL where:
  - Each verification method contributes POINTS toward trust levels
  - Multiple weak signals can equal a strong verification
  - People WITHOUT traditional documentation can still verify
  - Email/phone are OPTIONAL methods, NOT requirements
  
UNIQUE VERIFICATION PATHS BY USER TYPE:

INDIVIDUALS - In-Person Community Verification:
  BASELINE (Minimal): Two trusted community members confirm identity in person
  - NO email required, NO phone required, NO government ID required
  - Two-party in-person is sufficient for basic platform access
  - Additional methods (email, phone, ID) ADD trust, not required
  - Inclusive: Works for people without traditional documentation

BUSINESSES - Documentary Evidence:
  BASELINE (Minimal): Business legitimacy through official records
  - Business license OR tax ID OR business address verification
  - Email/phone are OPTIONAL, contribute to trust score
  - Multiple paths to prove business legitimacy

ORGANIZATIONS - Mission & Governance Verification:
  BASELINE (Minimal): Organizational legitimacy through documentation
  - 501(c)(3) status OR tax ID OR board verification
  - Email/phone are OPTIONAL, contribute to trust score
  - Focus on mission alignment and community fit

TEMPORAL WORKFLOW ARCHITECTURE:
  Uses advanced Temporal patterns for modular, adaptable verification:
  - Child workflows for each verification method
  - Signals for real-time verifier confirmations
  - Queries for checking verification status
  - Sagas for complex multi-step verifications
  - Compensation for revoked verifications
"""

from enum import Enum as PyEnum
from typing import Dict, List, Set, Optional
from dataclasses import dataclass


class VerificationLevel(str, PyEnum):
    """
    Tiered verification levels achieved through progressive trust accumulation.
    
    Each level requires a MINIMUM TRUST SCORE, not hard method requirements.
    Different paths can achieve the same level.
    """
    
    UNVERIFIED = "unverified"      # 0 points - No verification
    MINIMAL = "minimal"            # 100+ points - Type-specific baseline
    STANDARD = "standard"          # 250+ points - Enhanced trust signals
    ENHANCED = "enhanced"          # 400+ points - Strong multi-method verification
    COMPLETE = "complete"          # 600+ points - Comprehensive verification


# Trust score thresholds for each level
LEVEL_THRESHOLDS = {
    VerificationLevel.UNVERIFIED: 0,
    VerificationLevel.MINIMAL: 100,
    VerificationLevel.STANDARD: 250,
    VerificationLevel.ENHANCED: 400,
    VerificationLevel.COMPLETE: 600,
}


@dataclass
class VerificationMethodScore:
    """
    Point value and metadata for a verification method.
    
    Attributes:
        points: Base point value this method contributes
        max_multiplier: Maximum multiplier for repeated verifications (e.g., multiple references)
        decay_days: Days until verification needs renewal (0 = no decay)
        requires_human_review: Whether this method requires manual review
    """
    points: int
    max_multiplier: float = 1.0
    decay_days: int = 0
    requires_human_review: bool = False


class VerificationMethod(str, PyEnum):
    """
    Methods used to verify identity/legitimacy.
    
    ALL METHODS ARE OPTIONAL - they contribute to trust score.
    Different methods apply to different user types.
    """
    
    # ========================================================================
    # UNIVERSAL METHODS (All user types - OPTIONAL)
    # ========================================================================
    EMAIL = "email"                              # +30 points
    PHONE = "phone"                              # +30 points
    
    # ========================================================================
    # INDIVIDUAL METHODS
    # ========================================================================
    
    # Community verification (BASELINE for individuals)
    IN_PERSON_TWO_PARTY = "in_person_two_party"  # +150 points (2 verifiers)
    IN_PERSON_SINGLE = "in_person_single"        # +75 points (1 verifier)
    
    # Documentary evidence (OPTIONAL)
    GOVERNMENT_ID = "government_id"              # +100 points
    BIOMETRIC = "biometric"                      # +80 points
    
    # Social proof (OPTIONAL)
    PERSONAL_REFERENCE = "personal_reference"    # +50 points (can multiply up to 3x)
    COMMUNITY_ATTESTATION = "community_attestation"  # +40 points (community vouching)
    
    # Long-term trust signals (OPTIONAL)
    PLATFORM_HISTORY = "platform_history"        # +30 points (6+ months good standing)
    TRANSACTION_HISTORY = "transaction_history"  # +40 points (successful transactions)
    
    # ========================================================================
    # BUSINESS METHODS
    # ========================================================================
    
    # Documentary evidence (PRIMARY - any ONE is sufficient for baseline)
    BUSINESS_LICENSE = "business_license"        # +120 points
    TAX_ID_BUSINESS = "tax_id_business"         # +120 points
    BUSINESS_ADDRESS = "business_address"        # +80 points
    
    # Ownership and operations (SUPPORTING)
    OWNER_VERIFICATION = "owner_verification"    # +100 points
    BUSINESS_INSURANCE = "business_insurance"    # +60 points
    PROFESSIONAL_LICENSE = "professional_license" # +80 points
    
    # Reputation and trust (SUPPORTING)
    BUSINESS_REFERENCES = "business_references"  # +50 points (can multiply up to 3x)
    COMMUNITY_ENDORSEMENT = "community_endorsement"  # +60 points
    
    # ========================================================================
    # ORGANIZATION METHODS
    # ========================================================================
    
    # Organizational legitimacy (PRIMARY - any ONE is sufficient for baseline)
    NONPROFIT_STATUS = "nonprofit_status"        # +120 points (501c3 documentation)
    TAX_ID_NONPROFIT = "tax_id_nonprofit"       # +120 points
    
    # Governance (SUPPORTING)
    ORGANIZATION_BYLAWS = "organization_bylaws"  # +80 points
    BOARD_VERIFICATION = "board_verification"    # +100 points
    
    # Mission and community (SUPPORTING)
    MISSION_ALIGNMENT = "mission_alignment"      # +80 points (community review)
    ORG_REFERENCES = "org_references"           # +50 points (can multiply up to 3x)
    
    # ========================================================================
    # ENHANCED METHODS (All types - OPTIONAL)
    # ========================================================================
    NOTARY_VERIFICATION = "notary_verification"  # +90 points



# ============================================================================
# VERIFICATION METHOD SCORING
# ============================================================================

# Point values for each verification method
METHOD_SCORES: Dict[VerificationMethod, VerificationMethodScore] = {
    # Universal methods - OPTIONAL
    VerificationMethod.EMAIL: VerificationMethodScore(
        points=30,
        decay_days=365,  # Reconfirm annually
        requires_human_review=False
    ),
    VerificationMethod.PHONE: VerificationMethodScore(
        points=30,
        decay_days=365,  # Reconfirm annually
        requires_human_review=False
    ),
    
    # Individual methods
    VerificationMethod.IN_PERSON_TWO_PARTY: VerificationMethodScore(
        points=150,  # BASELINE for individuals
        decay_days=730,  # 2 years
        requires_human_review=True  # Verifiers must confirm
    ),
    VerificationMethod.IN_PERSON_SINGLE: VerificationMethodScore(
        points=75,  # Half of two-party
        decay_days=730,
        requires_human_review=True
    ),
    VerificationMethod.GOVERNMENT_ID: VerificationMethodScore(
        points=100,
        decay_days=1825,  # 5 years (typical ID expiry)
        requires_human_review=True  # Check ID validity
    ),
    VerificationMethod.BIOMETRIC: VerificationMethodScore(
        points=80,
        decay_days=0,  # No decay (biometric doesn't change)
        requires_human_review=False  # Automated
    ),
    VerificationMethod.PERSONAL_REFERENCE: VerificationMethodScore(
        points=50,
        max_multiplier=3.0,  # Up to 3 references (150 total)
        decay_days=1095,  # 3 years
        requires_human_review=True
    ),
    VerificationMethod.COMMUNITY_ATTESTATION: VerificationMethodScore(
        points=40,
        max_multiplier=2.0,  # Up to 2 attestations
        decay_days=730,
        requires_human_review=True
    ),
    VerificationMethod.PLATFORM_HISTORY: VerificationMethodScore(
        points=30,
        decay_days=0,  # Accumulated over time
        requires_human_review=False
    ),
    VerificationMethod.TRANSACTION_HISTORY: VerificationMethodScore(
        points=40,
        decay_days=0,  # Accumulated over time
        requires_human_review=False
    ),
    
    # Business methods
    VerificationMethod.BUSINESS_LICENSE: VerificationMethodScore(
        points=120,  # BASELINE for businesses (any one primary method)
        decay_days=365,  # Annual renewal typical
        requires_human_review=True
    ),
    VerificationMethod.TAX_ID_BUSINESS: VerificationMethodScore(
        points=120,  # BASELINE for businesses
        decay_days=0,  # EIN doesn't expire
        requires_human_review=True
    ),
    VerificationMethod.BUSINESS_ADDRESS: VerificationMethodScore(
        points=80,
        decay_days=730,
        requires_human_review=True
    ),
    VerificationMethod.OWNER_VERIFICATION: VerificationMethodScore(
        points=100,
        decay_days=1095,
        requires_human_review=True
    ),
    VerificationMethod.BUSINESS_INSURANCE: VerificationMethodScore(
        points=60,
        decay_days=365,  # Annual renewal
        requires_human_review=True
    ),
    VerificationMethod.PROFESSIONAL_LICENSE: VerificationMethodScore(
        points=80,
        decay_days=730,
        requires_human_review=True
    ),
    VerificationMethod.BUSINESS_REFERENCES: VerificationMethodScore(
        points=50,
        max_multiplier=3.0,
        decay_days=1095,
        requires_human_review=True
    ),
    VerificationMethod.COMMUNITY_ENDORSEMENT: VerificationMethodScore(
        points=60,
        max_multiplier=2.0,
        decay_days=730,
        requires_human_review=True
    ),
    
    # Organization methods
    VerificationMethod.NONPROFIT_STATUS: VerificationMethodScore(
        points=120,  # BASELINE for organizations
        decay_days=365,  # Annual documentation review
        requires_human_review=True
    ),
    VerificationMethod.TAX_ID_NONPROFIT: VerificationMethodScore(
        points=120,  # BASELINE for organizations
        decay_days=0,
        requires_human_review=True
    ),
    VerificationMethod.ORGANIZATION_BYLAWS: VerificationMethodScore(
        points=80,
        decay_days=1095,
        requires_human_review=True
    ),
    VerificationMethod.BOARD_VERIFICATION: VerificationMethodScore(
        points=100,
        decay_days=730,
        requires_human_review=True
    ),
    VerificationMethod.MISSION_ALIGNMENT: VerificationMethodScore(
        points=80,
        decay_days=730,
        requires_human_review=True  # Community review
    ),
    VerificationMethod.ORG_REFERENCES: VerificationMethodScore(
        points=50,
        max_multiplier=3.0,
        decay_days=1095,
        requires_human_review=True
    ),
    
    # Enhanced methods
    VerificationMethod.NOTARY_VERIFICATION: VerificationMethodScore(
        points=90,
        decay_days=1095,
        requires_human_review=True
    ),
}


# ============================================================================
# USER TYPE VERIFICATION PATHS
# ============================================================================

class UserType(str, PyEnum):
    """User account types with unique verification needs."""
    INDIVIDUAL = "individual"
    BUSINESS = "business"
    ORGANIZATION = "organization"


# Methods applicable to each user type
USER_TYPE_METHODS: Dict[UserType, Set[VerificationMethod]] = {
    UserType.INDIVIDUAL: {
        VerificationMethod.EMAIL,
        VerificationMethod.PHONE,
        VerificationMethod.IN_PERSON_TWO_PARTY,
        VerificationMethod.IN_PERSON_SINGLE,
        VerificationMethod.GOVERNMENT_ID,
        VerificationMethod.BIOMETRIC,
        VerificationMethod.PERSONAL_REFERENCE,
        VerificationMethod.COMMUNITY_ATTESTATION,
        VerificationMethod.PLATFORM_HISTORY,
        VerificationMethod.TRANSACTION_HISTORY,
        VerificationMethod.NOTARY_VERIFICATION,
    },
    UserType.BUSINESS: {
        VerificationMethod.EMAIL,
        VerificationMethod.PHONE,
        VerificationMethod.BUSINESS_LICENSE,
        VerificationMethod.TAX_ID_BUSINESS,
        VerificationMethod.BUSINESS_ADDRESS,
        VerificationMethod.OWNER_VERIFICATION,
        VerificationMethod.BUSINESS_INSURANCE,
        VerificationMethod.PROFESSIONAL_LICENSE,
        VerificationMethod.BUSINESS_REFERENCES,
        VerificationMethod.COMMUNITY_ENDORSEMENT,
        VerificationMethod.PLATFORM_HISTORY,
        VerificationMethod.TRANSACTION_HISTORY,
        VerificationMethod.NOTARY_VERIFICATION,
    },
    UserType.ORGANIZATION: {
        VerificationMethod.EMAIL,
        VerificationMethod.PHONE,
        VerificationMethod.NONPROFIT_STATUS,
        VerificationMethod.TAX_ID_NONPROFIT,
        VerificationMethod.ORGANIZATION_BYLAWS,
        VerificationMethod.BOARD_VERIFICATION,
        VerificationMethod.MISSION_ALIGNMENT,
        VerificationMethod.ORG_REFERENCES,
        VerificationMethod.COMMUNITY_ENDORSEMENT,
        VerificationMethod.PLATFORM_HISTORY,
        VerificationMethod.TRANSACTION_HISTORY,
        VerificationMethod.NOTARY_VERIFICATION,
    },
}


# BASELINE METHODS - Recommended strong starts for each type
# These are NOT required, but provide fastest path to MINIMAL level
BASELINE_METHODS: Dict[UserType, Set[VerificationMethod]] = {
    UserType.INDIVIDUAL: {
        VerificationMethod.IN_PERSON_TWO_PARTY,  # 150 points - reaches MINIMAL
    },
    UserType.BUSINESS: {
        # Any ONE of these reaches 120+ points (near MINIMAL)
        VerificationMethod.BUSINESS_LICENSE,
        VerificationMethod.TAX_ID_BUSINESS,
    },
    UserType.ORGANIZATION: {
        # Any ONE of these reaches 120+ points (near MINIMAL)
        VerificationMethod.NONPROFIT_STATUS,
        VerificationMethod.TAX_ID_NONPROFIT,
    },
}


# SUGGESTED PATHS - Example combinations to reach each level
# These are SUGGESTIONS, not requirements. Many paths possible.
SUGGESTED_PATHS: Dict[UserType, Dict[VerificationLevel, List[Set[VerificationMethod]]]] = {
    UserType.INDIVIDUAL: {
        VerificationLevel.MINIMAL: [
            # Path 1: Two-party in-person (ORIGINAL SPEC - works without ANY documentation)
            {VerificationMethod.IN_PERSON_TWO_PARTY},  # 150 points
            
            # Path 2: Single verifier + community attestation + email
            {
                VerificationMethod.IN_PERSON_SINGLE,      # 75
                VerificationMethod.COMMUNITY_ATTESTATION,  # 40
                VerificationMethod.EMAIL,                  # 30
            },  # 145 points
            
            # Path 3: Government ID + platform history
            {
                VerificationMethod.GOVERNMENT_ID,    # 100
                VerificationMethod.PLATFORM_HISTORY, # 30
            },  # 130 points
        ],
        VerificationLevel.STANDARD: [
            # Path 1: Two-party + email + phone + government ID
            {
                VerificationMethod.IN_PERSON_TWO_PARTY,  # 150
                VerificationMethod.EMAIL,                # 30
                VerificationMethod.PHONE,                # 30
                VerificationMethod.GOVERNMENT_ID,        # 100
            },  # 310 points
        ],
        VerificationLevel.ENHANCED: [
            # Path 1: Full individual verification
            {
                VerificationMethod.IN_PERSON_TWO_PARTY,     # 150
                VerificationMethod.GOVERNMENT_ID,           # 100
                VerificationMethod.EMAIL,                   # 30
                VerificationMethod.PHONE,                   # 30
                VerificationMethod.PERSONAL_REFERENCE,      # 50 (x2 = 100)
                VerificationMethod.PLATFORM_HISTORY,        # 30
            },  # 440 points
        ],
        VerificationLevel.COMPLETE: [
            # Path 1: Comprehensive verification
            {
                VerificationMethod.IN_PERSON_TWO_PARTY,     # 150
                VerificationMethod.GOVERNMENT_ID,           # 100
                VerificationMethod.BIOMETRIC,               # 80
                VerificationMethod.EMAIL,                   # 30
                VerificationMethod.PHONE,                   # 30
                VerificationMethod.PERSONAL_REFERENCE,      # 50 (x3 = 150)
                VerificationMethod.NOTARY_VERIFICATION,     # 90
                VerificationMethod.PLATFORM_HISTORY,        # 30
                VerificationMethod.TRANSACTION_HISTORY,     # 40
            },  # 700 points
        ],
    },
    UserType.BUSINESS: {
        VerificationLevel.MINIMAL: [
            # Path 1: Business license (single document sufficient)
            {VerificationMethod.BUSINESS_LICENSE},  # 120 points (near threshold, add email to reach)
            
            # Path 2: Tax ID + email
            {
                VerificationMethod.TAX_ID_BUSINESS,  # 120
                VerificationMethod.EMAIL,            # 30
            },  # 150 points
            
            # Path 3: Business address + owner verification
            {
                VerificationMethod.BUSINESS_ADDRESS,      # 80
                VerificationMethod.OWNER_VERIFICATION,    # 100
            },  # 180 points (stronger alternative)
        ],
        VerificationLevel.STANDARD: [
            # Path 1: License + address + owner + contact
            {
                VerificationMethod.BUSINESS_LICENSE,      # 120
                VerificationMethod.BUSINESS_ADDRESS,      # 80
                VerificationMethod.OWNER_VERIFICATION,    # 100
                VerificationMethod.EMAIL,                 # 30
            },  # 330 points
        ],
        VerificationLevel.ENHANCED: [
            # Path 1: Full business verification
            {
                VerificationMethod.BUSINESS_LICENSE,        # 120
                VerificationMethod.TAX_ID_BUSINESS,         # 120
                VerificationMethod.BUSINESS_ADDRESS,        # 80
                VerificationMethod.OWNER_VERIFICATION,      # 100
                VerificationMethod.BUSINESS_INSURANCE,      # 60
                VerificationMethod.EMAIL,                   # 30
                VerificationMethod.PHONE,                   # 30
            },  # 540 points
        ],
        VerificationLevel.COMPLETE: [
            # Path 1: Comprehensive business verification
            {
                VerificationMethod.BUSINESS_LICENSE,        # 120
                VerificationMethod.TAX_ID_BUSINESS,         # 120
                VerificationMethod.BUSINESS_ADDRESS,        # 80
                VerificationMethod.OWNER_VERIFICATION,      # 100
                VerificationMethod.BUSINESS_INSURANCE,      # 60
                VerificationMethod.PROFESSIONAL_LICENSE,    # 80
                VerificationMethod.BUSINESS_REFERENCES,     # 50 (x3 = 150)
                VerificationMethod.COMMUNITY_ENDORSEMENT,   # 60
                VerificationMethod.NOTARY_VERIFICATION,     # 90
                VerificationMethod.EMAIL,                   # 30
                VerificationMethod.PHONE,                   # 30
            },  # 920 points
        ],
    },
    UserType.ORGANIZATION: {
        VerificationLevel.MINIMAL: [
            # Path 1: 501(c)(3) status (single document)
            {
                VerificationMethod.NONPROFIT_STATUS,  # 120
                VerificationMethod.EMAIL,             # 30
            },  # 150 points
            
            # Path 2: Tax ID + board verification
            {
                VerificationMethod.TAX_ID_NONPROFIT,     # 120
                VerificationMethod.BOARD_VERIFICATION,   # 100
            },  # 220 points (stronger alternative)
        ],
        VerificationLevel.STANDARD: [
            # Path 1: Nonprofit status + governance
            {
                VerificationMethod.NONPROFIT_STATUS,        # 120
                VerificationMethod.ORGANIZATION_BYLAWS,     # 80
                VerificationMethod.BOARD_VERIFICATION,      # 100
                VerificationMethod.EMAIL,                   # 30
            },  # 330 points
        ],
        VerificationLevel.ENHANCED: [
            # Path 1: Full organizational verification
            {
                VerificationMethod.NONPROFIT_STATUS,        # 120
                VerificationMethod.TAX_ID_NONPROFIT,        # 120
                VerificationMethod.ORGANIZATION_BYLAWS,     # 80
                VerificationMethod.BOARD_VERIFICATION,      # 100
                VerificationMethod.MISSION_ALIGNMENT,       # 80
                VerificationMethod.EMAIL,                   # 30
                VerificationMethod.PHONE,                   # 30
            },  # 560 points
        ],
        VerificationLevel.COMPLETE: [
            # Path 1: Comprehensive organizational verification
            {
                VerificationMethod.NONPROFIT_STATUS,        # 120
                VerificationMethod.TAX_ID_NONPROFIT,        # 120
                VerificationMethod.ORGANIZATION_BYLAWS,     # 80
                VerificationMethod.BOARD_VERIFICATION,      # 100
                VerificationMethod.MISSION_ALIGNMENT,       # 80
                VerificationMethod.ORG_REFERENCES,          # 50 (x3 = 150)
                VerificationMethod.COMMUNITY_ENDORSEMENT,   # 60
                VerificationMethod.NOTARY_VERIFICATION,     # 90
                VerificationMethod.EMAIL,                   # 30
                VerificationMethod.PHONE,                   # 30
            },  # 860 points
        ],
    },
}


# ============================================================================
# AUTHORIZED VERIFIER SYSTEM
# ============================================================================

class VerifierCredential(str, PyEnum):
    """
    Credentials that qualify someone as an Authorized Verifier.
    
    Authorized Verifiers can perform two-party verifications for individuals.
    They must themselves be highly verified (STANDARD+ level).
    """
    
    NOTARY_PUBLIC = "notary_public"                      # Licensed notary
    ATTORNEY = "attorney"                                # Licensed attorney/bar member
    COMMUNITY_LEADER = "community_leader"                # Verified community organization leader
    VERIFIED_BUSINESS_OWNER = "verified_business_owner"  # COMPLETE-level verified business owner
    ORGANIZATION_DIRECTOR = "organization_director"      # COMPLETE-level verified org director
    GOVERNMENT_OFFICIAL = "government_official"          # Verified government employee/official
    TRUSTED_VERIFIER = "trusted_verifier"               # 50+ successful verifications performed


# Minimum verification level to become an Authorized Verifier
VERIFIER_MINIMUM_LEVEL = VerificationLevel.STANDARD  # 250+ points

# Credentials that automatically qualify someone as an Authorized Verifier
AUTO_VERIFIER_CREDENTIALS = [
    VerifierCredential.NOTARY_PUBLIC,
    VerifierCredential.ATTORNEY,
    VerifierCredential.GOVERNMENT_OFFICIAL,
]

# Credentials that can qualify with additional verification
QUALIFIED_VERIFIER_CREDENTIALS = [
    VerifierCredential.COMMUNITY_LEADER,
    VerifierCredential.VERIFIED_BUSINESS_OWNER,  # Must be COMPLETE level
    VerifierCredential.ORGANIZATION_DIRECTOR,    # Must be COMPLETE level
]


# ============================================================================
# HELPER FUNCTIONS - PROGRESSIVE TRUST SCORING
# ============================================================================

def calculate_trust_score(
    completed_methods: Dict[VerificationMethod, int],
    user_type: UserType,
) -> int:
    """
    Calculate total trust score from completed verification methods.
    
    Args:
        completed_methods: Dict mapping method to completion count (for multipliers)
        user_type: Type of user account
        
    Returns:
        Total trust score (points)
    """
    total_score = 0
    applicable_methods = USER_TYPE_METHODS.get(user_type, set())
    
    for method, count in completed_methods.items():
        if method not in applicable_methods:
            continue  # Method doesn't apply to this user type
            
        score_info = METHOD_SCORES.get(method)
        if not score_info:
            continue
            
        # Apply multiplier if applicable (e.g., multiple references)
        effective_count = min(count, score_info.max_multiplier)
        method_points = score_info.points * effective_count
        total_score += int(method_points)
    
    return total_score


def calculate_verification_level(
    trust_score: int,
) -> VerificationLevel:
    """
    Determine verification level from trust score.
    
    Args:
        trust_score: Total accumulated trust points
        
    Returns:
        Achieved verification level
    """
    # Check from highest to lowest
    for level in reversed(list(VerificationLevel)):
        threshold = LEVEL_THRESHOLDS.get(level, 0)
        if trust_score >= threshold:
            return level
    
    return VerificationLevel.UNVERIFIED


def get_next_level_requirements(
    current_score: int,
    user_type: UserType,
    completed_methods: Set[VerificationMethod],
) -> tuple[VerificationLevel, int, List[Set[VerificationMethod]]]:
    """
    Get requirements to reach the next verification level.
    
    Args:
        current_score: Current trust score
        user_type: Type of user account
        completed_methods: Methods already completed
        
    Returns:
        Tuple of (next_level, points_needed, suggested_method_combinations)
    """
    current_level = calculate_verification_level(current_score)
    
    # Find next level
    levels = list(VerificationLevel)
    try:
        current_index = levels.index(current_level)
        if current_index >= len(levels) - 1:
            return current_level, 0, []  # Already at max
        next_level = levels[current_index + 1]
    except ValueError:
        return VerificationLevel.UNVERIFIED, LEVEL_THRESHOLDS[VerificationLevel.MINIMAL], []
    
    # Calculate points needed
    next_threshold = LEVEL_THRESHOLDS.get(next_level, 0)
    points_needed = max(0, next_threshold - current_score)
    
    # Get suggested paths for next level
    suggested_paths = SUGGESTED_PATHS.get(user_type, {}).get(next_level, [])
    
    # Filter to paths that don't require already-completed methods
    # (show alternative paths)
    filtered_paths = []
    for path in suggested_paths:
        if not path.issubset(completed_methods):
            filtered_paths.append(path)
    
    return next_level, points_needed, filtered_paths


def get_applicable_methods(user_type: UserType) -> Set[VerificationMethod]:
    """
    Get all verification methods applicable to a user type.
    
    Args:
        user_type: Type of user account
        
    Returns:
        Set of applicable verification methods
    """
    return USER_TYPE_METHODS.get(user_type, set())


def get_method_details(method: VerificationMethod) -> Optional[VerificationMethodScore]:
    """
    Get scoring details for a verification method.
    
    Args:
        method: Verification method
        
    Returns:
        VerificationMethodScore with points, multipliers, etc.
    """
    return METHOD_SCORES.get(method)


def is_method_expired(
    method: VerificationMethod,
    completed_date: str,  # ISO format date
) -> bool:
    """
    Check if a verification method has expired and needs renewal.
    
    Args:
        method: Verification method
        completed_date: Date method was completed (ISO format)
        
    Returns:
        True if expired, False otherwise
    """
    score_info = METHOD_SCORES.get(method)
    if not score_info or score_info.decay_days == 0:
        return False  # No expiration
    
    from datetime import datetime, timedelta
    
    try:
        completed = datetime.fromisoformat(completed_date)
        expiry = completed + timedelta(days=score_info.decay_days)
        return datetime.now() > expiry
    except ValueError:
        return False  # Invalid date format, treat as not expired


def get_baseline_methods(user_type: UserType) -> Set[VerificationMethod]:
    """
    Get recommended baseline methods for fastest path to MINIMAL level.
    
    These are NOT required, but provide the strongest single-method or
    minimal-combination paths to platform access.
    
    Args:
        user_type: Type of user account
        
    Returns:
        Set of recommended baseline methods
    """
    return BASELINE_METHODS.get(user_type, set())


# ============================================================================
# LEGACY COMPATIBILITY (For migration from old system)
# ============================================================================

def get_requirements_for_level(
    user_type: str,
    level: VerificationLevel
) -> Set[VerificationMethod]:
    """
    DEPRECATED: Old API for hard requirements.
    
    Returns suggested methods for the level, but they are NOT required.
    Use get_next_level_requirements() for new scoring-based approach.
    """
    user_type_enum = UserType(user_type) if isinstance(user_type, str) else user_type
    suggested = SUGGESTED_PATHS.get(user_type_enum, {}).get(level, [])
    if suggested:
        return suggested[0]  # Return first suggested path
    return set()


def get_next_level(current_level: VerificationLevel) -> Optional[VerificationLevel]:
    """
    DEPRECATED: Use calculate_verification_level() instead.
    
    Get the next verification level.
    """
    levels = list(VerificationLevel)
    try:
        current_index = levels.index(current_level)
        if current_index < len(levels) - 1:
            return levels[current_index + 1]
    except ValueError:
        pass
    return None


def get_missing_methods(
    user_type: str,
    target_level: VerificationLevel,
    completed_methods: Set[VerificationMethod]
) -> Set[VerificationMethod]:
    """
    DEPRECATED: Old API for hard requirements.
    
    In new system, there are no "missing" methods - just points needed.
    Use get_next_level_requirements() instead.
    """
    required = get_requirements_for_level(user_type, target_level)
    return required - completed_methods


def calculate_level_from_methods(
    user_type: str,
    completed_methods: Set[VerificationMethod]
) -> VerificationLevel:
    """
    DEPRECATED: Use calculate_trust_score() + calculate_verification_level().
    
    Calculate verification level from completed methods (assumes 1x each).
    """
    user_type_enum = UserType(user_type) if isinstance(user_type, str) else user_type
    method_counts = {method: 1 for method in completed_methods}
    score = calculate_trust_score(method_counts, user_type_enum)
    return calculate_verification_level(score)
