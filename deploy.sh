#!/usr/bin/env bash
# ============================================================
#  Text Summarization Platform — Deployment Script
# ============================================================
set -euo pipefail

MODE="${1:-dev}"                 # dev | prod
PROJECT_NAME="summarization"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC}  $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# ── Pre-flight checks ───────────────────────────────────────
command -v docker >/dev/null 2>&1 || error "Docker is not installed"
docker info >/dev/null 2>&1     || error "Docker daemon is not running"

# ── Build & Start ────────────────────────────────────────────
if [ "$MODE" = "prod" ]; then
    info "Starting in PRODUCTION mode with Nginx proxy..."
    docker compose -p "$PROJECT_NAME" \
        -f docker-compose.yml \
        -f docker-compose.prod.yml \
        up --build -d
else
    info "Starting in DEVELOPMENT mode..."
    docker compose -p "$PROJECT_NAME" \
        -f docker-compose.yml \
        up --build -d
fi

# ── Wait for healthy services ───────────────────────────────
info "Waiting for services to become healthy..."
sleep 5

MAX_RETRIES=30
RETRY=0
TARGET_URL="http://localhost:3000/health"
[ "$MODE" = "prod" ] && TARGET_URL="http://localhost:80/health"

until curl -sf "$TARGET_URL" > /dev/null 2>&1; do
    RETRY=$((RETRY + 1))
    if [ "$RETRY" -ge "$MAX_RETRIES" ]; then
        warn "Services did not become healthy in time"
        echo ""
        docker compose -p "$PROJECT_NAME" logs --tail=20
        exit 1
    fi
    sleep 2
done

# ── Report ───────────────────────────────────────────────────
echo ""
info "========================================="
info " Deployment complete!"
info "========================================="

if [ "$MODE" = "prod" ]; then
    info " Nginx proxy:    http://localhost:80"
    info " Health check:   http://localhost:80/health"
    info " API docs:       http://localhost:80/api/v1/docs"
    info " Summarize:      POST http://localhost:80/api/v1/summarize"
else
    info " API Gateway:    http://localhost:3000"
    info " NLP Service:    http://localhost:8000"
    info " Health check:   http://localhost:3000/health"
    info " API docs:       http://localhost:3000/api/v1/docs"
    info " Summarize:      POST http://localhost:3000/api/v1/summarize"
fi

echo ""
info "Container status:"
docker compose -p "$PROJECT_NAME" ps
