"""
Unit tests for progressive trust verification system.

Tests the core verification logic in models/verification_types.py:
- Trust score calculations
- Verification level determination
- Next level requirements
- Method expiry checking
- Applicable methods for user types
"""

import pytest
from datetime import datetime, timedelta
from nabr.models.verification_types import (
    VerificationMethod,
    VerificationLevel,
    UserType,
    calculate_trust_score,
    calculate_verification_level,
    get_next_level_requirements,
    is_method_expired,
    get_applicable_methods,
    METHOD_SCORES,
    LEVEL_THRESHOLDS,
)


class TestTrustScoreCalculation:
    """Test trust score calculation with various method combinations."""
    
    def test_single_two_party_verification_reaches_minimal(self):
        """Test CORE INCLUSIVE METHOD: Two-party alone = MINIMAL level."""
        completed_methods = {
            VerificationMethod.IN_PERSON_TWO_PARTY: 1
        }
        score = calculate_trust_score(completed_methods, UserType.INDIVIDUAL)
        assert score == 150, "Two-party verification should give 150 points"
        assert score >= LEVEL_THRESHOLDS[VerificationLevel.MINIMAL], "Should reach MINIMAL"
    
    def test_email_phone_optional_not_required(self):
        """Test that email/phone are OPTIONAL and worth 30 points each."""
        # Email alone
        email_only = {VerificationMethod.EMAIL: 1}
        email_score = calculate_trust_score(email_only, UserType.INDIVIDUAL)
        assert email_score == 30, "Email should give 30 points"
        assert email_score < LEVEL_THRESHOLDS[VerificationLevel.MINIMAL], "Email alone should NOT reach MINIMAL"
        
        # Phone alone
        phone_only = {VerificationMethod.PHONE: 1}
        phone_score = calculate_trust_score(phone_only, UserType.INDIVIDUAL)
        assert phone_score == 30, "Phone should give 30 points"
        assert phone_score < LEVEL_THRESHOLDS[VerificationLevel.MINIMAL], "Phone alone should NOT reach MINIMAL"
        
        # Both together still not enough
        email_phone = {
            VerificationMethod.EMAIL: 1,
            VerificationMethod.PHONE: 1
        }
        both_score = calculate_trust_score(email_phone, UserType.INDIVIDUAL)
        assert both_score == 60, "Email + Phone should give 60 points"
        assert both_score < LEVEL_THRESHOLDS[VerificationLevel.MINIMAL], "Email + Phone should NOT reach MINIMAL alone"
    
    def test_government_id_plus_email_phone_reaches_minimal(self):
        """Test alternative path: Government ID + email + phone = MINIMAL."""
        completed_methods = {
            VerificationMethod.GOVERNMENT_ID: 1,
            VerificationMethod.EMAIL: 1,
            VerificationMethod.PHONE: 1
        }
        score = calculate_trust_score(completed_methods, UserType.INDIVIDUAL)
        assert score == 160, "Government ID (100) + Email (30) + Phone (30) should give 160 points"
        assert score >= LEVEL_THRESHOLDS[VerificationLevel.MINIMAL], "Should reach MINIMAL"
    
    def test_multiplier_for_references(self):
        """Test that references use 3x multiplier."""
        completed_methods = {
            VerificationMethod.PERSONAL_REFERENCE: 3  # 3 references
        }
        score = calculate_trust_score(completed_methods, UserType.INDIVIDUAL)
        # Base: 50 points, max_multiplier: 3, so 50 * 3 = 150
        assert score == 150, "3 personal references should give 150 points (50 * 3)"
        assert score >= LEVEL_THRESHOLDS[VerificationLevel.MINIMAL], "3 references should reach MINIMAL"
    
    def test_multiplier_for_attestations(self):
        """Test that community attestations use 2x multiplier."""
        completed_methods = {
            VerificationMethod.COMMUNITY_ATTESTATION: 2  # 2 attestations
        }
        score = calculate_trust_score(completed_methods, UserType.INDIVIDUAL)
        # Base: 40 points, max_multiplier: 2, so 40 * 2 = 80
        assert score == 80, "2 community attestations should give 80 points (40 * 2)"
    
    def test_standard_level_requires_250_points(self):
        """Test reaching STANDARD level with multiple methods."""
        completed_methods = {
            VerificationMethod.IN_PERSON_TWO_PARTY: 1,  # 150
            VerificationMethod.GOVERNMENT_ID: 1,  # 100
            VerificationMethod.EMAIL: 1,  # 30
            VerificationMethod.PHONE: 1  # 30
        }
        score = calculate_trust_score(completed_methods, UserType.INDIVIDUAL)
        assert score == 310, "Should have 310 points"
        level = calculate_verification_level(score)
        assert level == VerificationLevel.STANDARD, "310 points should reach STANDARD"
    
    def test_business_type_scoring(self):
        """Test business-specific methods."""
        completed_methods = {
            VerificationMethod.BUSINESS_LICENSE: 1,  # 120
            VerificationMethod.EMAIL: 1  # 30
        }
        score = calculate_trust_score(completed_methods, UserType.BUSINESS)
        assert score == 150, "Business license (120) + Email (30) should give 150 points"
        assert score >= LEVEL_THRESHOLDS[VerificationLevel.MINIMAL], "Should reach MINIMAL"
    
    def test_organization_type_scoring(self):
        """Test organization-specific methods."""
        completed_methods = {
            VerificationMethod.NONPROFIT_STATUS: 1,  # 120
            VerificationMethod.EMAIL: 1  # 30
        }
        score = calculate_trust_score(completed_methods, UserType.ORGANIZATION)
        assert score == 150, "Nonprofit status (120) + Email (30) should give 150 points"
        assert score >= LEVEL_THRESHOLDS[VerificationLevel.MINIMAL], "Should reach MINIMAL"


