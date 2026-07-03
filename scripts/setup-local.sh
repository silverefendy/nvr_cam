#!/bin/bash
# =============================================================
# setup-local.sh
# Setup environment development lokal dari nol (1x saja)
# Usage: bash scripts/setup-local.sh
# =============================================================
set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

ok()   { echo -e "${GREEN}✅ $1${NC}"; }
info() { echo -e "${YELLOW}➡  $1${NC}"; }

echo ""
echo "================================================"
echo " nvr_cam — Setup Development Lokal"
echo " $(date '+%Y-%m-%d %H:%M:%S')"
echo "================================================"
echo ""

# 1. Cek dependencies
info "Cek Docker..."
command -v docker &>/dev/null || { echo "❌ Docker tidak ditemukan. Install: https://docs.docker.com/get-docker/"; exit 1; }
ok "Docker OK ($(docker --version | cut -d' ' -f3 | tr -d ','))"

# 2. Setup .env
if [ ! -f .env ]; then
  cp .env.example .env
  ok ".env dibuat dari .env.example"
  echo ""
  echo "  ⚠️  PENTING: Edit file .env terlebih dahulu!"
  echo "     Minimal isi: DB_PASSWORD, JWT_SECRET, TELEGRAM_BOT_TOKEN"
  echo ""
  read -p "  Sudah edit .env? (y/N): " ans
  [ "$ans" = "y" ] || [ "$ans" = "Y" ] || { echo "Silakan edit .env dulu, lalu jalankan ulang script ini."; exit 0; }
else
  ok ".env sudah ada"
fi

# 3. Python venv (untuk test lokal tanpa Docker)
info "Setup Python virtual environment..."
if [ ! -d venv ]; then
  python3 -m venv venv
  ok "venv dibuat"
fi
./venv/bin/pip install -q -r backend/requirements.txt
ok "Python dependencies terinstall"

# 4. Frontend dependencies
info "Install frontend npm packages..."
cd frontend && npm install -q && cd ..
ok "npm packages terinstall"

# 5. Jalankan stack
info "Menjalankan stack lokal (Docker)..."
docker compose -f docker-compose.dev.yml up -d

# Tunggu DB ready
echo "   Tunggu database siap..."
for i in $(seq 1 15); do
  docker compose -f docker-compose.dev.yml exec -T db pg_isready -U nvr_user -d nvr_cam &>/dev/null && break
  sleep 2
done

# 6. Jalankan migrasi
info "Jalankan Alembic migration..."
docker compose -f docker-compose.dev.yml exec backend alembic upgrade head
ok "Database migration selesai"

echo ""
echo "================================================"
echo -e "${GREEN} Setup selesai! Stack berjalan:${NC}"
echo ""
echo "  Frontend : http://localhost:5173"
echo "  Backend  : http://localhost:8000"
echo "  API Docs : http://localhost:8000/api/docs"
echo "  Login    : admin / cctv1234"
echo ""
echo "  Perintah berguna:"
echo "    make logs         → lihat log semua service"
echo "    make test         → jalankan semua test"
echo "    make stop         → stop stack"
echo "    make deploy       → deploy ke server"
echo "================================================"
echo ""
