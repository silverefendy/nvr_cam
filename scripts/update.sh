#!/bin/bash
set -euo pipefail
cd /opt/nvr_cam
git pull
sudo -u nvr ./venv/bin/pip install -q -r backend/requirements.txt
sudo -u nvr ./venv/bin/alembic upgrade head
cd frontend && npm install -q && npm run build && cd ..
systemctl restart nvr-api nvr-recorder nvr-motion nvr-encoder
echo "Update selesai!"
