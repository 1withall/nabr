"""
Enhanced verification models with tiered verification system.

This module extends the base verification system to support:
- Multiple verification levels (Unverified to Completely Verified)
- Different verification paths for each user type
- Verifier authorization and credentials
- Verification method tracking
"""

from enum import Enum as PyEnum


class VerificationLevel(str, PyEnum):
    """
    Tiered verification levels for users.
    
    Each level represents increasing degrees of identity verification:
    - UNVERIFIED: No verification completed
    - MINIMAL: Basic email/phone verification
    - BASIC: Government ID verification
    - STANDARD: Two-party in-person verification
    - ENHANCED: Additional documentation (business license, etc.)
    - COMPLETE: Full verification with all supporting documents
    """
    
    UNVERIFIED = "unverified"
    MINIMAL = "minimal"           # Email + Phone verified
    BASIC = "basic"               # Government ID verified
    STANDARD = "standard"         # Two-party in-person verification
    ENHANCED = "enhanced"         # Additional documentation
    COMPLETE = "complete"         # All verification paths completed


class VerificationMethod(str, PyEnum):
    """
    Methods used to verify identity.
    
    Different methods contribute to different verification levels:
    - EMAIL: Email address confirmation
    - PHONE: SMS phone verification
    - GOVERNMENT_ID: Driver's license, passport, etc.
    - IN_PERSON_TWO_PARTY: Two verified users confirm identity
    - BUSINESS_LICENSE: Business registration documents
    - TAX_ID: EIN/Tax ID verification
    - NOTARY: Notarized identity verification
    - ORGANIZATION_501C3: 501(c)(3) tax-exempt status
    - PROFESSIONAL_LICENSE: Professional credentials (notary, attorney, etc.)
    - COMMUNITY_LEADER: Verified community organization leader
    - BIOMETRIC: Facial recognition or fingerprint (future)
    """
    
    EMAIL = "email"
    PHONE = "phone"
    GOVERNMENT_ID = "government_id"
    IN_PERSON_TWO_PARTY = "in_person_two_party"
    BUSINESS_LICENSE = "business_license"
    TAX_ID = "tax_id"
    NOTARY = "notary"
    ORGANIZATION_501C3 = "organization_501c3"
    PROFESSIONAL_LICENSE = "professional_license"
    COMMUNITY_LEADER = "community_leader"
    BIOMETRIC = "biometric"


class VerifierCredential(str, PyEnum):
    """
    Credentials that authorize a user to be a verifier.
    
    Verifiers must have rigorous verification themselves:
    - NOTARY_PUBLIC: Licensed notary public (government-verified)
    - ATTORNEY: Licensed attorney (bar-verified)
    - COMMUNITY_LEADER: Verified leader of trusted organization
    - VERIFIED_BUSINESS_OWNER: Fully verified business owner
    - ORGANIZATION_DIRECTOR: Director of 501(c)(3) organization
    - GOVERNMENT_OFFICIAL: Government employee (verified)
    - TRUSTED_VERIFIER: Users who completed 50+ successful verifications
    """
    
    NOTARY_PUBLIC = "notary_public"
    ATTORNEY = "attorney"
    COMMUNITY_LEADER = "community_leader"
    VERIFIED_BUSINESS_OWNER = "verified_business_owner"
    ORGANIZATION_DIRECTOR = "organization_director"
    GOVERNMENT_OFFICIAL = "government_official"
    TRUSTED_VERIFIER = "trusted_verifier"


class VerificationPathIndividual(str, PyEnum):
    """
    Verification paths specific to individual users.
    
    Path to COMPLETE verification for individuals:
    1. Email + Phone (MINIMAL)
    2. Government ID (BASIC)
    3. Two-party in-person (STANDARD)
    4. Optional: Additional methods for ENHANCED/COMPLETE
    """
    
    PATH_STANDARD = "standard"           # Email → Phone → ID → Two-party
    PATH_NOTARY = "notary"               # Email → Phone → Notarized ID
    PATH_BIOMETRIC = "biometric"         # Email → Phone → ID → Biometric


class VerificationPathBusiness(str, PyEnum):
    """
    Verification paths specific to business users.
    
    Path to COMPLETE verification for businesses:
    1. Email + Phone (MINIMAL)
    2. Business License (BASIC)
    3. Tax ID/EIN (STANDARD)
    4. Owner verification (ENHANCED)
    5. Physical location verification (COMPLETE)
    """
    
    PATH_STANDARD = "standard"           # Email → Phone → License → Tax ID → Owner
    PATH_NOTARY = "notary"               # Email → Phone → License → Notarized docs
    PATH_GOVERNMENT = "government"       # Email → Phone → Government verification


