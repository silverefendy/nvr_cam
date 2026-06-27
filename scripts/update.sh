#!/bin/bash
set -euo pipefail
cd /opt/cctv
git pull
./venv/bin/pip install -q -r backend/requirements.txt
./venv/bin/alembic upgrade head
cd frontend && npm install -q && npm run build && cd ..
systemctl restart cctv-api cctv-motion cctv-encoder
echo "Update selesai!"
