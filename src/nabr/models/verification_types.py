"""
Verification types and requirements for tiered verification system.

Each user type (Individual, Business, Organization) has unique verification
requirements and workflows.

INDIVIDUALS - Original Spec:
  "Minimal verification" requires in-person confirmation by at least TWO trusted
  community members (notaries, community leaders, or other recognized figures).
  This is the BASELINE to access platform features.

BUSINESSES - Logical Requirements:
  Must verify business legitimacy through official documentation before
  operating on platform (business license, tax ID, ownership proof).

ORGANIZATIONS - Logical Requirements:
  Must verify organizational legitimacy and mission alignment through
  documentation (501(c)(3) status, leadership verification, mission alignment).
"""

from enum import Enum as PyEnum
from typing import Dict, List, Set


class VerificationLevel(str, PyEnum):
    """
    Tiered verification levels.
    
    Each user type progresses through these levels differently.
    """
    
    UNVERIFIED = "unverified"      # No verification - CANNOT access platform features
    MINIMAL = "minimal"            # Type-specific baseline verification (see below)
    STANDARD = "standard"          # Enhanced verification for each type
    ENHANCED = "enhanced"          # Additional credentials/trust signals
    COMPLETE = "complete"          # Full verification with all methods


class VerificationMethod(str, PyEnum):
    """
    Methods used to verify identity/legitimacy.
    
    Different methods apply to different user types.
    """
    
    # Universal methods (all user types)
    EMAIL = "email"                              # Email address confirmation
    PHONE = "phone"                              # Phone number verification
    
    # Individual-specific methods
    IN_PERSON_TWO_PARTY = "in_person_two_party"  # Two Authorized Verifiers confirm identity
    GOVERNMENT_ID = "government_id"              # Driver's license, passport, etc.
    BIOMETRIC = "biometric"                      # Facial recognition (future)
    PERSONAL_REFERENCE = "personal_reference"    # References from verified community members
    
    # Business-specific methods
    BUSINESS_LICENSE = "business_license"        # Business registration/license
    TAX_ID_BUSINESS = "tax_id_business"         # EIN verification
    BUSINESS_ADDRESS = "business_address"        # Physical business location verification
    BUSINESS_INSURANCE = "business_insurance"    # Liability insurance verification
    OWNER_VERIFICATION = "owner_verification"    # Business owner identity verification
    
    # Organization-specific methods
    NONPROFIT_STATUS = "nonprofit_status"        # 501(c)(3) or equivalent tax-exempt status
    TAX_ID_NONPROFIT = "tax_id_nonprofit"       # EIN for non-profit
    ORGANIZATION_BYLAWS = "organization_bylaws"  # Governing documents
    BOARD_VERIFICATION = "board_verification"    # Board of directors verification
    MISSION_ALIGNMENT = "mission_alignment"      # Community alignment review
    
    # Enhanced methods (optional for higher levels)
    NOTARY_VERIFICATION = "notary_verification"  # Notarized documents
    PROFESSIONAL_LICENSE = "professional_license" # Professional credentials
    COMMUNITY_ENDORSEMENT = "community_endorsement" # Community leader endorsement


class VerifierCredential(str, PyEnum):
    """
    Credentials that qualify someone as an Authorized Verifier.
    
    Authorized Verifiers can perform two-party verifications for individuals.
    They must themselves be highly verified.
    """
    
    NOTARY_PUBLIC = "notary_public"                      # Licensed notary
    ATTORNEY = "attorney"                                # Licensed attorney/bar member
    COMMUNITY_LEADER = "community_leader"                # Verified community organization leader
    VERIFIED_BUSINESS_OWNER = "verified_business_owner"  # COMPLETE-level verified business owner
    ORGANIZATION_DIRECTOR = "organization_director"      # COMPLETE-level verified org director
    GOVERNMENT_OFFICIAL = "government_official"          # Verified government employee/official
    TRUSTED_VERIFIER = "trusted_verifier"               # 50+ successful verifications performed


# User type path enums for type safety
class IndividualVerificationPath(str, PyEnum):
    """Verification progression for Individuals."""
    UNVERIFIED = "unverified"
    MINIMAL = "minimal"        # TWO-PARTY IN-PERSON (baseline per original spec)
    STANDARD = "standard"      # Minimal + Government ID
    ENHANCED = "enhanced"      # Standard + Personal references
    COMPLETE = "complete"      # All individual methods


class BusinessVerificationPath(str, PyEnum):
    """Verification progression for Businesses."""
    UNVERIFIED = "unverified"
    MINIMAL = "minimal"        # Business license + Tax ID + Email/Phone
    STANDARD = "standard"      # Minimal + Business address + Owner verification
    ENHANCED = "enhanced"      # Standard + Insurance + Notarized docs
    COMPLETE = "complete"      # All business methods


