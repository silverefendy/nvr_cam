# Technical Debt and Improvement Register

`docs/TECH_DEBT.md` adalah dokumen induk untuk semua kebutuhan improvement repository ini.  
Semua backlog perbaikan, hardening, cleanup arsitektur, peningkatan UX, operasional, testing, dan roadmap eksekusi dirangkum di sini supaya tidak tersebar.

## Cara Pakai

- Gunakan dokumen ini sebagai single source of truth untuk improvement.
- Jika ada temuan audit baru, tambahkan ke seksi yang sesuai.
- Jika ada item selesai, pindahkan statusnya atau beri catatan implementasi.
- Prioritas mengikuti urutan: `Critical`, `High`, `Medium`, `Low`.

## Critical

| Area | Item | Evidence / Context | Consequence | Recommended improvement | Complexity | Impact | Effort |
|---|---|---|---|---|---|---|---|
| Security | Playback endpoint has token parameter but no validation. | `recordings.py` imports `get_current_user_flexible`, accepts `token`, then serves the file without a user dependency. | Private recordings can be exposed. | Enforce auth and add negative/positive endpoint tests. | Low | Critical | 0.5 day |
| Security | Config restore endpoint lacks admin auth. | `restore_backup(file: UploadFile = File(...))` has no admin dependency. | Unauthenticated config overwrite risk. | Require admin, validate ZIP contents, add tests. | Low | Critical | 0.5 day |
| Security | Production defaults are usable secrets. | `devpassword123`, `changeme-secret-key-for-development-only`, default admin password, sample camera password. | Misconfiguration can become a real incident. | Fail startup on default secrets and remove real-looking sample credentials. | Medium | Critical | 1 day |
| Security | CORS is wildcard with credentials enabled. | App middleware allows all origins. | Browser trust boundary is too broad. | Use explicit env-driven allowlist, keep localhost-only defaults for dev. | Low | High | 0.5 day |

## High

| Area | Item | Evidence / Context | Consequence | Recommended improvement | Complexity | Impact | Effort |
|---|---|---|---|---|---|---|---|
| Architecture | Camera schema drift. | Migration has `segment_duration`; model relies on `config_json` and fallback logic. | Behavior is implicit and migration changes become risky. | Reconcile DB column, model, and config source of truth. | Medium | High | 1 day |
| Data lifecycle | Cleanup does not reconcile DB metadata. | Storage manager unlinks files directly from disk. | Broken playback rows and inaccurate storage/reporting. | Delete or mark metadata in the same retention workflow. | Medium | High | 1-2 days |
| Performance | HEVC playback transcode runs in request path. | First playback of large files can take minutes. | API workers can stall and UX becomes confusing. | Move transcode/remux to background jobs with status polling. | Medium | High | 2-3 days |
| Deployment | Docker backend runs as root and DB is published by default. | Current container hardening is minimal. | Higher blast radius if host or container is compromised. | Add non-root user, tighten container defaults, limit DB exposure. | Medium | High | 1 day |
| Testing | Tests do not cover current security surface. | Existing tests are minimal; legacy auth imports still exist. | High-risk regressions can pass unnoticed. | Fix stale tests and add route-level auth/config/playback tests. | Medium | High | 2 days |
| CI/CD | No CI pipeline. | No `.github/workflows` directory exists. | Regressions can land directly on `main`. | Add GitHub Actions for backend tests, frontend build, Docker build, and YAML validation. | Medium | High | 1 day |
| Operations | No actionable runbook set. | Recovery knowledge still lives in scattered docs and code familiarity. | Operators will struggle during outages or maintenance. | Add runbooks for disk full, restore backup, camera offline, service restart, and playback recovery. | Low | High | 1 day |
| Observability | Logs and service health are not yet operationally rich. | There is logging, but not a complete troubleshooting surface. | Debugging production incidents stays manual and slow. | Add request IDs, camera IDs, job IDs, failure counters, and last-error views. | Medium | High | 1-2 days |

## Medium

