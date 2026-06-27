#!/bin/bash
set -euo pipefail
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
log()  { echo -e "${GREEN}[OK]${NC} $1"; }
warn() { echo -e "${YELLOW}[!!]${NC} $1"; }
err()  { echo -e "${RED}[ERR]${NC} $1"; exit 1; }
echo "============================================"
echo "  CCTV NVR System — Installer"
echo "============================================"
[[ $EUID -ne 0 ]] && err "Harus root: sudo bash install.sh"
log "Install dependencies..."
apt-get update -qq
apt-get install -y -qq ffmpeg python3 python3-pip python3-venv postgresql-16 nginx git curl wget zfsutils-linux build-essential
curl -fsSL https://deb.nodesource.com/setup_20.x | bash - &>/dev/null
apt-get install -y -qq nodejs
INSTALL_DIR="/opt/cctv"
if [ -d "$INSTALL_DIR/.git" ]; then
    log "Update dari GitHub..."; cd "$INSTALL_DIR" && git pull
else
    log "Clone dari GitHub..."; git clone https://github.com/USERNAME/cctv-system "$INSTALL_DIR"
fi
cd "$INSTALL_DIR"
log "Setup Python env..."
python3 -m venv venv
./venv/bin/pip install -q --upgrade pip
./venv/bin/pip install -q -r backend/requirements.txt
[ ! -f .env ] && cp .env.example .env && warn "Edit /opt/cctv/.env dulu!"
log "Setup DB..."
sudo -u postgres psql -c "CREATE USER cctv_user WITH PASSWORD 'GANTI';" 2>/dev/null || true
sudo -u postgres psql -c "CREATE DATABASE cctv_db OWNER cctv_user;" 2>/dev/null || true
./venv/bin/alembic upgrade head
log "Build frontend..."
cd frontend && npm install -q && npm run build && cd ..
log "Setup Nginx..."
cp scripts/nginx/cctv.conf /etc/nginx/sites-available/cctv
ln -sf /etc/nginx/sites-available/cctv /etc/nginx/sites-enabled/cctv
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx
log "Register services..."
cp scripts/systemd/*.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable cctv-api cctv-recorder cctv-motion cctv-encoder
systemctl start  cctv-api cctv-recorder cctv-motion cctv-encoder
SERVER_IP=$(hostname -I | awk '{print $1}')
echo ""; echo "============================================"
echo -e "  ${GREEN}Selesai! Buka: http://$SERVER_IP${NC}"
echo "  Login: admin / cctv1234"
echo "============================================"