class OrganizationVerificationPath(str, PyEnum):
    """Verification progression for Organizations."""
    UNVERIFIED = "unverified"
    MINIMAL = "minimal"        # 501(c)(3) status + Tax ID + Email/Phone
    STANDARD = "standard"      # Minimal + Bylaws + Board verification
    ENHANCED = "enhanced"      # Standard + Mission alignment + Community endorsement
    COMPLETE = "complete"      # All organization methods


# ============================================================================
# VERIFICATION REQUIREMENTS BY USER TYPE AND LEVEL
# ============================================================================

# INDIVIDUAL VERIFICATION REQUIREMENTS
# Per original spec: "Minimal verification" = in-person confirmation by 2 trusted members
INDIVIDUAL_VERIFICATION_REQUIREMENTS: Dict[VerificationLevel, Set[VerificationMethod]] = {
    VerificationLevel.UNVERIFIED: set(),
    
    # BASELINE: Two-party in-person verification (ORIGINAL SPEC)
    VerificationLevel.MINIMAL: {
        VerificationMethod.EMAIL,
        VerificationMethod.PHONE,
        VerificationMethod.IN_PERSON_TWO_PARTY,  # Must have 2 Authorized Verifiers confirm
    },
    
    # Enhanced identity verification
    VerificationLevel.STANDARD: {
        VerificationMethod.EMAIL,
        VerificationMethod.PHONE,
        VerificationMethod.IN_PERSON_TWO_PARTY,
        VerificationMethod.GOVERNMENT_ID,  # Driver's license, passport, etc.
    },
    
    # Additional trust signals
    VerificationLevel.ENHANCED: {
        VerificationMethod.EMAIL,
        VerificationMethod.PHONE,
        VerificationMethod.IN_PERSON_TWO_PARTY,
        VerificationMethod.GOVERNMENT_ID,
        VerificationMethod.PERSONAL_REFERENCE,  # References from community
    },
    
    # Full verification
    VerificationLevel.COMPLETE: {
        VerificationMethod.EMAIL,
        VerificationMethod.PHONE,
        VerificationMethod.IN_PERSON_TWO_PARTY,
        VerificationMethod.GOVERNMENT_ID,
        VerificationMethod.PERSONAL_REFERENCE,
        VerificationMethod.NOTARY_VERIFICATION,  # Notarized identity confirmation
    },
}


# BUSINESS VERIFICATION REQUIREMENTS
# Businesses must prove legitimacy through official business documentation
BUSINESS_VERIFICATION_REQUIREMENTS: Dict[VerificationLevel, Set[VerificationMethod]] = {
    VerificationLevel.UNVERIFIED: set(),
    
    # BASELINE: Prove business legitimacy
    VerificationLevel.MINIMAL: {
        VerificationMethod.EMAIL,  # Business email
        VerificationMethod.PHONE,  # Business phone
        VerificationMethod.BUSINESS_LICENSE,  # Official business registration/license
        VerificationMethod.TAX_ID_BUSINESS,  # EIN verification
    },
    
    # Verify physical presence and ownership
    VerificationLevel.STANDARD: {
        VerificationMethod.EMAIL,
        VerificationMethod.PHONE,
        VerificationMethod.BUSINESS_LICENSE,
        VerificationMethod.TAX_ID_BUSINESS,
        VerificationMethod.BUSINESS_ADDRESS,  # Physical location verification
        VerificationMethod.OWNER_VERIFICATION,  # Owner identity confirmed
    },
    
    # Professional operations verification
    VerificationLevel.ENHANCED: {
        VerificationMethod.EMAIL,
        VerificationMethod.PHONE,
        VerificationMethod.BUSINESS_LICENSE,
        VerificationMethod.TAX_ID_BUSINESS,
        VerificationMethod.BUSINESS_ADDRESS,
        VerificationMethod.OWNER_VERIFICATION,
        VerificationMethod.BUSINESS_INSURANCE,  # Liability insurance
        VerificationMethod.NOTARY_VERIFICATION,  # Notarized business documents
    },
    
    # Full business verification
    VerificationLevel.COMPLETE: {
        VerificationMethod.EMAIL,
        VerificationMethod.PHONE,
        VerificationMethod.BUSINESS_LICENSE,
        VerificationMethod.TAX_ID_BUSINESS,
        VerificationMethod.BUSINESS_ADDRESS,
        VerificationMethod.OWNER_VERIFICATION,
        VerificationMethod.BUSINESS_INSURANCE,
        VerificationMethod.NOTARY_VERIFICATION,
        VerificationMethod.PROFESSIONAL_LICENSE,  # If applicable (contractors, etc.)
        VerificationMethod.COMMUNITY_ENDORSEMENT,  # Community reputation
    },
}


