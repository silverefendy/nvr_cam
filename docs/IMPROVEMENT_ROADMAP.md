# Improvement Roadmap

## Phase 0: Immediate Security Fixes

| Priority | Work item | Why | Best solution | Complexity | Impact | Effort |
|---|---|---|---|---|---|---|
| Critical | Enforce auth on playback streaming. | Recordings are sensitive. | Use `get_current_user_flexible` on `/recordings/{id}/play`; add negative tests. | Low | Critical | 0.5 day |
| Critical | Enforce admin auth on config restore. | Restore can overwrite system behavior. | Add `Depends(get_current_admin_user)` and validate ZIP entries. | Low | Critical | 0.5 day |
| Critical | Block default secrets in production. | Defaults are public. | Runtime checks for `JWT_SECRET`, `DB_PASSWORD`, and default admin state. | Medium | Critical | 1 day |
| High | Replace wildcard CORS in production. | Browser trust boundary is too broad. | Env-driven `CORS_ORIGINS`, localhost defaults for dev. | Low | High | 0.5 day |

## Phase 1: Reliability and Test Foundation

| Priority | Work item | Why | Best solution | Complexity | Impact | Effort |
|---|---|---|---|---|---|---|
| High | Add GitHub Actions. | Prevent regressions on `main`. | Backend import/tests, frontend build, YAML validation, Docker build. | Medium | High | 1 day |
| High | Fix current backend tests. | Existing unit imports are stale. | Update imports to `backend.core.security` or current service modules. | Low | High | 0.5 day |
| High | Add route-level security tests. | Security regressions are likely without tests. | Use `pytest`, `httpx.AsyncClient`, dependency overrides, and temp files. | Medium | High | 1-2 days |
| Medium | Add smoke tests for Docker startup. | Docker mode is a supported workflow. | Compose health check test or documented manual smoke test. | Medium | Medium | 1 day |

## Phase 2: Data and Configuration Hygiene

| Priority | Work item | Why | Best solution | Complexity | Impact | Effort |
|---|---|---|---|---|---|---|
| High | Reconcile `segment_duration`. | DB/model/config disagreement causes hidden behavior. | Pick DB column or JSON schema, write migration, update forms and recorder. | Medium | High | 1 day |
| High | Reconcile cleanup with DB metadata. | File deletion must not leave stale recording rows. | `RetentionService` deletes files and rows together; log failures. | Medium | High | 1-2 days |
| Medium | Define config source of truth. | Settings are split across env, YAML, DB, JSON. | Add `docs/CONFIGURATION.md` and migrate duplicate APIs. | Medium | Medium | 1 day |
| Medium | Mask camera credentials in API responses. | RTSP URLs include usernames/passwords. | Store credentials separately or mask response fields for non-admin use. | Medium | Medium | 1-2 days |

## Phase 3: Performance and Operations

| Priority | Work item | Why | Best solution | Complexity | Impact | Effort |
|---|---|---|---|---|---|---|
| High | Move playback transcode out of request path. | Large files can block requests for minutes. | Job queue with status endpoint and cached output. | Medium | High | 2-3 days |
| Medium | Add cache cleanup for `/tmp/nvr_remux`. | Transcoded files can fill OS disk. | Size/age limit, background cleanup, dashboard metric. | Low | Medium | 0.5 day |
| Medium | Add service health and restart runbooks. | Operators need predictable recovery steps. | `docs/runbooks/*.md` plus systemd/Docker health checks. | Low | Medium | 1 day |
| Medium | Add observability fields. | Camera failures need traceable logs. | Request IDs, camera IDs, job IDs, structured log consistency. | Medium | Medium | 1 day |

## Phase 4: Product and UX

| Priority | Work item | Why | Best solution | Complexity | Impact | Effort |
|---|---|---|---|---|---|---|
| Medium | Finish light-theme redesign consistently. | Current UI history mentions partial redesign. | Shared theme tokens and reusable table/filter controls. | Medium | Medium | 2-4 days |
| Medium | Improve playback workflow. | Transcode delay needs user feedback. | Show preparing/progress state, retry, and cache status. | Medium | High | 2 days |
| Low | Improve mobile verification. | Flutter code exists but build is not verified here. | Add `flutter analyze` and release build instructions to CI or manual checklist. | Medium | Medium | 1 day |
| Low | Add operator docs. | NVR systems need repeatable operations. | Camera add/edit, storage full, restore backup, rotate secrets, update app. | Low | Medium | 1 day |

