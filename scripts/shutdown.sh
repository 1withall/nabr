#!/usr/bin/env bash
#
# Nābr System Shutdown Script
# 
# Gracefully shuts down all Nābr services in the correct order.
#
# Usage:
#   ./scripts/shutdown.sh            # Graceful shutdown
#   ./scripts/shutdown.sh --force    # Force shutdown (no graceful period)

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# Flags
FORCE=false

# Parse arguments
for arg in "$@"; do
    case $arg in
        --force|-f)
            FORCE=true
            shift
            ;;
        --help|-h)
            cat << EOF
Nābr System Shutdown Script

Usage:
  $0 [OPTIONS]

Options:
  --force, -f      Force immediate shutdown (no graceful period)
  --help, -h       Show this help message

Shutdown Order:
  1. Temporal Workers (graceful completion of in-progress tasks)
  2. FastAPI Backend
  3. PostgreSQL Database
  4. Temporal Server

EOF
            exit 0
            ;;
    esac
done

log_info() {
    echo -e "${GREEN}✓${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1"
}

log_step() {
    echo -e "\n${CYAN}▶ $1${NC}"
}

cat << "EOF"
    _   __     __     
   / | / /___ _/ /_    
  /  |/ / __ `/ __ \   
 / /|  / /_/ / /_/ /   
/_/ |_/\__,_/_.___/    
                       
  System Shutdown      
EOF

echo -e "\n${CYAN}Shutting down Nābr Platform...${NC}\n"

if [ "$FORCE" = true ]; then
    log_warn "Force shutdown enabled - services will stop immediately"
    docker compose down
    log_info "All services stopped"
else
    # Graceful shutdown
    
    log_step "Stopping Temporal Workers..."
    docker compose stop worker || log_warn "Worker not running"
    log_info "Workers stopped"
    
    log_step "Stopping FastAPI Backend..."
    docker compose stop backend || log_warn "Backend not running"
    log_info "Backend stopped"
    
    log_step "Stopping Temporal Web UI..."
    docker compose stop temporal-web || log_warn "Temporal UI not running"
    log_info "Temporal UI stopped"
    
    log_step "Stopping Temporal Server..."
    docker compose stop temporal || log_warn "Temporal not running"
    log_info "Temporal stopped"
    
    log_step "Stopping PostgreSQL..."
    docker compose stop postgres || log_warn "PostgreSQL not running"
    log_info "PostgreSQL stopped"
    
    log_info "Removing containers..."
    docker compose down
fi

echo ""
log_info "Nābr Platform shutdown complete"
echo ""
echo -e "${YELLOW}To start the system again:${NC}"
echo "  ./scripts/startup.sh"
echo ""
