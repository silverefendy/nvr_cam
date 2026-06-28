#!/bin/bash
set -euo pipefail
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
log()  { echo -e "${GREEN}[OK]${NC} $1"; }
warn() { echo -e "${YELLOW}[!!]${NC} $1"; }
err()  { echo -e "${RED}[ERR]${NC} $1"; exit 1; }
echo "============================================"
echo "  NVR Cam — Installer"
echo "============================================"
[[ $EUID -ne 0 ]] && err "Harus root: sudo bash install.sh"
log "Install dependencies..."
apt-get update -qq
apt-get install -y -qq ffmpeg python3 python3-pip python3-venv python3-opencv libopencv-dev postgresql-16 nginx git curl wget zfsutils-linux build-essential
curl -fsSL https://deb.nodesource.com/setup_20.x | bash - &>/dev/null
apt-get install -y -qq nodejs
INSTALL_DIR="/opt/nvr_cam"
if [ -d "$INSTALL_DIR/.git" ]; then
    log "Update dari GitHub..."; cd "$INSTALL_DIR" && git pull
else
    log "Clone dari GitHub..."; git clone https://github.com/silverefendy/nvr_cam "$INSTALL_DIR"
fi
cd "$INSTALL_DIR"
log "Create nvr user..."
if ! id -u nvr > /dev/null 2>&1; then
    useradd -r -s /bin/bash -d "$INSTALL_DIR" nvr
    chown -R nvr:nvr "$INSTALL_DIR"
fi
log "Setup Python env..."
sudo -u nvr python3 -m venv venv
sudo -u nvr ./venv/bin/pip install -q --upgrade pip
sudo -u nvr ./venv/bin/pip install -q -r backend/requirements.txt
[ ! -f .env ] && cp .env.example .env && warn "Edit /opt/nvr_cam/.env dulu!"
log "Setup DB..."
sudo -u postgres psql -c "CREATE USER cctv_user WITH PASSWORD 'CHANGE_THIS';" 2>/dev/null || true
sudo -u postgres psql -c "CREATE DATABASE cctv_db OWNER cctv_user;" 2>/dev/null || true
sudo -u nvr ./venv/bin/alembic upgrade head
log "Create admin user..."
sudo -u nvr ./venv/bin/python scripts/setup_db.py
log "Build frontend..."
cd frontend && npm install -q && npm run build && cd ..
log "Create directories..."
mkdir -p /tmp/hls
mkdir -p /tmp/hls/snapshots
chown -R nvr:nvr /tmp/hls
log "Setup Nginx..."
[ -f scripts/nginx/nvr_cam.conf ] && cp scripts/nginx/nvr_cam.conf /etc/nginx/sites-available/nvr_cam
ln -sf /etc/nginx/sites-available/nvr_cam /etc/nginx/sites-enabled/nvr_cam 2>/dev/null || true
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx
log "Register services..."
[ -d scripts/systemd ] && cp scripts/systemd/*.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable nvr-api nvr-recorder nvr-motion nvr-encoder 2>/dev/null || true
systemctl start  nvr-api nvr-recorder nvr-motion nvr-encoder 2>/dev/null || true
SERVER_IP=$(hostname -I | awk '{print $1}')
echo ""; echo "============================================"
echo -e "  ${GREEN}Selesai! Buka: http://$SERVER_IP${NC}"
echo "  Login: admin / nvr1234"
echo "============================================"
