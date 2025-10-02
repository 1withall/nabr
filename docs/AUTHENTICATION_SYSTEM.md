# Authentication System - Username/PIN Architecture

## Overview

The Nābr platform implements a **UN/PIN (Username/PIN)** authentication system designed for **maximum accessibility**. This system ensures that community members without email addresses, phone numbers, or personal devices can still access services through shared kiosks at community centers, libraries, and partner locations.

## Core Principles

1. **No Email Required**: Email is optional, not mandatory
2. **No Phone Required**: Phone numbers are optional
3. **Device-Agnostic**: Works on shared kiosks and personal devices
4. **Biometric-First**: Personal devices use biometric auth (fingerprint/face)
5. **PIN Backup**: 6-digit PIN for shared devices or biometric failures
6. **Offline-Ready**: Supports limited offline functionality via caching

## Authentication Methods

### Primary: Username + PIN (Universal)
- **What**: Unique username + 6-digit PIN
- **Where**: Works everywhere - kiosks, personal devices, any browser
- **Security**: Argon2 hashed PIN, rate limiting, account lockout
- **Accessibility**: No email/phone required

### Secondary: Biometric (Personal Devices)
- **What**: Device-stored biometric (fingerprint, Face ID)
- **How**: Device unlocks → retrieves stored credentials → authenticates
- **Security**: Biometric data never leaves device
- **Fallback**: Falls back to UN/PIN if biometric fails

### Tertiary: Email/Password (Optional)
- **What**: Traditional email + password login
- **When**: For users who prefer email-based auth
- **Security**: Argon2 password hashing, 8+ characters
- **Note**: Email can be added later, not required at signup

## Database Schema

### Enhanced User Model
```sql
-- Make email and phone OPTIONAL
ALTER TABLE users
    ALTER COLUMN email DROP NOT NULL,
    ALTER COLUMN phone_number DROP NOT NULL,
    
    -- Enforce: At least ONE identifier required
    ADD CONSTRAINT at_least_one_identifier 
        CHECK (
            email IS NOT NULL 
            OR phone_number IS NOT NULL 
            OR username IS NOT NULL
        );

-- Username is now the PRIMARY identifier
CREATE UNIQUE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email) WHERE email IS NOT NULL;
CREATE INDEX idx_users_phone ON users(phone_number) WHERE phone_number IS NOT NULL;
```

### User Authentication Methods Table
```sql
CREATE TABLE user_authentication_methods (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) NOT NULL,
    method_type VARCHAR(50) NOT NULL,  -- 'pin', 'biometric', 'email', 'phone'
    method_identifier TEXT,  -- Device ID for biometric, null for PIN
    
    -- Security metadata
    hashed_secret TEXT,  -- For PIN codes (Argon2)
    public_key TEXT,  -- For device keys (future)
    
    -- Status
    is_active BOOLEAN DEFAULT true,
    is_primary BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT NOW(),
    last_used_at TIMESTAMP,
    deactivated_at TIMESTAMP,
    deactivation_reason TEXT,
    
    -- Security tracking
    failed_attempts INT DEFAULT 0,
    locked_until TIMESTAMP,
    
    UNIQUE(user_id, method_type, method_identifier)
);

CREATE INDEX idx_auth_methods_user ON user_authentication_methods(user_id);
CREATE INDEX idx_auth_methods_active ON user_authentication_methods(is_active, is_primary);
```

### Kiosk Sessions Table
```sql
CREATE TABLE kiosk_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) NOT NULL,
    kiosk_id VARCHAR(100),  -- Kiosk identifier
    location TEXT,
    
    -- Session details
    session_token TEXT UNIQUE NOT NULL,
    started_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP NOT NULL,
    last_activity_at TIMESTAMP DEFAULT NOW(),
    ended_at TIMESTAMP,
    
    -- Auth method used
    auth_method VARCHAR(50),  -- 'pin', 'biometric', 'helper_assisted'
    
    -- Security
    ip_address INET,
    user_agent TEXT,
    
    CONSTRAINT valid_session_duration CHECK (expires_at > started_at)
);

CREATE INDEX idx_kiosk_sessions_user ON kiosk_sessions(user_id);
CREATE INDEX idx_kiosk_sessions_active ON kiosk_sessions(expires_at) WHERE ended_at IS NULL;
CREATE INDEX idx_kiosk_sessions_token ON kiosk_sessions(session_token);
```

