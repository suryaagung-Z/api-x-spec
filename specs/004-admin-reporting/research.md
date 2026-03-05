# Research: 004-admin-reporting

**Phase**: 0 — Research  
**Date**: 2026-03-05  
**Source spec**: [spec.md](spec.md)

---

## Research Questions & Decisions

### R-001 — Aggregation strategy to avoid N+1 (NFR-001, NFR-002)

**Question**: How should `total_registered` and `remaining_quota` be computed for all active events without N+1 queries?

**Decision**: Single SQL query using `LEFT JOIN … GROUP BY` with a conditional aggregate:

```sql
SELECT
    e.id,
    e.title,
    e.date,
    e.quota,
    COUNT(er.id) FILTER (WHERE er.status = 'active') AS total_registered,
    e.quota - COUNT(er.id) FILTER (WHERE er.status = 'active') AS remaining_quota
FROM events e
LEFT JOIN event_registrations er ON er.event_id = e.id
WHERE e.status = 'active'
  AND e.date > NOW()
GROUP BY e.id
ORDER BY e.date ASC, e.id ASC
LIMIT :limit OFFSET :offset;
```

`COUNT(...) FILTER (WHERE ...)` is standard ANSI SQL (PostgreSQL 9.4+) and efficient — avoids subqueries while correctly excluding `cancelled` registrations from the count.

**Rationale**: One round-trip to the DB regardless of the number of active events. SQLAlchemy 2.x exposes this as `func.count(col).filter(condition)` in ORM queries. The approach is idiomatic and composable.

**Alternatives considered**:
- *Subquery per event* — classic N+1 problem, rejected per NFR-001.
- *Denormalized `current_participants` counter* (from 003) — available on `events` table. Could substitute `total_registered`, but the spec explicitly defines `total_registered` as "active registrations at query time". Using the live COUNT aggregate is preferred here because: (a) admin reporting demands accuracy, (b) `current_participants` may drift under edge-case bugs, (c) this is a read-only report and the aggregate is cheap with proper indexing.
- *Materialized view* — over-engineering for this scale; rejected per Constitution Principle V (simplicity).

---

### R-002 — "Active event" SQL predicate consistency (FR-001, FR-002, spec clarification)

**Question**: What is the exact SQL predicate for "active event" classification?

**Decision**:

```sql
WHERE e.status = 'active'
  AND e.date > NOW()
```

`NOW()` is evaluated once per query (PostgreSQL transaction timestamp), ensuring consistency within a single request.

**Rationale**: Matches the clarification: `status = aktif AND date belum lewat pada saat query dijalankan`. Also consistent with the 002-event-management public events `_public_events_query()` helper which uses `status = ACTIVE AND date > now()`. Parity avoids confusion.

**Alternatives considered**:
- Using `date >= NOW()` — rejected; events with `date == NOW()` at millisecond precision are effectively happening now and their registration window is closed. The `>` predicate matches 002's convention.
- Including `registration_deadline` — spec clarification does not require it for admin reporting filter; only `status` and `date` determine active event membership for this feature.

---

### R-003 — Paginating the per-event stats endpoint (FR-007)

**Question**: Should pagination be cursor-based or offset-based, and what are the page size limits?

**Decision**: Offset-based pagination, `page` + `size` parameters, matching the exact pattern established by 002-event-management and shared via `src/api/schemas/pagination.py` (`PaginationParams`, `Page[T]`). Default page size 20, max 100.

**Rationale**: Consistency with existing API surface. Cursor-based pagination would benefit very large datasets with frequent writes, but the events table is admin-managed and unlikely to exceed tens of thousands of rows. Offset pagination is simpler and already used in the project.

**Alternatives considered**:
- Cursor pagination — better for near-real-time feeds; rejected here as over-engineering for a bounded admin report with relatively stable data.

---

### R-004 — Admin role enforcement (FR-004, spec §001-authentication dependency)

**Question**: How is admin-only access enforced at the API layer?

