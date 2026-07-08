#!/bin/bash
set -euo pipefail
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
log()  { echo -e "${GREEN}[OK]${NC} $1"; }
warn() { echo -e "${YELLOW}[!!]${NC} $1"; }
err()  { echo -e "${RED}[ERR]${NC} $1"; exit 1; }

echo "============================================"
echo "  NVR Cam — Installer (Native Ubuntu)"
echo "============================================"

[[ $EUID -ne 0 ]] && err "Harus root: sudo bash install.sh"

# ── 1. Dependencies ──────────────────────────────────────────
log "Install dependencies sistem..."
apt-get update -qq
apt-get install -y -qq \
    ffmpeg \
    python3 python3-pip python3-venv \
    python3-opencv libopencv-dev \
    postgresql nginx git curl wget \
    zfsutils-linux build-essential

curl -fsSL https://deb.nodesource.com/setup_20.x | bash - &>/dev/null
apt-get install -y -qq nodejs

# ── 2. Clone / Update Repo ───────────────────────────────────
INSTALL_DIR="/opt/nvr_cam"
if [ -d "$INSTALL_DIR/.git" ]; then
    log "Update dari GitHub..."
    cd "$INSTALL_DIR" && git pull
else
    log "Clone dari GitHub..."
    git clone https://github.com/silverefendy/nvr_cam "$INSTALL_DIR"
fi
cd "$INSTALL_DIR"

# ── 3. System User ───────────────────────────────────────────
log "Buat system user 'nvr'..."
if ! id -u nvr > /dev/null 2>&1; then
    useradd -r -s /bin/bash -d "$INSTALL_DIR" nvr
fi
chown -R nvr:nvr "$INSTALL_DIR"

# ── 4. Python Virtualenv ─────────────────────────────────────
log "Setup Python virtualenv..."
sudo -u nvr python3 -m venv venv
sudo -u nvr ./venv/bin/pip install -q --upgrade pip
sudo -u nvr ./venv/bin/pip install -q -r backend/requirements.txt

# ── 5. Environment File ──────────────────────────────────────
if [ ! -f .env ]; then
    cp .env.example .env
    warn "File .env dibuat dari .env.example."
    warn "WAJIB edit /opt/nvr_cam/.env sebelum menjalankan aplikasi!"
    warn "Minimal set: DB_PASSWORD, JWT_SECRET, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID"
fi

# ── 6. PostgreSQL ────────────────────────────────────────────
log "Setup database PostgreSQL..."

# Ambil password dari .env jika sudah ada, fallback ke default dev
DB_PASSWORD=$(grep '^DB_PASSWORD=' .env | cut -d'=' -f2 || echo "devpassword123")

# Buat user dan database jika belum ada
sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='nvr_user'" \
    | grep -q 1 || \
    sudo -u postgres psql -c "CREATE USER nvr_user WITH PASSWORD '${DB_PASSWORD}';"

sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='nvr_cam'" \
    | grep -q 1 || \
    sudo -u postgres psql -c "CREATE DATABASE nvr_cam OWNER nvr_user;"

# Jalankan migrasi
log "Jalankan Alembic migration..."
sudo -u nvr ./venv/bin/alembic -c backend/alembic.ini upgrade head

# ── 7. Seed Admin User ───────────────────────────────────────
log "Buat admin user default..."
sudo -u nvr ./venv/bin/python scripts/setup_db.py

# ── 8. Frontend Build ────────────────────────────────────────
log "Build frontend React..."
cd frontend
npm install -q
npm run build
cd ..

# ── 9. Direktori Runtime ─────────────────────────────────────
log "Buat direktori runtime..."
mkdir -p /var/lib/nvr_cam/hls
mkdir -p /var/lib/nvr_cam/snapshots
mkdir -p /var/log/nvr_cam
chown -R nvr:nvr /var/lib/nvr_cam /var/log/nvr_cam

# ── 10. Nginx ────────────────────────────────────────────────
log "Setup Nginx..."
cp scripts/nginx/cctv.conf /etc/nginx/sites-available/nvr_cam
ln -sf /etc/nginx/sites-available/nvr_cam /etc/nginx/sites-enabled/nvr_cam 2>/dev/null || true
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

# ── 11. Systemd Services ─────────────────────────────────────
log "Register systemd services..."
cp scripts/systemd/cctv-api.service      /etc/systemd/system/nvr-api.service
cp scripts/systemd/cctv-recorder.service /etc/systemd/system/nvr-recorder.service
cp scripts/systemd/cctv-motion.service   /etc/systemd/system/nvr-motion.service
cp scripts/systemd/cctv-encoder.service  /etc/systemd/system/nvr-encoder.service

systemctl daemon-reload
systemctl enable nvr-api nvr-recorder nvr-motion nvr-encoder
systemctl start  nvr-api nvr-recorder nvr-motion nvr-encoder

# ── Selesai ──────────────────────────────────────────────────
SERVER_IP=$(hostname -I | awk '{print $1}')
echo ""
echo "============================================"
echo -e "  ${GREEN}Instalasi selesai!${NC}"
echo -e "  Buka: ${GREEN}http://$SERVER_IP${NC}"
echo "  Login: admin / nvr1234"
echo ""
echo "  Cek status services:"
echo "    systemctl status nvr-api"
echo "    journalctl -u nvr-api -f"
echo ""
echo -e "  ${YELLOW}INGAT: Edit /opt/nvr_cam/.env jika belum!${NC}"
echo "============================================"
