# Nābr - Community Support Platform

## Overview

Nābr is a community-focused platform that connects verified community members who can offer assistance with those in need, coordinating support, feedback, and follow-up through a secure, transparent, and reliable system. The platform supports three distinct user types (individuals, businesses, and organizations), each with unique workflows and capabilities.

## User Types

### 1. Individual Users
**Purpose**: Community members who can both request and provide assistance

**Capabilities**:
- Create requests for assistance
- Accept and fulfill requests from others
- Most flexible role in the platform
- Peer-to-peer community support

**Profile Includes**:
- Skills and interests
- Availability schedule
- Max distance willing to travel
- Languages spoken
- Emergency contact information

**Unique Workflows**:
- Personal request creation and matching
- Peer assistance workflows
- Individual verification process
- Personal impact tracking

### 2. Business Users
**Purpose**: Local businesses contributing services, resources, or sponsorship

**Capabilities**:
- Offer business services/resources to community
- Accept requests aligned with business capabilities
- Track business impact and community contribution
- Verified business credentials

**Profile Includes**:
- Business name and type
- Tax ID / EIN
- Services offered
- Resources available
- Business hours and service area
- Business license and insurance verification

**Unique Workflows**:
- Resource allocation workflows
- Service provision tracking
- Business verification process
- Impact and ROI reporting

### 3. Organization Users
**Purpose**: Non-profits, community groups, and institutions coordinating larger-scale efforts

**Capabilities**:
- Manage multiple programs
- Coordinate batch requests
- Track volunteer and staff capacity
- Program-level impact reporting

**Profile Includes**:
- Organization name and mission
- Organization type (non-profit, community group, etc.)
- Tax ID / EIN for non-profits
- Programs offered
- Service areas
- Staff count and volunteer capacity
- Accreditations and non-profit status

**Unique Workflows**:
- Program management workflows
- Batch request handling
- Capacity planning
- Grant reporting and impact measurement

## Core Features

### 1. User Verification
- All participants must have verified identities
- Two-party verification system (notaries, community leaders, recognized figures)
- Multiple verification methods for layered security
- Prevents duplication, fraud, and unauthorized access
- Implemented as Temporal workflows for immutability and auditability

### 2. Community Assistance Requests
- Any verified user can create or accept requests
- Advanced matching algorithm connects requests with capabilities
- No searchable database - privacy-preserving matching only
- Request lifecycle managed through Temporal workflows
- Enforces fairness and prevents exploitation

### 3. Event-Linked Reviews
- Bidirectional reviews between requester and acceptor
- Tied to completed, verified events
- Immutable and auditable
- Private assistance details, public accountability (participants, time, location)
- Prevents duplicate or fraudulent submissions

## Technical Architecture

### Backend Stack
- **FastAPI**: Modern async web framework
- **SQLAlchemy 2.0**: Async ORM with PostgreSQL
- **Temporal**: Workflow orchestration for all business processes
- **PostgreSQL**: Primary database
- **Argon2**: Password hashing (OWASP recommended)
- **JWT**: Token-based authentication

### Key Design Principles
- **Temporal-First**: All business logic in workflows/activities
- **Type Safety**: Full type hints and Pydantic validation
- **User-Type Separation**: Distinct profiles and workflows per user type
- **Privacy-Preserving**: No searchable request database
- **Immutable Audit Trail**: All events logged in Temporal

## Project Structure

```
nabr/
├── src/nabr/
│   ├── core/                  # Configuration and security utilities
│   ├── db/                    # Database session management
│   ├── models/                # SQLAlchemy models
│   │   ├── user.py           # User, IndividualProfile, BusinessProfile, OrganizationProfile
│   │   ├── request.py        # Request model
│   │   └── review.py         # Review model
│   ├── schemas/               # Pydantic schemas for API
│   ├── api/                   # FastAPI routes and dependencies
│   │   ├── dependencies/     # Auth dependencies
│   │   └── routes/           # API endpoints
│   ├── services/              # Business logic layer
│   └── temporal/              # Temporal workflows and activities
│       ├── workflows/        # Workflow definitions
│       └── activities/       # Activity implementations
├── alembic/                   # Database migrations
├── tests/                     # Test suite
└── docker/                    # Docker configurations

```

## Development Setup

### Prerequisites
- Python 3.11+
- PostgreSQL 16+
- Docker and Docker Compose
- uv package manager

### Installation

```bash
# Clone repository
git clone <repository-url>
cd nabr

# Install dependencies
uv sync

# Start PostgreSQL
docker-compose up postgres -d

# Run migrations
uv run alembic upgrade head

# Start server
uv run uvicorn nabr.main:app --reload
```

### Environment Variables

Create `.env` file:
```
SECRET_KEY=<generated-key>
DATABASE_URL=postgresql+asyncpg://nabr:password@localhost:5432/nabr_db
POSTGRES_PASSWORD=<password>
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
```

## API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Register new user (any type)
- `POST /api/v1/auth/login` - Login and get JWT tokens
- `POST /api/v1/auth/refresh` - Refresh access token
- `GET /api/v1/auth/me` - Get current user info

### Health
- `GET /health` - Service health check
- `GET /health/ready` - Database connectivity check

## Database Schema

### User Types
- `individual` - Community members (can request and provide)
- `business` - Local businesses
- `organization` - Non-profits and community groups

### Profile Tables
- `individual_profiles` - Skills, availability, interests
- `business_profiles` - Services, resources, business info
- `organization_profiles` - Programs, capacity, mission

### Core Tables
- `users` - Base user accounts
- `verifications` - Two-party verification records
- `requests` - Assistance requests
- `reviews` - Event-linked feedback

## Migration History

### Current Schema (v2)
- **Removed**: VolunteerProfile, background check fields, volunteer-specific terminology
- **Added**: IndividualProfile, BusinessProfile, OrganizationProfile
- **Changed**: User types reduced to 3, request.volunteer_id → request.acceptor_id
- **Simplified**: Required certifications removed, participants_needed replaces num_volunteers_needed

## Security Features

- Argon2 password hashing (memory-hard, GPU-resistant)
- JWT-based authentication (30min access, 7-day refresh tokens)
- Two-party verification system
- Privacy-preserving request matching
- No background check storage (removed for privacy)
- Immutable audit trails via Temporal

## Testing

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=nabr

# Run specific test file
uv run pytest tests/test_auth.py
```

## Documentation

- [CHANGELOG.md](CHANGELOG.md) - Version history
- [PHASE_2A_COMPLETE.md](PHASE_2A_COMPLETE.md) - Phase 2A completion status
- [DEVELOPMENT.md](DEVELOPMENT.md) - Development guidelines
- [.github/AI_DEVELOPMENT_GUIDE.md](.github/AI_DEVELOPMENT_GUIDE.md) - AI agent guide

## Contributing

1. Follow the existing code structure
2. Write tests for new features
3. Update documentation
4. Use `uv` for package management
5. Follow type hints and Pydantic validation patterns

## License

[License information]

## Contact

[Contact information]
