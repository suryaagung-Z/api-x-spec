# Tasks: Dokumentasi API dengan Swagger (005-swagger-api-docs)

**Input**: Design documents from `specs/005-swagger-api-docs/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, contracts/openapi.yaml ✓, quickstart.md ✓

**Approach**: Code-first — tambah metadata ke kode yang sudah ada. Tidak ada endpoint baru, tidak ada migrasi, tidak ada dependensi baru.

**Actual Endpoint Paths** (dari research.md R-1):
```
Auth (3):       POST /auth/register · POST /auth/login · GET /auth/me
Admin (1):      GET /admin/users
Admin-Events:   POST /admin/events · GET /admin/events/{id} · PUT /admin/events/{id} · DELETE /admin/events/{id}
Events (2):     GET /events · GET /events/{event_id}
Registrations:  POST /registrations/{event_id} · DELETE /registrations/{event_id} · GET /registrations/me
Reports (2):    GET /admin/reports/events/stats · GET /admin/reports/events/summary
```

---

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Dapat dijalankan paralel (file berbeda, tanpa dependensi pada task yang belum selesai)
- **[Story]**: User story terkait task — [US1], [US2], [US3], [US4], [US5]
- Sertakan path file eksak di setiap deskripsi

---

## Phase 1: Setup

**Tujuan**: Buat file konstanta baru yang akan digunakan oleh `src/main.py`. Tidak ada breaking change.

- [X] T001 Buat `src/api/docs_metadata.py` berisi API_TITLE, API_VERSION, API_DESCRIPTION (multi-line dengan panduan register→login→Authorize), dan OPENAPI_TAGS (list 6 tag dengan nama dan deskripsi Bahasa Indonesia). **Nama tag canonical**: `auth`, `admin`, `admin-events`, `events`, `registrations`, `admin-reporting` (semua lowercase hyphenated, konsisten). Setelah file dibuat, perbarui juga `src/api/routers/reports.py` baris `tags=["Admin Reporting"]` menjadi `tags=["admin-reporting"]`.

**Checkpoint**: `src/api/docs_metadata.py` tersedia untuk diimport

---

## Phase 2: Foundational (Blocking — selesaikan sebelum semua User Story)

**Tujuan**: Perbarui konstruktor FastAPI di `src/main.py` agar menggunakan konstanta dari `docs_metadata.py`. Semua verifikasi user story bergantung pada perubahan ini.

**⚠️ CRITICAL**: Semua user story bergantung pada phase ini. Mulai US1–US5 hanya setelah T002 selesai.

- [X] T002 Perbarui `src/main.py` — ubah konstruktor `FastAPI(title="API-X Authentication", version="1.0.0")` menjadi menggunakan import dari `src/api/docs_metadata.py` dengan params: `title`, `version`, `description`, `openapi_tags`

**Checkpoint**: Server restart → `GET /openapi.json` mengembalikan `info.title == "API-X"`, `info.version == "0.1.0"`, `info.description` berisi teks panduan, dan array `tags` berisi 6 entri dengan deskripsi

---

## Phase 3: User Story 1 — Developer Baru Memahami API (Prioritas: P1) 🎯 MVP

**Goal**: Swagger UI menampilkan judul, versi, deskripsi API; semua 15 endpoint terkelompok dalam 6 tag domain; setiap endpoint memiliki ringkasan satu kalimat dalam Bahasa Indonesia.

**Independent Test**: `GET /openapi.json` → `info.title` ada, `tags` array memiliki 6 entri masing-masing dengan `description`, setiap operasi di `paths` memiliki field `summary` berisi kalimat dalam Bahasa Indonesia.

- [X] T003 [P] [US1] Tambah `summary=` (satu kalimat Bahasa Indonesia) ke 3 operasi di `src/api/routers/auth.py` — register, login, me
- [X] T004 [P] [US1] Tambah `summary=` (satu kalimat Bahasa Indonesia) ke 6 operasi di `src/api/routers/events.py` — create, get-by-id, update, delete (admin_router) + list, get-by-id (public_router)
- [X] T005 [P] [US1] Tambah `summary=` (satu kalimat Bahasa Indonesia) ke 3 operasi di `src/api/routers/registrations.py` — register-to-event, cancel-registration, get-my-registrations
- [X] T006 [P] [US1] Tambah `summary=` (satu kalimat Bahasa Indonesia) ke 2 operasi di `src/api/routers/reports.py` — event-stats, event-summary
- [X] T007 [P] [US1] Tambah `summary=` (satu kalimat Bahasa Indonesia) ke 1 operasi di `src/api/routers/admin.py` — list-users

**Checkpoint**: User Story 1 selesai — buka `/docs` → lihat nama API, versi, deskripsi, 6 grup tag, masing-masing endpoint memiliki ringkasan satu kalimat

---

## Phase 4: User Story 2 — Try It Out dengan Contoh (Prioritas: P1)

**Goal**: Fitur "Try it out" Swagger UI memiliki contoh nilai yang sudah terisi untuk setiap field request body, serta contoh body untuk setiap respons. Developer dapat langsung klik Execute tanpa mengetik data manual.

**Independent Test**: `GET /openapi.json` → `paths./auth/register.post.requestBody.content.application/json.schema.properties.name.examples` berisi nilai contoh. Di Swagger UI, buka endpoint dengan request body → klik "Try it out" → contoh nilai otomatis terisi.

- [X] T008 [P] [US2] Anotasi semua field di `src/api/schemas/auth.py` dengan `Field(description=..., examples=[...])` dan tambah `model_config.json_schema_extra` — RegisterRequest (name, email, password), LoginRequest (email, password), TokenResponse (access_token, token_type), UserRead (id, name, email, role, created_at)
- [X] T009 [P] [US2] Anotasi semua field di `src/api/schemas/events.py` dengan `Field(description=..., examples=[...])` dan tambah `model_config.json_schema_extra` — EventCreate (title, description, date, registration_deadline, quota), EventUpdate (semua field optional), EventResponse (id, title, description, date, registration_deadline, quota, status, registered_count, created_at, updated_at)
- [X] T010 [P] [US2] Anotasi semua field di `src/api/schemas/registrations.py` dengan `Field(description=..., examples=[...])` dan tambah `model_config.json_schema_extra` — RegistrationResponse, RegistrationWithEventResponse
- [X] T011 [P] [US2] Anotasi semua field di `src/api/schemas/reports.py` dengan `Field(description=..., examples=[...])` dan tambah `model_config.json_schema_extra` — EventStatItem (event_id, title, registered_count, quota, fill_rate), ReportSummaryResponse (active_events_count)
- [X] T012 [P] [US2] Anotasi semua field di `src/api/schemas/pagination.py` dengan `Field(description=..., examples=[...])` dan tambah `model_config.json_schema_extra` — `Page[T]` (items, total_items, page, page_size, total_pages) dan `EventStatsPage` (items, total, page, size, pages) — perhatikan kedua schema punya nama field yang berbeda, dokumentasikan masing-masing sesuai implementasi aktual (research.md R-3)
- [X] T013 [P] [US2] Tambah `model_config.json_schema_extra` dengan contoh error envelope ke `src/api/schemas/errors.py` — `ErrorDetail` (code, message, httpStatus) dan `ErrorEnvelope` (error: ErrorDetail) beserta contoh JSON konkret per kode error (UNAUTHORIZED, FORBIDDEN, NOT_FOUND, VALIDATION_ERROR, dll.)

**Checkpoint**: User Story 2 selesai — klik endpoint manapun di Swagger UI → "Try it out" → semua field request body terisi contoh nilai; response schema menampilkan contoh body

---

## Phase 5: User Story 3 — Detail Schema Lengkap (Prioritas: P1)

**Goal**: Setiap endpoint memiliki deskripsi panjang (tujuan, konteks bisnis, label akses Bahasa Indonesia, aturan bisnis), dan semua kemungkinan kode HTTP response terdaftar dengan contoh body JSON menggunakan struktur error envelope standar.

**Independent Test**: `GET /openapi.json` → setiap operasi di `paths` memiliki `description` (bukan hanya `summary`); setiap operasi memiliki minimal 2 kode respons di `responses`; setiap respons 4xx memiliki `content.application/json.example` atau `.examples` berisi ErrorEnvelope dengan `error.code` spesifik.

- [X] T014 [P] [US3] Tambah docstring lengkap + `responses={}` (401/409/422 dengan contoh error envelope) ke 3 operasi di `src/api/routers/auth.py`:
  - POST /auth/register: label "**Akses**: Publik", aturan email unik, password hash bcrypt; responses 409 EMAIL_ALREADY_EXISTS, 422 VALIDATION_ERROR
  - POST /auth/login: label "**Akses**: Publik", aturan verifikasi email+password; responses 401 INVALID_CREDENTIALS, 422 VALIDATION_ERROR
  - GET /auth/me: label "**Akses**: Memerlukan token", deskripsi profil pengguna aktif; responses 401 UNAUTHORIZED
- [X] T015 [P] [US3] Tambah docstring lengkap + `responses={}` ke 6 operasi di `src/api/routers/events.py`:
  - Admin operations (4): label "**Akses**: Khusus admin" pada POST/PUT/DELETE; responses 401/403/404/409/422 dengan contoh error envelope spesifik per operasi (QUOTA_MUST_BE_POSITIVE, EVENT_NOT_FOUND, EVENT_HAS_REGISTRATIONS, dll.)
  - Public operations (2): label "**Akses**: Publik" pada GET /events dan GET /events/{event_id}; responses 404 EVENT_NOT_FOUND; deskripsikan parameter pagination `page` (default=1) dan `page_size` (default=20, max=100)
- [X] T016 [P] [US3] Tambah docstring lengkap + `responses={}` ke 3 operasi di `src/api/routers/registrations.py`:
  - POST /registrations/{event_id}: label "**Akses**: Memerlukan token", aturan deadline/quota/duplikat; responses 401/404/409 dengan DUPLICATE_REGISTRATION, QUOTA_FULL, REGISTRATION_CLOSED
  - DELETE /registrations/{event_id}: label "**Akses**: Memerlukan token", aturan hanya bisa cancel milik sendiri; responses 401/403/404
  - GET /registrations/me: label "**Akses**: Memerlukan token"; responses 401
- [X] T017 [P] [US3] Tambah docstring lengkap + `responses={}` ke 2 operasi di `src/api/routers/reports.py`:
  - GET /admin/reports/events/stats: label "**Akses**: Khusus admin", deskripsi statistik peserta per event aktif, parameter pagination `page`/`page_size`; responses 401/403
  - GET /admin/reports/events/summary: label "**Akses**: Khusus admin", deskripsi ringkasan jumlah event aktif; responses 401/403
- [X] T018 [P] [US3] Tambah docstring lengkap + `responses={}` ke 1 operasi di `src/api/routers/admin.py`:
  - GET /admin/users: label "**Akses**: Khusus admin", deskripsi daftar semua pengguna terdaftar; responses 401/403

**Checkpoint**: User Story 3 selesai — buka detail endpoint manapun di Swagger UI → lihat deskripsi panjang dengan label akses; buka "Responses" → semua kode HTTP terdaftar; expand error response → lihat JSON body dengan `error.code` spesifik

---

## Phase 6: User Story 4 — Alur Autentikasi Terdokumentasi (Prioritas: P2)

**Goal**: Security scheme `BearerAuth` terdefinisi di Swagger UI; tombol "Authorize" berfungsi; semua endpoint terproteksi menampilkan ikon kunci (🔒); deskripsi API menyertakan panduan register→login→Authorize.

**Independent Test**: `GET /openapi.json` → `components.securitySchemes.BearerAuth` ada dengan `type: http`, `scheme: bearer`; semua 11 operasi terproteksi memiliki `security: [{BearerAuth: []}]`; di Swagger UI tombol "Authorize" terlihat; endpoint terproteksi menampilkan ikon kunci.

- [X] T019 [US4] Definisikan security scheme `BearerAuth` di `src/main.py` dengan meng-override `app.openapi()` — tambah `components.securitySchemes.BearerAuth` (type: http, scheme: bearer, bearerFormat: JWT, description: "Token dari POST /auth/login. Format: `Bearer <token>`")
- [X] T020 [P] [US4] Tambah `security=[{"BearerAuth": []}]` ke 1 operasi terproteksi di `src/api/routers/auth.py` — GET /auth/me
- [X] T021 [P] [US4] Tambah `security=[{"BearerAuth": []}]` ke 4 operasi admin di `src/api/routers/events.py` — POST/GET/{id}/PUT/{id}/DELETE/{id} /admin/events
- [X] T022 [P] [US4] Tambah `security=[{"BearerAuth": []}]` ke 3 operasi di `src/api/routers/registrations.py` — POST/DELETE /registrations/{event_id}, GET /registrations/me
- [X] T023 [P] [US4] Tambah `security=[{"BearerAuth": []}]` ke 2 operasi di `src/api/routers/reports.py` — GET /admin/reports/events/stats, GET /admin/reports/events/summary
- [X] T024 [P] [US4] Tambah `security=[{"BearerAuth": []}]` ke 1 operasi di `src/api/routers/admin.py` — GET /admin/users

**Checkpoint**: User Story 4 selesai — buka Swagger UI → tombol "Authorize" terlihat di kanan atas; endpoint terproteksi tampilkan ikon kunci; klik lock icon → modal "Authorize" → masukkan token → endpoint terproteksi dapat diakses langsung dari Swagger UI

---

## Phase 7: User Story 5 — Admin Memahami Endpoint Khusus Admin (Prioritas: P2)

**Goal**: Semua endpoint admin sudah punya label "Khusus admin" di deskripsi (dari US3) dan lock icon (dari US4). Task ini menambahkan snapshot test otomatis yang memvalidasi semua acceptance criteria dari US1–US5 secara komprehensif.

**Independent Test**: Jalankan `pytest tests/unit/test_openapi_schema.py` → semua test lulus; setiap test admin memverifikasi label "Khusus admin" di description dan keberadaan security scheme.

- [X] T025 [US5] Buat `tests/unit/test_openapi_schema.py` — snapshot test dengan fungsi berikut:
  - `test_api_metadata()`: title == "API-X", version == "0.1.0", description mengandung kata "Authorize" atau "Bearer"
  - `test_all_6_tags_with_descriptions()`: array `tags` memiliki 6 entri, setiap tag punya `description`
  - `test_all_operations_have_summary()`: iterasi `paths`, setiap operasi memiliki `summary` non-empty
  - `test_all_operations_have_description()`: setiap operasi memiliki `description` non-empty
  - `test_bearer_auth_scheme_defined()`: `components.securitySchemes.BearerAuth` ada, `scheme == "bearer"`
  - `test_protected_operations_have_security()`: 11 operasi non-publik memiliki `security: [{BearerAuth: []}]`; 4 operasi publik tidak memiliki security
  - `test_admin_operations_have_khusus_admin_label()`: deskripsi GET /admin/users, POST/PUT/DELETE /admin/events, GET /admin/reports/... mengandung teks "Khusus admin"
  - `test_all_4xx_responses_have_examples()`: setiap respons 4xx di semua operasi memiliki `content.application/json.example` atau `.examples`
  - `test_schema_fields_have_descriptions()`: setiap property di setiap schema `components/schemas` punya `description`
  - `test_no_inline_schema_duplicates()`: setiap schema yang muncul lebih dari satu kali di `/openapi.json` direferensikan via `$ref` ke `components/schemas`, bukan diduplikasi inline (FR-017)

**Checkpoint**: User Story 5 selesai — `pytest tests/unit/test_openapi_schema.py -v` → semua 9 test lulus; output pytest menunjukkan semua admin endpoints terverifikasi dengan label "Khusus admin"

---

## Phase 8: Polish & Cross-Cutting Concerns

**Tujuan**: Perbaikan lintas user story — konsistensi, koreksi inkonsistensi, dan validasi akhir.

> **Catatan**: Koreksi tabel endpoint di `spec.md` (jalur, tag names, parameter pagination `page_size`, envelope schema dua-bentuk) telah diselesaikan pada fase analisis pre-implementasi — T026 resolved.

- [X] T027 Jalankan `pytest tests/unit/test_openapi_schema.py tests/contract/ -v` dan perbaiki semua assertion failure yang ditemukan — pastikan semua 10 snapshot test + existing contract tests lulus tanpa degradasi
- [X] T028 [P] Verifikasi manual checklist via browser — buka http://localhost:8000/docs dan centang semua item di `specs/005-swagger-api-docs/quickstart.md` bagian "Checklist Verifikasi Manual" (14 item): judul, versi, deskripsi, tombol Authorize, 6 tag dengan deskripsi, summary per endpoint, lock icon pada endpoint terproteksi, Field description di request schema, semua kode respons error terdaftar, contoh JSON body per kode error. **NFR-001 check**: pastikan tidak ada environment-aware guard yang menyembunyikan Swagger UI (tidak ada kondisi `if settings.env != "production"` di sekitar `/docs` mount atau `openapi_url` set ke `None`).
- [X] T029 [P] *(Manual pre-release gate — SC-002)* Tantang seorang developer yang belum pernah menggunakan API-X untuk berhasil mendapatkan JWT token dan memanggil setidaknya satu endpoint terproteksi hanya dengan membaca Swagger UI — target ≤10 menit. Catat hasil (lulus/gagal, waktu yang dibutuhkan, hambatan yang ditemukan) di `specs/005-swagger-api-docs/checklists/requirements.md`.

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (Setup)       → No dependencies → mulai sekarang
Phase 2 (Foundational) → Depends on Phase 1 → BLOCKS semua user story
Phase 3 (US1)         → Depends on Phase 2 → dapat mulai setelah T002
Phase 4 (US2)         → Depends on Phase 2 → dapat mulai paralel dengan Phase 3
Phase 5 (US3)         → Depends on Phase 2 → dapat mulai paralel dengan Phase 3+4
                         (secara logis: US3 descr untuk file yang sama setelah US1 summary selesai)
Phase 6 (US4)         → Depends on Phase 2 → T019 terlebih dahulu, lalu T020-T024 paralel
Phase 7 (US5)         → Depends on Phase 5 + Phase 6 → T025 setelah US3 dan US4 selesai
Phase 8 (Polish)      → Depends on Phase 7 → T028/T029 paralel, T027 setelah T025
```