## User Type-Specific Signup Forms

### INDIVIDUAL Signup
**Required Fields:**
- `username`: Unique, 3-20 characters, alphanumeric + underscores
- `full_name`: 2-100 characters
- `pin`: 6 digits (confirmed twice)
- `user_type`: 'individual'
- `date_of_birth`: For age verification
- `location`: City, state (for matching)

**Optional Fields:**
- `email`: For email-based login and notifications
- `phone_number`: For SMS notifications
- `bio`: Up to 500 characters
- `skills`: JSON array of skills
- `interests`: JSON array of interests
- `languages_spoken`: JSON array of languages
- `availability_schedule`: JSON schedule object

**Validation Rules:**
- Username must be unique across all users
- PIN must be 6 digits, not sequential (123456), not repeated (111111)
- Date of birth must indicate user is 13+ years old
- Location city and state required for proximity matching

### BUSINESS Signup
**Required Fields:**
- `username`: Unique business identifier
- `full_name`: Business legal name or DBA
- `pin`: 6 digits (confirmed twice)
- `user_type`: 'business'
- `business_name`: Official business name
- `business_type`: e.g., "Restaurant", "Retail", "Services"
- `location`: Business address (city, state, street)

**Optional Fields:**
- `email`: Business contact email
- `phone_number`: Business phone
- `website`: Business website URL
- `tax_id`: EIN (for verification, encrypted)
- `services_offered`: JSON array of services
- `business_hours`: JSON schedule
- `business_license`: File upload for verification

**Validation Rules:**
- Business name must be 2-200 characters
- Location must include street address for business verification
- If tax_id provided, must be valid EIN format (XX-XXXXXXX)
- Business license upload triggers verification workflow

### ORGANIZATION Signup
**Required Fields:**
- `username`: Unique organization identifier
- `full_name`: Organization official name
- `pin`: 6 digits (confirmed twice)
- `user_type`: 'organization'
- `organization_name`: Official organization name
- `organization_type`: "Non-Profit", "Community Group", "Government", "Educational"
- `mission_statement`: 50-500 characters
- `location`: Organization address (city, state)

**Optional Fields:**
- `email`: Organization contact email
- `phone_number`: Organization phone
- `website`: Organization website
- `tax_id`: EIN for non-profits (encrypted)
- `programs_offered`: JSON array of programs
- `staff_count`: Approximate number of staff/volunteers
- `nonprofit_status`: Boolean + verification docs

**Validation Rules:**
- Organization name must be 2-200 characters
- Mission statement required, 50-500 characters
- If nonprofit_status=true, must provide verification documents
- Tax ID required for non-profit verification workflows

## Temporal Workflow Integration

### Signup Workflow Architecture
Every user signup triggers a **long-running Temporal workflow** that manages:

1. **Account Creation** (Immediate)
2. **Profile Completion** (Async)
3. **Verification Journey** (Long-running)
4. **Security Monitoring** (Continuous)

