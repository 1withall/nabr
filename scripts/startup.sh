#!/usr/bin/env bash
#
# Nābr System Startup Script
# 
# This script orchestrates the complete system startup in the correct order:
# 1. Temporal server (with built-in SQLite persistence)
# 2. PostgreSQL database
# 3. Bootstrap Workflow (via Temporal) - runs migrations, health checks, etc.
# 4. FastAPI backend
# 5. Temporal workers
#
# The bootstrap workflow leverages Temporal's retry logic, error handling,
# and observability for all initialization tasks.
#
# Usage:
#   ./scripts/startup.sh              # Start entire system
#   ./scripts/startup.sh --skip-db    # Skip database services (use existing)
#   ./scripts/startup.sh --dev        # Development mode (no workers in background)

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_DIR="${PROJECT_ROOT}/logs"
PYTHON_CMD="${PYTHON_CMD:-python}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Flags
SKIP_DB=false
DEV_MODE=false

# Parse arguments
for arg in "$@"; do
    case $arg in
        --skip-db)
            SKIP_DB=true
            shift
            ;;
        --dev)
            DEV_MODE=true
            shift
            ;;
        --help|-h)
            cat << EOF
Nābr System Startup Script

Usage:
  $0 [OPTIONS]

Options:
  --skip-db        Skip starting database services (use existing instances)
  --dev            Development mode (workers run in foreground, verbose logging)
  --help, -h       Show this help message

Boot Sequence:
  1. Temporal Server (with SQLite persistence)
  2. PostgreSQL Database
  3. Bootstrap Workflow (migrations, health checks, seed data)
  4. FastAPI Backend
  5. Temporal Workers

The bootstrap workflow runs as a Temporal workflow, providing:
  - Automatic retries with exponential backoff
  - Full observability in Temporal UI
  - Error handling and recovery
  - Activity-level logging and tracing

Logs: $LOG_DIR/

