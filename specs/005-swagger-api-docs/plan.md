# Implementation Plan: Dokumentasi API dengan Swagger

**Branch**: `main` | **Date**: 2026-03-09 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification dari `specs/005-swagger-api-docs/spec.md`

---

## Summary

Fitur ini memperkaya Swagger UI API-X dari tampilan minimal (judul generik, schema tanpa deskripsi, tidak ada contoh) menjadi dokumentasi API kelas pertama yang interaktif dan komprehensif. Pendekatan yang digunakan adalah **code-first**: menambahkan metadata ke Pydantic schema (`Field` dengan `description` dan `examples`), FastAPI router operation (`summary`, `description`, `responses`), dan konstruktor `FastAPI(...)` (`title`, `description`, `version`, `openapi_tags`). Tidak ada endpoint baru, tidak ada migrasi database, tidak ada dependensi Python baru.

### Penyesuaian Penting: Jalur Endpoint Aktual vs Spesifikasi

Setelah pemeriksaan kode sumber, ditemukan beberapa perbedaan antara tabel "Cakupan Endpoint" di `spec.md` dan jalur endpoint yang sesungguhnya diimplementasikan. Dokumentasi HARUS mengikuti implementasi aktual (code-first). Detail perbedaan dan resolusinya ada di [research.md](research.md).

---

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: FastAPI ≥0.111.0 (OpenAPI 3.1.0 default), Pydantic v2 (≥2.2 via pydantic-settings), pytest ≥8.0.0
**Storage**: N/A — fitur ini hanya menyentuh lapisan API (schema annotations dan router metadata); tidak ada perubahan pada lapisan database atau domain
**Testing**: pytest — snapshot test terhadap `/openapi.json`, contract test menggunakan example data dari dokumentasi; tools: pytest, httpx, ruff, black, mypy
**Target Platform**: Linux server (sama dengan deployment API-X saat ini)
**Project Type**: Web service (Python/FastAPI), code-first API documentation enrichment
**Performance Goals**: N/A — perubahan murni metadata, tidak ada logika runtime baru yang bermakna
**Constraints**:
- Code-first only; tidak boleh ada file OpenAPI YAML yang dikelola manual secara terpisah sebagai sumber kebenaran (FR-016)
- Swagger UI aktif di semua environment tanpa environment-aware toggle (NFR-001)
- Semua deskripsi dalam Bahasa Indonesia; istilah teknis yang tak tergantikan tetap English (Assumption 4)
- OpenAPI 3.1.0 — FastAPI ≥0.111.0 sudah menghasilkan OpenAPI 3.1.0 secara default tanpa konfigurasi tambahan
**Scale/Scope**: 15 endpoint diimplementasikan, 6 tag di router, 4 tag domain di spec, 1 security scheme (BearerAuth)

---

## Constitution Check

*GATE: Harus lulus sebelum Phase 0. Di-re-check setelah Phase 1.*

### I. Stack Alignment ✅

- **Bahasa**: Python 3.11+ ✅
- **Framework**: FastAPI ≥0.111.0 — framework utama, mainstream, well-supported ✅
- **Library tambahan**: Tidak ada library baru yang dibutuhkan. FastAPI sudah menyertakan Swagger UI via `fastapi[standard]`/`starlette`. `email-validator` sudah ada untuk `EmailStr`. ✅
- **Deviasi**: Tidak ada — semua perubahan pada library yang sudah digunakan.

### II. Clean Architecture Boundaries ✅

- **Lapisan yang disentuh**: Hanya lapisan API (Pydantic schemas di `src/api/schemas/` dan FastAPI routers di `src/api/routers/`). Tidak ada perubahan pada `src/application/`, `src/domain/`, atau `src/infrastructure/`. ✅
- **Arah dependency**: Tidak berubah — schema tetap berada di API layer. ✅
- **Composition root**: `src/main.py` — tempat `FastAPI(title=..., description=..., openapi_tags=[...])` dikonfigurasi. Tidak ada perubahan arsitektural. ✅

### III. Test-First & Fast Feedback ✅

- Setiap user story memiliki acceptance scenario yang dapat diotomatisasi:
  - **US-1 & US-2 (Swagger UI)**: Snapshot test pada output `GET /openapi.json` memverifikasi keberadaan `info.description`, `tags`, `summary` per operasi.
  - **US-3 (Detail schema)**: Test memeriksa `description` dan `examples` di setiap field schema dalam output `/openapi.json`.
  - **US-4 (Alur autentikasi)**: Contract test end-to-end: register → login → pakai token → akses protected endpoint.
  - **US-5 (Admin endpoint)**: Contract test: token admin→ 200, token user→ 403, tanpa token → 401.
- Testing stack: pytest + httpx (sudah ada di `tests/contract/`) ✅
- SC-003 dan SC-004 dapat diverifikasi via pytest yang memeriksa struktur `/openapi.json`.

### IV. Specification-Driven APIs & Contracts ✅

- Spec tersedia di `specs/005-swagger-api-docs/spec.md` ✅
- Kontrak OpenAPI 3.1.0 (`contracts/openapi.yaml`) dibuat sebagai artefak desain yang menggambarkan target state dokumentasi ✅
- Perubahan contract (field descriptions, examples) didokumentasikan di spec dan divalidasi oleh tests ✅
- Tidak ada perubahan pada request/response schema yang sudah ada (hanya penambahan metadata) ✅

### V. Simplicity & Observability ✅

