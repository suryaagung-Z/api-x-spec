# Research: 003-event-registration

All NEEDS CLARIFICATION items resolved. Decisions finalized for Phase 1 design.

---

## 1. Quota Enforcement Under Concurrency

**Decision**: Denormalized `current_participants` counter on `Event` table, updated with an **atomic conditional UPDATE** as part of the registration transaction.

**Problem**: Two concurrent requests both read `current_participants = quota - 1`, both pass the check, both INSERT → overbooking. A plain `SELECT COUNT(*) + INSERT` sequence cannot be made safe under PostgreSQL's default `READ COMMITTED` isolation without a lock.

**Chosen pattern — atomic test-and-set UPDATE**:
```python
# Step 1: Atomically increment — returns 0 rows if quota already full
result = await session.execute(
    update(Event)
    .where(Event.id == event_id)
    .where(Event.status == EventStatus.ACTIVE)
    .where(Event.current_participants < Event.quota)
    .values(current_participants=Event.current_participants + 1)
    .returning(Event.id)
)
if result.first() is None:
    raise QuotaFullError(event_id)

# Step 2: INSERT registration record (in same transaction)
# Step 3: If IntegrityError on unique index → rollback increments automatically
```

PostgreSQL holds a row lock on `events.id` from the `UPDATE` start until commit. Any concurrent `UPDATE` on the same row **blocks and waits**, then re-evaluates the `WHERE current_participants < quota` predicate against the freshly committed value — structurally preventing overbooking.

**On cancellation** (decrement):
```python
await session.execute(
    update(Event)
    .where(Event.id == event_id)
    .values(current_participants=Event.current_participants - 1)
)
```

**Why not SELECT FOR UPDATE + COUNT subquery**:
- SELECT FOR UPDATE is also correct but requires two queries (lock + count)
- The atomic UPDATE is a single SQL statement, zero extra round-trips
- Rollback automatically restores the counter if a later step in the same transaction fails

**Why not COUNT subquery without lock**:
- Fatally broken under `READ COMMITTED` (PostgreSQL default): two transactions both read the same count → both pass the check → overbooking

**Schema addition for 003** (migration adds column to existing `events` table):
```sql
ALTER TABLE events ADD COLUMN current_participants INTEGER NOT NULL DEFAULT 0;
ALTER TABLE events ADD CONSTRAINT chk_participants_not_negative CHECK (current_participants >= 0);
ALTER TABLE events ADD CONSTRAINT chk_participants_not_over_quota CHECK (current_participants <= quota);
```

**Alternatives considered**:

| Approach | Verdict |
|----------|---------|
| SELECT FOR UPDATE + COUNT | Correct but 2 queries; rejected for verbosity |
| COUNT subquery only (no lock) | Fatally broken under READ COMMITTED; rejected |
| Optimistic locking (`version_id_col`, `StaleDataError`) | Requires retry loop; adds complexity; rejected |
| SERIALIZABLE isolation | Works but high overhead (SSI); rejected for performance |

---

## 2. Duplicate Registration Prevention (Partial Unique Index)

**Decision**: PostgreSQL partial unique index on `(user_id, event_id) WHERE status = 'active'` + app-level pre-check for friendly error message.

**Why a full unique constraint on `(user_id, event_id)` fails**:
- A `cancelled` row would permanently block re-registration
- Spec FR-005 explicitly mandates re-registration after cancellation

**Partial unique index**:
```python
# In EventRegistration.__table_args__:
Index(
    "uq_active_registration",
    "user_id",
    "event_id",
    unique=True,
    postgresql_where="status = 'active'",
)
```

```python
# Alembic migration (sa.text() required in op.create_index):
op.create_index(
    "uq_active_registration",
    "event_registrations",
    ["user_id", "event_id"],
    unique=True,
    postgresql_where=sa.text("status = 'active'"),
)
```

