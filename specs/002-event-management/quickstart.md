# Developer Quickstart: 002-event-management

> **Prerequisites**: Complete [001-authentication quickstart](../../001-authentication/quickstart.md) first.
> This feature extends the same application — no new environment setup is required.

---

## What was added

| Layer | New file(s) |
|-------|-------------|
| Router | `src/api/routers/events.py` |
| Schemas | `src/api/schemas/events.py`, `src/api/schemas/pagination.py` |
| Dependency | `src/api/dependencies/pagination.py` |
| Service | `src/application/event_service.py` |
| Domain | `EventStatus` enum in `src/domain/models.py`; `EventNotFoundError`, `QuotaBelowParticipantsError`, `EventDateInPastError` in `src/domain/exceptions.py` |
| ORM model | `Event` model with composite index in `src/infrastructure/db/models.py` |
| Repository | `src/infrastructure/repositories/event_repository.py` |
| Migration | `src/infrastructure/alembic/versions/xxxx_add_events_table.py` |
| Tests | `tests/contract/test_events_admin.py`, `tests/contract/test_events_public.py`, `tests/integration/test_event_repository.py`, `tests/unit/test_event_schemas.py`, `tests/unit/test_event_service.py` |

---

## 1. Run the migration

```bash
alembic upgrade head
```

This creates the `events` table with the `eventstatus` enum type and both indexes:
- `ix_events_date_title` — covers public listing ORDER BY
- `ix_events_registration_deadline` — for feature 003

---

## 2. Start the server

```bash
uvicorn src.main:app --reload
```

The server is now ready at `http://localhost:8000`.

---

## 3. Authenticate

Event admin endpoints require an ADMIN token. Public endpoints require no token.

**Get an admin token** (requires an admin user created via `001-authentication`):

```bash
ADMIN_TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "yourpassword"}' \
  | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

echo "Admin token: $ADMIN_TOKEN"
```

**Get a regular user token** (for testing 403 scenarios and public endpoints):

```bash
USER_TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "yourpassword"}' \
  | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
```

---

## 4. Admin: Create an event

```bash
curl -X POST http://localhost:8000/admin/events \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Tech Conference 2025",
    "description": "Annual technology conference covering AI, cloud, and open source.",
    "date": "2025-09-15T09:00:00+07:00",
    "registration_deadline": "2025-09-01T23:59:59+07:00",
    "quota": 200
  }'
```

**Expected 201 response**:
```json
{
  "id": 1,
  "title": "Tech Conference 2025",
  "description": "Annual technology conference covering AI, cloud, and open source.",
  "date": "2025-09-15T02:00:00Z",
  "registration_deadline": "2025-09-01T16:59:59Z",
  "quota": 200,
  "status": "active",
  "created_at": "2025-01-10T08:30:00Z",
  "registration_closed": false
}
```

> Note: `date` and `registration_deadline` are normalized to UTC (`+07:00` → `Z`). `registration_closed` is derived at serialization time.

---

## 5. Admin: Create event — validation error (deadline after date)

```bash
curl -X POST http://localhost:8000/admin/events \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Bad Event",
    "description": "desc",
    "date": "2025-09-01T09:00:00+00:00",
    "registration_deadline": "2025-09-15T09:00:00+00:00",
    "quota": 50
  }'
```

**Expected 422**:
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "registration_deadline must be on or before the event date",
    "httpStatus": 422
  }
}
```

---

## 6. Admin: Update an event

```bash
curl -X PUT http://localhost:8000/admin/events/1 \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"quota": 250}'
```

**Expected 200** — returns full updated `EventResponse`.

---

## 7. Admin: Delete an event (soft delete)

```bash
curl -X DELETE http://localhost:8000/admin/events/1 \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

**Expected 204** — no response body. Event status is now `deleted`.

Attempting to access the deleted event via the public endpoint returns 404:
```bash
curl http://localhost:8000/events/1
# → 404 EVENT_NOT_FOUND
```

