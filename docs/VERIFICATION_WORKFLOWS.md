# Verification Workflows - User Type Specific

**Created:** October 1, 2025  
**Phase:** 2C - Verification System  
**Status:** ✅ Complete - Corrected per original requirements

---

## Critical Understanding

**Each user type has a UNIQUE verification workflow because they are fundamentally different entities:**

- **Individuals** need **identity confirmation** from trusted community members
- **Businesses** need **legitimacy proof** through official business documentation  
- **Organizations** need **mission/governance verification** and community alignment

This document details the unique verification requirements and workflows for each user type.

---

## Verification Levels (All User Types)

All user types progress through the same level names, but with **different requirements** at each level:

1. **UNVERIFIED** - No verification completed, **CANNOT access platform features**
2. **MINIMAL** - Type-specific baseline verification (see below)
3. **STANDARD** - Enhanced verification for the user type
4. **ENHANCED** - Additional credentials and trust signals
5. **COMPLETE** - Full verification with all methods for that type

---

## Individual Verification Workflow

### Original Requirement (from README_OLD.md)
> "All participants must have verified identities. **'Minimal verification' requires in-person confirmation by at least two trusted community members** (notaries, community leaders, or other recognized figures)."

### Individual Verification Path

#### UNVERIFIED
- **Status**: Cannot access any platform features
- **Required**: Nothing yet
- **Next Step**: Complete minimal verification

#### MINIMAL (BASELINE REQUIREMENT) ✅
**This is the REQUIRED baseline to use the platform as an individual.**

**Requirements:**
- ✅ Email verification
- ✅ Phone verification  
- ✅ **Two-party in-person verification**
  - Must be confirmed by **2 Authorized Verifiers**
  - Verifiers scan QR codes to confirm identity
  - Verifiers must be STANDARD level or higher
  - Verifiers must have credentials (notary, attorney, community leader, etc.)

**Why**: Ensures real, verified community members. Prevents fraud, bots, duplicates.

**What Unlocks**: Can create requests, accept requests, participate in community

