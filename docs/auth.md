# Auth & RBAC

## What ships

A self-contained local identity provider with **no native dependencies**:

* Passwords hashed with stdlib `hashlib.scrypt` (`app/core/security.py`).
* JWT access + refresh tokens (HS256, PyJWT). Access TTL 30 min, refresh 24 h (configurable).
* Three roles with server-side capability checks (`app/api/deps.py::require_cap`):

  | Capability | admin | analyst | viewer |
  |---|:-:|:-:|:-:|
  | `read` (all GET endpoints) | ✓ | ✓ | ✓ |
  | `scan:start`, `scan:cancel` | ✓ | ✓ | |
  | `report:generate`, migration updates | ✓ | ✓ | |
  | `settings:write` (weights, CRQC, application metadata) | ✓ | | |

RBAC is enforced in the API layer, not just hidden in the UI — a `viewer` calling
`POST /scans` gets `403` (covered by `tests/integration/test_scan_pipeline.py`).

## Swapping in OIDC / Auth0 / Keycloak

Nothing in the app depends on the token *mechanism* — only on
`app/core/security.py::decode_token(str) -> TokenPayload | None` and the `require_cap`
dependency. To integrate an external IdP:

1. Replace `decode_token` with JWKS validation of the IdP's access tokens
   (`PyJWT` + `PyJWKClient`, verify `iss` / `aud` / `exp`).
2. Map an IdP claim (group, role, `scope`) to one of `admin | analyst | viewer` when building
   `TokenPayload`, or extend `ROLE_CAPS` with your own capability set.
3. Drop `/auth/login` + `/auth/refresh` (the SPA redirects to the IdP instead) and keep
   `/me` reading from the validated token.
4. Remove the `users` table seed if identities are fully external, or keep it as a local
   profile/role cache keyed by `sub`.

No scanner, engine, router (other than `auth.py`), or frontend data-fetching code changes.