---

## 8. Access control checks

**Regular user attempting admin create** → 403:
```bash
curl -X POST http://localhost:8000/admin/events \
  -H "Authorization: Bearer $USER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"X","description":"Y","date":"2025-12-01T10:00:00Z","registration_deadline":"2025-11-01T10:00:00Z","quota":10}'
# → 403 FORBIDDEN
```

**Unauthenticated admin create** → 401:
```bash
curl -X POST http://localhost:8000/admin/events \
  -H "Content-Type: application/json" \
  -d '{"title":"X","description":"Y","date":"2025-12-01T10:00:00Z","registration_deadline":"2025-11-01T10:00:00Z","quota":10}'
# → 401 UNAUTHORIZED
```

---

## 9. Public: Browse events (paginated)

No authentication required.

```bash
# First page, default page_size=20
curl "http://localhost:8000/events"

# Second page, 10 events per page
curl "http://localhost:8000/events?page=2&page_size=10"
```

**Expected 200 response shape**:
```json
{
  "items": [
    {
      "id": 2,
      "title": "Workshop: Python Async",
      "description": "Hands-on async workshop.",
      "date": "2025-10-05T06:00:00Z",
      "registration_deadline": "2025-09-28T16:59:59Z",
      "quota": 30,
      "status": "active",
      "created_at": "2025-01-15T10:00:00Z",
      "registration_closed": false
    }
  ],
  "total_items": 15,
  "page": 2,
  "page_size": 10,
  "total_pages": 2
}
```

**Invalid pagination** → 422:
```bash
curl "http://localhost:8000/events?page=0"
# → 422 VALIDATION_ERROR (page must be ≥ 1)

curl "http://localhost:8000/events?page_size=200"
# → 422 VALIDATION_ERROR (page_size must be ≤ 100)
```

---

## 10. Public: Event detail

```bash
curl http://localhost:8000/events/2
```

**404 for non-existent, cancelled, or deleted events**:
```bash
curl http://localhost:8000/events/999
# → 404 EVENT_NOT_FOUND
```

---

## 11. Run tests

```bash
# All event tests
pytest tests/contract/test_events_admin.py tests/contract/test_events_public.py \
       tests/integration/test_event_repository.py \
       tests/unit/test_event_schemas.py tests/unit/test_event_service.py -v

# Full suite
pytest -v
```

---

## 12. Architecture overview

```
POST /admin/events
│
├── Router (events.py)          — validate request body (EventCreate), inject Depends(get_current_user)
├── Dependency (auth.py)        — require_role(UserRole.ADMIN) from 001-authentication
├── Service (event_service.py)  — business logic: deadline ≤ date check, UTC normalization
├── Repository (event_repo.py)  — SQLAlchemy async session, persist Event ORM object
└── Response                    — EventResponse schema, registration_closed @computed_field

GET /events?page=1&page_size=20
│
├── Router (events.py)          — inject Depends(pagination_params) → (page, page_size)
├── Service (event_service.py)  — _public_events_query(), two-query pagination (count + data)
├── Repository (event_repo.py)  — SQLAlchemy async, uses ix_events_date_title composite index
└── Response                    — Page[EventResponse] with total_pages @computed_field
```

---

## 13. Key implementation notes

| Topic | Rule |
|-------|------|
| Datetime input | Always use `AwareDatetime` in `EventCreate`/`EventUpdate` — naive datetimes are rejected (422) |
| UTC normalization | Service layer calls `dt.astimezone(timezone.utc)` before persisting |
| Public filter | Always use `_public_events_query()` helper for user-facing endpoints — never bypass |
| Soft delete | `DELETE /admin/events/{id}` sets `status = "deleted"` — never physically removes the row |
| Pagination | `page > total_pages` returns empty `items` (not 404) |
| Concurrent queries | Do **not** use `asyncio.gather` on queries sharing a single `AsyncSession` |
