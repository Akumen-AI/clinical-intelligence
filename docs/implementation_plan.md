# Fix Authentication and Session Security

Provide a brief description of the problem, any background context, and what the change accomplishes.

The current authentication model has several security flaws: it relies on JWTs as the source of truth (leading to stale roles/permissions), allows bearer tokens in query parameters (`?token=`), uses `localStorage` for long-lived tokens on the frontend, and lacks rate limiting or a session revocation mechanism.

This plan hardens the authentication layer by migrating to HttpOnly cookies, performing server-side user/role revalidation on every request, implementing refresh-token rotation and revocation, and adding login rate limiting.

## User Review Required

> [!WARNING]
> This is a major structural change to how the API client and backend authenticate. `?token=` parameters will be removed, meaning all document/image retrieval will rely on cookies.

## Open Questions

> [!NOTE]
> Since this is a demo environment without Redis, login rate limiting will be implemented using a simple in-memory cache (sliding window) on the FastAPI worker. Is this acceptable, or would you prefer adding a new database table for rate-limiting logs?

## Proposed Changes

### Database Layer
- Add a new `refresh_tokens` table to track issued refresh tokens, their expiry, and revocation status for reuse detection.

#### [NEW] `backend/app/models/refresh_token.py`
- SQLAlchemy model `RefreshToken` (id, user_id, token_jti, expires_at, revoked).

#### [NEW] `backend/alembic/versions/xxx_add_refresh_tokens.py`
- Alembic migration to create the `refresh_tokens` table.

### Backend Authentication

#### [MODIFY] `backend/app/core/security.py`
- Refactor `create_access_token` and `create_refresh_token` to only encode the principal (`sub` / `user_id`) and token type, plus a unique `jti` for refresh tokens.
- Update `get_current_user` to depend on the `db` session, lookup the user in the database, and verify their existence/status. This guarantees roles and patient access lists are always current.
- Remove fallback logic that reads `?token=` from query parameters.
- Change `security_scheme` to extract the token from the `access_token` cookie instead of the Authorization header, or support both but prioritize the cookie.

#### [MODIFY] `backend/app/api/v1/auth.py`
- Add in-memory rate limiting to the `login` endpoint.
- Refactor `login` to issue HttpOnly, Secure, SameSite=Lax cookies for `access_token` and `refresh_token` instead of returning them in the JSON body.
- Record the new refresh token in the `refresh_tokens` table.
- Implement `/refresh`: read the `refresh_token` cookie, validate its `jti` against the DB. If it's valid, revoke it (rotation), issue new tokens, and update cookies. If it's already revoked, revoke all tokens for that user (reuse detection).
- Add `/logout` to revoke the current refresh token and clear cookies.
- Add `/me` to return the current user's profile information (id, email, role, patient_access) for frontend initialization.

#### [MODIFY] `backend/app/api/upload.py` and `backend/app/routers/review.py`
- Ensure file streaming routes (e.g., `/documents/{id}/file`, `/review/pending/{id}/image`) rely on the standard `get_current_user` dependency (now cookie-based) rather than accepting `?token=`.

### Frontend

#### [MODIFY] `frontend/src/services/api.js`
- Set `apiClient.defaults.withCredentials = true` so Axios automatically sends HttpOnly cookies.
- Remove the request interceptor that reads `localStorage.getItem('token')`.
- Remove the response interceptor's manual `/auth/refresh` API calls, as `/refresh` will now be a cookie-based POST request that sets new cookies. We will update the interceptor to call `/auth/refresh` without passing manual tokens when a 401 occurs, and then retry.
- Update `getReviewImageUrl` and `getDocumentFileUrl` to remove `?token=` logic. The browser automatically sends cookies with `<img src="...">` if it's same-origin.

#### [MODIFY] `frontend/src/contexts/AuthContext.jsx`
- Replace `jwtDecode` logic with a call to the new `/api/v1/auth/me` endpoint to initialize user state.
- Update `login` and `logout` functions to handle the new cookie-based API responses.

## Verification Plan

### Automated Tests
- Run `pytest` and specifically add/update the required tests from Prompt 1:
  - Role/Patient assignment changes are reflected immediately.
  - Revoked/disabled users are rejected.
  - Unknown roles are rejected.
  - Refresh token rotation and reuse detection.
  - Query parameter bearer tokens are rejected.
  - Login rate limiting works.

### Manual Verification
- Login via UI and verify HttpOnly cookies are set.
- Change a user's role in the DB while logged in and verify their next request gets the new role (or fails if unauthorized).
- Verify document images load correctly using cookie authentication.
- Verify session expires and refreshes automatically using the interceptor.