class TestVerificationLevelCalculation:
    """Test verification level determination from trust scores."""
    
    def test_unverified_level(self):
        """Test UNVERIFIED level (0 points)."""
        assert calculate_verification_level(0) == VerificationLevel.UNVERIFIED
        assert calculate_verification_level(99) == VerificationLevel.UNVERIFIED
    
    def test_minimal_level(self):
        """Test MINIMAL level (100-249 points)."""
        assert calculate_verification_level(100) == VerificationLevel.MINIMAL
        assert calculate_verification_level(150) == VerificationLevel.MINIMAL
        assert calculate_verification_level(249) == VerificationLevel.MINIMAL
    
    def test_standard_level(self):
        """Test STANDARD level (250-399 points)."""
        assert calculate_verification_level(250) == VerificationLevel.STANDARD
        assert calculate_verification_level(300) == VerificationLevel.STANDARD
        assert calculate_verification_level(399) == VerificationLevel.STANDARD
    
    def test_enhanced_level(self):
        """Test ENHANCED level (400-599 points)."""
        assert calculate_verification_level(400) == VerificationLevel.ENHANCED
        assert calculate_verification_level(500) == VerificationLevel.ENHANCED
        assert calculate_verification_level(599) == VerificationLevel.ENHANCED
    
    def test_complete_level(self):
        """Test COMPLETE level (600+ points)."""
        assert calculate_verification_level(600) == VerificationLevel.COMPLETE
        assert calculate_verification_level(1000) == VerificationLevel.COMPLETE


class TestNextLevelRequirements:
    """Test calculation of next level requirements and suggested paths."""
    
    def test_next_level_from_unverified(self):
        """Test getting requirements from UNVERIFIED to MINIMAL."""
        current_score = 0
        completed_methods = set()
        
        next_level, points_needed, suggested_paths = get_next_level_requirements(
            current_score, UserType.INDIVIDUAL, completed_methods
        )
        
        assert next_level == VerificationLevel.MINIMAL
        assert points_needed == 100
        assert len(suggested_paths) > 0
        
        # Two-party should be in suggested paths
        has_two_party_path = any(
            VerificationMethod.IN_PERSON_TWO_PARTY in path 
            for path in suggested_paths
        )
        assert has_two_party_path, "Two-party verification should be suggested as CORE INCLUSIVE METHOD"
    
    def test_next_level_from_minimal(self):
        """Test getting requirements from MINIMAL to STANDARD."""
        current_score = 150  # Two-party completed
        completed_methods = {VerificationMethod.IN_PERSON_TWO_PARTY}
        
        next_level, points_needed, suggested_paths = get_next_level_requirements(
            current_score, UserType.INDIVIDUAL, completed_methods
        )
        
        assert next_level == VerificationLevel.STANDARD
        assert points_needed == 100  # Need 100 more to reach 250
        assert len(suggested_paths) > 0
    
    def test_no_next_level_at_complete(self):
        """Test that COMPLETE level has no next level."""
        current_score = 600
        completed_methods = set()
        
        next_level, points_needed, suggested_paths = get_next_level_requirements(
            current_score, UserType.INDIVIDUAL, completed_methods
        )
        
        assert next_level == VerificationLevel.COMPLETE
        assert points_needed == 0
        assert len(suggested_paths) == 0


