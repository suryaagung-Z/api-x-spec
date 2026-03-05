# Error Envelope Contract: 004-admin-reporting

> **Base contract**: Extends `specs/003-event-registration/contracts/error-envelope.md`,
> which in turn extends `specs/001-authentication/contracts/error-envelope.md`.
> The error envelope structure and all previously-defined error codes are inherited.
> This document confirms that **no new error codes** are introduced by admin reporting.

---

## Envelope Structure (inherited)

All error responses use the same envelope established in 001-authentication:

```json
{
  "error": {
    "code":       "<SCREAMING_SNAKE_CASE string>",
    "message":    "<human-readable description>",
    "httpStatus": <integer HTTP status code>
  }
}
```

`Content-Type: application/json` on all error responses.

---

## New Error Codes in 004-admin-reporting

*None.* This feature introduces no new business rules that produce novel error states. All error conditions are covered by the inherited codes below.

---

## Applicable Inherited Error Codes

| Code | HTTP Status | Trigger Condition |
|------|------------|-------------------|
| `UNAUTHORIZED` | 401 | Missing or invalid JWT token (`Authorization: Bearer ...` header absent or expired) |
| `FORBIDDEN` | 403 | Valid JWT but `role ≠ admin` — `require_role(UserRole.ADMIN)` rejects the request |
| `VALIDATION_ERROR` | 422 | Invalid pagination parameters (e.g., `page < 1`, `size > 100`) |
| `INTERNAL_SERVER_ERROR` | 500 | Unhandled exception caught by FastAPI exception handler |

---

## Example Responses

### 401 — Missing or expired token

```json
{
  "error": {
    "code": "UNAUTHORIZED",
    "message": "Not authenticated",
    "httpStatus": 401
  }
}
```

### 403 — Authenticated but not admin

```json
{
  "error": {
    "code": "FORBIDDEN",
    "message": "Insufficient permissions",
    "httpStatus": 403
  }
}
```

### 422 — Invalid pagination parameter

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "size must be between 1 and 100",
    "httpStatus": 422
  }
}
```
