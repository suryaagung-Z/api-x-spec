# Quickstart: 004-admin-reporting

**Prerequisites**: 001-authentication, 002-event-management, and 003-event-registration must be implemented and working. This feature extends the same project — no new repository, service, or migration is needed.

---

## 1. No Migration Required

`004-admin-reporting` is read-only. It queries existing `events` and `event_registrations` tables using the indexes already created by 002 and 003. No `alembic upgrade` step is required for this feature alone.

Verify your database is already at the latest 003 migration head:

```bash
alembic current
# Expected: <003_migration_id> (head)
```

---

## 2. Environment

No new environment variables. Uses the same `.env` as 001, 002, and 003.

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

The two new routes below are available immediately after the router is registered in `src/main.py`.

---

## 4. Quick Smoke Tests (curl)

### 4a. Obtain an admin token

```bash
ADMIN_TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"adminpass"}' | jq -r '.access_token')
```

### 4b. Per-event statistics (paginated)

```bash
curl -s http://localhost:8000/admin/reports/events/stats?page=1&size=20 \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq .
```

**Expected response shape** (200):
```json
{
  "items": [
    {
      "id": 42,
      "title": "Tech Conference 2026",
      "date": "2026-09-15T09:00:00Z",
      "quota": 100,
      "total_registered": 87,
      "remaining_quota": 13
    }
  ],
  "total": 1,
  "page": 1,
  "size": 20,
  "pages": 1
}
```

### 4c. Summary — total active events

```bash
curl -s http://localhost:8000/admin/reports/events/summary \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq .
```

**Expected response** (200):
```json
{
  "total_active_events": 1
}
```

### 4d. Verify non-admin is rejected

```bash
USER_TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"userpass"}' | jq -r '.access_token')

curl -s http://localhost:8000/admin/reports/events/stats \
  -H "Authorization: Bearer $USER_TOKEN" | jq .
```

**Expected response** (403):
```json
{
  "error": {
    "code": "FORBIDDEN",
    "message": "Insufficient permissions",
    "httpStatus": 403
  }
}
```

### 4e. Verify unauthenticated access is rejected

```bash
curl -s http://localhost:8000/admin/reports/events/stats | jq .
```

**Expected response** (401):
```json
{
  "error": {
    "code": "UNAUTHORIZED",
    "message": "Not authenticated",
    "httpStatus": 401
  }
}
```

---

## 5. Edge Cases to Verify Manually

### 5a. Event with no registrations

Create an active future event with no registrations. Expect:
```json
{ "total_registered": 0, "remaining_quota": <quota> }
```

### 5b. Negative remaining_quota (data anomaly detection)

If an event has `quota=5` but `total_registered=7` (possible if quota was lowered after registrations), the API must return `remaining_quota=-2` without clamping or error.

### 5c. No active events

When no events are active, `GET /admin/reports/events/stats` must return an empty items list and `total=0`; `GET /admin/reports/events/summary` must return `total_active_events=0`.

---

## 6. Running the Test Suite

```bash
# Unit tests for the reporting service
pytest tests/unit/test_reporting_service.py -v

# Integration tests for the reporting repository
pytest tests/integration/test_reporting_repository.py -v

# Contract tests for both endpoints
pytest tests/contract/test_reports.py -v

# Full suite
pytest tests/ -v
```