class TestMethodExpiry:
    """Test verification method expiry checking."""
    
    def test_email_expires_after_365_days(self):
        """Test that email verification expires after 365 days."""
        # Recent email
        recent_date = (datetime.utcnow() - timedelta(days=30)).isoformat()
        assert not is_method_expired(VerificationMethod.EMAIL, recent_date)
        
        # Expired email
        old_date = (datetime.utcnow() - timedelta(days=366)).isoformat()
        assert is_method_expired(VerificationMethod.EMAIL, old_date)
    
    def test_phone_expires_after_365_days(self):
        """Test that phone verification expires after 365 days."""
        # Recent phone
        recent_date = (datetime.utcnow() - timedelta(days=30)).isoformat()
        assert not is_method_expired(VerificationMethod.PHONE, recent_date)
        
        # Expired phone
        old_date = (datetime.utcnow() - timedelta(days=366)).isoformat()
        assert is_method_expired(VerificationMethod.PHONE, old_date)
    
    def test_government_id_expires_after_5_years(self):
        """Test that government ID expires after 1825 days (5 years)."""
        # Recent ID
        recent_date = (datetime.utcnow() - timedelta(days=365)).isoformat()
        assert not is_method_expired(VerificationMethod.GOVERNMENT_ID, recent_date)
        
        # Expired ID
        old_date = (datetime.utcnow() - timedelta(days=1826)).isoformat()
        assert is_method_expired(VerificationMethod.GOVERNMENT_ID, old_date)
    
    def test_biometric_never_expires(self):
        """Test that biometric verification never expires (decay_days=0)."""
        old_date = (datetime.utcnow() - timedelta(days=3650)).isoformat()  # 10 years ago
        assert not is_method_expired(VerificationMethod.BIOMETRIC, old_date)
    
    def test_platform_history_never_expires(self):
        """Test that platform history never expires (decay_days=0)."""
        old_date = (datetime.utcnow() - timedelta(days=3650)).isoformat()  # 10 years ago
        assert not is_method_expired(VerificationMethod.PLATFORM_HISTORY, old_date)


class TestApplicableMethods:
    """Test getting applicable methods for each user type."""
    
    def test_individual_methods(self):
        """Test applicable methods for INDIVIDUAL user type."""
        methods = get_applicable_methods(UserType.INDIVIDUAL)
        
        # Universal methods should be included
        assert VerificationMethod.EMAIL in methods
        assert VerificationMethod.PHONE in methods
        
        # Individual-specific methods should be included
        assert VerificationMethod.IN_PERSON_TWO_PARTY in methods
        assert VerificationMethod.GOVERNMENT_ID in methods
        assert VerificationMethod.PERSONAL_REFERENCE in methods
        
        # Business-specific methods should NOT be included
        assert VerificationMethod.BUSINESS_LICENSE not in methods
        assert VerificationMethod.TAX_ID_BUSINESS not in methods
        
        # Organization-specific methods should NOT be included
        assert VerificationMethod.NONPROFIT_STATUS not in methods
    
    def test_business_methods(self):
        """Test applicable methods for BUSINESS user type."""
        methods = get_applicable_methods(UserType.BUSINESS)
        
        # Universal methods should be included
        assert VerificationMethod.EMAIL in methods
        assert VerificationMethod.PHONE in methods
        
        # Business-specific methods should be included
        assert VerificationMethod.BUSINESS_LICENSE in methods
        assert VerificationMethod.TAX_ID_BUSINESS in methods
        assert VerificationMethod.BUSINESS_ADDRESS in methods
        assert VerificationMethod.OWNER_VERIFICATION in methods
        
        # Individual-specific methods should NOT be included
        assert VerificationMethod.IN_PERSON_TWO_PARTY not in methods
        assert VerificationMethod.PERSONAL_REFERENCE not in methods
        
        # Organization-specific methods should NOT be included
        assert VerificationMethod.NONPROFIT_STATUS not in methods
    
    def test_organization_methods(self):
        """Test applicable methods for ORGANIZATION user type."""
        methods = get_applicable_methods(UserType.ORGANIZATION)
        
        # Universal methods should be included
        assert VerificationMethod.EMAIL in methods
        assert VerificationMethod.PHONE in methods
        
        # Organization-specific methods should be included
        assert VerificationMethod.NONPROFIT_STATUS in methods
        assert VerificationMethod.TAX_ID_NONPROFIT in methods
        assert VerificationMethod.ORGANIZATION_BYLAWS in methods
        assert VerificationMethod.BOARD_VERIFICATION in methods
        
        # Individual-specific methods should NOT be included
        assert VerificationMethod.IN_PERSON_TWO_PARTY not in methods
        assert VerificationMethod.PERSONAL_REFERENCE not in methods
        
        # Business-specific methods should NOT be included
        assert VerificationMethod.BUSINESS_LICENSE not in methods


