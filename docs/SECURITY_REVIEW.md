# Security Review

## Overall Assessment

The project has a reasonable start: JWT auth, role hierarchy, password hashing, admin/operator/viewer roles, and protected CRUD routes. However, several high-value routes and default settings need immediate hardening before production exposure.

## Critical Issues

| Priority | Issue | Evidence | Consequence | Fix | Complexity | Impact | Effort |
|---|---|---|---|---|---|---|---|
| Critical | Playback stream route does not authenticate. | `/recordings/{recording_id}/play` accepts `token` but has no user dependency. | Unauthorized users can access recordings by ID. | Add flexible auth dependency and tests. | Low | Critical | 0.5 day |
| Critical | Config restore route does not authenticate. | `restore_backup(file: UploadFile = File(...))` lacks admin dependency. | Unauthenticated config overwrite risk. | Require admin, validate ZIP, add tests. | Low | Critical | 0.5 day |
| Critical | Production can run with default JWT and DB secrets. | Defaults in `backend/core/config.py` and Compose. | Token forging and DB compromise if defaults are used. | Fail startup on default secrets when `APP_ENV=production`. | Medium | Critical | 1 day |
| Critical | Default admin password is documented and seeded. | `scripts/setup_db.py` creates `admin / nvr1234`. | Known credentials may remain active. | Force first-login password change or print one-time generated password. | Medium | Critical | 1 day |

## High Issues

| Priority | Issue | Consequence | Fix | Complexity | Impact | Effort |
|---|---|---|---|---|---|---|
| High | Wildcard CORS with credentials. | Any origin is allowed by policy. | Env-driven allowlist. | Low | High | 0.5 day |
| High | Camera credentials are stored in RTSP URLs and `config_json`. | Credential leakage through DB dumps, logs, or API responses. | Store credential fields separately, mask responses, avoid logging RTSP URLs. | Medium | High | 1-2 days |
| High | Tracked sample config includes a camera password. | Users may copy weak credentials or leak real credentials if samples are edited. | Replace with placeholder and add `config/cameras.example.yaml`. | Low | High | 0.5 day |
| High | Docker backend runs as root. | Container breakout or file permission mistakes have wider impact. | Add non-root user in Dockerfile. | Low | High | 0.5 day |
| High | No rate limiting on login. | Brute force is easier on exposed deployments. | Add rate limiting at app or Nginx level. | Medium | High | 1 day |

## Medium Issues

| Priority | Issue | Consequence | Fix | Complexity | Impact | Effort |
|---|---|---|---|---|---|---|
| Medium | Access token stored in `localStorage`. | XSS can steal tokens. | Prefer httpOnly cookie or short-lived access token plus refresh flow. | Medium | Medium | 1-2 days |
| Medium | Refresh token is returned but refresh/logout endpoints are not implemented in current auth router. | Token lifecycle is incomplete. | Implement refresh/logout or remove claims from docs until implemented. | Medium | Medium | 1 day |
| Medium | File upload restore needs ZIP-slip protection. | Malicious archive paths can overwrite unexpected files. | Reject absolute paths, `..`, symlinks, and non-YAML entries. | Low | High | 0.5 day |
| Medium | PostgreSQL port is published by default in Compose. | Local network can reach DB if firewall allows it. | Use dev-only profile or bind to `127.0.0.1`. | Low | Medium | 0.5 day |

## Recommended Security Tests

- Playback without token returns 401.
- Playback with invalid token returns 401.
- Playback with valid token returns 200 or 206.
- Config restore without token returns 401.
- Config restore as non-admin returns 403.
- Config restore rejects ZIP entries containing `../`.
- Login is rate-limited after repeated failures.
- Production startup fails with default JWT secret.

## Secure Configuration Checklist

- Change admin password immediately after install.
- Set a random `JWT_SECRET` with at least 32 bytes of entropy.
- Use a unique PostgreSQL password per environment.
- Restrict CORS to the real dashboard origin.
- Put the NVR behind VPN or HTTPS reverse proxy.
- Do not expose PostgreSQL outside the host.
- Rotate camera credentials and avoid committing them to Git.

