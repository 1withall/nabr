# Nābr Development Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### [2025-10-01] - Initial Project Setup

#### Added
- Initialized project with `uv` package manager (Python 3.13)
- Created comprehensive project structure following best practices:
  - `src/nabr/` - Main application code
  - `src/nabr/api/` - FastAPI routes and dependencies
  - `src/nabr/core/` - Core configuration and utilities
  - `src/nabr/db/` - Database session management
  - `src/nabr/models/` - SQLAlchemy ORM models
  - `src/nabr/schemas/` - Pydantic schemas
  - `src/nabr/services/` - Business logic services
  - `src/nabr/temporal/` - Temporal workflows and activities
  - `tests/` - Unit and integration tests
  - `docker/` - Docker configuration
  - `alembic/` - Database migrations
  - `scripts/` - Utility scripts
  - `data/` - Local data storage

#### Dependencies Installed
- **Core Backend**: fastapi, uvicorn, sqlalchemy, asyncpg, psycopg2-binary, alembic
- **Data Validation**: pydantic, pydantic-settings
- **Security**: python-jose, passlib, bcrypt, python-multipart
- **Temporal**: temporalio
- **Utilities**: aiofiles
- **Development**: pytest, pytest-asyncio, pytest-cov, black, ruff, mypy, httpx

#### Configuration
- Created `core/config.py` with Pydantic Settings for environment-based configuration
- Configured security settings with JWT authentication (HS256 algorithm)
- Set up PostgreSQL database connection with asyncpg
- Configured Temporal connection parameters
- Defined verification requirements (2 verifiers minimum)
- Established matching algorithm weights and parameters
- Set rate limiting defaults

#### Security Implementation
- Implemented `core/security.py` with comprehensive security utilities:
  - Password hashing using bcrypt
  - Password strength validation (min 8 chars, uppercase, lowercase, digit, special char)
  - JWT access token generation with configurable expiration (30 min default)
  - JWT refresh token generation with configurable expiration (7 days default)
  - Token decoding and validation
  - Support for OAuth2 scopes in tokens

#### Database Setup
- Created async SQLAlchemy engine and session management in `db/session.py`
- Implemented connection pooling (pool_size=10, max_overflow=20)
- Added database initialization and cleanup utilities

#### Database Models Created
- **User Model** (`models/user.py`):
  - Core user authentication and profile data
  - Support for multiple user types (individual, volunteer, business, organization)
  - Verification status tracking
  - Location data for geographical matching
  - Profile information (bio, phone, image)
  - Ratings and statistics (completed requests, verifications performed)
  - Timestamps for audit trail
  - Relationships to volunteer profiles, verifications, requests, and reviews

- **VolunteerProfile Model** (`models/user.py`):
  - Extended profile for volunteers
  - Skills and certifications (stored as JSON)
  - Experience level tracking
  - Availability schedule (stored as JSON)
  - Maximum service distance
  - Request type preferences
  - Languages spoken
  - Background check status and date

- **Verification Model** (`models/user.py`):
  - Two-party verification system
  - Support for multiple verification methods (QR code, ID scan)
  - Secure ID document hash storage
  - Verification location tracking
  - Status tracking (pending, verified, rejected, expired)
  - Temporal workflow ID for process orchestration
  - Expiration date management

- **Request Model** (`models/request.py`):
  - Volunteer assistance requests
  - Multiple request types (physical labor, technical support, transportation, etc.)
  - Priority levels (low, medium, high, urgent)
  - Status tracking (pending, matched, in_progress, completed, cancelled, expired)
  - Detailed location information
  - Required skills and certifications (stored as JSON)
  - Estimated duration and volunteer count
  - Flexible scheduling options
  - Privacy controls (anonymous, contact sharing)
  - Matching score tracking
  - Temporal workflow integration

- **RequestEventLog Model** (`models/request.py`):
  - Immutable audit log for all request events
  - Event type classification
  - Event data stored as JSON
  - Actor tracking (who triggered the event)
  - Temporal workflow and activity ID tracking
  - Indexed timestamps for efficient querying

- **Review Model** (`models/review.py`):
  - Bidirectional reviews (requester ↔ volunteer)
  - Overall rating (1-5 stars)
  - Public comments (visible to all)
  - Private comments (visible to participants and admins)
  - Detailed category ratings:
    - Professionalism
    - Communication
    - Punctuality
    - Skill level
  - Moderation flags
  - Verification linkage to completed requests
  - Temporal workflow integration

#### Enumeration Types Defined
- `UserType`: individual, volunteer, business, organization
- `VerificationStatus`: pending, verified, rejected, expired
- `RequestStatus`: pending, matched, in_progress, completed, cancelled, expired
- `RequestPriority`: low, medium, high, urgent
- `RequestType`: 10 categories covering common volunteer needs
- `ReviewType`: requester_to_volunteer, volunteer_to_requester

#### Architecture Decisions
1. **Async-First**: Using asyncio and async SQLAlchemy for scalability
2. **Type Safety**: Leveraging Python 3.13 type hints and Pydantic
3. **Security-First**: Enterprise-grade authentication and authorization
4. **Temporal Integration**: All processes orchestrated through Temporal workflows
5. **Privacy by Design**: Separate public/private data fields
6. **Audit Trail**: Immutable event logs for transparency
7. **Geographic Matching**: Built-in location support for proximity-based matching
8. **Modular Design**: Clear separation of concerns for maintainability

#### Technical Specifications
- Python Version: 3.13.7
- Database: PostgreSQL with async support (asyncpg)
- API Framework: FastAPI (latest)
- ORM: SQLAlchemy 2.0 (async)
- Workflow Engine: Temporal (latest Python SDK)
- Authentication: OAuth2 + JWT
- Password Hashing: bcrypt
- Testing Framework: pytest with async support

### Next Steps (To Be Implemented)
- [ ] Create Pydantic schemas for request/response validation
- [ ] Implement Temporal workflows for verification process
- [ ] Implement Temporal workflows for request matching
- [ ] Implement Temporal workflows for review submission
- [ ] Create FastAPI routes and endpoints
- [ ] Implement authentication dependencies
- [ ] Create matching algorithm service
- [ ] Set up Alembic for database migrations
- [ ] Create Docker Compose configuration
- [ ] Write unit tests
- [ ] Write integration tests
- [ ] Create frontend React application
- [ ] Create React Native mobile app
- [ ] Implement notification system
- [ ] Add comprehensive logging
- [ ] Create deployment scripts
- [ ] Write API documentation