**Exception handling chain**:
```python
# PostgreSQL raises SQLSTATE 23505 (UniqueViolationError)
# asyncpg surfaces as asyncpg.exceptions.UniqueViolationError
# SQLAlchemy wraps in sqlalchemy.exc.IntegrityError

except IntegrityError as exc:
    if (
        isinstance(exc.__cause__, asyncpg.exceptions.UniqueViolationError)
        and "uq_active_registration" in str(exc.__cause__)
    ):
        raise DuplicateActiveRegistrationError(user_id, event_id)
    raise  # re-raise unrecognised IntegrityErrors
```

Narrowing by index name prevents masking future constraints on the same table.

**Combined flow**:
```
Request
  └─ app-level SELECT active row?  ← fast path (common sequential case)
       ├── found  → raise DuplicateActiveRegistrationError (409)
       └── not found → UPDATE quota (atomic) → INSERT registration
              ├── success → 201
              └── IntegrityError (rare concurrent race) → catch → 409
```

The DB index is the **hard guarantee**; the app pre-check provides the **friendly error path** for sequential requests.

**Alternatives considered**:
- App-level check only — TOCTOU race condition under concurrency; rejected
- Full unique on `(user_id, event_id)` — permanently blocks re-registration; rejected
- Trigger-based enforcement — adds DDL complexity; rejected

---

## 3. RegistrationStatus Enum & Re-Registration

**Decision**: `RegistrationStatus` enum with values `ACTIVE` | `CANCELLED`. On re-registration after cancellation, always **INSERT a new `ACTIVE` record** (previous `CANCELLED` record stays as history).

**Rationale**: Spec language is explicit — User Story 3 Acceptance Scenario 3: *"sistem menerima pendaftaran dan membuat record **aktif baru**"* (creates a **new** active record). FR-005 confirms: `cancelled` record does not block a new registration.

```python
class RegistrationStatus(str, enum.Enum):
    ACTIVE    = "active"
    CANCELLED = "cancelled"
```

**Registration flow** (`register` service method):
1. Check event exists and is `ACTIVE` + `date >= now()` (use `_public_events_query()` from 002)
2. Check `registration_deadline` has not passed
3. App-level check: any existing `ACTIVE` registration for this `(user_id, event_id)` → 409
4. Atomic UPDATE `events.current_participants + 1 WHERE current_participants < quota` → 0 rows → 422
5. INSERT new `EventRegistration(status=ACTIVE)` in same transaction
6. Catch `IntegrityError` on `uq_active_registration` → rollback → 409

**Cancellation flow** (`cancel` service method):
1. Find `EventRegistration` where `user_id = current_user.id AND event_id = ? AND status = ACTIVE`
   — returns `None` → `NoActiveRegistrationError` → 404
2. Check `registration_deadline` has not passed → 422
3. UPDATE registration `status = CANCELLED`, set `cancelled_at = now()`
4. Decrement `events.current_participants - 1`
5. Both changes in same transaction

**Re-registration** uses **identical path** to first-time registration — no special code path needed. The partial unique index excludes `cancelled` rows, so the INSERT succeeds normally.

**Alternatives considered**:
- UPDATE existing `cancelled` record back to `active` — spec says "new record"; harder to audit; rejected

---

## 4. User's Own Registrations (`GET /registrations/me`)

**Decision**: `GET /registrations/me` (no path param with user ID), returns `list[RegistrationWithEventResponse]` with nested `EventSummary`, no pagination, ordered `registered_at DESC`. Relationship loaded with `selectinload`.

**Auth isolation**:
```python
@router.get("/me", response_model=list[RegistrationWithEventResponse])
async def get_my_registrations(
    current_user: Annotated[User, Depends(get_current_user)],
    session:      Annotated[AsyncSession, Depends(get_db)],
) -> list[RegistrationWithEventResponse]:
    stmt = (
        select(EventRegistration)
        .where(EventRegistration.user_id == current_user.id)
        .options(selectinload(EventRegistration.event))
        .order_by(EventRegistration.registered_at.desc())
    )
    result = await session.scalars(stmt)
    return list(result.all())
```

`GET /users/{user_id}/registrations` is rejected — requires an ownership check or admin bypass; adds unnecessary complexity. `/me` is structurally self-enforcing (user ID always comes from the verified JWT).