#### STANDARD (ENHANCED IDENTITY)
**Requirements:**
- All MINIMAL requirements +
- ✅ Government ID verification (driver's license, passport, etc.)

**Why**: Additional identity confirmation for higher-trust interactions

**What Unlocks**: Can become an Authorized Verifier, higher request limits

#### ENHANCED (COMMUNITY TRUST)
**Requirements:**
- All STANDARD requirements +
- ✅ Personal references from verified community members

**Why**: Demonstrates community integration and trust

**What Unlocks**: Priority matching, community leadership opportunities

#### COMPLETE (FULL VERIFICATION)
**Requirements:**
- All ENHANCED requirements +
- ✅ Notary verification (notarized identity confirmation)

**Why**: Highest level of identity verification

**What Unlocks**: All platform features, can become notary-level verifier

---

## Business Verification Workflow

### Logical Requirement
Businesses must prove they are **legitimate, registered businesses** before operating on the platform to prevent scams and protect community members.

### Business Verification Path

#### UNVERIFIED
- **Status**: Cannot offer services or resources
- **Required**: Nothing yet
- **Next Step**: Prove business legitimacy

#### MINIMAL (BASELINE REQUIREMENT) ✅
**This is the REQUIRED baseline for businesses to operate on platform.**

**Requirements:**
- ✅ Business email verification
- ✅ Business phone verification
- ✅ **Business license** (official business registration/license)
- ✅ **Tax ID (EIN)** verification

**Why**: Proves business is legally registered and operating

**What Unlocks**: Can offer services, accept business-related requests

#### STANDARD (PHYSICAL PRESENCE)
**Requirements:**
- All MINIMAL requirements +
- ✅ **Business address verification** (physical location)
- ✅ **Owner verification** (owner identity confirmed)

**Why**: Confirms business has physical presence and verified ownership

**What Unlocks**: Higher service limits, featured business listings

#### ENHANCED (PROFESSIONAL OPERATIONS)
**Requirements:**
- All STANDARD requirements +
- ✅ **Business insurance** (liability insurance verification)
- ✅ **Notarized business documents**

**Why**: Shows professional, insured operation

**What Unlocks**: Priority placement, enterprise features

#### COMPLETE (FULL BUSINESS VERIFICATION)
**Requirements:**
- All ENHANCED requirements +
- ✅ **Professional licenses** (if applicable - contractors, etc.)
- ✅ **Community endorsement** (community reputation verification)

**Why**: Highest trust level for businesses

**What Unlocks**: All business features, partnership opportunities

---

## Organization Verification Workflow

### Logical Requirement
Organizations must prove they are **legitimate non-profits/community organizations** with proper governance and mission alignment before coordinating community efforts.

### Organization Verification Path

#### UNVERIFIED
- **Status**: Cannot coordinate programs or requests
- **Required**: Nothing yet
- **Next Step**: Prove organization legitimacy

#### MINIMAL (BASELINE REQUIREMENT) ✅
**This is the REQUIRED baseline for organizations to operate on platform.**

**Requirements:**
- ✅ Organization email verification
- ✅ Organization phone verification
- ✅ **501(c)(3) status** (or equivalent non-profit documentation)
- ✅ **Tax ID (EIN)** for non-profit

**Why**: Proves organization is legally registered as non-profit

**What Unlocks**: Can create programs, coordinate batch requests

#### STANDARD (GOVERNANCE VERIFICATION)
**Requirements:**
- All MINIMAL requirements +
- ✅ **Organization bylaws** (governing documents)
- ✅ **Board of directors verification** (board members verified)

**Why**: Confirms proper governance structure

**What Unlocks**: Multi-program management, volunteer coordination

#### ENHANCED (MISSION & COMMUNITY)
**Requirements:**
- All STANDARD requirements +
- ✅ **Mission alignment** (mission aligns with community values)
- ✅ **Community endorsement** (community support/endorsement)

**Why**: Ensures organization serves community interests

**What Unlocks**: Featured programs, partnership opportunities

#### COMPLETE (FULL ORGANIZATION VERIFICATION)
**Requirements:**
- All ENHANCED requirements +
- ✅ **Notarized organizational documents**

**Why**: Highest trust level for organizations

**What Unlocks**: All organization features, grant eligibility

---

## Authorized Verifiers (For Individual Verification Only)

### Who Can Be an Authorized Verifier?

**Authorized Verifiers** perform the two-party in-person verification for **individuals only**.

**Requirements to become an Authorized Verifier:**
1. Must be at **STANDARD verification level or higher**
2. Must have one or more of these credentials:

**Auto-Qualified Credentials** (automatically authorized):
- **Notary Public** - Licensed notary
- **Attorney** - Licensed attorney/bar member
- **Government Official** - Verified government employee

**Qualified with Verification** (need additional verification):
- **Community Leader** - Verified community organization leader
- **Verified Business Owner** - COMPLETE-level business owner
- **Organization Director** - COMPLETE-level organization director

**Earned Through Activity**:
- **Trusted Verifier** - 50+ successful verifications performed

### Verifier Responsibilities

Authorized Verifiers:
- Scan QR code to confirm identity
- Meet individual in person
- Verify identity documents
- Provide notes on verification
- Can be revoked for misconduct

### Verifier Protections

- Comprehensive audit trail of all verifications
- Can report suspicious activity
- Protected from retaliation
- Statistics tracking for reputation

---

## Verification Methods Summary

### Universal Methods (All Types)
- **EMAIL** - Email address confirmation
- **PHONE** - Phone number verification

### Individual-Specific Methods
- **IN_PERSON_TWO_PARTY** - Two Authorized Verifiers confirm identity ✅ BASELINE
- **GOVERNMENT_ID** - Driver's license, passport, etc.
- **BIOMETRIC** - Facial recognition (future)
- **PERSONAL_REFERENCE** - References from verified community members

### Business-Specific Methods
- **BUSINESS_LICENSE** - Business registration/license ✅ BASELINE
- **TAX_ID_BUSINESS** - EIN verification ✅ BASELINE
- **BUSINESS_ADDRESS** - Physical location verification
- **BUSINESS_INSURANCE** - Liability insurance
- **OWNER_VERIFICATION** - Business owner identity

### Organization-Specific Methods
- **NONPROFIT_STATUS** - 501(c)(3) documentation ✅ BASELINE
- **TAX_ID_NONPROFIT** - EIN for non-profit ✅ BASELINE
- **ORGANIZATION_BYLAWS** - Governing documents
- **BOARD_VERIFICATION** - Board of directors verification
- **MISSION_ALIGNMENT** - Community alignment review

### Enhanced Methods (Optional for Higher Levels)
- **NOTARY_VERIFICATION** - Notarized documents
- **PROFESSIONAL_LICENSE** - Professional credentials
- **COMMUNITY_ENDORSEMENT** - Community leader endorsement

---

## Technical Implementation

### Temporal Workflows

Each user type has a **unique verification workflow**:

1. **IndividualVerificationWorkflow**
   - Generates QR codes for two-party verification
   - Tracks verifier confirmations
   - Validates government ID
   - Manages personal references

2. **BusinessVerificationWorkflow**
   - Validates business license with state databases
   - Verifies EIN with IRS
   - Confirms business address
   - Verifies owner identity
   - Checks insurance status

3. **OrganizationVerificationWorkflow**
   - Validates 501(c)(3) status
   - Verifies EIN for non-profit
   - Reviews bylaws and governance
   - Validates board of directors
   - Assesses mission alignment

### Activities (Shared but Type-Aware)

The verification activities are shared but behave differently based on user type:

- `generate_verification_qr_codes` - Only for individuals
- `check_verifier_authorization` - Only for individual verification
- `validate_business_license` - Only for businesses
- `validate_nonprofit_status` - Only for organizations
- `calculate_verification_level` - Type-aware level calculation
- `update_user_verification_level` - Type-specific updates

### Database Models

All user types share the same database models but use them differently:

- **VerificationRecord** - Stores method completion (method field is type-aware)
- **UserVerificationLevel** - Tracks current level (requirements differ by type)
- **VerifierProfile** - Only for individuals who verify others
- **VerificationMethodCompletion** - Audit trail (methods differ by type)
- **VerificationEvent** - Immutable log (all types)

---

## Why This Design?

### Different Entities, Different Needs

**Individuals** are people joining a community:
- Need identity confirmation to prevent fraud
- Community trust is paramount
- Two-party verification builds local relationships

**Businesses** are commercial entities:
- Need legitimacy proof to prevent scams
- Legal registration is verifiable through official channels
- Insurance and licenses protect consumers

**Organizations** are mission-driven groups:
- Need governance verification to ensure accountability
- Mission alignment ensures community fit
- Board verification prevents bad actors

### Progressive Trust Building

Each user type progresses through verification levels at their own pace:
- **MINIMAL** - Enough to participate safely
- **STANDARD** - Enhanced trust for expanded activity
- **ENHANCED** - Additional signals for priority treatment
- **COMPLETE** - Full verification for maximum trust and features

### Platform Safety

Different verification paths provide different safety benefits:
- **Individuals**: Two-party verification prevents bots, duplicates, bad actors
- **Businesses**: License/EIN verification prevents scams
- **Organizations**: 501(c)(3) verification ensures legitimacy

---

## Summary

✅ **3 Unique Verification Workflows** - One for each user type  
✅ **5 Verification Levels** - Progressive trust building  
✅ **19 Verification Methods** - Type-specific requirements  
✅ **Authorized Verifier System** - For individual verification only  
✅ **Type-Aware Activities** - Shared code, different behavior  
✅ **Temporal Integration** - All workflows orchestrated via Temporal  

**Key Insight**: Verification requirements must match the fundamental nature of each user type. You don't verify a business the same way you verify a person, and you don't verify an organization the same way you verify a business.

**Next Steps**: Implement the three unique verification workflows in Temporal.
