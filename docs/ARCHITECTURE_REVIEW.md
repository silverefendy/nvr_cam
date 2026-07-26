# Architecture Review

## Current Architecture

The project follows a layered architecture:

- Client layer: React web dashboard and Flutter mobile app.
- API layer: FastAPI routers under `backend/api/routers`.
- Service layer: recorder, motion, storage, encoder, notifier, discovery, and health services.
- Data layer: SQLAlchemy models, repositories, Alembic migrations, and PostgreSQL.
- Runtime layer: FFmpeg/OpenCV processes, HLS folders, snapshot folders, systemd services, Docker Compose, and Nginx.

This is a good baseline for a self-hosted NVR because video processing is isolated from API routing and persistent metadata is separated from file storage.

## Strengths

- Folder structure is understandable and maps to business domains.
- Repository pattern exists for database access.
- Recorder, motion, storage, encoder, and notifier are independent service modules.
- Frontend separates API clients, pages, stores, hooks, and components.
- Deployment supports both native Ubuntu/systemd and Docker-based development.
- Existing docs capture project goals, hardware assumptions, and feature history.

## Architecture Risks

| Priority | Risk | Why it matters | Recommendation | Complexity | Impact | Effort |
|---|---|---|---|---|---|---|
| Critical | Auth-sensitive streaming logic is implemented directly in the playback router and currently misses auth enforcement. | Playback is the highest-value data path. | Move reusable stream authorization into a tested dependency or service-level policy. | Low | Critical | 0.5 day |
| High | Long-running FFmpeg remux/transcode work runs during HTTP requests. | API workers can be blocked by video jobs and user requests can time out. | Introduce a job queue table or lightweight background worker for playback preparation. | Medium | High | 2-3 days |
| High | Application startup launches recorder, storage monitor, and motion loops inside API lifespan. | A web API restart also restarts video services; failures are coupled. | Keep current path for small installs, but define a clear service boundary for production: API, recorder, motion, encoder as separate commands. | Medium | High | 2 days |
| Medium | Settings are split across `.env`, YAML, DB models, and `config_json`. | Configuration behavior is hard to reason about. | Define a source-of-truth matrix and migrate volatile camera settings either to columns or explicit JSON schema. | Medium | Medium | 1-2 days |
| Medium | Service singleton state is updated through imports from `backend.api.app`. | Cross-module coupling makes tests and multi-process deployments harder. | Use FastAPI app state only at API boundaries; pass service handles explicitly or use a small service registry module. | Medium | Medium | 1 day |

## Folder Organization

The main structure is suitable:

```text
backend/
  api/
  core/
  db/
  services/
  utils/
frontend/
  src/api/
  src/components/
  src/hooks/
  src/pages/
  src/store/
mobile/
config/
scripts/
docs/
```

Recommended cleanup:

- Move historical patch scripts out of the repository root.
- Keep all project documentation under lowercase `docs/` so links are stable across case-sensitive and case-insensitive filesystems.
- Add `docs/runbooks/` for operator tasks: restore config, rotate secrets, add camera, recover disk full, recover DB.

## Separation of Concerns

The backend mostly separates routing, persistence, and services. The main exceptions are:

- Routers perform process-related work and background task scheduling.
- Storage cleanup operates directly on files without repository-level metadata reconciliation.
- Config routes know about camera credential layout and RTSP URL construction.

Recommended design:

- Add `CameraConfigService` for RTSP URL building, credential masking, and recorder restart decisions.
- Add `PlaybackService` for codec probe, cache lookup, remux/transcode job creation, and range response metadata.
- Add `RetentionService` for disk cleanup plus DB reconciliation.

## Dependency Injection

FastAPI dependencies are used for DB sessions and auth, but service objects are largely singletons or pulled from `app.state`.

Recommended improvements:

- Keep DB and user dependencies as-is.
- Add explicit dependencies for `RecordingManager`, `StorageManager`, and `MotionManager`.
- Avoid importing `app` inside service modules; it makes services depend on the web framework.

## Scalability

The current architecture can support a small to medium single-server install, especially when recording uses stream copy. The main scaling risks are CPU-bound transcodes, motion detection across many cameras, and disk cleanup across large file trees.

Recommended scaling path:

1. Keep one API instance.
2. Run recorder, motion, and encoder as separate processes or systemd services.
3. Add a job queue for transcode/remux/AV1 work.
4. Add DB-backed service heartbeats and job state.
5. Add per-camera resource limits and global CPU safeguards.