| Area | Item | Evidence / Context | Consequence | Recommended improvement | Complexity | Impact | Effort |
|---|---|---|---|---|---|---|---|
| API design | Response shapes are inconsistent. | Some clients unwrap `data.data`, others expect arrays directly. | Frontend client code becomes brittle. | Standardize API response contracts and document them. | Medium | Medium | 1-2 days |
| Configuration | Settings are split across `.env`, YAML, DB, and `config_json`. | Ownership of config is unclear. | Features drift and support gets harder over time. | Define one owner per config field and document the matrix. | Medium | Medium | 1 day |
| Backend | Settings router still contains placeholders. | `backend/api/routers/settings.py` has TODOs and overlaps with config APIs. | Duplicate config surfaces create confusion. | Remove or complete it and keep one settings surface. | Low | Medium | 0.5-1 day |
| Security | Tokens are stored in `localStorage`. | Auth store and API clients rely on browser storage. | XSS impact includes token theft. | Consider httpOnly cookie or shorter-lived token strategy. | Medium | Medium | 1-2 days |
| Security | Camera credentials are embedded in RTSP URLs and config JSON. | Credentials can leak via logs, dumps, or admin APIs. | Sensitive data handling is weaker than necessary. | Separate or mask credentials and avoid returning raw RTSP where possible. | Medium | Medium | 1-2 days |
| Frontend | Operational pages use heavy inline styling. | Layout and behavior are tightly mixed in large files. | UI maintenance gets slower and more fragile. | Extract reusable layout/table/filter components and shared tokens. | Medium | Medium | 2 days |
| UX | Playback UX does not explain heavy processing states. | Large files may appear stuck while remux/transcode runs. | Users perceive playback as broken. | Add preparing/progress/error/retry states. | Medium | High | 2 days |
| UX | Operator workflows still need polish. | Saved filters, bulk actions, and clearer empty/error states are limited. | Daily use stays heavier than it should be. | Improve workflow ergonomics in cameras, playback, events, and storage pages. | Medium | Medium | 2-3 days |
| Performance | No lifecycle management for `/tmp/nvr_remux`. | Cached outputs can accumulate indefinitely. | OS disk can fill unexpectedly. | Add age/size-based cache cleanup and dashboard visibility. | Low | Medium | 0.5 day |
| Performance | Motion detection and HLS transcode need scaling guardrails. | Many cameras can compete for CPU. | Performance degrades unpredictably under load. | Add concurrency caps and CPU-based safeguards. | Medium | Medium | 1-2 days |
| Database | API lists may grow without pagination. | `recordings` and event-heavy screens can expand over time. | Query latency and UI load can increase. | Add stable pagination and query limits. | Medium | Medium | 1 day |
| Mobile | Flutter app exists but verification is incomplete. | Build/analyze status is not consistently proven. | Mobile confidence is lower than web/backend. | Add `flutter analyze`, release build checks, and documented support matrix. | Medium | Medium | 1 day |
| Product ops | No structured audit trail for admin actions. | Login, delete, config change, restore, and user changes are not fully audit-friendly. | Harder to investigate mistakes and incidents. | Add admin/user audit logs with timestamps and actor IDs. | Medium | Medium | 1-2 days |
| Alerting | Alerts are still narrow. | Disk alerts exist conceptually, broader health alerting is limited. | Failures can go unnoticed too long. | Add alerts for camera offline duration, service crash loops, queue buildup, and cleanup failure. | Medium | Medium | 1-2 days |

## Low

| Area | Item | Evidence / Context | Consequence | Recommended improvement | Complexity | Impact | Effort |
|---|---|---|---|---|---|---|---|
| Repo hygiene | Root contains one-off patch scripts. | `patch*.py`, `patch*.ps1`, `fix*.ps1`. | Repository intent is harder to scan. | Archive or delete after confirming they are no longer needed. | Low | Low | 0.5 day |
| Documentation | Encoding drift remains in older markdown files. | Mojibake still appears in several docs. | Readability and professionalism drop. | Normalize docs to UTF-8 and simplify diagrams to ASCII where needed. | Low | Low | 0.5 day |
| Documentation | Mobile docs still have placeholder details. | `mobile/README.md` uses generic repository references. | Onboarding is slightly noisier. | Update mobile README to match the actual repo and current endpoints. | Low | Low | 0.25 day |
| UI polish | Light theme and visual consistency still need finishing work. | Some screens feel more evolved than others. | Product quality looks uneven. | Finish shared theme tokens and apply consistently. | Medium | Medium | 2-4 days |

## Suggested Execution Order

### Wave 1 - Secure the system

1. Enforce playback auth.
2. Enforce config restore auth.
3. Block default production secrets.
4. Replace wildcard CORS in production.

### Wave 2 - Stabilize delivery

1. Add CI pipeline.
2. Fix stale tests.
3. Add route-level auth/config/playback tests.
4. Add smoke checks for Docker startup.

### Wave 3 - Clean up data and architecture

1. Reconcile `segment_duration`.
2. Reconcile cleanup with DB metadata.
3. Define config source of truth.
4. Remove or finish duplicate settings surface.

### Wave 4 - Improve operations and observability

1. Add runbooks.
2. Add richer logs, request IDs, and service health surfaces.
3. Add broader alerting.
4. Add admin audit logs.

### Wave 5 - Improve performance and UX

1. Move playback processing out of request path.
2. Add playback cache lifecycle management.
3. Add transcode/motion scaling guardrails.
4. Improve playback status UX and operator workflows.

## Suggested Debt Policy

- Every feature PR should include a test or a clear reason no test was added.
- Every config field should have one source of truth: env, DB column, JSON config, or YAML.
- Every security-sensitive endpoint should have at least one negative test.
- Every operationally critical flow should have a runbook.
- Every new background process should expose health and last-error visibility.

## Notes

- `docs/AUDIT_REPORT.md` tetap berguna sebagai ringkasan audit.
- `docs/TECH_DEBT.md` sekarang menjadi daftar utama semua improvement.
- Roadmap terpisah sebaiknya hanya menjadi pointer ke dokumen ini agar tidak ada dua backlog yang divergen.
