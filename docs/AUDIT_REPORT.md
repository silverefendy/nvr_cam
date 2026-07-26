# Engineering Audit Report

**Repository:** `silverefendy/nvr_cam`  
**Branch audited:** `main`  
**Audit date:** 2026-07-26  
**Scope:** Backend, frontend, mobile app, database, Docker, native deployment scripts, tests, CI/CD, and documentation.

## Executive Summary

`nvr_cam` is a custom NVR system for Dahua/ONVIF cameras. The current stack is:

- Backend: Python 3.12, FastAPI, SQLAlchemy asyncio, Alembic, PostgreSQL 16, FFmpeg, OpenCV, JWT auth.
- Frontend: React 18, TypeScript, Vite, Tailwind, Zustand, TanStack Query, hls.js.
- Mobile: Flutter, Riverpod, Dio, shared_preferences, flutter_vlc_player.
- Deployment: Native Ubuntu/systemd/Nginx path plus Docker Compose for local or containerized operation.
- Storage/video: RTSP ingest, segmented MP4 recording, HLS live view, playback remux/transcode cache, multi-drive cleanup.

The repository has a useful modular shape: API routers, services, repositories, models, schemas, frontend API clients, pages, reusable camera components, and operational scripts are separated enough to maintain. The major concerns are security gaps, configuration drift, inconsistent test coverage, and production hardening.

## Critical Findings

| Area | Finding | Consequence | Recommended fix | Complexity | Impact | Effort |
|---|---|---|---|---|---|---|
| Security | `GET /api/v1/recordings/{id}/play` accepts a `token` query parameter but does not validate it. | Anyone who can reach the API and guess a recording ID can stream video. | Add `current_user: User = Depends(get_current_user_flexible)` to the endpoint and pass `token_query=token` through a dependency wrapper or parse the query in the dependency. Add tests for no token, invalid token, expired token, and valid token. | Low | Critical | 0.5 day |
| Security | `POST /api/v1/config/restore` has no auth dependency. | Unauthenticated callers may overwrite config if the API is reachable. | Add `Depends(get_current_admin_user)`, restrict uploaded ZIP contents, validate file names, and add integration tests. | Low | Critical | 0.5 day |
| Security | Default secrets and passwords exist in runtime defaults and compose files: DB password, JWT secret, admin password, and sample camera password. | Accidental production deployment with known secrets is possible. | Fail startup in production when secrets equal defaults; document required `.env`; remove real-looking camera credentials from tracked sample config. | Medium | Critical | 1 day |
| Security | CORS is `allow_origins=["*"]` with credentials enabled. | Browser-origin controls are ineffective and risky if cookies or credentialed requests are introduced. | Configure explicit origins from env, default to localhost only in development. | Low | High | 0.5 day |

## High Priority Findings

| Area | Finding | Consequence | Recommended fix | Complexity | Impact | Effort |
|---|---|---|---|---|---|---|
| Database | Camera migration includes `segment_duration`, while the ORM model relies on `config_json` and fallback logic. | Schema drift increases surprise during migrations and feature changes. | Reconcile model and migration: either map the column or migrate the setting into JSON consistently. | Medium | High | 1 day |
| Storage | Cleanup deletes files from disk but does not remove or reconcile recording metadata. | UI/API can show missing files; retention reporting becomes inaccurate. | Delete or mark DB records in the same cleanup workflow, preferably transactionally through repository methods. | Medium | High | 1-2 days |
| Playback | HEVC playback transcode happens synchronously inside the request path. | Large files can tie up API workers for minutes and create poor user experience. | Move transcode/remux to a background job with status polling, queue limits, and cache cleanup. | Medium | High | 2-3 days |
| Deployment | Docker backend runs as root and exposes PostgreSQL on host by default. | Higher blast radius if container or DB credentials are compromised. | Add non-root user, reduce Linux capabilities, restrict DB port exposure to dev profile, add health checks for API/frontend. | Medium | High | 1 day |
| CI/CD | No `.github/workflows` directory is present. | Regressions in imports, tests, TypeScript, Docker build, and security linting can land unnoticed. | Add GitHub Actions for backend tests, frontend build, dependency audit, Docker build, and YAML validation. | Medium | High | 1 day |

## Recommended Next Sprint

1. Fix playback auth and config restore auth.
2. Add production secret guardrails.
3. Add a minimal GitHub Actions workflow.
4. Reconcile camera `segment_duration` schema drift.
5. Add integration tests for the fixed security paths.

## Code Examples

Playback auth should become explicit at the endpoint boundary:

```python
@router.get("/{recording_id}/play")
async def play_recording(
    recording_id: int,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_flexible),
):
    ...
```

Production secret validation should fail closed:

```python
if settings.app_env == "production":
    if settings.jwt_secret.startswith("changeme-"):
        raise RuntimeError("JWT_SECRET must be changed in production")
    if settings.db_password == "devpassword123":
        raise RuntimeError("DB_PASSWORD must be changed in production")
```

