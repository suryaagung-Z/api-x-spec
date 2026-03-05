# Error Envelope Contract: 002-event-management

> **Base contract**: Extends `specs/001-authentication/contracts/error-envelope.md`.
> The error envelope structure and all auth error codes are defined there.
> This document adds only the new error codes introduced by event management.

---

## Envelope Structure (inherited)

All error responses use the same envelope from 001-authentication:

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

## Error Codes — New in 002-event-management

| Code | HTTP Status | Trigger Condition |
|------|------------|-------------------|
| `EVENT_NOT_FOUND` | 404 | Event ID does not exist, or event status is `cancelled`/`deleted` (user-facing: treated as non-existent) |
| `QUOTA_BELOW_PARTICIPANTS` | 409 | Update would set `quota` to a value lower than the current participant count |
| `INVALID_DATE_RANGE` | 422 | `registration_deadline` > `event.date` (Pydantic `model_validator` or explicit service check) |

---

## Error Codes — Inherited from 001-authentication

| Code | HTTP Status | Trigger Condition |
|------|------------|-------------------|
| `UNAUTHORIZED` | 401 | Missing or invalid JWT token (`Authorization: Bearer ...` header absent or expired) |
| `FORBIDDEN` | 403 | Valid JWT but user role does not satisfy `require_role(UserRole.ADMIN)` |
| `VALIDATION_ERROR` | 422 | Pydantic request body / query parameter validation failure (field-level, not business-rule) |
| `INTERNAL_SERVER_ERROR` | 500 | Unhandled exception caught by FastAPI exception handler |

---

## Example Responses

### 404 — Event not found

```json
{
  "error": {
    "code": "EVENT_NOT_FOUND",
    "message": "Event 42 not found",
    "httpStatus": 404
  }
}
```

### 409 — Quota below participants

```json
{
  "error": {
    "code": "QUOTA_BELOW_PARTICIPANTS",
    "message": "Cannot set quota to 5; event 42 already has 10 participants",
    "httpStatus": 409
  }
}
```

### 422 — Invalid date range (deadline after event date)

```json
{
  "error": {
    "code": "INVALID_DATE_RANGE",
    "message": "registration_deadline must be on or before the event date",
    "httpStatus": 422
  }
}
```

### 422 — Pydantic validation error

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "quota: Input should be greater than or equal to 1",
    "httpStatus": 422
  }
}
```

### 401 — Unauthorized (inherited)

```json
{
  "error": {
    "code": "UNAUTHORIZED",
    "message": "Authentication required",
    "httpStatus": 401
  }
}
```

### 403 — Forbidden (inherited)

```json
{
  "error": {
    "code": "FORBIDDEN",
    "message": "Admin role required",
    "httpStatus": 403
  }
}
```

---

## Notes

- **404 is ambiguous by design**: A user requesting a deleted or cancelled event receives `EVENT_NOT_FOUND` (404), identical to a non-existent event. This prevents leaking soft-delete state to unauthenticated users.
- **409 vs 422**: `QUOTA_BELOW_PARTICIPANTS` is a business constraint (409 Conflict) because it crosses a data boundary (existing registrations). Field-level Pydantic errors are 422.
- **Admin endpoints**: Even admin users receive `EVENT_NOT_FOUND` (404) for a truly non-existent event ID. Admin endpoints show all statuses (active/cancelled/deleted) for existing events.
