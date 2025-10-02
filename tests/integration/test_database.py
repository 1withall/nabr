"""
Integration tests for verification system - Database connectivity.

Tests basic database operations and model creation without Temporal.
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import select, delete

from nabr.db.session import AsyncSessionLocal
from nabr.models.user import User, UserType as UserUserType
from nabr.models.verification import (
    VerificationRecord,
    VerificationStatus,
    UserVerificationLevel,
    VerifierProfile,
    VerificationEvent,
)
from nabr.models.verification_types import VerificationMethod, VerificationLevel


@pytest.mark.asyncio
class TestDatabaseConnectivity:
    """Test basic database operations."""
    
    async def test_database_connection(self):
        """Test that we can connect to the database."""
        async with AsyncSessionLocal() as db:
            # Simple query to test connection
            result = await db.execute(select(User).limit(1))
            # Should not raise an exception
            assert result is not None
    
    async def test_create_user(self):
        """Test creating a user in the database."""
        user_id = uuid4()
        
        async with AsyncSessionLocal() as db:
            user = User(
                id=user_id,
                email=f"test-{user_id}@example.com",
                username=f"testuser-{user_id}",
                full_name="Test User",
                user_type=UserUserType.INDIVIDUAL,
                is_verified=True,
                hashed_password="hashed_test_password",
            )
            db.add(user)
            await db.commit()
        
        # Verify user was created
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(User).where(User.id == user_id)
            )
            fetched_user = result.scalar_one_or_none()
            
            assert fetched_user is not None
            assert fetched_user.email == f"test-{user_id}@example.com"
            assert fetched_user.user_type == UserUserType.INDIVIDUAL
            
            # Cleanup
            await db.delete(fetched_user)
            await db.commit()


@pytest.mark.asyncio
class TestVerificationModels:
    """Test verification model creation and relationships."""
    
    async def test_create_verification_record(self):
        """Test creating a verification record."""
        user_id = uuid4()
        verification_id = uuid4()
        
        # Create user first
        async with AsyncSessionLocal() as db:
            user = User(
                id=user_id,
                email=f"test-{user_id}@example.com",
                username=f"testuser-{user_id}",
                full_name="Test User",
                user_type=UserUserType.INDIVIDUAL,
                is_verified=True,
                hashed_password="hashed_test_password",
            )
            db.add(user)
            await db.commit()
        
        # Create verification record
        async with AsyncSessionLocal() as db:
            verification = VerificationRecord(
                id=verification_id,
                user_id=user_id,
                method=VerificationMethod.IN_PERSON_TWO_PARTY.value,
                status=VerificationStatus.PENDING,
            )
            db.add(verification)
            await db.commit()
        
        # Verify it was created
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(VerificationRecord).where(VerificationRecord.id == verification_id)
            )
            fetched_verification = result.scalar_one_or_none()
            
            assert fetched_verification is not None
            assert fetched_verification.user_id == user_id
            assert fetched_verification.method == VerificationMethod.IN_PERSON_TWO_PARTY.value
            assert fetched_verification.status == VerificationStatus.PENDING
            
            # Cleanup
            await db.delete(fetched_verification)
            await db.commit()
        
        # Cleanup user
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            if user:
                await db.delete(user)
                await db.commit()
    
    async def test_create_user_verification_level(self):
        """Test creating user verification level record."""
        user_id = uuid4()
        
        # Create user first
        async with AsyncSessionLocal() as db:
            user = User(
                id=user_id,
                email=f"test-{user_id}@example.com",
                username=f"testuser-{user_id}",
                full_name="Test User",
                user_type=UserUserType.INDIVIDUAL,
                is_verified=True,
                hashed_password="hashed_test_password",
            )
            db.add(user)
            await db.commit()
        
        # Create verification level
        async with AsyncSessionLocal() as db:
            level = UserVerificationLevel(
                user_id=user_id,
                current_level=VerificationLevel.MINIMAL,
                completed_methods=[
                    VerificationMethod.EMAIL.value,
                    VerificationMethod.PHONE.value,
                    VerificationMethod.IN_PERSON_TWO_PARTY.value,
                ],
                in_progress_methods=[],
                total_methods_completed=3,
                level_progress_percentage=50.0,
            )
            db.add(level)
            await db.commit()
        
        # Verify it was created
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(UserVerificationLevel).where(UserVerificationLevel.user_id == user_id)
            )
            fetched_level = result.scalar_one_or_none()
            
            assert fetched_level is not None
            assert fetched_level.current_level == VerificationLevel.MINIMAL
            assert len(fetched_level.completed_methods) == 3
            assert VerificationMethod.EMAIL.value in fetched_level.completed_methods
            
            # Cleanup
            await db.delete(fetched_level)
            await db.commit()
        
        # Cleanup user
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            if user:
                await db.delete(user)
                await db.commit()
    
    async def test_create_verifier_profile(self):
        """Test creating verifier profile."""
        user_id = uuid4()
        
        # Create user first
        async with AsyncSessionLocal() as db:
            user = User(
                id=user_id,
                email=f"verifier-{user_id}@example.com",
                username=f"verifier-{user_id}",
                full_name="Test Verifier",
                user_type=UserUserType.INDIVIDUAL,
                is_verified=True,
                hashed_password="hashed_test_password",
            )
            db.add(user)
            await db.commit()
        
        # Create verifier profile
        async with AsyncSessionLocal() as db:
            profile = VerifierProfile(
                user_id=user_id,
                is_authorized=True,
                credentials=["NOTARY_PUBLIC", "ATTORNEY"],
                auto_qualified=True,
                total_verifications_performed=5,
                verifier_rating=4.8,
            )
            db.add(profile)
            await db.commit()
        
        # Verify it was created
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(VerifierProfile).where(VerifierProfile.user_id == user_id)
            )
            fetched_profile = result.scalar_one_or_none()
            
            assert fetched_profile is not None
            assert fetched_profile.is_authorized is True
            assert "NOTARY_PUBLIC" in fetched_profile.credentials
            assert fetched_profile.verifier_rating == 4.8
            
            # Cleanup
            await db.delete(fetched_profile)
            await db.commit()
        
        # Cleanup user
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            if user:
                await db.delete(user)
                await db.commit()
    
    async def test_create_verification_event(self):
        """Test creating verification event for audit trail."""
        user_id = uuid4()
        event_id = uuid4()
        
        # Create user first
        async with AsyncSessionLocal() as db:
            user = User(
                id=user_id,
                email=f"test-{user_id}@example.com",
                username=f"testuser-{user_id}",
                full_name="Test User",
                user_type=UserUserType.INDIVIDUAL,
                is_verified=True,
                hashed_password="hashed_test_password",
            )
            db.add(user)
            await db.commit()
        
        # Create verification event
        async with AsyncSessionLocal() as db:
            event = VerificationEvent(
                id=event_id,
                user_id=user_id,
                event_type="points_awarded",
                event_data={
                    "method": VerificationMethod.EMAIL.value,
                    "points": 30,
                    "trust_score": 30,
                },
                temporal_workflow_id="test-workflow-123",
            )
            db.add(event)
            await db.commit()
        
        # Verify it was created
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(VerificationEvent).where(VerificationEvent.id == event_id)
            )
            fetched_event = result.scalar_one_or_none()
            
            assert fetched_event is not None
            assert fetched_event.user_id == user_id
            assert fetched_event.event_type == "points_awarded"
            assert fetched_event.event_data["points"] == 30
            assert fetched_event.temporal_workflow_id == "test-workflow-123"
            
            # Cleanup
            await db.delete(fetched_event)
            await db.commit()
        
        # Cleanup user
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            if user:
                await db.delete(user)
                await db.commit()


@pytest.mark.asyncio
class TestVerificationBusinessLogic:
    """Test verification business logic without Temporal."""
    
    async def test_progressive_trust_accumulation(self):
        """Test that verification methods accumulate trust score."""
        from nabr.models.verification_types import calculate_trust_score
        
        # Test single method
        methods = {VerificationMethod.EMAIL: 1}
        score = calculate_trust_score(methods, UserUserType.INDIVIDUAL)
        assert score == 30
        
        # Test multiple methods
        methods = {
            VerificationMethod.EMAIL: 1,
            VerificationMethod.PHONE: 1,
            VerificationMethod.IN_PERSON_TWO_PARTY: 1,
        }
        score = calculate_trust_score(methods, UserUserType.INDIVIDUAL)
        assert score == 210  # 30 + 30 + 150
    
    async def test_verification_level_thresholds(self):
        """Test verification level determination from trust score."""
        from nabr.models.verification_types import calculate_verification_level
        
        # Test thresholds
        assert calculate_verification_level(0) == VerificationLevel.UNVERIFIED
        assert calculate_verification_level(50) == VerificationLevel.UNVERIFIED
        assert calculate_verification_level(100) == VerificationLevel.MINIMAL
        assert calculate_verification_level(250) == VerificationLevel.STANDARD
        assert calculate_verification_level(400) == VerificationLevel.ENHANCED
        assert calculate_verification_level(600) == VerificationLevel.COMPLETE
        assert calculate_verification_level(1000) == VerificationLevel.COMPLETE
    
    async def test_next_level_requirements(self):
        """Test getting requirements for next verification level."""
        from nabr.models.verification_types import get_next_level_requirements
        
        # From unverified (score 50)
        next_level, points_needed, suggested = get_next_level_requirements(
            current_score=50,
            user_type=UserUserType.INDIVIDUAL,
            completed_methods=set(),
        )
        
        assert next_level == VerificationLevel.MINIMAL
        assert points_needed == 50  # Need 100 total, have 50
        assert len(suggested) > 0
