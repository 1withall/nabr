# Nābr - Community Volunteer Coordination Platform

[![Python 3.13](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.118+-green.svg)](https://fastapi.tiangolo.com)
[![Temporal](https://img.shields.io/badge/Temporal-Latest-orange.svg)](https://temporal.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Nābr** (from Arabic نَبْر, meaning "voice" or "tone") is a community-focused platform that connects verified volunteers with local individuals or groups in need. The app coordinates assistance, feedback, and follow-up through a secure, transparent, and reliable system built on Temporal workflows.

## 🌟 Core Values

- **Trust & Accountability**: Two-party verification system ensures genuine participants
- **Privacy & Security**: Enterprise-grade security with granular privacy controls
- **Transparency**: Immutable event logs and public review system
- **Fairness & Equality**: Algorithmic matching prevents exploitation
- **Community-First**: Local focus strengthens neighborhood connections

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose installed
- At least 4GB RAM available
- Ports 5432, 7233, 8000, and 8080 available

### Setup

1. **Clone the repository:**
```bash
git clone <repository-url>
cd nabr
```

2. **Create environment file:**
```bash
cp .env.example .env
```

3. **Generate a secure secret key:**
```bash
openssl rand -hex 32
```
   Copy the output and set it as `SECRET_KEY` in your `.env` file.

4. **Configure database password:**
   Edit `.env` and set a secure `POSTGRES_PASSWORD`.

5. **Start all services:**
```bash
docker-compose up -d
```

6. **Verify services are running:**
```bash
docker-compose ps
```

All services should show as "healthy" or "running".

### Access Points

- **API Documentation:** http://localhost:8000/docs
- **API Alternative Docs:** http://localhost:8000/redoc
- **Temporal Web UI:** http://localhost:8080
- **Backend API:** http://localhost:8000

### Development Setup

For local development without Docker:

1. **Install uv package manager:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

2. **Install dependencies:**
```bash
uv sync
```

3. **Set up local database** (requires PostgreSQL installed):
```bash
createdb nabr_db
```

4. **Run database migrations:**
```bash
uv run alembic upgrade head
```

5. **Start the development server:**
```bash
uv run uvicorn nabr.main:app --reload
```

## 🏗️ Architecture

### Technology Stack

**Backend:**
- FastAPI (async Python web framework)
- PostgreSQL (database)
- SQLAlchemy 2.0 (async ORM)
- Temporal (workflow orchestration)
- OAuth2 + JWT (authentication)
- bcrypt (password hashing)

**Frontend:** *(To be implemented)*
- React (web application)
- React Native (mobile application)

**Infrastructure:**
- Docker & Docker Compose
- uv (Python package manager)
- Alembic (database migrations)

### System Design

All backend processes are orchestrated through **Temporal workflows and activities**, ensuring:
- **Reliability**: Automatic retries and error handling
- **Observability**: Complete visibility into all processes
- **Auditability**: Immutable workflow execution history
- **Scalability**: Distributed processing capabilities

## 📋 MVP Features

### 1. User Verification *(In Development)*
- Two-party in-person verification system
- QR code generation for verification sessions
- Multiple verification methods (ID scan, trusted verifier)
- Expiration tracking and renewal

### 2. Volunteer Requests *(In Development)*
- Comprehensive request creation forms
- Intelligent matching algorithm considering:
  - Skills and certifications
  - Geographic proximity
  - Availability schedules
  - User ratings and history
- Privacy-preserving matching (no searchable request database)
- Real-time status tracking

### 3. Event-Linked Reviews *(In Development)*
- Bidirectional reviews (requester ↔ volunteer)
- Public and private review sections
- Detailed rating categories:
  - Overall satisfaction
  - Professionalism
  - Communication
  - Punctuality
  - Skill level
- Verified reviews tied to completed events

### 4. Temporal Integration *(Infrastructure Complete)*
- All processes orchestrated as workflows
- Immutable audit trails
- Automatic error recovery
- Complete observability

## 📁 Project Structure

```
nabr/
├── src/nabr/              # Main application
│   ├── api/              # API routes and dependencies
│   ├── core/             # Configuration and utilities
│   ├── db/               # Database session management
│   ├── models/           # SQLAlchemy ORM models
│   ├── schemas/          # Pydantic validation schemas
│   ├── services/         # Business logic
│   └── temporal/         # Workflows and activities
├── tests/                # Test suite
├── docker/               # Docker configuration
├── alembic/             # Database migrations
└── data/                # Local data storage
```

## 🧪 Testing

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=nabr --cov-report=html

# Run specific test file
uv run pytest tests/unit/test_security.py -v

# Run integration tests only
uv run pytest tests/integration/ -v
```

## 🔧 Development Commands

```bash
# Format code
uv run black src/

# Lint code
uv run ruff check src/

# Type check
uv run mypy src/

# Create database migration
uv run alembic revision --autogenerate -m "description"

# Apply migrations
uv run alembic upgrade head

# Rollback migration
uv run alembic downgrade -1

# View Docker logs
docker-compose logs -f

# Stop all services
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

## 🔒 Security

### Implemented
- ✅ bcrypt password hashing
- ✅ Strong password requirements
- ✅ JWT access and refresh tokens
- ✅ OAuth2 authentication flow
- ✅ Environment-based secrets
- ✅ Async database driver
- ✅ Type validation

### Planned
- [ ] Rate limiting
- [ ] CORS configuration
- [ ] HTTPS enforcement
- [ ] Data encryption at rest
- [ ] Audit logging
- [ ] Security headers

## 📊 MVP Progress

- **Infrastructure:** 100% ✅
- **Database Models:** 100% ✅
- **Security:** 80% ✅
- **API Endpoints:** 0% 🚧
- **Temporal Workflows:** 0% 🚧
- **Frontend:** 0% 🚧
- **Testing:** 10% 🚧

See [PROJECT_STATUS.md](PROJECT_STATUS.md) for detailed progress tracking.

## 📝 Documentation

- [PROJECT_STATUS.md](PROJECT_STATUS.md) - Current implementation status
- [CHANGELOG.md](CHANGELOG.md) - Detailed change history
- [.github/copilot_instructions.md](.github/copilot_instructions.md) - Development guidelines
- API Documentation: http://localhost:8000/docs (when running)

## 🤝 Contributing

*(To be established)*

## 📜 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🎯 SMART Goals (MVP)

- **Specific:** Enable verified volunteers to assist local community members via secure request matching
- **Measurable:** Successfully process at least 100 volunteer requests with complete tracking
- **Achievable:** All core features functional using Temporal workflows
- **Relevant:** Strengthen community engagement, trust, and security
- **Time-bound:** MVP fully functional within 12 weeks from project start

**Current Week:** 1 of 12  
**Status:** Foundation Complete, Ready for Feature Implementation

## 🙏 Acknowledgments

Built with:
- [FastAPI](https://fastapi.tiangolo.com/) - Modern, fast web framework
- [Temporal](https://temporal.io/) - Workflow orchestration platform
- [SQLAlchemy](https://www.sqlalchemy.org/) - Python SQL toolkit
- [uv](https://github.com/astral-sh/uv) - Fast Python package manager
- [PostgreSQL](https://www.postgresql.org/) - Advanced open source database

---

**Note:** This is a work in progress. The MVP is currently in active development with the foundational infrastructure complete. See PROJECT_STATUS.md for current status and next steps.