### User Story Dependencies

| User Story | Depends On | Independent? |
|-----------|-----------|--------------|
| US1 (Phase 3) | Phase 2 selesai | Ya — hanya butuh T002 |
| US2 (Phase 4) | Phase 2 selesai | Ya — berbeda file dari US1 |
| US3 (Phase 5) | Phase 2 selesai | Ya — logis setelah US1 summaries ada; untuk file yang sama edit setelah US1 |
| US4 (Phase 6) | Phase 2 selesai | Ya — T019 (main.py) pertama, lalu T020-T024 paralel; berbeda scope dari US1/US2/US3 |
| US5 (Phase 7) | US3 + US4 | Tidak bebas — butuh deskripsi "Khusus admin" (US3) dan security scheme (US4) |

### Parallel Opportunities

**Untuk satu orang** — urutan rekomendasi (MVP-first):
```
T001 → T002 → T003-T007 (pilih satu per satu) → T008-T013 (pilih satu per satu)
     → T014-T018 (pilih satu per satu) → T019 → T020-T024 → T025 → T027-T029
```

**Untuk dua orang** — split berdasarkan file:
```
Person A: T001 → T002 → T003, T005, T008, T010, T012, T014, T016, T020, T022
Person B: (setelah T002) → T004, T006, T007, T009, T011, T013, T015, T017, T018, T021, T023, T024
kemudian bersama: T019 → T025 → T027, T028, T029
```