- Solusi sesederhana mungkin: menambahkan `Field(description=..., examples=[...])` ke Pydantic model dan docstring ke router operation. Tidak ada abstraksi baru. ✅
- Tidak ada service baru, tidak ada modul baru (kecuali mungkin `src/api/docs.py` untuk memusatkan konstanta tag — dikaji di research).
- Logging: Tidak ada perubahan pada logging yang sudah ada; perubahan ini bersifat deklaratif.
- No breaking changes: Penambahan `description`/`examples` di Field tidak mengubah serialisasi JSON Pydantic. ✅

**Kesimpulan**: Semua gate lulus. Tidak ada violation. Implementasi dapat dilanjutkan.

---

## Project Structure

### Dokumentasi (fitur ini)

```text
specs/005-swagger-api-docs/
├── plan.md              # File ini
├── research.md          # Phase 0: temuan riset dan keputusan desain
├── data-model.md        # Phase 1: inventaris schema dengan field, tipe, constraint
├── quickstart.md        # Phase 1: panduan cara menambahkan anotasi ke kode
├── contracts/
│   ├── openapi.yaml     # Phase 1: kontrak OpenAPI 3.1.0 target state
│   └── error-envelope.md # Sudah ada — tidak diubah
└── tasks.md             # Phase 2: dibuat oleh /speckit.tasks (BUKAN oleh /speckit.plan)
```

### Kode Sumber (root repositori)

```text
src/
├── main.py                      # Modifikasi: FastAPI constructor metadata + openapi_tags
├── api/
│   ├── schemas/
│   │   ├── auth.py              # Modifikasi: Field descriptions + examples
│   │   ├── events.py            # Modifikasi: Field descriptions + examples
│   │   ├── registrations.py     # Modifikasi: Field descriptions + examples
│   │   ├── reports.py           # Modifikasi: Field descriptions + examples
│   │   ├── pagination.py        # Modifikasi: Field descriptions
│   │   └── errors.py            # Modifikasi: model_config json_schema_extra example
│   └── routers/
│       ├── auth.py              # Modifikasi: docstrings + responses={} per operasi
│       ├── events.py            # Modifikasi: docstrings + responses={} per operasi
│       ├── registrations.py     # Modifikasi: docstrings + responses={} per operasi
│       ├── reports.py           # Modifikasi: docstrings + responses={} per operasi (sudah ada sebagian)
│       └── admin.py             # Modifikasi: docstrings + responses={}

tests/
├── unit/
│   └── test_openapi_schema.py   # Baru: snapshot test struktur /openapi.json
├── contract/
│   └── (file yang ada)          # Diperluas: contoh dokumentasi dipakai sebagai data test
```

**Structure Decision**: Menggunakan struktur proyek tunggal yang sudah ada (`Option 1`). Tidak ada direktori baru di `src/`. File baru satu-satunya di `tests/unit/test_openapi_schema.py` untuk memvalidasi output `/openapi.json`.

---

## Phase 0: Research Summary

Lihat [research.md](research.md) untuk detail lengkap. Ringkasan keputusan:

| # | Item | Keputusan |
|---|------|-----------|
| R-1 | Jalur endpoint aktual vs spec | Dokumentasikan jalur aktual; spec endpoint table perlu diperbarui |
| R-2 | Pagination param: `page_size` vs `size` | Dokumentasikan `page_size` (implementasi aktual), tambahkan alias `size` optional jika diinginkan |
| R-3 | Response envelope: `Page` vs `EventStatsPage` | Dokumentasikan masing-masing schema aktual; keduanya tetap |
| R-4 | OpenAPI version | 3.1.0 — FastAPI ≥0.111.0 default, tidak perlu konfigurasi tambahan |
| R-5 | Tag unification | Pertahankan 6 tag aktual; tambahkan deskripsi per tag via `openapi_tags`; rename `Admin Reporting` → `admin-reporting` (lowercase, lihat R-5) |
| R-6 | Centralize tag constants | Buat `src/api/docs_metadata.py` untuk konstanta tag dan deskripsi |

---

## Phase 1: Design Summary

### Data Model

Lihat [data-model.md](data-model.md) untuk inventaris lengkap semua schema beserta field, tipe, constraint, dan rencana anotasi.

### Contract

Lihat [contracts/openapi.yaml](contracts/openapi.yaml) untuk kontrak OpenAPI 3.1.0 target state yang mencakup semua 15 endpoint dengan metadata lengkap.

### Quickstart

Lihat [quickstart.md](quickstart.md) untuk panduan implementasi langkah-demi-langkah cara menambahkan anotasi dokumentasi ke kode FastAPI.

---

## Complexity Tracking

> Tidak ada violation konstitusi hard (MUST) yang perlu dijustifikasi.

### CT-1: Test-First Soft Deviation — Snapshot Tests Dibuat Setelah Implementation Phases

- **Deviation**: Test suite snapshot (`tests/unit/test_openapi_schema.py`, T025, Phase 7) dibuat setelah implementation phases 3–6, bukan before/alongside.
- **Justification**: Fitur ini tidak menambah *behavior* baru — hanya menambah metadata deklaratif (Field annotations, docstrings, `responses=` dicts) ke komponen yang sudah ada. Tidak ada logic path baru yang perlu di-drive dengan red-green-refactor. Test snapshot memverifikasi *state akhir* dari metadata yang ditambahkan, bukan correctness of domain logic.
- **Mitigasi**: Setiap implementation phase (3–6) memiliki checkpoint manual yang jelas dan dapat diverifikasi secara instan via `GET /openapi.json`. T027 menjalankan full test suite setelah T025 selesai untuk memastikan tidak ada regresi pada contract tests yang sudah ada.
- **Constitution Principle III compliance**: Unit tests untuk application/domain logic tidak terpengaruh (tidak ada logic baru). Snapshot tests untuk API metadata termasuk kategori acceptance/contract tests, yang oleh Principle III **SHOULD** (bukan MUST) ditulis alongside implementation.
