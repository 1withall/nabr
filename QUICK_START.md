# Nābr MVP - Quick Start Guide

## 🚀 Getting Started

Your Nābr MVP is now fully configured and ready to run! All import errors have been fixed, and the system is set up to use Temporal workflows for reliable initialization and operation.

### Prerequisites Check

```bash
# Verify you have all required tools
which docker docker-compose uv
python --version  # Should be 3.13+
```

### Starting the System

#### Option 1: Full System Startup (Recommended)

```bash
cd /home/prometheus/nabr

# Start the entire system with one command
./scripts/startup.sh

# For development mode (workers in foreground)
./scripts/startup.sh --dev

# If database is already running
./scripts/startup.sh --skip-db
```

This script will:
1. ✅ Start Temporal Server (with UI at http://localhost:8080)
2. ✅ Start PostgreSQL Database
3. ✅ Run Bootstrap Workflow via Temporal (migrations, health checks, etc.)
4. ✅ Start FastAPI Backend at http://localhost:8000
5. ✅ Start all Temporal Workers (verification, matching, review, notification)

#### Option 2: Manual Startup (For Development)

```bash
# Terminal 1: Start infrastructure services
sudo docker compose up temporal postgres

# Terminal 2: Run bootstrap workflow
uv run python -m nabr.temporal.bootstrap_runner

# Terminal 3: Start FastAPI backend
uv run uvicorn nabr.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 4: Start workers
uv run python -m nabr.temporal.worker

# Or start specific workers
uv run python -m nabr.temporal.worker verification
uv run python -m nabr.temporal.worker matching
```

### Accessing the System

Once started, access these endpoints:

**API & Documentation:**
- 🌐 Backend API: http://localhost:8000
- 📚 Interactive Docs: http://localhost:8000/api/docs
- 📖 ReDoc: http://localhost:8000/api/redoc
- 💚 Health Check: http://localhost:8000/health

**Temporal Dashboard:**
- 🎯 Temporal UI: http://localhost:8080
  - View all workflow executions
  - Monitor worker status
  - Debug workflow failures
  - See complete audit trail

**Database:**
- 🐘 PostgreSQL: localhost:5432
  - Database: `nabr_db`
  - User: `nabr`
  - Password: (from your `.env` file)

### Testing the API

```bash
# Test health endpoint
curl http://localhost:8000/health

# Test registration
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "SecurePass123!",
    "full_name": "Test User",
    "user_type": "individual"
  }'

# Check verification status
curl -X GET http://localhost:8000/api/v1/verification/status \
  -H "Authorization: Bearer <your_token>"
```

### Stopping the System

```bash
# Stop all services
sudo docker compose down

# Or use the shutdown script
./scripts/shutdown.sh

# To remove volumes (WARNING: deletes data)
sudo docker compose down -v
```

### Troubleshooting

#### Import Errors
```bash
# Verify all imports work
uv run python -c "from nabr.main import app; print('✓ Success')"
```

#### Database Connection Issues
```bash
# Check PostgreSQL is running
sudo docker compose ps postgres

# View PostgreSQL logs
sudo docker compose logs postgres

# Test database connection
uv run python -c "
from nabr.db.session import engine
import asyncio
from sqlalchemy import text

async def test():
    async with engine.begin() as conn:
        result = await conn.execute(text('SELECT 1'))
        print('✓ Database connected')

asyncio.run(test())
"
```

#### Temporal Issues
```bash
# Check Temporal is running
sudo docker compose ps temporal

# View Temporal logs
sudo docker compose logs temporal

# Check Temporal connectivity
curl http://localhost:8080
```

#### Worker Not Starting
```bash
# Check worker logs
sudo docker compose logs worker

# Or if running manually
uv run python -m nabr.temporal.worker

# Verify activities import
uv run python -c "
from nabr.temporal.activities.matching import MatchingActivities
from nabr.temporal.activities.review import ReviewActivities
print('✓ Activities loaded')
"
```

### Development Workflow

```bash
# Make code changes...

# Run linting
uv run ruff check src/

# Run type checking
uv run mypy src/

# Run tests
uv run pytest

# Format code
uv run black src/

# Restart backend (if running manually)
# The --reload flag will auto-restart on code changes

# View logs
sudo docker compose logs -f
sudo docker compose logs -f backend
sudo docker compose logs -f worker
```

### Database Migrations

```bash
# Create a new migration
uv run alembic revision --autogenerate -m "Description of changes"

# Apply migrations
uv run alembic upgrade head

# Rollback last migration
uv run alembic downgrade -1

# View migration history
uv run alembic history

# View current migration
uv run alembic current
```

### Key Features Ready to Use

#### 1. User Registration & Authentication
- ✅ Email/password registration
- ✅ JWT-based authentication
- ✅ PIN authentication support
- ✅ Refresh token flow
- ✅ Multi-user types (Individual, Business, Organization)

#### 2. Progressive Verification System
- ✅ 6 verification levels (Unverified → Ultimate Trust)
- ✅ Multiple verification methods (email, phone, ID, two-party, etc.)
- ✅ Trust score calculation
- ✅ Real-time status queries
- ✅ QR code generation for two-party verification

#### 3. Request Matching
- ✅ Intelligent volunteer matching algorithm
- ✅ Skill-based matching
- ✅ Geographic proximity calculation
- ✅ Rating and availability consideration
- ✅ Match score calculation

#### 4. Review System
- ✅ Bidirectional reviews (requester ↔ volunteer)
- ✅ Public and private review components
- ✅ Rating aggregation
- ✅ Review moderation support

#### 5. Temporal Workflows
- ✅ All workflows use Temporal for reliability
- ✅ Automatic retries on failure
- ✅ Complete observability and audit trail
- ✅ Long-running workflow support (verification can run for years)

### Next Steps

1. **Test User Registration Flow**
   - Register a new user
   - Check verification workflow starts automatically
   - View workflow in Temporal UI

2. **Test Verification Methods**
   - Start email verification
   - Start phone verification
   - Check trust score updates

3. **Create Test Requests**
   - Create a volunteer request
   - Watch matching workflow execute
   - Review matched volunteers

4. **Implement Frontend**
   - Connect to API endpoints
   - Build user registration UI
   - Create verification interface
   - Add request creation forms

### Monitoring & Observability

**Temporal UI Features:**
- 📊 Workflow execution history
- 🔍 Search workflows by ID, type, or status
- 📈 Worker metrics and health
- 🐛 Detailed error messages and stack traces
- ⏱️ Execution timelines
- 🔄 Retry attempts and policies

**API Logs:**
```bash
# View backend logs
sudo docker compose logs -f backend

# View worker logs
sudo docker compose logs -f worker

# View specific workflow logs in Temporal UI
# Navigate to: http://localhost:8080
```

### Configuration

All configuration is in `.env` file:

```bash
# Copy example
cp .env.example .env

# Edit configuration
nano .env

# Required settings:
# - SECRET_KEY (generate with: openssl rand -hex 32)
# - POSTGRES_PASSWORD
# - DATABASE_URL (auto-generated if components provided)
```

### Support & Documentation

- 📖 Full Documentation: `docs/README.md`
- 🔧 Development Guide: `docs/DEVELOPMENT.md`
- 📝 API Reference: http://localhost:8000/api/docs
- 🎯 Temporal Docs: https://docs.temporal.io
- 💬 FastAPI Docs: https://fastapi.tiangolo.com

---

## ✅ System Status

All components are now operational:
- ✅ Import errors fixed
- ✅ Verification routes registered  
- ✅ Bootstrap workflow integrated
- ✅ Startup script enhanced
- ✅ Worker architecture ready
- ✅ Database models defined
- ✅ API endpoints documented

**Your MVP is ready to run! 🎉**

Execute: `./scripts/startup.sh` to begin.