**Paralel within a phase** (setelah T002):
- US1: T003, T004, T005, T006, T007 semua dapat dikerjakan bersamaan (file berbeda)
- US2: T008, T009, T010, T011, T012, T013 semua dapat dikerjakan bersamaan (file berbeda)
- US3: T014 dapat dikerjakan setelah T003; T015 setelah T004; dst. Atau setelah seluruh US1 selesai, kerjakan T014-T018 serentak.
- US4: T019 pertama → lalu T020, T021, T022, T023, T024 serentak

---

## Implementation Strategy

### MVP Scope (rekomendasi: User Story 1 + User Story 2)

Setelah Phase 2, US1 dan US2 sudah dapat di-deliver sebagai increment:
- US1: Title, tags, summaries → developer baru sudah bisa navigasi API
- US2: Schema examples → "Try it out" sudah berfungsi dengan data dummy

**Total task MVP**: T001 + T002 + T003–T007 + T008–T013 = **14 task**

### Full Delivery

Setelah semua phase selesai (T001–T025, T027–T029 = **28 task**), dokumentasi API-X memiliki:
- ✅ Header API lengkap (judul, versi, deskripsi dengan panduan auth)
- ✅ 6 tag domain dengan deskripsi
- ✅ Semua 15 endpoint dengan summary + description + label akses Bahasa Indonesia
- ✅ Semua field schema dengan description + examples (Try it out ready)
- ✅ Semua kode respons 4xx dengan contoh error envelope konkret
- ✅ BearerAuth security scheme + lock icon pada 11 endpoint terproteksi
- ✅ Label "Khusus admin" pada semua 7 endpoint admin
- ✅ Snapshot test suite (9 test cases) yang memvalidasi kelengkapan dokumentasi

