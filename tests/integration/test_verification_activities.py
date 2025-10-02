"""
Integration tests for verification activities.

Tests the verification activities with real database connections
and Temporal activity execution.
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4

from nabr.temporal.activities.verification import (
    generate_verification_qr_codes,
    check_verifier_authorization,
    calculate_trust_score_activity,
    award_verification_points,
    record_verification_event,
)
from nabr.models.verification_types import VerificationMethod, UserType
from nabr.db.session import AsyncSessionLocal
from nabr.models.user import User
from nabr.models.verification import (
    VerificationRecord,
    VerificationStatus,
    UserVerificationLevel,
    VerifierProfile,
)


@pytest.fixture
async def test_user():
    """Create a test user in the database."""
    async with AsyncSessionLocal() as db:
        user = User(
            id=uuid4(),
            email="test@example.com",
            username="testuser",
            full_name="Test User",
            user_type=UserType.INDIVIDUAL,
            email_verified=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        
        yield user
        
        # Cleanup
        await db.delete(user)
        await db.commit()


@pytest.fixture
async def test_verifier():
    """Create a test verifier with profile."""
    async with AsyncSessionLocal() as db:
        verifier = User(
            id=uuid4(),
            email="verifier@example.com",
            username="testverifier",
            full_name="Test Verifier",
            user_type=UserType.INDIVIDUAL,
            email_verified=True,
        )
        db.add(verifier)
        await db.flush()
        
        # Create verifier profile
        verifier_profile = VerifierProfile(
            user_id=verifier.id,
            is_authorized=True,
            credentials=["NOTARY_PUBLIC"],
            auto_qualified=True,
            total_verifications_performed=0,
        )
        db.add(verifier_profile)
        
        # Create verification level (must be at least MINIMAL)
        verification_level = UserVerificationLevel(
            user_id=verifier.id,
            current_level="MINIMAL",
            completed_methods=["EMAIL", "PHONE", "IN_PERSON_TWO_PARTY"],
            total_methods_completed=3,
        )
        db.add(verification_level)
        
        await db.commit()
        await db.refresh(verifier)
        
        yield verifier
        
        # Cleanup
        await db.delete(verifier_profile)
        await db.delete(verification_level)
        await db.delete(verifier)
        await db.commit()


@pytest.mark.asyncio
class TestQRCodeGeneration:
    """Test QR code generation activity."""
    
    async def test_generate_qr_codes_creates_tokens(self, test_user):
        """Test that QR code generation creates unique tokens."""
        # Create verification record
        async with AsyncSessionLocal() as db:
            verification = VerificationRecord(
                id=uuid4(),
                user_id=test_user.id,
                method=VerificationMethod.IN_PERSON_TWO_PARTY.value,
                status=VerificationStatus.PENDING,
            )
            db.add(verification)
            await db.commit()
            verification_id = str(verification.id)
        
        # Generate QR codes
        result = await generate_verification_qr_codes(
            verification_id=verification_id,
            user_id=str(test_user.id),
            user_name=test_user.full_name,
        )
        
        # Verify result structure
        assert "qr_code_1" in result
        assert "qr_code_2" in result
        assert "token_1" in result
        assert "token_2" in result
        assert "expires_at" in result
        
        # Verify tokens are different
        assert result["token_1"] != result["token_2"]
        
        # Verify tokens are stored in database
        async with AsyncSessionLocal() as db:
            verification = await db.get(VerificationRecord, uuid4(verification_id))
            assert verification.verifier1_token == result["token_1"]
            assert verification.verifier2_token == result["token_2"]
            assert verification.qr_expires_at is not None
            
            # Cleanup
            await db.delete(verification)
            await db.commit()


@pytest.mark.asyncio
class TestVerifierAuthorization:
    """Test verifier authorization checks."""
    
    async def test_authorized_verifier_passes(self, test_verifier):
        """Test that authorized verifier passes authorization check."""
        result = await check_verifier_authorization(
            verifier_id=str(test_verifier.id),
            user_type="individual",
        )
        
        assert result["authorized"] is True
        assert "NOTARY_PUBLIC" in result["credentials"]
        assert result["auto_qualified"] is True
    
    async def test_nonexistent_verifier_fails(self):
        """Test that non-existent verifier fails authorization."""
        result = await check_verifier_authorization(
            verifier_id=str(uuid4()),
            user_type="individual",
        )
        
        assert result["authorized"] is False
        assert result["reason"] == "Verifier not found"
    
    async def test_unverified_user_cannot_verify(self, test_user):
        """Test that unverified user cannot be a verifier."""
        result = await check_verifier_authorization(
            verifier_id=str(test_user.id),
            user_type="individual",
        )
        
        assert result["authorized"] is False
        assert "must be verified" in result["reason"].lower()


@pytest.mark.asyncio
class TestTrustScoreCalculation:
    """Test trust score calculation activity."""
    
    async def test_calculate_score_single_method(self):
        """Test trust score calculation with single method."""
        completed_methods = {
            VerificationMethod.EMAIL.value: 1,
        }
        
        score = await calculate_trust_score_activity(
            completed_methods=completed_methods,
            user_type="individual",
        )
        
        assert score == 30  # Email is worth 30 points
    
    async def test_calculate_score_multiple_methods(self):
        """Test trust score calculation with multiple methods."""
        completed_methods = {
            VerificationMethod.EMAIL.value: 1,
            VerificationMethod.PHONE.value: 1,
            VerificationMethod.IN_PERSON_TWO_PARTY.value: 1,
        }
        
        score = await calculate_trust_score_activity(
            completed_methods=completed_methods,
            user_type="individual",
        )
        
        # Email (30) + Phone (30) + Two-Party (150) = 210 points
        assert score == 210
    
    async def test_calculate_score_with_multipliers(self):
        """Test trust score with reference multipliers."""
        completed_methods = {
            VerificationMethod.PERSONAL_REFERENCE.value: 3,  # 3x multiplier
        }
        
        score = await calculate_trust_score_activity(
            completed_methods=completed_methods,
            user_type="individual",
        )
        
        # Base 40 points * 3 references = 120 points
        assert score == 120


@pytest.mark.asyncio
class TestPointsAwarding:
    """Test points awarding and level progression."""
    
    async def test_award_points_creates_level_record(self, test_user):
        """Test awarding points creates UserVerificationLevel record."""
        result = await award_verification_points(
            user_id=str(test_user.id),
            method=VerificationMethod.EMAIL.value,
            points=30,
            metadata={"test": True},
        )
        
        assert result["points_awarded"] == 30
        assert result["trust_score"] == 30
        assert result["new_level"] == "UNVERIFIED"  # Not enough points yet
        assert result["level_changed"] is False
        
        # Verify database record
        async with AsyncSessionLocal() as db:
            level = await db.execute(
                f"SELECT * FROM user_verification_levels WHERE user_id = '{test_user.id}'"
            )
            level_record = level.fetchone()
            assert level_record is not None
            assert VerificationMethod.EMAIL.value in level_record.completed_methods
            
            # Cleanup
            await db.execute(
                f"DELETE FROM user_verification_levels WHERE user_id = '{test_user.id}'"
            )
            await db.commit()
    
    async def test_award_points_reaches_minimal_level(self, test_user):
        """Test that accumulating points reaches MINIMAL level."""
        # Award email verification (30 points)
        await award_verification_points(
            user_id=str(test_user.id),
            method=VerificationMethod.EMAIL.value,
            points=30,
        )
        
        # Award phone verification (30 points) - now at 60 points
        await award_verification_points(
            user_id=str(test_user.id),
            method=VerificationMethod.PHONE.value,
            points=30,
        )
        
        # Award two-party verification (150 points) - now at 210 points
        result = await award_verification_points(
            user_id=str(test_user.id),
            method=VerificationMethod.IN_PERSON_TWO_PARTY.value,
            points=150,
        )
        
        assert result["trust_score"] == 210
        assert result["new_level"] == "MINIMAL"  # Crossed 100-point threshold
        assert result["level_changed"] is True
        assert result["old_level"] == "UNVERIFIED"
        
        # Cleanup
        async with AsyncSessionLocal() as db:
            await db.execute(
                f"DELETE FROM user_verification_levels WHERE user_id = '{test_user.id}'"
            )
            await db.commit()


@pytest.mark.asyncio
class TestEventRecording:
    """Test verification event recording."""
    
    async def test_record_event_creates_audit_trail(self, test_user):
        """Test that events are recorded in database."""
        result = await record_verification_event(
            user_id=str(test_user.id),
            event_type="test_event",
            method=VerificationMethod.EMAIL.value,
            data={"test_key": "test_value"},
        )
        
        assert "event_id" in result
        assert result["event_type"] == "test_event"
        
        # Verify database record
        async with AsyncSessionLocal() as db:
            event_id = result["event_id"]
            event = await db.get(VerificationEvent, uuid4(event_id))
            assert event is not None
            assert event.user_id == test_user.id
            assert event.event_type == "test_event"
            assert event.event_data["test_key"] == "test_value"
            
            # Cleanup
            await db.delete(event)
            await db.commit()


@pytest.mark.asyncio
class TestEndToEndVerificationFlow:
    """Test complete verification flow."""
    
    async def test_complete_two_party_verification_flow(self, test_user, test_verifier):
        """Test end-to-end two-party verification flow."""
        # Step 1: Generate QR codes
        async with AsyncSessionLocal() as db:
            verification = VerificationRecord(
                id=uuid4(),
                user_id=test_user.id,
                method=VerificationMethod.IN_PERSON_TWO_PARTY.value,
                status=VerificationStatus.PENDING,
            )
            db.add(verification)
            await db.commit()
            verification_id = str(verification.id)
        
        qr_result = await generate_verification_qr_codes(
            verification_id=verification_id,
            user_id=str(test_user.id),
            user_name=test_user.full_name,
        )
        
        assert qr_result["qr_code_1"] is not None
        assert qr_result["qr_code_2"] is not None
        
        # Step 2: Check verifier authorization
        auth_result = await check_verifier_authorization(
            verifier_id=str(test_verifier.id),
            user_type="individual",
        )
        
        assert auth_result["authorized"] is True
        
        # Step 3: Award verification points
        points_result = await award_verification_points(
            user_id=str(test_user.id),
            method=VerificationMethod.IN_PERSON_TWO_PARTY.value,
            points=150,
            metadata={
                "verifier_id": str(test_verifier.id),
                "verification_id": verification_id,
            },
        )
        
        assert points_result["trust_score"] == 150
        assert points_result["new_level"] == "MINIMAL"  # Reached minimal level
        
        # Step 4: Verify event was recorded
        # (This would be called by award_verification_points internally)
        
        # Cleanup
        async with AsyncSessionLocal() as db:
            verification = await db.get(VerificationRecord, uuid4(verification_id))
            if verification:
                await db.delete(verification)
            
            await db.execute(
                f"DELETE FROM user_verification_levels WHERE user_id = '{test_user.id}'"
            )
            await db.execute(
                f"DELETE FROM verification_events WHERE user_id = '{test_user.id}'"
            )
            await db.commit()