### SignupWorkflow Implementation
```python
@workflow.defn
class SignupWorkflow:
    """
    Long-running workflow for user signup and onboarding.
    
    This workflow:
    - Creates user account and authentication methods
    - Initializes verification level tracking
    - Sends welcome messages
    - Monitors account security
    - Triggers verification workflows when user opts in
    """
    
    @workflow.run
    async def run(
        self,
        user_data: SignupData,
        signup_location: str | None = None
    ) -> SignupResult:
        """
        Execute signup workflow.
        
        Args:
            user_data: Validated signup form data
            signup_location: Physical location of signup (kiosk ID, etc.)
            
        Returns:
            SignupResult with user_id, session_token, and next steps
        """
        
        # Step 1: Create user account (Activity)
        user_id = await workflow.execute_activity(
            create_user_account,
            user_data,
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=RetryPolicy(maximum_attempts=3)
        )
        
        # Step 2: Create PIN authentication method (Activity)
        await workflow.execute_activity(
            create_pin_auth_method,
            user_id,
            user_data.pin,
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=RetryPolicy(maximum_attempts=3)
        )
        
        # Step 3: Create user-type-specific profile (Activity)
        await workflow.execute_activity(
            create_user_profile,
            user_id,
            user_data.user_type,
            user_data.profile_data,
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=RetryPolicy(maximum_attempts=3)
        )
        
        # Step 4: Initialize verification level tracking (Activity)
        await workflow.execute_activity(
            initialize_verification_level,
            user_id,
            user_data.user_type,
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=RetryPolicy(maximum_attempts=3)
        )
        
        # Step 5: Generate session token for immediate login (Activity)
        session_token = await workflow.execute_activity(
            create_session,
            user_id,
            signup_location,
            auth_method='pin',
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=RetryPolicy(maximum_attempts=3)
        )
        
        # Step 6: Send welcome message (Activity, non-critical)
        try:
            await workflow.execute_activity(
                send_welcome_message,
                user_id,
                user_data.preferred_contact_method,
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=RetryPolicy(
                    maximum_attempts=3,
                    non_retryable_error_types=['InvalidContactError']
                )
            )
        except Exception as e:
            workflow.logger.warning(f"Failed to send welcome message: {e}")
            # Non-critical failure, continue workflow
        
        # Step 7: Record signup event (Activity)
        await workflow.execute_activity(
            record_signup_event,
            user_id,
            signup_location,
            user_data.user_type,
            start_to_close_timeout=timedelta(seconds=10)
        )
        
        # Step 8: Start parent verification workflow (Child Workflow)
        # This runs indefinitely, managing the user's verification journey
        verification_workflow_class = self._get_verification_workflow_class(
            user_data.user_type
        )
        
        await workflow.start_child_workflow(
            verification_workflow_class.run,
            user_id,
            id=f"verification-{user_id}",
            task_queue="verification-task-queue"
        )
        
        # Return signup result
        return SignupResult(
            success=True,
            user_id=user_id,
            username=user_data.username,
            session_token=session_token,
            verification_level='UNVERIFIED',
            next_steps=[
                "Complete your profile",
                "Start verification journey",
                "Explore community requests"
            ]
        )
    
    def _get_verification_workflow_class(self, user_type: str):
        """Get appropriate verification workflow for user type."""
        from nabr.temporal.workflows.verification import (
            IndividualVerificationWorkflow,
            BusinessVerificationWorkflow,
            OrganizationVerificationWorkflow
        )
        
        if user_type == 'individual':
            return IndividualVerificationWorkflow
        elif user_type == 'business':
            return BusinessVerificationWorkflow
        elif user_type == 'organization':
            return OrganizationVerificationWorkflow
        else:
            raise ValueError(f"Invalid user type: {user_type}")
```

## API Endpoints

### POST /api/v1/auth/signup
**Multi-step signup with type-specific validation**

**Request Body:**
```json
{
  "user_type": "individual",  // "individual" | "business" | "organization"
  "username": "janedoe123",
  "full_name": "Jane Doe",
  "pin": "123456",
  "pin_confirm": "123456",
  
  // Optional common fields
  "email": "jane@example.com",
  "phone_number": "+1234567890",
  "location": {
    "address": "123 Main St",
    "city": "Oakland",
    "state": "CA",
    "postal_code": "94601"
  },
  
  // Type-specific fields (validated based on user_type)
  "profile_data": {
    // For INDIVIDUAL:
    "date_of_birth": "1990-01-15",
    "bio": "Community helper",
    "skills": ["gardening", "tutoring"],
    "interests": ["environment", "education"],
    "languages_spoken": ["en", "es"]
    
    // For BUSINESS:
    // "business_name": "Jane's Bakery",
    // "business_type": "Restaurant",
    // "services_offered": ["catering", "baked_goods"],
    // "business_hours": {"mon": "9-5", "tue": "9-5"}
    
    // For ORGANIZATION:
    // "organization_name": "Oakland Community Helpers",
    // "organization_type": "Non-Profit",
    // "mission_statement": "Connecting neighbors...",
    // "programs_offered": ["food_bank", "tutoring"]
  }
}
```

