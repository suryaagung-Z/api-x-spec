# Error Envelope Contract (001-authentication)

**Source**: spec.md §Requirements FR-010, FR-011  
**Applies to**: All HTTP error responses from `api-x` authentication and authorization endpoints

---

## Envelope Structure

Every error response body MUST conform to this JSON structure:

```json
{
  "error": {
    "code": "<SCREAMING_SNAKE_CASE string>",
    "message": "<human-readable string>",
    "httpStatus": <integer matching the HTTP response status code>
  }
}
```

**Content-Type**: `application/json`

---

## Field Rules

| Field | Type | Rules |
|---|---|---|
| `error.code` | string | SCREAMING_SNAKE_CASE; machine-readable; stable across versions |
| `error.message` | string | Human-readable; may change over time; NOT for programmatic branching |
| `error.httpStatus` | integer | MUST equal the HTTP response status code |

---

## Standard Error Codes

| `code` | HTTP Status | Trigger (per spec clarifications) |
|---|---|---|
| `UNAUTHORIZED` | 401 | Missing `Authorization` header; malformed/tampered/expired JWT; wrong email or password on login |
| `FORBIDDEN` | 403 | Valid JWT but role is `user` and endpoint requires `admin` |
| `EMAIL_ALREADY_EXISTS` | 409 | Registration with email already in use |
| `VALIDATION_ERROR` | 422 | Pydantic input validation failure (missing field, wrong type, constraint violation) |
| `INTERNAL_ERROR` | 500 | Unhandled server exception (message must NOT leak stack traces or internal details) |

---

## HTTP Status Code Rules

Per spec clarification (FR-010):

| Condition | HTTP Status |
|---|---|
| Login with wrong credentials | **401** |
| Request to protected endpoint without token | **401** |
| Request with invalid or expired token | **401** |
| Valid `user`-role token on admin-only endpoint | **403** |
| Registration with duplicate email | **409** |

**`WWW-Authenticate` header**: MUST be included in all 401 responses per RFC 6750 §3.
Value: `Bearer`

---

## Examples

### 401 — Invalid/expired token

```http
HTTP/1.1 401 Unauthorized
Content-Type: application/json
WWW-Authenticate: Bearer

{
  "error": {
    "code": "UNAUTHORIZED",
    "message": "Could not validate credentials.",
    "httpStatus": 401
  }
}
```

### 401 — Wrong login credentials

```http
HTTP/1.1 401 Unauthorized
Content-Type: application/json
WWW-Authenticate: Bearer

{
  "error": {
    "code": "UNAUTHORIZED",
    "message": "Invalid email or password.",
    "httpStatus": 401
  }
}
```

> The message MUST NOT reveal whether email or password was the incorrect part
> (prevents username enumeration — spec Edge Cases).

### 403 — Insufficient role

```http
HTTP/1.1 403 Forbidden
Content-Type: application/json

{
  "error": {
    "code": "FORBIDDEN",
    "message": "Insufficient permissions.",
    "httpStatus": 403
  }
}
```

### 409 — Duplicate email

```http
HTTP/1.1 409 Conflict
Content-Type: application/json

{
  "error": {
    "code": "EMAIL_ALREADY_EXISTS",
    "message": "An account with this email already exists.",
    "httpStatus": 409
  }
}
```

### 422 — Validation failure

```http
HTTP/1.1 422 Unprocessable Entity
Content-Type: application/json

{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "password must be between 8 and 72 characters.",
    "httpStatus": 422
  }
}
```

---

## Security Notes

- Error messages MUST NOT expose internal details: stack traces, SQL errors,
  file paths, secret key hints, or which specific field caused an auth failure.
- The `UNAUTHORIZED` message for token errors MUST be generic (e.g., "Could not
  validate credentials.") — not "Token expired" or "Signature verification failed".
- The `UNAUTHORIZED` message for login failures MUST be combined (e.g., "Invalid
  email or password.") to prevent username enumeration.