**Decision**: Reuse `require_role(UserRole.ADMIN)` dependency from 001-authentication — the same FastAPI `Depends()` pattern already used in 002 and 003 admin routes. No new mechanism needed.

```python
# src/api/routers/reports.py
@router.get("/admin/reports/events/stats")
async def get_event_stats(
    pagination: PaginationParams = Depends(pagination_params),
    _current_user: User          = Depends(require_role(UserRole.ADMIN)),
    ...
):
```

**Rationale**: Single implementation reuse, zero new auth code, test coverage inherited from existing admin-gate contract tests.

---

### R-005 — `remaining_quota` display when negative (FR-008)

**Question**: Should `remaining_quota` be clamped to 0 or returned as-is when negative?

**Decision**: Return raw value `quota - total_registered` — including negative values. No clamping.

**Rationale**: Spec FR-008 is explicit: *"sistem TIDAK BOLEH men-clamp nilai ini ke 0 sehingga admin dapat mendeteksi anomali data."* Negative `remaining_quota` is a data-integrity signal that the admin should see. The response schema documents this as `type: integer` with no minimum constraint.

---

### R-006 — Performance index requirements (SC-002, NFR-001, NFR-002)

**Question**: What indexes are needed to satisfy p95 ≤ 2 s with 10,000 active events?

**Decision**: No new migrations required — the required indexes were already created by 003-event-registration:

| Index | Table | Columns | Benefit |
|-------|-------|---------|---------|
| `ix_event_registrations_event_active` | `event_registrations` | `(event_id) WHERE status = 'active'` | Partial index for the conditional COUNT |
| `ix_events_status_date` | `events` | `(status, date)` | Required for the WHERE filter on active events |

`ix_event_registrations_event_active` (partial index from 003) covers `COUNT(er.id) FILTER (WHERE er.status = 'active')` per event efficiently. `ix_events_status_date` (002) covers the `WHERE status = 'active' AND date > NOW()` predicate.

The `GROUP BY e.id` with `ORDER BY e.date ASC` uses the PK index for grouping and a composite index for ordering. With 10,000 active events and paginated output (max 100 rows), this is well within the p95 ≤ 2 s target.

---

### R-007 — No new ORM models or migrations

**Question**: Does this feature require new database tables?

**Decision**: No. `004-admin-reporting` is read-only and queries the existing `events` and `event_registrations` tables. No Alembic migration is generated.

**Rationale**: The spec introduces no new entities, only derived read views over existing ones. A new `reporting_repository.py` performs the aggregation query via SQLAlchemy `select()` with `.join()` and `func.count().filter()`.

---

### R-008 — Summary endpoint: count total active events

**Question**: How is `total_active_events` computed?

**Decision**: `SELECT COUNT(*) FROM events WHERE status = 'active' AND date > NOW()` — a separate lightweight query executed by `ReportingRepository.get_total_active_events()`.

**Rationale**: This is a trivially cheap scalar query and matches the spec requirement for a dedicated summary endpoint (FR-007, FR-003). It is kept separate from the paginated stats query.

---

## Summary Table

| ID | Question | Decision | Rejected Alternatives |
|----|----------|----------|----------------------|
| R-001 | Aggregation to avoid N+1 | Single LEFT JOIN + `COUNT FILTER` | Subquery per event; denormalized counter; materialized view |
| R-002 | Active event predicate | `status='active' AND date > NOW()` | `date >= NOW()`; include `registration_deadline` |
| R-003 | Pagination style | Offset (page/size), existing `Page[T]` | Cursor pagination |
| R-004 | Admin auth enforcement | `require_role(UserRole.ADMIN)` Depends() | New auth mechanism |
| R-005 | Negative remaining_quota | Return as-is, no clamp | Clamp to 0 |
| R-006 | Index requirements | Existing 002/003 indexes sufficient | New composite indexes |
| R-007 | New DB tables | None — read-only feature | New reporting table/view |
| R-008 | Summary count query | Separate `COUNT(*)` query | Reuse paginated stats count |