---

## Summary

| Phase | User Story | Priority | Tasks | Parallelizable |
|-------|-----------|----------|-------|----------------|
| 1 | Setup | — | T001 | Tidak (1 task) |
| 2 | Foundational | — | T002 | Tidak (1 task) |
| 3 | US1: API header + grouping + summaries | P1 🎯 MVP | T003–T007 (5) | Ya — semua [P] |
| 4 | US2: Schema field examples + Try it out | P1 🎯 MVP | T008–T013 (6) | Ya — semua [P] |
| 5 | US3: Full descriptions + response codes | P1 | T014–T018 (5) | Ya — semua [P] |
| 6 | US4: BearerAuth + lock icons | P2 | T019–T024 (6) | T020–T024 [P] |
| 7 | US5: Admin labels + test file | P2 | T025 (1) | Tidak |
| 8 | Polish | — | T027–T029 (3) | T028, T029 [P] |
| **Total** | | | **28 tasks** | |

**Parallel opportunities**: 22 dari 28 task memiliki marker [P]

**Files yang dimodifikasi** (14 file):
- `src/main.py` — T002, T019
- `src/api/docs_metadata.py` (baru) — T001
- `src/api/schemas/auth.py` — T008
- `src/api/schemas/events.py` — T009
- `src/api/schemas/registrations.py` — T010
- `src/api/schemas/reports.py` — T011
- `src/api/schemas/pagination.py` — T012
- `src/api/schemas/errors.py` — T013
- `src/api/routers/auth.py` — T003, T014, T020
- `src/api/routers/events.py` — T004, T015, T021
- `src/api/routers/registrations.py` — T005, T016, T022
- `src/api/routers/reports.py` — T001, T006, T017, T023
- `src/api/routers/admin.py` — T007, T018, T024
- `tests/unit/test_openapi_schema.py` (baru) — T025
