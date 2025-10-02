# Nābr System Scripts

This directory contains scripts for managing the Nābr platform.

## Overview

The Nābr platform uses a sophisticated startup sequence that leverages **Temporal workflows** for system initialization. This approach provides:

- ✅ **Automatic retries** with exponential backoff
- ✅ **Full observability** in Temporal UI
- ✅ **Error handling** and recovery
- ✅ **Activity-level logging** and tracing
- ✅ **Workflow history** for debugging

## Quick Start

```bash
# Start the entire system
./scripts/startup.sh

# Stop the system
./scripts/shutdown.sh
```

## Startup Architecture

### Boot Sequence

```
1. Temporal Server (with SQLite persistence)
   ↓
2. PostgreSQL Database
   ↓
3. Bootstrap Workflow (via Temporal)
   ├─ Run database migrations (Alembic)
   ├─ Verify database health
   ├─ Validate schema
   ├─ Initialize default data
   ├─ Validate configuration
   └─ Run service health checks
   ↓
4. FastAPI Backend
   ↓
5. Temporal Workers
   ├─ Verification Worker (verification-queue)
   ├─ Matching Worker (matching-queue)
   ├─ Review Worker (review-queue)
   └─ Notification Worker (notification-queue)
```

### Why Use Temporal for Bootstrap?

The bootstrap workflow runs as a **Temporal workflow** instead of a simple script because:

1. **Automatic Retries**: If a migration fails due to a transient network issue, Temporal automatically retries with exponential backoff
2. **Observability**: Watch the entire initialization process in the Temporal UI at http://localhost:8080
3. **Error Handling**: Each step is an activity with proper error handling and recovery
4. **Workflow History**: Full audit trail of what happened during initialization
5. **Coordination**: Easy to add parallel initialization tasks or complex dependencies

## Scripts

### `startup.sh`

Starts the entire Nābr platform in the correct order.

**Usage:**
```bash
./scripts/startup.sh              # Start entire system
./scripts/startup.sh --skip-db    # Skip database services
./scripts/startup.sh --dev        # Development mode (workers in foreground)
```

**What it does:**
1. Starts Temporal server with SQLite persistence
2. Starts PostgreSQL database
3. Runs bootstrap workflow via Temporal
4. Starts FastAPI backend
5. Starts Temporal workers

**Development Mode:**
- Workers run in foreground (see logs in terminal)
- Press Ctrl+C to stop workers
- Good for debugging workflow execution

**Production Mode:**
- All services run in Docker containers
- Workers run in background
- Logs accessible via `docker compose logs`

### `shutdown.sh`

Gracefully shuts down all services.

**Usage:**
```bash
./scripts/shutdown.sh           # Graceful shutdown
./scripts/shutdown.sh --force   # Force immediate shutdown
```

**Shutdown Order:**
1. Temporal Workers (graceful completion)
2. FastAPI Backend
3. Temporal Server
4. PostgreSQL Database

## Bootstrap Workflow

The bootstrap workflow (`src/nabr/temporal/workflows/bootstrap.py`) orchestrates system initialization through Temporal.

**Activities:**
- `run_database_migrations`: Executes Alembic migrations
- `check_database_health`: Verifies PostgreSQL connectivity
- `validate_database_schema`: Confirms schema integrity
- `initialize_default_data`: Creates default data if needed
- `validate_configuration`: Checks all configuration values
- `run_service_health_checks`: Tests all service connections

**Run Manually:**
```bash
python -m nabr.temporal.bootstrap
```

**Monitor in Temporal UI:**
- Open http://localhost:8080
- Find workflow ID: `system-bootstrap`
- View step-by-step execution, retries, and errors

## Service URLs

After startup, these services are available:

| Service | URL | Description |
|---------|-----|-------------|
| **Temporal gRPC** | localhost:7233 | Temporal server endpoint |
| **Temporal UI** | http://localhost:8080 | Workflow monitoring |
| **FastAPI** | http://localhost:8000 | API server |
| **API Docs** | http://localhost:8000/docs | Interactive API documentation |
| **PostgreSQL** | localhost:5432 | Database server |

## Logs

View logs for any service:

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f worker
docker compose logs -f backend
docker compose logs -f temporal

# Bootstrap workflow
cat logs/bootstrap.log
```

## Troubleshooting

### Bootstrap Workflow Failed

1. Check the logs:
   ```bash
   cat logs/bootstrap.log
   ```

2. View in Temporal UI:
   - Open http://localhost:8080
   - Find workflow `system-bootstrap`
   - Check activity errors and retry history

3. Common issues:
   - **Database not ready**: Increase PostgreSQL health check timeout
   - **Migration conflicts**: Check Alembic revision history
   - **Configuration errors**: Verify `.env` file settings

### Workers Not Starting

1. Check worker logs:
   ```bash
   docker compose logs worker
   ```

2. Verify Temporal is healthy:
   ```bash
   docker compose ps temporal
   ```

3. Ensure bootstrap workflow completed:
   ```bash
   python -m nabr.temporal.bootstrap
   ```

### Services Not Responding

1. Check service health:
   ```bash
   docker compose ps
   ```

2. Restart specific service:
   ```bash
   docker compose restart backend
   ```

3. Full restart:
   ```bash
   ./scripts/shutdown.sh
   ./scripts/startup.sh
   ```

## Development Tips

### Run Workers Locally (not in Docker)

```bash
# Start infrastructure only
docker compose up -d temporal postgres

# Run workers in terminal
python -m nabr.temporal.worker

# Or run specific worker
python -m nabr.temporal.worker verification
```

### Skip Bootstrap for Fast Iteration

If database is already initialized:

```bash
# Start services without running migrations again
docker compose up -d backend worker
```

### Monitor Workflow Execution

The Temporal UI (http://localhost:8080) shows:
- All workflow executions
- Activity timelines
- Retry attempts
- Error details
- Event history

This is invaluable for debugging initialization issues.

## Architecture Benefits

### Traditional Startup Script Problems:
- ❌ No visibility into what failed
- ❌ Manual retry logic for transient errors
- ❌ No audit trail of initialization
- ❌ Hard to coordinate distributed tasks
- ❌ Error handling is ad-hoc

### Temporal Bootstrap Solution:
- ✅ Full visibility in UI
- ✅ Automatic retries with backoff
- ✅ Complete workflow history
- ✅ Easy task coordination
- ✅ Robust error handling

## Next Steps

After successful startup:

1. **Check Bootstrap Status**: http://localhost:8080 (find workflow: `system-bootstrap`)
2. **Test API**: http://localhost:8000/docs
3. **View Logs**: `docker compose logs -f`
4. **Monitor Workers**: Check Temporal UI task queues

## Related Documentation

- [Temporal Guide](../.github/temporal_guide.md)
- [Development Setup](../docs/DEVELOPMENT.md)
- [Project Status](../docs/PROJECT_STATUS.md)
