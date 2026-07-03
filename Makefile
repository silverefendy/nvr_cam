# Makefile — nvr_cam
# Shortcut perintah sehari-hari
# Usage: make <target>
# Contoh: make dev | make test | make deploy

.PHONY: help dev stop test build logs shell-backend shell-db deploy clean

# Default: tampilkan help
help:
	@echo ""
	@echo "  nvr_cam — Available Commands"
	@echo "  ========================================="
	@echo ""
	@echo "  DEVELOPMENT (lokal)"
	@echo "  make dev          Jalankan stack lokal (DB + Backend + Frontend)"
	@echo "  make stop         Stop semua container"
	@echo "  make logs         Lihat log semua service"
	@echo "  make logs-backend Lihat log backend saja"
	@echo "  make shell-backend Masuk ke container backend"
	@echo "  make shell-db     Masuk ke psql"
	@echo ""
	@echo "  TESTING"
	@echo "  make test         Jalankan semua local test (python + frontend + flutter)"
	@echo "  make test-backend Hanya backend pytest"
	@echo "  make test-build   Hanya frontend build check"
	@echo ""
	@echo "  BUILD"
	@echo "  make build        Build semua docker image"
	@echo "  make build-apk    Build Flutter APK (butuh Flutter CLI)"
	@echo ""
	@echo "  DEPLOY"
	@echo "  make deploy       Push ke server (via git push server main)"
	@echo "  make deploy-check Cek status service di server"
	@echo ""
	@echo "  LAINNYA"
	@echo "  make clean        Hapus container + volume dev"
	@echo "  make db-reset     Reset DB lokal (HAPUS SEMUA DATA)"
	@echo ""

# ---- Development ----

dev:
	@echo "🚀 Menjalankan stack development lokal..."
	@[ -f .env ] || (cp .env.example .env && echo "⚠️  .env dibuat dari .env.example — edit sesuai kebutuhan")
	docker compose -f docker-compose.dev.yml up -d
	@echo ""
	@echo "✅ Stack berjalan:"
	@echo "   Frontend : http://localhost:5173"
	@echo "   Backend  : http://localhost:8000"
	@echo "   API Docs : http://localhost:8000/api/docs"
	@echo "   Database : localhost:5432"
	@echo ""
	@echo "Log: make logs"

stop:
	docker compose -f docker-compose.dev.yml down

logs:
	docker compose -f docker-compose.dev.yml logs -f

logs-backend:
	docker compose -f docker-compose.dev.yml logs -f backend

shell-backend:
	docker compose -f docker-compose.dev.yml exec backend bash

shell-db:
	docker compose -f docker-compose.dev.yml exec db psql -U nvr_user -d nvr_cam

# ---- Testing ----

test:
	@bash scripts/local-test.sh

test-backend:
	pytest backend/tests/ -v --tb=short

test-build:
	cd frontend && npm run build

# ---- Build ----

build:
	docker compose -f docker-compose.dev.yml build

build-apk:
	@echo "📱 Build Flutter APK..."
	cd mobile && flutter pub get && flutter build apk --release
	@echo "✅ APK: mobile/build/app/outputs/flutter-apk/app-release.apk"

# ---- Deploy ke server ----

deploy:
	@echo "🚢 Push ke server..."
	@bash scripts/local-test.sh
	git push server main
	@echo "✅ Deploy selesai! Cek: make deploy-check"

deploy-check:
	@echo "📡 Status service di server:"
	ssh $${SERVER_USER:-nvr}@$${SERVER_IP} "systemctl is-active nvr-api nvr-recorder nvr-motion nvr-encoder"

# ---- Lainnya ----

clean:
	docker compose -f docker-compose.dev.yml down -v
	@echo "🧹 Container dan volume dev dihapus"

db-reset:
	@echo "⚠️  Ini akan HAPUS SEMUA DATA di DB lokal!"
	@read -p "Ketik 'yes' untuk lanjut: " confirm && [ "$$confirm" = "yes" ]
	docker compose -f docker-compose.dev.yml down -v
	docker compose -f docker-compose.dev.yml up -d db
	@sleep 3
	docker compose -f docker-compose.dev.yml exec backend alembic upgrade head
	@echo "✅ DB direset dan migration dijalankan"