**Response (201 Created):**
```json
{
  "success": true,
  "user": {
    "id": "uuid",
    "username": "janedoe123",
    "user_type": "individual",
    "full_name": "Jane Doe",
    "verification_level": "UNVERIFIED",
    "created_at": "2025-10-02T10:30:00Z"
  },
  "session": {
    "access_token": "jwt_token",
    "refresh_token": "refresh_jwt_token",
    "token_type": "bearer",
    "expires_in": 1800
  },
  "next_steps": [
    "Complete your profile",
    "Start verification journey",
    "Explore community requests"
  ]
}
```

### POST /api/v1/auth/login/pin
**Login with username + PIN**

**Request Body:**
```json
{
  "username": "janedoe123",
  "pin": "123456",
  "kiosk_id": "oakland-library-kiosk-1",  // Optional
  "remember_device": false
}
```

**Response (200 OK):**
```json
{
  "access_token": "jwt_token",
  "refresh_token": "refresh_jwt_token",
  "token_type": "bearer",
  "expires_in": 1800,  // 30 minutes for kiosk, 7 days for personal device
  "user": {
    "id": "uuid",
    "username": "janedoe123",
    "full_name": "Jane Doe",
    "user_type": "individual",
    "verification_level": "MINIMAL"
  }
}
```

**Error Response (401 Unauthorized):**
```json
{
  "detail": "Incorrect username or PIN",
  "attempts_remaining": 2,
  "locked_until": null  // Or ISO timestamp if locked
}
```

### POST /api/v1/auth/login/biometric
**Login with biometric + device credentials**

**Request Body:**
```json
{
  "device_id": "unique_device_identifier",
  "biometric_token": "device_generated_token",
  "username": "janedoe123"  // Optional, for device with multiple users
}
```

### POST /api/v1/auth/change-pin
**Change user's PIN (requires authentication)**

**Request Body:**
```json
{
  "current_pin": "123456",
  "new_pin": "654321",
  "new_pin_confirm": "654321"
}
```

### POST /api/v1/auth/reset-pin
**Reset PIN via alternative auth method (email, helper, etc.)**

**Request Body:**
```json
{
  "username": "janedoe123",
  "reset_method": "email",  // "email" | "phone" | "helper_assisted"
  "verification_code": "ABC123"  // If using email/phone
}
```

## Security Features

### PIN Security
- **Hashing**: Argon2id (OWASP recommended)
- **Validation**: No sequential (123456), no repeated (111111), no common PINs
- **Rate Limiting**: 5 attempts per 15 minutes per username
- **Account Lockout**: After 5 failed attempts, lock for 30 minutes
- **Audit Trail**: All login attempts logged with timestamp, IP, location

### Session Security
- **Token Expiry**: 
  - Kiosk sessions: 30 minutes
  - Personal devices: 7 days (refresh token)
- **Activity Tracking**: Sessions auto-logout after 5 minutes inactivity on kiosks
- **Device Binding**: Biometric sessions tied to specific device ID
- **Revocation**: Users can revoke sessions from their account dashboard

