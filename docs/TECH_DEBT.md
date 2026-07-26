# Technical Debt Register

## Critical

| Debt | Evidence | Consequence | Recommendation | Complexity | Impact | Effort |
|---|---|---|---|---|---|---|
| Playback endpoint has token parameter but no validation. | `recordings.py` imports `get_current_user_flexible`, accepts `token`, and then serves the file without a user dependency. | Private recordings can be exposed. | Enforce auth and add endpoint tests. | Low | Critical | 0.5 day |
| Config restore endpoint lacks admin auth. | `restore_backup(file: UploadFile = File(...))` has no `_user=Depends(...)`. | Unauthenticated config overwrite risk. | Add admin dependency and ZIP validation. | Low | Critical | 0.5 day |
| Production defaults are usable secrets. | `devpassword123`, `changeme-secret-key-for-development-only`, default admin password. | Misconfiguration can become a security incident. | Fail production startup on default secrets. | Medium | Critical | 1 day |

## High

| Debt | Evidence | Consequence | Recommendation | Complexity | Impact | Effort |
|---|---|---|---|---|---|---|
| Camera schema drift. | Migration has `segment_duration`; model reads from `config_json` or fallback. | Feature behavior depends on implicit fallback. | Reconcile column/model/config. | Medium | High | 1 day |
| Cleanup does not reconcile DB metadata. | Storage manager unlinks files directly. | Broken playback rows and inaccurate retention metrics. | Delete or mark metadata through repository methods. | Medium | High | 1-2 days |
| Tests do not cover current security surface. | Existing tests are minimal; unit test imports legacy `services.auth` paths. | High-risk regressions can pass. | Fix imports and add route-level tests with `httpx`. | Medium | High | 2 days |
| No CI pipeline. | No `.github/workflows` directory. | Build/test regressions reach `main`. | Add GitHub Actions. | Medium | High | 1 day |

## Medium

| Debt | Evidence | Consequence | Recommendation | Complexity | Impact | Effort |
|---|---|---|---|---|---|---|
| Response shapes are inconsistent. | Some clients defensively unwrap `data.data`; others expect arrays. | Frontend code becomes brittle. | Define API response conventions and update clients. | Medium | Medium | 1-2 days |
| Settings router still contains placeholders. | `backend/api/routers/settings.py` has TODOs. | Duplicate config surfaces can confuse users. | Remove or implement it; prefer one settings API. | Low | Medium | 0.5-1 day |
| Frontend uses inline styles heavily in operational screens. | Large page/component files contain layout and behavior together. | UI changes get harder over time. | Extract reusable layout primitives and table/filter components. | Medium | Medium | 2 days |
| Token storage in `localStorage`. | Auth store and API clients read/write access token from localStorage. | XSS impact includes token theft. | Consider httpOnly cookies or short-lived memory token plus refresh strategy. | Medium | Medium | 1-2 days |

## Low

| Debt | Evidence | Consequence | Recommendation | Complexity | Impact | Effort |
|---|---|---|---|---|---|---|
| Root contains one-off patch scripts. | `patch*.py`, `patch*.ps1`, `fix*.ps1`. | Repository intent is harder to scan. | Archive or delete after confirming history is in Git. | Low | Low | 0.5 day |
| Documentation encoding drift. | Existing markdown contains mojibake. | Lower readability. | Normalize docs to UTF-8 and ASCII diagrams. | Low | Low | 0.5 day |
| Mobile docs mention placeholder repo URL. | `mobile/README.md` uses `yourusername/nvr_cam`. | New developer confusion. | Update mobile README. | Low | Low | 0.25 day |

## Suggested Debt Policy

- Every feature PR should include a test or an explicit reason no test is needed.
- Every config field should have one owner: env, DB column, JSON config, or YAML.
- Every security-sensitive endpoint should have a negative test.
- Operational scripts should be idempotent and documented in `docs/runbooks/`.