EOF
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $arg${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Logging functions
log_step() {
    echo -e "\n${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}▶ $1${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
}

log_info() {
    echo -e "${GREEN}✓${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1"
}

log_progress() {
    echo -e "${BLUE}…${NC} $1"
}

# Create log directory
mkdir -p "$LOG_DIR"

# Banner
cat << "EOF"
    _   __     __     
   / | / /___ _/ /_    
  /  |/ / __ `/ __ \   
 / /|  / /_/ / /_/ /   
/_/ |_/\__,_/_.___/    
                       
   System Startup      
EOF

echo -e "\n${CYAN}Starting Nābr Platform...${NC}\n"

# ============================================================================
# STEP 1: Start Temporal Server
# ============================================================================
log_step "STEP 1: Starting Temporal Server"

log_progress "Checking if Temporal is already running..."
if docker ps | grep -q nabr-temporal; then
    log_info "Temporal is already running"
else
    log_progress "Starting Temporal server with SQLite persistence..."
    docker compose up -d temporal
    
    log_progress "Waiting for Temporal to be healthy..."
    for i in {1..60}; do
        if docker compose ps temporal | grep -q "healthy"; then
            log_info "Temporal is healthy"
            break
        fi
        if [ $i -eq 60 ]; then
            log_error "Temporal failed to become healthy after 60 seconds"
            exit 1
        fi
        sleep 1
    done
fi

log_info "Temporal Server ready at localhost:7233"
log_info "Temporal UI available at http://localhost:8080"

# ============================================================================
# STEP 2: Start PostgreSQL
# ============================================================================
if [ "$SKIP_DB" = false ]; then
    log_step "STEP 2: Starting PostgreSQL Database"
    
    log_progress "Checking if PostgreSQL is already running..."
    if docker ps | grep -q nabr-postgres; then
        log_info "PostgreSQL is already running"
    else
        log_progress "Starting PostgreSQL server..."
        docker compose up -d postgres
        
        log_progress "Waiting for PostgreSQL to be healthy..."
        for i in {1..30}; do
            if docker compose ps postgres | grep -q "healthy"; then
                log_info "PostgreSQL is healthy"
                break
            fi
            if [ $i -eq 30 ]; then
                log_error "PostgreSQL failed to become healthy after 30 seconds"
                exit 1
            fi
            sleep 1
        done
    fi
    
    log_info "PostgreSQL ready at localhost:5432"
else
    log_warn "Skipping database startup (--skip-db flag)"
fi

# ============================================================================
# STEP 3: Run Bootstrap Workflow
# ============================================================================
log_step "STEP 3: Running Bootstrap Workflow"

log_info "Executing bootstrap workflow via Temporal..."
log_info "This workflow will:"
echo "  • Run database migrations (via Alembic)"
echo "  • Verify database schema"
echo "  • Run health checks on all services"
echo "  • Initialize default data (if needed)"
echo "  • Validate configuration"
echo ""
log_progress "Starting bootstrap workflow..."

# Run the bootstrap workflow
cd "$PROJECT_ROOT"
$PYTHON_CMD -m nabr.temporal.bootstrap 2>&1 | tee "$LOG_DIR/bootstrap.log"

if [ ${PIPESTATUS[0]} -eq 0 ]; then
    log_info "Bootstrap workflow completed successfully"
    log_info "View execution details in Temporal UI: http://localhost:8080"
else
    log_error "Bootstrap workflow failed"
    log_error "Check logs: $LOG_DIR/bootstrap.log"
    log_error "Check Temporal UI for detailed error: http://localhost:8080"
    exit 1
fi

# ============================================================================
# STEP 4: Start FastAPI Backend
# ============================================================================
log_step "STEP 4: Starting FastAPI Backend"

log_progress "Checking if backend is already running..."
if docker ps | grep -q nabr-backend; then
    log_warn "Backend is already running, restarting..."
    docker compose restart backend
else
    log_progress "Starting backend server..."
    docker compose up -d backend
fi

log_progress "Waiting for backend to be ready..."
for i in {1..30}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        log_info "Backend is ready"
        break
    fi
    if [ $i -eq 30 ]; then
        log_error "Backend failed to start after 30 seconds"
        exit 1
    fi
    sleep 1
done

log_info "FastAPI Backend ready at http://localhost:8000"
log_info "API Documentation: http://localhost:8000/docs"

# ============================================================================
# STEP 5: Start Temporal Workers
# ============================================================================
log_step "STEP 5: Starting Temporal Workers"

if [ "$DEV_MODE" = true ]; then
    log_warn "Development mode: Workers will run in foreground"
    log_info "Press Ctrl+C to stop workers"
    echo ""
    exec $PYTHON_CMD -m nabr.temporal.worker
else
    log_progress "Starting workers in Docker container..."
    docker compose up -d worker
    
    # Wait a moment for workers to initialize
    sleep 3
    
    # Check if workers are running
    if docker compose ps worker | grep -q "Up"; then
        log_info "Workers started successfully"
        log_info "Worker logs: docker compose logs -f worker"
    else
        log_error "Workers failed to start"
        log_error "Check logs: docker compose logs worker"
        exit 1
    fi
fi

# ============================================================================
# Startup Complete
# ============================================================================
log_step "System Startup Complete! 🎉"

cat << EOF
${GREEN}All services are running:${NC}

  ${CYAN}Temporal Server${NC}
    • gRPC:    localhost:7233
    • Web UI:  http://localhost:8080
    • Status:  $(docker compose ps temporal | grep -q "healthy" && echo -e "${GREEN}Healthy${NC}" || echo -e "${RED}Unhealthy${NC}")

  ${CYAN}PostgreSQL${NC}
    • Host:    localhost:5432
    • Status:  $(docker compose ps postgres | grep -q "healthy" && echo -e "${GREEN}Healthy${NC}" || echo -e "${RED}Unhealthy${NC}")

  ${CYAN}FastAPI Backend${NC}
    • API:     http://localhost:8000
    • Docs:    http://localhost:8000/docs
    • Health:  http://localhost:8000/health
    • Status:  $(curl -s http://localhost:8000/health > /dev/null 2>&1 && echo -e "${GREEN}Healthy${NC}" || echo -e "${RED}Unhealthy${NC}")

  ${CYAN}Temporal Workers${NC}
    • Verification Worker:  $(docker compose ps worker | grep -q "Up" && echo -e "${GREEN}Running${NC}" || echo -e "${RED}Stopped${NC}")
    • Matching Worker:      $(docker compose ps worker | grep -q "Up" && echo -e "${GREEN}Running${NC}" || echo -e "${RED}Stopped${NC}")
    • Review Worker:        $(docker compose ps worker | grep -q "Up" && echo -e "${GREEN}Running${NC}" || echo -e "${RED}Stopped${NC}")
    • Notification Worker:  $(docker compose ps worker | grep -q "Up" && echo -e "${GREEN}Running${NC}" || echo -e "${RED}Stopped${NC}")

${YELLOW}Useful Commands:${NC}
  • View all logs:        docker compose logs -f
  • View worker logs:     docker compose logs -f worker
  • Stop all services:    docker compose down
  • Restart service:      docker compose restart [service]
  • Bootstrap workflow:   python -m nabr.temporal.bootstrap

${YELLOW}Next Steps:${NC}
  1. Check Temporal UI to see bootstrap workflow: http://localhost:8080
  2. Test API endpoints: http://localhost:8000/docs
  3. View logs: docker compose logs -f

EOF