class VerificationPathOrganization(str, PyEnum):
    """
    Verification paths specific to organization users.
    
    Path to COMPLETE verification for organizations:
    1. Email + Phone (MINIMAL)
    2. 501(c)(3) or incorporation docs (BASIC)
    3. Tax ID/EIN (STANDARD)
    4. Director verification (ENHANCED)
    5. Physical location + board verification (COMPLETE)
    """
    
    PATH_NONPROFIT = "nonprofit"         # 501(c)(3) → Tax ID → Director → Board
    PATH_COMMUNITY_GROUP = "community"   # Incorporation → Community leader verification
    PATH_RELIGIOUS = "religious"         # Religious organization documentation
    PATH_GOVERNMENT = "government"       # Government agency verification


# Verification level requirements by user type
VERIFICATION_REQUIREMENTS = {
    "individual": {
        VerificationLevel.MINIMAL: [
            VerificationMethod.EMAIL,
            VerificationMethod.PHONE,
        ],
        VerificationLevel.BASIC: [
            VerificationMethod.EMAIL,
            VerificationMethod.PHONE,
            VerificationMethod.GOVERNMENT_ID,
        ],
        VerificationLevel.STANDARD: [
            VerificationMethod.EMAIL,
            VerificationMethod.PHONE,
            VerificationMethod.GOVERNMENT_ID,
            VerificationMethod.IN_PERSON_TWO_PARTY,
        ],
        VerificationLevel.ENHANCED: [
            VerificationMethod.EMAIL,
            VerificationMethod.PHONE,
            VerificationMethod.GOVERNMENT_ID,
            VerificationMethod.IN_PERSON_TWO_PARTY,
            # Plus one of: NOTARY, PROFESSIONAL_LICENSE, or COMMUNITY_LEADER
        ],
        VerificationLevel.COMPLETE: [
            # All ENHANCED requirements plus BIOMETRIC or multiple additional methods
        ],
    },
    "business": {
        VerificationLevel.MINIMAL: [
            VerificationMethod.EMAIL,
            VerificationMethod.PHONE,
        ],
        VerificationLevel.BASIC: [
            VerificationMethod.EMAIL,
            VerificationMethod.PHONE,
            VerificationMethod.BUSINESS_LICENSE,
        ],
        VerificationLevel.STANDARD: [
            VerificationMethod.EMAIL,
            VerificationMethod.PHONE,
            VerificationMethod.BUSINESS_LICENSE,
            VerificationMethod.TAX_ID,
        ],
        VerificationLevel.ENHANCED: [
            VerificationMethod.EMAIL,
            VerificationMethod.PHONE,
            VerificationMethod.BUSINESS_LICENSE,
            VerificationMethod.TAX_ID,
            VerificationMethod.GOVERNMENT_ID,  # Owner's ID
        ],
        VerificationLevel.COMPLETE: [
            # All ENHANCED requirements plus physical location verification
            # and in-person owner verification
        ],
    },
    "organization": {
        VerificationLevel.MINIMAL: [
            VerificationMethod.EMAIL,
            VerificationMethod.PHONE,
        ],
        VerificationLevel.BASIC: [
            VerificationMethod.EMAIL,
            VerificationMethod.PHONE,
            VerificationMethod.ORGANIZATION_501C3,  # Or incorporation docs
        ],
        VerificationLevel.STANDARD: [
            VerificationMethod.EMAIL,
            VerificationMethod.PHONE,
            VerificationMethod.ORGANIZATION_501C3,
            VerificationMethod.TAX_ID,
        ],
        VerificationLevel.ENHANCED: [
            VerificationMethod.EMAIL,
            VerificationMethod.PHONE,
            VerificationMethod.ORGANIZATION_501C3,
            VerificationMethod.TAX_ID,
            VerificationMethod.GOVERNMENT_ID,  # Director's ID
        ],
        VerificationLevel.COMPLETE: [
            # All ENHANCED requirements plus board member verification
            # and community leader endorsement
        ],
    },
}


# Minimum verification level required to become an authorized verifier
VERIFIER_MINIMUM_LEVEL = VerificationLevel.STANDARD


# Credentials that automatically qualify someone as a verifier
AUTO_VERIFIER_CREDENTIALS = [
    VerifierCredential.NOTARY_PUBLIC,
    VerifierCredential.ATTORNEY,
    VerifierCredential.GOVERNMENT_OFFICIAL,
]