### Brute Force Protection
```python
@activity.defn
async def validate_pin_login(
    username: str,
    pin: str,
    kiosk_id: str | None = None
) -> LoginResult:
    """
    Validate PIN login with rate limiting and lockout protection.
    """
    async with AsyncSessionLocal() as db:
        # Check if user exists
        user = await get_user_by_username(db, username)
        if not user:
            # Don't reveal if user exists
            await asyncio.sleep(random.uniform(0.1, 0.3))  # Timing attack protection
            raise ApplicationError("Invalid username or PIN", non_retryable=True)
        
        # Get PIN auth method
        pin_method = await get_auth_method(db, user.id, 'pin')
        if not pin_method or not pin_method.is_active:
            raise ApplicationError("PIN authentication not enabled", non_retryable=True)
        
        # Check if account is locked
        if pin_method.locked_until and pin_method.locked_until > datetime.utcnow():
            remaining = (pin_method.locked_until - datetime.utcnow()).total_seconds()
            raise ApplicationError(
                f"Account locked. Try again in {int(remaining/60)} minutes",
                non_retryable=True
            )
        
        # Verify PIN
        if not verify_password(pin, pin_method.hashed_secret):
            # Increment failed attempts
            pin_method.failed_attempts += 1
            
            if pin_method.failed_attempts >= 5:
                # Lock account for 30 minutes
                pin_method.locked_until = datetime.utcnow() + timedelta(minutes=30)
                await db.commit()
                raise ApplicationError("Too many failed attempts. Account locked for 30 minutes", non_retryable=True)
            
            await db.commit()
            attempts_remaining = 5 - pin_method.failed_attempts
            raise ApplicationError(
                f"Invalid PIN. {attempts_remaining} attempts remaining",
                non_retryable=True
            )
        
        # Successful login - reset failed attempts
        pin_method.failed_attempts = 0
        pin_method.locked_until = None
        pin_method.last_used_at = datetime.utcnow()
        await db.commit()
        
        # Create session
        session_token = await create_session_token(user.id, kiosk_id)
        
        return LoginResult(
            success=True,
            user_id=user.id,
            session_token=session_token,
            verification_level=user.verification_level.current_level
        )
```

## Frontend Implementation Notes

### Signup Form Flow
1. **Step 1**: Select User Type (INDIVIDUAL/BUSINESS/ORGANIZATION)
2. **Step 2**: Username + PIN creation
3. **Step 3**: Basic Info (name, location)
4. **Step 4**: Type-Specific Profile (conditional fields based on user type)
5. **Step 5**: Optional Contact Info (email, phone)
6. **Step 6**: Review & Submit

### Form Validation (Client-Side)
- Username: Real-time availability check via debounced API call
- PIN: Immediate feedback on strength (weak/ok/strong)
- Location: Autocomplete with Google Places API or similar
- Profile fields: Type-specific validation rules displayed

### Accessibility Features
- **Large touch targets**: All buttons 44px minimum for kiosk use
- **High contrast mode**: Toggle for visually impaired
- **Screen reader support**: ARIA labels on all form elements
- **Multi-language**: i18n support for Spanish, Chinese, etc.
- **Simplified mode**: Optional "basic" form with only required fields

## Implementation Phases

### Phase 1: Core UN/PIN Auth ✅ PRIORITY
- [ ] Update User model: make email/phone optional
- [ ] Create `user_authentication_methods` table
- [ ] Create `kiosk_sessions` table
- [ ] Implement SignupWorkflow (Temporal)
- [ ] Create signup activities (create_user_account, create_pin_auth_method, etc.)
- [ ] Implement /auth/signup endpoint with type-specific validation
- [ ] Implement /auth/login/pin endpoint with rate limiting

### Phase 2: Enhanced Security
- [ ] Implement PIN validation rules (no sequential, no repeated)
- [ ] Add rate limiting middleware
- [ ] Implement account lockout logic
- [ ] Add audit logging for all auth events
- [ ] Implement /auth/change-pin endpoint
- [ ] Create admin dashboard for security monitoring

### Phase 3: Biometric Support
- [ ] Create /auth/login/biometric endpoint
- [ ] Implement device registration flow
- [ ] Add device-based session management
- [ ] Create device management dashboard for users

### Phase 4: Kiosk Enhancements
- [ ] Kiosk-specific UI optimizations
- [ ] Implement session warning (5 min before expiry)
- [ ] Add "extend session" functionality
- [ ] Create kiosk management admin panel
- [ ] Implement location-based session tracking

## Testing Strategy

### Unit Tests
- PIN validation rules
- Rate limiting logic
- Session expiry calculations
- Type-specific form validation

### Integration Tests
- Complete signup flow (all user types)
- Login with UN/PIN
- Account lockout after failed attempts
- Session management
- Workflow execution (SignupWorkflow)

### Security Tests
- Brute force protection
- Timing attack resistance
- SQL injection prevention
- XSS prevention in form inputs
- CSRF protection on all endpoints

### Accessibility Tests
- Keyboard navigation
- Screen reader compatibility
- Color contrast ratios
- Touch target sizes (mobile/kiosk)
- Multi-language support
