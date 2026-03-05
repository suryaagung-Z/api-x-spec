# Error Envelope Contract: 003-event-registration

> **Base contract**: Extends `specs/001-authentication/contracts/error-envelope.md`.
> **Event errors**: See `specs/002-event-management/contracts/error-envelope.md` for `EVENT_NOT_FOUND`.
> This document adds only the new error codes introduced by event registration.

---

## Envelope Structure (inherited)

```json
{
  "error": {
    "code":       "<SCREAMING_SNAKE_CASE string>",
    "message":    "<human-readable description>",
    "httpStatus": <integer HTTP status code>
  }
}
```

---

## Error Codes — New in 003-event-registration

| Code | HTTP Status | Trigger Condition | FR reference |
|------|------------|-------------------|--------------|
| `REGISTRATION_DEADLINE_PASSED` | 422 | `registration_deadline` has already passed — for both registration requests and cancellation requests | FR-003, FR-007, FR-011 |
| `QUOTA_FULL` | 422 | `event.current_participants >= event.quota` at the time of the atomic UPDATE check | FR-004, FR-011 |
| `DUPLICATE_REGISTRATION` | 409 | Calling user already has a record with `status = active` for this event | FR-005, FR-011 |
| `REGISTRATION_NOT_FOUND` | 404 | No `active` registration exists for the calling user + event combination when attempting cancellation | FR-011 |

---

## Error Codes — Inherited

| Code | HTTP Status | Source |
|------|------------|--------|
| `EVENT_NOT_FOUND` | 404 | 002-event-management — event does not exist, is `cancelled`, or `deleted` |
| `UNAUTHORIZED` | 401 | 001-authentication — missing or invalid JWT |
| `FORBIDDEN` | 403 | 001-authentication — valid JWT but insufficient role (not used in this feature — all endpoints are user-level) |
| `VALIDATION_ERROR` | 422 | Pydantic field validation failure |
| `INTERNAL_SERVER_ERROR` | 500 | Unhandled exception |

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

### 422 — Registration deadline passed

```json
{
  "error": {
    "code": "REGISTRATION_DEADLINE_PASSED",
    "message": "Registration deadline for event 42 has passed",
    "httpStatus": 422
  }
}
```

### 422 — Quota full

```json
{
  "error": {
    "code": "QUOTA_FULL",
    "message": "Event 42 is fully booked",
    "httpStatus": 422
  }
}
```

### 409 — Duplicate registration

```json
{
  "error": {
    "code": "DUPLICATE_REGISTRATION",
    "message": "User already has an active registration for event 42",
    "httpStatus": 409
  }
}
```

### 404 — Registration not found (for cancellation)

```json
{
  "error": {
    "code": "REGISTRATION_NOT_FOUND",
    "message": "No active registration found for this event",
    "httpStatus": 404
  }
}
```

---

## Notes

- **422 vs 409 distinction**: `QUOTA_FULL` and `REGISTRATION_DEADLINE_PASSED` are 422 because the *current state of the resource* makes the request unprocessable. `DUPLICATE_REGISTRATION` is 409 Conflict because it represents a conflict with an existing resource in the system.
- **`REGISTRATION_DEADLINE_PASSED` applies to both register and cancel**: The same `registration_deadline` cutoff blocks both registering and cancelling — per spec clarification. This means after the deadline, a user cannot cancel even if they have an active registration.
- **`REGISTRATION_NOT_FOUND` (404) for cancel**: A user trying to cancel a registration they never made, or one that is already `cancelled`, receives 404. This prevents leaking the existence of other users' cancelled registrations.
- **Re-registration**: After cancellation, the user may register again (new POST) as long as the deadline hasn't passed and quota is available. The previous `cancelled` record remains and does not appear as an obstacle — the partial unique index only covers `active` rows.