class TestInclusiveDesignPrinciples:
    """Test that the system adheres to inclusive design principles."""
    
    def test_no_email_phone_id_still_works(self):
        """
        CRITICAL TEST: Person WITHOUT email, phone, or government ID 
        can still reach MINIMAL level via two-party verification.
        """
        # User has ONLY two-party in-person verification
        completed_methods = {
            VerificationMethod.IN_PERSON_TWO_PARTY: 1
        }
        score = calculate_trust_score(completed_methods, UserType.INDIVIDUAL)
        level = calculate_verification_level(score)
        
        assert score == 150, "Two-party should give 150 points"
        assert level == VerificationLevel.MINIMAL, "Should reach MINIMAL level"
        print("\n✅ INCLUSIVE DESIGN VERIFIED: Person without email/phone/ID can verify!")
    
    def test_multiple_paths_to_minimal(self):
        """Test that there are multiple paths to reach MINIMAL level."""
        # Path 1: Two-party alone
        path1 = {VerificationMethod.IN_PERSON_TWO_PARTY: 1}
        score1 = calculate_trust_score(path1, UserType.INDIVIDUAL)
        assert calculate_verification_level(score1) == VerificationLevel.MINIMAL
        
        # Path 2: Government ID + email + phone
        path2 = {
            VerificationMethod.GOVERNMENT_ID: 1,
            VerificationMethod.EMAIL: 1,
            VerificationMethod.PHONE: 1
        }
        score2 = calculate_trust_score(path2, UserType.INDIVIDUAL)
        assert calculate_verification_level(score2) == VerificationLevel.MINIMAL
        
        # Path 3: 3 personal references
        path3 = {VerificationMethod.PERSONAL_REFERENCE: 3}
        score3 = calculate_trust_score(path3, UserType.INDIVIDUAL)
        assert calculate_verification_level(score3) == VerificationLevel.MINIMAL
        
        print(f"\n✅ MULTIPLE PATHS VERIFIED: {3} different ways to reach MINIMAL level")
    
    def test_email_phone_not_required(self):
        """
        CRITICAL TEST: Verify that email and phone are truly OPTIONAL,
        not required at any level.
        """
        # Reach MINIMAL without email/phone
        minimal_methods = {VerificationMethod.IN_PERSON_TWO_PARTY: 1}
        minimal_score = calculate_trust_score(minimal_methods, UserType.INDIVIDUAL)
        assert calculate_verification_level(minimal_score) == VerificationLevel.MINIMAL
        
        # Reach STANDARD without email/phone
        standard_methods = {
            VerificationMethod.IN_PERSON_TWO_PARTY: 1,  # 150
            VerificationMethod.GOVERNMENT_ID: 1,  # 100
            VerificationMethod.BIOMETRIC: 1  # 80
        }
        standard_score = calculate_trust_score(standard_methods, UserType.INDIVIDUAL)
        assert standard_score >= 250
        assert calculate_verification_level(standard_score) == VerificationLevel.STANDARD
        
        print("\n✅ EMAIL/PHONE OPTIONAL VERIFIED: Can reach STANDARD without email or phone!")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