# ORGANIZATION VERIFICATION REQUIREMENTS
# Organizations must prove legitimacy and mission alignment
ORGANIZATION_VERIFICATION_REQUIREMENTS: Dict[VerificationLevel, Set[VerificationMethod]] = {
    VerificationLevel.UNVERIFIED: set(),
    
    # BASELINE: Prove non-profit/org legitimacy
    VerificationLevel.MINIMAL: {
        VerificationMethod.EMAIL,  # Organization email
        VerificationMethod.PHONE,  # Organization phone
        VerificationMethod.NONPROFIT_STATUS,  # 501(c)(3) or equivalent documentation
        VerificationMethod.TAX_ID_NONPROFIT,  # EIN verification
    },
    
    # Verify governance and leadership
    VerificationLevel.STANDARD: {
        VerificationMethod.EMAIL,
        VerificationMethod.PHONE,
        VerificationMethod.NONPROFIT_STATUS,
        VerificationMethod.TAX_ID_NONPROFIT,
        VerificationMethod.ORGANIZATION_BYLAWS,  # Governing documents
        VerificationMethod.BOARD_VERIFICATION,  # Board of directors verified
    },
    
    # Verify mission and community fit
    VerificationLevel.ENHANCED: {
        VerificationMethod.EMAIL,
        VerificationMethod.PHONE,
        VerificationMethod.NONPROFIT_STATUS,
        VerificationMethod.TAX_ID_NONPROFIT,
        VerificationMethod.ORGANIZATION_BYLAWS,
        VerificationMethod.BOARD_VERIFICATION,
        VerificationMethod.MISSION_ALIGNMENT,  # Mission aligns with community values
        VerificationMethod.COMMUNITY_ENDORSEMENT,  # Community support/endorsement
    },
    
    # Full organization verification
    VerificationLevel.COMPLETE: {
        VerificationMethod.EMAIL,
        VerificationMethod.PHONE,
        VerificationMethod.NONPROFIT_STATUS,
        VerificationMethod.TAX_ID_NONPROFIT,
        VerificationMethod.ORGANIZATION_BYLAWS,
        VerificationMethod.BOARD_VERIFICATION,
        VerificationMethod.MISSION_ALIGNMENT,
        VerificationMethod.COMMUNITY_ENDORSEMENT,
        VerificationMethod.NOTARY_VERIFICATION,  # Notarized organizational documents
    },
}


# Combined requirements map
VERIFICATION_REQUIREMENTS: Dict[str, Dict[VerificationLevel, Set[VerificationMethod]]] = {
    "individual": INDIVIDUAL_VERIFICATION_REQUIREMENTS,
    "business": BUSINESS_VERIFICATION_REQUIREMENTS,
    "organization": ORGANIZATION_VERIFICATION_REQUIREMENTS,
}


# ============================================================================
# AUTHORIZED VERIFIER REQUIREMENTS
# ============================================================================

# Minimum verification level to become an Authorized Verifier
# Authorized Verifiers perform two-party verifications for INDIVIDUALS
VERIFIER_MINIMUM_LEVEL = VerificationLevel.STANDARD

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
# HELPER FUNCTIONS
# ============================================================================

def get_requirements_for_level(user_type: str, level: VerificationLevel) -> Set[VerificationMethod]:
    """
    Get verification method requirements for a specific user type and level.
    
    Args:
        user_type: "individual", "business", or "organization"
        level: Target verification level
        
    Returns:
        Set of VerificationMethod enums required for that level
    """
    return VERIFICATION_REQUIREMENTS.get(user_type, {}).get(level, set())


def get_next_level(current_level: VerificationLevel) -> VerificationLevel | None:
    """
    Get the next verification level.
    
    Args:
        current_level: Current verification level
        
    Returns:
        Next level, or None if already at COMPLETE
    """
    levels = [
        VerificationLevel.UNVERIFIED,
        VerificationLevel.MINIMAL,
        VerificationLevel.STANDARD,
        VerificationLevel.ENHANCED,
        VerificationLevel.COMPLETE,
    ]
    
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
    Get verification methods still needed to reach target level.
    
    Args:
        user_type: "individual", "business", or "organization"
        target_level: Desired verification level
        completed_methods: Methods already completed
        
    Returns:
        Set of methods still needed
    """
    required = get_requirements_for_level(user_type, target_level)
    return required - completed_methods


def calculate_level_from_methods(
    user_type: str,
    completed_methods: Set[VerificationMethod]
) -> VerificationLevel:
    """
    Calculate current verification level based on completed methods.
    
    Args:
        user_type: "individual", "business", or "organization"
        completed_methods: Set of completed verification methods
        
    Returns:
        Highest verification level achieved
    """
    type_requirements = VERIFICATION_REQUIREMENTS.get(user_type, {})
    
    # Check from highest to lowest level
    for level in reversed(list(VerificationLevel)):
        required_methods = type_requirements.get(level, set())
        if required_methods.issubset(completed_methods):
            return level
    
    return VerificationLevel.UNVERIFIED
