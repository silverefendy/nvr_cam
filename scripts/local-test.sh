#!/bin/bash
# =============================================================
# local-test.sh
# Run local checks before deploy.
# Usage: bash scripts/local-test.sh
# =============================================================
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

pass() { echo -e "${GREEN}OK:${NC} $1"; }
fail() { echo -e "${RED}FAIL:${NC} $1"; exit 1; }
info() { echo -e "${YELLOW}RUN:${NC} $1"; }

CREATED_ENV_FILE=0
cleanup() {
  rm -f .env.ci
  if [ "$CREATED_ENV_FILE" = "1" ]; then
    rm -f .env
  fi
}
trap cleanup EXIT

PYTHON_BIN="${PYTHON_BIN:-}"
if [ -z "$PYTHON_BIN" ]; then
  if command -v python.exe &>/dev/null; then
    PYTHON_BIN=python.exe
  elif command -v python3 &>/dev/null; then
    PYTHON_BIN=python3
  elif command -v python &>/dev/null; then
    PYTHON_BIN=python
  else
    fail "Python not found"
  fi
fi

echo ""
echo "================================================"
echo " nvr_cam - Local Test Suite"
echo " $(date '+%Y-%m-%d %H:%M:%S')"
echo "================================================"
echo ""

info "[1/6] Python backend import"
APP_ENV=development "$PYTHON_BIN" -c "from backend.api.app import app" \
  && pass "Backend import" || fail "Backend import"

info "[2/6] Backend tests"
if "$PYTHON_BIN" -m pytest --version &>/dev/null; then
  APP_ENV=development "$PYTHON_BIN" -m pytest backend/tests/ -q --tb=short \
    && pass "Backend tests" || fail "Backend tests"
else
  echo "      pytest not found, skipping"
fi

info "[3/6] Frontend TypeScript build"
if [ -d frontend ]; then
  cd frontend
  npm run build --silent \
    && pass "Frontend build" || fail "Frontend build"
  cd ..
else
  echo "      frontend directory not found, skipping"
fi

info "[4/6] Flutter analyze"
if command -v flutter &>/dev/null && flutter --version &>/dev/null; then
  cd mobile
  flutter analyze --no-pub \
    && pass "Flutter analyze" || fail "Flutter analyze"
  cd ..
else
  echo "      Flutter CLI not found or not usable, skipping"
fi

info "[5/6] Config YAML"
"$PYTHON_BIN" -c "
import sys
import yaml
for f in ['config/cameras.yaml', 'config/storage.yaml', 'config/system.yaml']:
    try:
        yaml.safe_load(open(f, encoding='utf-8'))
        print(f'  OK: {f}')
    except Exception as e:
        print(f'  ERROR: {f}: {e}')
        sys.exit(1)
" && pass "Config YAML" || fail "Config YAML"

info "[6/6] Docker Compose config smoke"
if command -v docker &>/dev/null && docker compose version &>/dev/null; then
  cp .env.example .env.ci
  if [ ! -f .env ]; then
    cp .env.example .env
    CREATED_ENV_FILE=1
  fi
  DB_HOST=db DB_PORT=5432 DB_NAME=nvr_cam DB_USER=nvr_user \
    DB_PASSWORD=ci-db-password JWT_SECRET=ci-jwt-secret-with-at-least-32-bytes \
    APP_ENV=production CORS_ALLOW_ORIGINS=http://localhost:3000 \
    docker compose --env-file .env.ci -f docker-compose.yml config >/dev/null \
    && DB_PASSWORD=ci-db-password docker compose -f docker-compose.dev.yml config >/dev/null \
    && pass "Docker Compose config" || fail "Docker Compose config"
else
  echo "      Docker Compose not found or not usable, skipping"
fi

echo ""
echo "================================================"
echo -e "${GREEN}All local checks passed.${NC}"
echo "================================================"
echo ""
