"""add_tiered_verification_models

Revision ID: 8a7f3c9d4e21
Revises: 61358bb5b352
Create Date: 2025-10-01 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '8a7f3c9d4e21'
down_revision: Union[str, None] = '61358bb5b352'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create verification_records table
    op.create_table(
        'verification_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('method', sa.Enum('EMAIL', 'PHONE', 'GOVERNMENT_ID', 'IN_PERSON_TWO_PARTY', 'BUSINESS_LICENSE', 'TAX_ID', 'NOTARY', 'ORGANIZATION_501C3', 'PROFESSIONAL_LICENSE', 'COMMUNITY_LEADER', 'BIOMETRIC', name='verificationmethod'), nullable=False),
        sa.Column('status', sa.Enum('PENDING', 'IN_PROGRESS', 'VERIFIED', 'REJECTED', 'EXPIRED', 'REVOKED', name='verificationstatus'), nullable=False),
        sa.Column('verifier1_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('verifier2_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('verifier1_confirmed_at', sa.DateTime(), nullable=True),
        sa.Column('verifier2_confirmed_at', sa.DateTime(), nullable=True),
        sa.Column('verifier1_location', sa.Text(), nullable=True),
        sa.Column('verifier2_location', sa.Text(), nullable=True),
        sa.Column('verifier1_notes', sa.Text(), nullable=True),
        sa.Column('verifier2_notes', sa.Text(), nullable=True),
        sa.Column('verifier1_token', sa.String(length=255), nullable=True),
        sa.Column('verifier2_token', sa.String(length=255), nullable=True),
        sa.Column('qr_expires_at', sa.DateTime(), nullable=True),
        sa.Column('document_hash', sa.String(length=255), nullable=True),
        sa.Column('document_type', sa.String(length=100), nullable=True),
        sa.Column('credential_number', sa.String(length=255), nullable=True),
        sa.Column('credential_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('verification_location', sa.Text(), nullable=True),
        sa.Column('latitude', sa.Float(), nullable=True),
        sa.Column('longitude', sa.Float(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('revocation_reason', sa.Text(), nullable=True),
        sa.Column('revoked_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('temporal_workflow_id', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('verified_at', sa.DateTime(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('revoked_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['revoked_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['verifier1_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['verifier2_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_verification_records_method'), 'verification_records', ['method'], unique=False)
    op.create_index(op.f('ix_verification_records_status'), 'verification_records', ['status'], unique=False)
    op.create_index(op.f('ix_verification_records_temporal_workflow_id'), 'verification_records', ['temporal_workflow_id'], unique=False)
    op.create_index(op.f('ix_verification_records_user_id'), 'verification_records', ['user_id'], unique=False)
    op.create_index(op.f('ix_verification_records_verifier1_id'), 'verification_records', ['verifier1_id'], unique=False)
    op.create_index(op.f('ix_verification_records_verifier1_token'), 'verification_records', ['verifier1_token'], unique=True)
    op.create_index(op.f('ix_verification_records_verifier2_id'), 'verification_records', ['verifier2_id'], unique=False)
    op.create_index(op.f('ix_verification_records_verifier2_token'), 'verification_records', ['verifier2_token'], unique=True)

    # Create user_verification_levels table
    op.create_table(
        'user_verification_levels',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('current_level', sa.Enum('UNVERIFIED', 'MINIMAL', 'BASIC', 'STANDARD', 'ENHANCED', 'COMPLETE', name='verificationlevel'), nullable=False),
        sa.Column('completed_methods', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('in_progress_methods', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('total_methods_completed', sa.Integer(), nullable=False),
        sa.Column('level_progress_percentage', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('level_achieved_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id')
    )
    op.create_index(op.f('ix_user_verification_levels_current_level'), 'user_verification_levels', ['current_level'], unique=False)
    op.create_index(op.f('ix_user_verification_levels_user_id'), 'user_verification_levels', ['user_id'], unique=True)

    # Create verifier_profiles table
    op.create_table(
        'verifier_profiles',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('is_authorized', sa.Boolean(), nullable=False),
        sa.Column('auto_qualified', sa.Boolean(), nullable=False),
        sa.Column('credentials', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('total_verifications_performed', sa.Integer(), nullable=False),
        sa.Column('successful_verifications', sa.Integer(), nullable=False),
        sa.Column('rejected_verifications', sa.Integer(), nullable=False),
        sa.Column('verifier_rating', sa.Float(), nullable=False),
        sa.Column('revoked', sa.Boolean(), nullable=False),
        sa.Column('revoked_at', sa.DateTime(), nullable=True),
        sa.Column('revocation_reason', sa.Text(), nullable=True),
        sa.Column('revoked_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('training_completed', sa.Boolean(), nullable=False),
        sa.Column('training_completed_at', sa.DateTime(), nullable=True),
        sa.Column('last_activity_check', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('authorized_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['revoked_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id')
    )
    op.create_index(op.f('ix_verifier_profiles_is_authorized'), 'verifier_profiles', ['is_authorized'], unique=False)
    op.create_index(op.f('ix_verifier_profiles_revoked'), 'verifier_profiles', ['revoked'], unique=False)
    op.create_index(op.f('ix_verifier_profiles_user_id'), 'verifier_profiles', ['user_id'], unique=True)

    # Create verifier_credential_validations table
    op.create_table(
        'verifier_credential_validations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('verifier_profile_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('credential_type', sa.Enum('NOTARY_PUBLIC', 'ATTORNEY', 'COMMUNITY_LEADER', 'VERIFIED_BUSINESS_OWNER', 'ORGANIZATION_DIRECTOR', 'GOVERNMENT_OFFICIAL', 'TRUSTED_VERIFIER', name='verifiercredential'), nullable=False),
        sa.Column('is_valid', sa.Boolean(), nullable=False),
        sa.Column('validation_method', sa.String(length=100), nullable=True),
        sa.Column('credential_number', sa.String(length=255), nullable=True),
        sa.Column('issuing_authority', sa.String(length=255), nullable=True),
        sa.Column('credential_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('validation_source', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('validated_at', sa.DateTime(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('last_checked_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['verifier_profile_id'], ['verifier_profiles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_verifier_credential_validations_is_valid'), 'verifier_credential_validations', ['is_valid'], unique=False)
    op.create_index(op.f('ix_verifier_credential_validations_verifier_profile_id'), 'verifier_credential_validations', ['verifier_profile_id'], unique=False)

    # Create verification_method_completions table
    op.create_table(
        'verification_method_completions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('method', sa.Enum('EMAIL', 'PHONE', 'GOVERNMENT_ID', 'IN_PERSON_TWO_PARTY', 'BUSINESS_LICENSE', 'TAX_ID', 'NOTARY', 'ORGANIZATION_501C3', 'PROFESSIONAL_LICENSE', 'COMMUNITY_LEADER', 'BIOMETRIC', name='verificationmethod'), nullable=False),
        sa.Column('verification_record_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=False),
        sa.Column('level_before', sa.Enum('UNVERIFIED', 'MINIMAL', 'BASIC', 'STANDARD', 'ENHANCED', 'COMPLETE', name='verificationlevel'), nullable=True),
        sa.Column('level_after', sa.Enum('UNVERIFIED', 'MINIMAL', 'BASIC', 'STANDARD', 'ENHANCED', 'COMPLETE', name='verificationlevel'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['verification_record_id'], ['verification_records.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'method', name='uq_user_method')
    )
    op.create_index(op.f('ix_verification_method_completions_method'), 'verification_method_completions', ['method'], unique=False)
    op.create_index(op.f('ix_verification_method_completions_user_id'), 'verification_method_completions', ['user_id'], unique=False)

    # Create verification_events table
    op.create_table(
        'verification_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('verification_record_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('event_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('actor_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('temporal_workflow_id', sa.String(length=255), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['actor_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['verification_record_id'], ['verification_records.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_verification_events_created_at'), 'verification_events', ['created_at'], unique=False)
    op.create_index(op.f('ix_verification_events_event_type'), 'verification_events', ['event_type'], unique=False)
    op.create_index(op.f('ix_verification_events_temporal_workflow_id'), 'verification_events', ['temporal_workflow_id'], unique=False)
    op.create_index(op.f('ix_verification_events_user_id'), 'verification_events', ['user_id'], unique=False)
    op.create_index(op.f('ix_verification_events_verification_record_id'), 'verification_events', ['verification_record_id'], unique=False)


def downgrade() -> None:
    # Drop all tables in reverse order
    op.drop_index(op.f('ix_verification_events_verification_record_id'), table_name='verification_events')
    op.drop_index(op.f('ix_verification_events_user_id'), table_name='verification_events')
    op.drop_index(op.f('ix_verification_events_temporal_workflow_id'), table_name='verification_events')
    op.drop_index(op.f('ix_verification_events_event_type'), table_name='verification_events')
    op.drop_index(op.f('ix_verification_events_created_at'), table_name='verification_events')
    op.drop_table('verification_events')
    
    op.drop_index(op.f('ix_verification_method_completions_user_id'), table_name='verification_method_completions')
    op.drop_index(op.f('ix_verification_method_completions_method'), table_name='verification_method_completions')
    op.drop_table('verification_method_completions')
    
    op.drop_index(op.f('ix_verifier_credential_validations_verifier_profile_id'), table_name='verifier_credential_validations')
    op.drop_index(op.f('ix_verifier_credential_validations_is_valid'), table_name='verifier_credential_validations')
    op.drop_table('verifier_credential_validations')
    
    op.drop_index(op.f('ix_verifier_profiles_user_id'), table_name='verifier_profiles')
    op.drop_index(op.f('ix_verifier_profiles_revoked'), table_name='verifier_profiles')
    op.drop_index(op.f('ix_verifier_profiles_is_authorized'), table_name='verifier_profiles')
    op.drop_table('verifier_profiles')
    
    op.drop_index(op.f('ix_user_verification_levels_user_id'), table_name='user_verification_levels')
    op.drop_index(op.f('ix_user_verification_levels_current_level'), table_name='user_verification_levels')
    op.drop_table('user_verification_levels')
    
    op.drop_index(op.f('ix_verification_records_verifier2_token'), table_name='verification_records')
    op.drop_index(op.f('ix_verification_records_verifier2_id'), table_name='verification_records')
    op.drop_index(op.f('ix_verification_records_verifier1_token'), table_name='verification_records')
    op.drop_index(op.f('ix_verification_records_verifier1_id'), table_name='verification_records')
    op.drop_index(op.f('ix_verification_records_user_id'), table_name='verification_records')
    op.drop_index(op.f('ix_verification_records_temporal_workflow_id'), table_name='verification_records')
    op.drop_index(op.f('ix_verification_records_status'), table_name='verification_records')
    op.drop_index(op.f('ix_verification_records_method'), table_name='verification_records')
    op.drop_table('verification_records')
    
    # Drop enums
    op.execute('DROP TYPE IF EXISTS verificationmethod')
    op.execute('DROP TYPE IF EXISTS verificationlevel')
    op.execute('DROP TYPE IF EXISTS verifiercredential')