**Response schema**:
```python
class EventSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:                    int
    title:                 str
    date:                  datetime
    registration_deadline: datetime
    status:                EventStatus  # let user see if event is cancelled

class RegistrationWithEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:           int
    event_id:     int
    status:       RegistrationStatus
    registered_at:  datetime
    cancelled_at:   datetime | None
    event:          EventSummary
```

**No pagination**: A user's own registration history is expected to be small (single/double-digit count). Spec says "see all their registrations" implying completeness. Pagination can be added non-breakingly later with optional `page`/`page_size` params.

**`selectinload` over `joinedload`**: SQLAlchemy async docs list `selectinload` first; `joinedload` is discouraged with LIMIT/OFFSET and can cause row inflation on 1-to-many. `selectinload` issues 2 queries (main + `WHERE id IN (...)`) — safe, predictable.

**ORM relationship** (declared on `EventRegistration`):
```python
event: Mapped["Event"] = relationship("Event", lazy="raise")
# lazy="raise" converts accidental unloaded access to a hard error at test time
```

**Indexes supporting this query**:
```python
Index("ix_event_registrations_user_registered", "user_id", "registered_at")
# covers WHERE user_id = ? ORDER BY registered_at DESC
```

**Alternatives considered**:
- `GET /users/{user_id}/registrations` — ownership check required; rejected
- Pagination — not needed at current scale; deferred
- `joinedload` — discouraged in async + LIMIT context; rejected

---

## 5. Runtime / Framework

**Decision**: Same stack as 001-authentication and 002-event-management — no new libraries introduced.

| Component | Choice |
|-----------|--------|
| Language | Python 3.11+ |
| HTTP framework | FastAPI |
| ORM | SQLAlchemy 2.x async |
| Migration | Alembic 1.13+ |
| Validation | Pydantic v2 |
| DB (prod) | PostgreSQL 15+ via asyncpg |
| DB (dev/test) | SQLite via aiosqlite |
| Testing | pytest + pytest-asyncio + httpx |
| Code quality | black + ruff + mypy |
| Config | pydantic-settings BaseSettings |

**Dependencies on previous features**:
- **001-authentication**: `get_current_user` dependency, `require_role(UserRole.ADMIN)` (not used in this feature — all endpoints are user-level), `User` ORM model
- **002-event-management**: `Event` ORM model, `EventStatus` enum, `_public_events_query()` helper, `EventNotFoundError`

---

## 6. Testing Strategy

| Test type | Coverage |
|-----------|---------|
| Contract (httpx AsyncClient) | All 3 endpoints, all status codes per spec FR-011 |
| Integration (real AsyncSession) | Repository methods, `current_participants` counter, soft-delete cancellation, re-registration |
| Unit (no DB/network) | `register` service guards (deadline check, quota check, duplicate check logic), `cancel` service guards (no active reg, deadline check), status transitions |

**Critical concurrent test** (SC-004): Spin up N concurrent tasks (e.g., `asyncio.gather`) all registering to an event with quota=1 — assert exactly 1 succeeds and N-1 get 422, and `current_participants == 1` after all complete.

---

## 7. Summary of All Decisions

| Topic | Decision |
|-------|----------|
| Quota enforcement | Denormalized `current_participants` on `Event`, atomic `UPDATE … WHERE current_participants < quota RETURNING id` in same transaction as INSERT |
| Duplicate prevention | Partial unique index `(user_id, event_id) WHERE status='active'` + app-level pre-check |
| Re-registration | Always INSERT new `ACTIVE` record (spec: "record aktif baru"); partial index excludes `cancelled` rows |
| User own registrations | `GET /registrations/me`, `selectinload`, `list[RegistrationWithEventResponse]`, no pagination, `registered_at DESC` |
| Status enum | `RegistrationStatus.ACTIVE / CANCELLED` (soft delete — never hard delete) |
| Participant decrement | Atomic `UPDATE events SET current_participants - 1` in same transaction as status flip |
| Runtime | Python 3.11 · FastAPI · SQLAlchemy 2.x async · Alembic 1.13 · Pydantic v2 (identical to 001 + 002) |
