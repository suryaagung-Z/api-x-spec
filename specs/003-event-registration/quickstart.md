# Quickstart: 003-event-registration

**Prerequisites**: 001-authentication and 002-event-management implemented and working.
This feature extends the same project — no new repository or service needed.

---

## 1. Apply the 003 Migration

```bash
# From repository root, with your DATABASE_URL env var set:
alembic upgrade head
```

The 003 migration:
1. Adds `current_participants INTEGER NOT NULL DEFAULT 0` column to `events`
2. Creates `event_registrations` table
3. Creates `registrationstatus` enum type
4. Creates partial unique index `uq_active_registration ON event_registrations (user_id, event_id) WHERE status = 'active'`
5. Creates covering indexes `ix_event_registrations_user_registered`, `ix_event_registrations_event_active`

---

## 2. Environment

No new environment variables. Uses the same `.env` / `DATABASE_URL` as 001 and 002.

```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/api_x
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

---

## 3. Start the Server

```bash
uvicorn src.main:app --reload
```

---

## 4. Quick Smoke Tests (curl)

### 4a. Get tokens

```bash
# Admin token (for creating events)
ADMIN_TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"adminpass"}' | jq -r '.access_token')

# User token (for registration)
USER_TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"userpass"}' | jq -r '.access_token')
```

### 4b. Create a test event (admin)

```bash
EVENT_ID=$(curl -s -X POST http://localhost:8000/admin/events \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Test Event",
    "description": "A test event for registration",
    "date": "2026-12-01T09:00:00+00:00",
    "registration_deadline": "2026-11-28T23:59:59+00:00",
    "quota": 3
  }' | jq -r '.id')

echo "Created event ID: $EVENT_ID"
```

### 4c. Register for the event (user)

```bash
curl -s -X POST http://localhost:8000/registrations/$EVENT_ID \
  -H "Authorization: Bearer $USER_TOKEN" | jq
# Expected: 201 {"id": 1, "event_id": <EVENT_ID>, "status": "active", "registered_at": "..."}
```

### 4d. Try to register again (duplicate — should 409)

```bash
curl -s -o /dev/null -w "%{http_code}" \
  -X POST http://localhost:8000/registrations/$EVENT_ID \
  -H "Authorization: Bearer $USER_TOKEN"
# Expected: 409
```

### 4e. View my registrations

```bash
curl -s http://localhost:8000/registrations/me \
  -H "Authorization: Bearer $USER_TOKEN" | jq
# Expected: array with one item, status: "active", nested event info
```

### 4f. Cancel the registration

```bash
curl -s -o /dev/null -w "%{http_code}" \
  -X DELETE http://localhost:8000/registrations/$EVENT_ID \
  -H "Authorization: Bearer $USER_TOKEN"
# Expected: 204
```

### 4g. View registrations again (should show cancelled)

```bash
curl -s http://localhost:8000/registrations/me \
  -H "Authorization: Bearer $USER_TOKEN" | jq
# Expected: one item with status: "cancelled", cancelled_at: populated
```

### 4h. Re-register (should succeed — creates new ACTIVE record)

```bash
curl -s -X POST http://localhost:8000/registrations/$EVENT_ID \
  -H "Authorization: Bearer $USER_TOKEN" | jq
# Expected: 201 with a new registration id (different from the first)
```

---

## 5. Quota Enforcement Demo

```bash
# Create event with quota=1
QUOTA_EVENT=$(curl -s -X POST http://localhost:8000/admin/events \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Quota Test",
    "description": "Only 1 slot",
    "date": "2026-12-10T09:00:00+00:00",
    "registration_deadline": "2026-12-07T23:59:59+00:00",
    "quota": 1
  }' | jq -r '.id')

# User 1 registers — succeeds
curl -s -X POST http://localhost:8000/registrations/$QUOTA_EVENT \
  -H "Authorization: Bearer $USER_TOKEN" | jq '.status'
# Expected: "active"

# User 2 registers different token — gets 422 quota full
SECOND_USER_TOKEN="..."  # token for a different user
curl -s -o /dev/null -w "%{http_code}" \
  -X POST http://localhost:8000/registrations/$QUOTA_EVENT \
  -H "Authorization: Bearer $SECOND_USER_TOKEN"
# Expected: 422
```

---

## 6. Run Tests

```bash
# All 003 tests
pytest tests/ -k "registration" -v

# Specific test files
pytest tests/unit/test_registration_service.py -v
pytest tests/integration/test_registration_repository.py -v
pytest tests/contract/test_registrations.py -v

# Concurrent quota test (SC-004)
pytest tests/integration/test_registration_repository.py::test_concurrent_registration_respects_quota -v

# Full suite (no regressions)
pytest tests/ -v
```

---

## 7. Architecture Overview

```
POST /registrations/{event_id}
  └─ registrations.py (router)
       └─ registration_service.register(session, user_id, event_id)
            ├─ _public_events_query() → 404 if not found         [002 helper]
            ├─ deadline check         → 422 if passed
            ├─ active duplicate check → 409 if found
            ├─ atomic UPDATE events.current_participants + 1
            │    WHERE current_participants < quota               ← quota lock
            │    RETURNING id → 422 if 0 rows
            ├─ INSERT event_registrations (status=active)
            └─ catch IntegrityError → DuplicateActiveRegistrationError → 409

DELETE /registrations/{event_id}
  └─ registrations.py (router)
       └─ registration_service.cancel(session, user_id, event_id)
            ├─ SELECT active registration → 404 if not found
            ├─ deadline check             → 422 if passed
            ├─ UPDATE registration status=cancelled, cancelled_at=now()
            └─ UPDATE events.current_participants - 1

GET /registrations/me
  └─ registrations.py (router)
       └─ registration_service.get_my_registrations(session, user_id)
            └─ SELECT * FROM event_registrations
                 WHERE user_id = ?
                 OPTIONS selectinload(event)
                 ORDER BY registered_at DESC
```

---

## 8. Key Implementation Notes

| Topic | Note |
|-------|------|
| Quota safety | `UPDATE events SET current_participants = current_participants + 1 WHERE current_participants < quota RETURNING id` — if 0 rows, quota is full. Atomic; no race condition possible. |
| Rollback on IntegrityError | The `current_participants` increment is in the same transaction as the INSERT. If the INSERT raises `IntegrityError`, the entire transaction rolls back — counter is automatically restored. |
| `current_participants` vs COUNT | Do not use `SELECT COUNT(*)` for quota checks in production — broken under READ COMMITTED concurrency. Use the denormalized counter exclusively. |
| `lazy="raise"` on relationship | `EventRegistration.event` has `lazy="raise"`. Always use `selectinload(EventRegistration.event)` when loading registrations for the `/me` endpoint. Forgetting it becomes a hard error at test time, not a silent N+1. |
| Re-registration | `cancel()` + `register()` creates TWO records with the same `event_id`: one `cancelled`, one `active`. This is intentional — spec says "make new active record". The partial unique index on `(user_id, event_id) WHERE status='active'` handles this correctly. |
| Cancellable after `registration_deadline`? | **No** — the same deadline cutoff blocks both registration and cancellation. After the deadline, the active registration exists but cannot be cancelled via the API (spec clarification). |
