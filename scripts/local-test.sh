#!/bin/bash
# =============================================================
# local-test.sh
# Jalankan semua test lokal sebelum push ke server
# Usage: bash scripts/local-test.sh
# =============================================================
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

pass() { echo -e "${GREEN}✅ $1${NC}"; }
fail() { echo -e "${RED}❌ $1${NC}"; exit 1; }
info() { echo -e "${YELLOW}⏳ $1...${NC}"; }

echo ""
echo "================================================"
echo " nvr_cam — Local Test Suite"
echo " $(date '+%Y-%m-%d %H:%M:%S')"
echo "================================================"
echo ""

# ---- Backend ----
info "[1/5] Cek Python import backend"
python -c "from backend.api.app import app" 2>/dev/null && pass "Backend import OK" || fail "Backend import GAGAL"

info "[2/5] Jalankan integration test"
if command -v pytest &>/dev/null; then
  pytest backend/tests/integration/ -q --tb=short && pass "Integration tests OK" || fail "Integration tests GAGAL"
else
  echo "      (pytest tidak ditemukan, skip)"
fi

# ---- Frontend ----
info "[3/5] Frontend TypeScript build"
if [ -d frontend ]; then
  cd frontend
  npm run build --silent && pass "Frontend build OK" || fail "Frontend build GAGAL"
  cd ..
else
  echo "      (folder frontend tidak ditemukan, skip)"
fi

# ---- Flutter ----
info "[4/5] Flutter analyze"
if command -v flutter &>/dev/null; then
  cd mobile
  flutter analyze --no-pub 2>&1 | tail -5
  flutter analyze --no-pub &>/dev/null && pass "Flutter analyze OK" || fail "Flutter analyze GAGAL"
  cd ..
else
  echo -e "${YELLOW}      (Flutter CLI tidak ditemukan — skip)${NC}"
fi

# ---- Config ----
info "[5/5] Validasi config YAML"
python -c "
import yaml, sys
for f in ['config/cameras.yaml','config/storage.yaml','config/system.yaml']:
    try:
        yaml.safe_load(open(f))
        print(f'  OK: {f}')
    except Exception as e:
        print(f'  ERROR: {f}: {e}')
        sys.exit(1)
" && pass "Config YAML valid" || fail "Config YAML error"

echo ""
echo "================================================"
echo -e "${GREEN} Semua test PASSED — aman untuk di-deploy!${NC}"
echo "================================================"
echo ""
