# Data Model: Dokumentasi API dengan Swagger

**Dibuat**: 2026-03-09
**Sumber**: Inventaris Pydantic schema dari `src/api/schemas/`

Dokumen ini mendaftar semua schema yang diemit ke OpenAPI, beserta field, tipe data, constraint, dan rencana anotasi metadata yang akan ditambahkan.

---

## Konvensi Anotasi

Setiap field akan dianotasi menggunakan `pydantic.Field`:

```python
field: type = Field(
    ...,                          # wajib (atau default value)
    description="Deskripsi ...",  # ditampilkan di Swagger UI
    examples=["contoh_nilai"],    # ditampilkan di schema preview
    # + constraint yang sudah ada: min_length, max_length, ge, le, dll.
)
```

---

## Auth Schemas (`src/api/schemas/auth.py`)

### `RegisterRequest` — Request body untuk `POST /auth/register`

| Field | Tipe | Wajib | Constraint | Deskripsi Rencana | Contoh |
|-------|------|-------|-----------|-------------------|--------|
| `name` | `str` | ✓ | min=1, max=255 | Nama lengkap pengguna | `"Budi Santoso"` |
| `email` | `EmailStr` | ✓ | format email | Alamat email unik yang digunakan untuk login | `"budi@contoh.com"` |
| `password` | `str` | ✓ | min=8, max=72 | Kata sandi (min. 8 karakter). Disimpan sebagai hash bcrypt, tidak pernah plain text. | `"R4h4sia!Kuat"` |

### `LoginRequest` — Request body untuk `POST /auth/login`

| Field | Tipe | Wajib | Constraint | Deskripsi Rencana | Contoh |
|-------|------|-------|-----------|-------------------|--------|
| `email` | `EmailStr` | ✓ | format email | Alamat email akun | `"budi@contoh.com"` |
| `password` | `str` | ✓ | min=1 | Kata sandi akun | `"R4h4sia!Kuat"` |

### `TokenResponse` — Response body untuk `POST /auth/login`

| Field | Tipe | Default | Deskripsi Rencana | Contoh |
|-------|------|---------|-------------------|--------|
| `access_token` | `str` | — | JWT access token. Sertakan di header `Authorization: Bearer <token>` untuk mengakses endpoint terproteksi. Berlaku selama 60 menit sejak diterbitkan. | `"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."` |
| `token_type` | `str` | `"bearer"` | Tipe token. Selalu `"bearer"`. | `"bearer"` |

### `UserRead` — Response body untuk `POST /auth/register`, `GET /auth/me`, `GET /admin/users`

| Field | Tipe | Deskripsi Rencana | Contoh |
|-------|------|-------------------|--------|
| `id` | `str` | ID unik pengguna (UUID) | `"f47ac10b-58cc-4372-a567-0e02b2c3d479"` |
| `name` | `str` | Nama lengkap pengguna | `"Budi Santoso"` |
| `email` | `str` | Alamat email pengguna | `"budi@contoh.com"` |
| `role` | `str` | Peran pengguna: `"user"` untuk pengguna biasa, `"admin"` untuk administrator | `"user"` |
| `created_at` | `datetime` | Waktu pembuatan akun (UTC ISO 8601) | `"2026-03-01T08:00:00Z"` |

---

## Event Schemas (`src/api/schemas/events.py`)

### `EventCreate` — Request body untuk `POST /admin/events`

| Field | Tipe | Wajib | Constraint | Deskripsi Rencana | Contoh |
|-------|------|-------|-----------|-------------------|--------|
| `title` | `str` | ✓ | min=1, max=255 | Judul event yang akan ditampilkan kepada peserta | `"Workshop Python Lanjutan"` |
| `description` | `str` | ✓ | min=1 | Deskripsi lengkap event, termasuk agenda dan informasi pembicara | `"Workshop intensif selama satu hari tentang FastAPI dan Pydantic v2..."` |
| `date` | `AwareDatetime` | ✓ | harus di masa depan saat dibuat | Tanggal dan waktu pelaksanaan event (ISO 8601 dengan timezone) | `"2026-06-15T09:00:00+07:00"` |
| `registration_deadline` | `AwareDatetime` | ✓ | ≤ `date` | Batas waktu pendaftaran (harus sebelum atau sama dengan waktu event) | `"2026-06-10T23:59:59+07:00"` |
| `quota` | `int` | ✓ | ge=1 | Kapasitas maksimum peserta. Harus minimal 1. | `50` |

**Validasi lintas-field**: `registration_deadline` harus ≤ `date`. Pelanggaran → 422 dengan `code: "INVALID_DATE_RANGE"`.

### `EventUpdate` — Request body untuk `PUT /admin/events/{event_id}`

Semua field opsional (partial update). Constraint per field sama dengan `EventCreate`.

| Field | Tipe | Wajib | Deskripsi Rencana |
|-------|------|-------|-------------------|
| `title` | `str \| None` | ✗ | Judul baru event (opsional) |
| `description` | `str \| None` | ✗ | Deskripsi baru event (opsional) |
| `date` | `AwareDatetime \| None` | ✗ | Tanggal baru pelaksanaan (opsional) |
| `registration_deadline` | `AwareDatetime \| None` | ✗ | Batas waktu pendaftaran baru (opsional) |
| `quota` | `int \| None` | ✗ | Kuota baru (opsional). Tidak boleh lebih kecil dari jumlah peserta aktif saat ini. |

### `EventResponse` — Response body untuk semua endpoint event

| Field | Tipe | Deskripsi Rencana | Contoh |
|-------|------|-------------------|--------|
| `id` | `int` | ID unik event | `42` |
| `title` | `str` | Judul event | `"Workshop Python Lanjutan"` |
| `description` | `str` | Deskripsi lengkap event | `"Workshop intensif..."` |
| `date` | `datetime` | Tanggal dan waktu pelaksanaan | `"2026-06-15T09:00:00"` |
| `registration_deadline` | `datetime` | Batas waktu pendaftaran | `"2026-06-10T23:59:59"` |
| `quota` | `int` | Kapasitas maksimum peserta | `50` |
| `status` | `EventStatus` | Status event: `"active"` atau `"deleted"` | `"active"` |
| `created_at` | `datetime` | Waktu event dibuat | `"2026-03-01T08:00:00"` |
| `registration_closed` | `bool` | `true` jika batas waktu pendaftaran sudah lewat (dihitung saat respons) | `false` |

---

## Registration Schemas (`src/api/schemas/registrations.py`)

### `RegistrationResponse` — Response body untuk `POST /registrations/{event_id}`

| Field | Tipe | Deskripsi Rencana | Contoh |
|-------|------|-------------------|--------|
| `id` | `int` | ID unik pendaftaran | `101` |
| `event_id` | `int` | ID event yang didaftarkan | `42` |
| `status` | `RegistrationStatus` | Status pendaftaran: `"active"` atau `"cancelled"` | `"active"` |
| `registered_at` | `datetime` | Waktu pendaftaran dilakukan | `"2026-03-09T10:30:00"` |

### `RegistrationWithEventResponse` — Response body untuk `GET /registrations/me`

| Field | Tipe | Deskripsi Rencana | Contoh |
|-------|------|-------------------|--------|
| `id` | `int` | ID unik pendaftaran | `101` |
| `event_id` | `int` | ID event yang didaftarkan | `42` |
| `status` | `RegistrationStatus` | Status pendaftaran: `"active"` atau `"cancelled"` | `"active"` |
| `registered_at` | `datetime` | Waktu pendaftaran dilakukan | `"2026-03-09T10:30:00"` |
| `cancelled_at` | `datetime \| None` | Waktu pembatalan, atau `null` jika belum dibatalkan | `null` |
| `event` | `EventSummary` | Ringkasan informasi event yang didaftarkan | — |

### `EventSummary` — Embedded dalam `RegistrationWithEventResponse`

| Field | Tipe | Deskripsi Rencana | Contoh |
|-------|------|-------------------|--------|
| `id` | `int` | ID event | `42` |
| `title` | `str` | Judul event | `"Workshop Python Lanjutan"` |
| `date` | `datetime` | Tanggal dan waktu pelaksanaan | `"2026-06-15T09:00:00"` |
| `registration_deadline` | `datetime` | Batas waktu pendaftaran | `"2026-06-10T23:59:59"` |
| `status` | `EventStatus` | Status event | `"active"` |

---

## Report Schemas (`src/api/schemas/reports.py`)

### `EventStatItem` — Item dalam `EventStatsPage`

| Field | Tipe | Deskripsi Rencana | Contoh |
|-------|------|-------------------|--------|
| `id` | `int` | ID event | `42` |
| `title` | `str` | Judul event | `"Workshop Python Lanjutan"` |
| `date` | `datetime` | Tanggal pelaksanaan | `"2026-06-15T09:00:00"` |
| `quota` | `int` | Kapasitas maksimum peserta | `50` |
| `total_registered` | `int` | Jumlah peserta terdaftar saat ini (hanya dengan status `active`) | `37` |
| `remaining_quota` | `int` | Sisa kuota = `quota − total_registered`. **Dapat bernilai negatif** jika data anomali. | `13` |

### `EventStatsPage` — Response body untuk `GET /admin/reports/events/stats`

| Field | Tipe | Deskripsi Rencana | Contoh |
|-------|------|-------------------|--------|
| `items` | `list[EventStatItem]` | Daftar statistik per event aktif pada halaman ini | — |
| `total` | `int` | Total seluruh event aktif di semua halaman | `120` |
| `page` | `int` | Nomor halaman saat ini (dimulai dari 1) | `1` |
| `size` | `int` | Jumlah item per halaman | `20` |
| `pages` | `int` | Total jumlah halaman | `6` |

### `ReportSummaryResponse` — Response body untuk `GET /admin/reports/events/summary`

| Field | Tipe | Deskripsi Rencana | Contoh |
|-------|------|-------------------|--------|
| `total_active_events` | `int` | Total event yang berstatus `active` DAN tanggalnya belum lewat saat ini | `42` |

---

## Pagination Schema (`src/api/schemas/pagination.py`)

### `Page[T]` — Response body generik untuk `GET /events`

| Field | Tipe | Deskripsi Rencana | Contoh |
|-------|------|-------------------|--------|
| `items` | `list[T]` | Daftar item pada halaman ini | — |
| `total_items` | `int` | Total seluruh item di semua halaman | `85` |
| `page` | `int` | Nomor halaman saat ini (dimulai dari 1) | `1` |
| `page_size` | `int` | Jumlah item per halaman | `20` |
| `total_pages` | `int` | Total jumlah halaman (dihitung dari `total_items / page_size`) | `5` |

---

## Error Schema (`src/api/schemas/errors.py`)

### `ErrorDetail` — Nested di dalam `ErrorEnvelope`

| Field | Tipe | Deskripsi Rencana | Contoh |
|-------|------|-------------------|--------|
| `code` | `str` | Kode error mesin yang unik dan dapat dibaca program (snake_case atau UPPER_SNAKE_CASE). Daftar nilai yang mungkin terdefinisi di kontrak error-envelope. | `"EMAIL_ALREADY_EXISTS"` |
| `message` | `str` | Pesan error yang dapat dibaca manusia, menjelaskan apa yang terjadi | `"An account with this email already exists."` |
| `httpStatus` | `int` | Kode HTTP status sama dengan status code respons | `409` |

### `ErrorEnvelope` — Root object semua error response

| Field | Tipe | Deskripsi Rencana |
|-------|------|-------------------|
| `error` | `ErrorDetail` | Detail error. Selalu ada pada setiap respons error. |

**Contoh JSON**:
```json
{
  "error": {
    "code": "UNAUTHORIZED",
    "message": "Could not validate credentials.",
    "httpStatus": 401
  }
}
```

---

## Kode Error yang Terdefinisi

Daftar error code yang digunakan di seluruh API:

| Code | HTTP | Kondisi |
|------|------|---------|
| `EMAIL_ALREADY_EXISTS` | 409 | Registrasi dengan email yang sudah digunakan |
| `UNAUTHORIZED` | 401 | Token tidak ada, tidak valid, atau kedaluwarsa; atau kredensial login salah |
| `FORBIDDEN` | 403 | Token valid tapi role tidak mencukupi (user biasa akses endpoint admin) |
| `EVENT_NOT_FOUND` | 404 | Event dengan ID yang diminta tidak ditemukan atau sudah dihapus |
| `QUOTA_FULL` | 409 | Kuota event sudah penuh, pendaftaran baru tidak diterima |
| `DUPLICATE_REGISTRATION` | 409 | Pengguna sudah memiliki pendaftaran aktif untuk event yang sama |
| `REGISTRATION_DEADLINE_PASSED` | 409 | Batas waktu pendaftaran event sudah lewat |
| `NO_ACTIVE_REGISTRATION` | 404 | Tidak ada pendaftaran aktif yang dapat dibatalkan |
| `QUOTA_BELOW_PARTICIPANTS` | 409 | Update kuota event di bawah jumlah peserta aktif |
| `INVALID_DATE_RANGE` | 422 | `registration_deadline` harus sebelum atau sama dengan `date` |
| `VALIDATION_ERROR` | 422 | Validasi request body gagal (field tidak valid, tipe salah, dll.) |

---

## Domain Enum

### `EventStatus`

| Value | Keterangan |
|-------|-----------|
| `"active"` | Event aktif dan bisa dilihat publik |
| `"deleted"` | Event telah dihapus oleh admin (soft delete) |

### `RegistrationStatus`

| Value | Keterangan |
|-------|-----------|
| `"active"` | Pendaftaran aktif, peserta terdaftar |
| `"cancelled"` | Pendaftaran telah dibatalkan |

---

## State Transitions

### Event Lifecycle

```
[dibuat] → status=active → (admin DELETE) → status=deleted
```

- Event yang baru dibuat selalu berstatus `active`
- Status `deleted` bersifat permanen (soft delete)
- Event dengan `date` yang sudah lewat masih berstatus `active` di database, tapi tidak muncul di endpoint publik dan laporan aktif

### Registration Lifecycle

```
[POST /registrations/{event_id}] → status=active
[DELETE /registrations/{event_id}] → status=cancelled
```

- Tidak bisa mendaftar ulang setelah `cancelled` (akan mendapat `DUPLICATE_REGISTRATION` jika mencoba mendaftar ke event yang sama lagi dengan status `active` yang ada, tapi karena yang ada `cancelled`, behavior perlu dikonfirmasi di implementasi)
- Sebenarnya berdasarkan spec 003, yang dicek adalah tidak ada active registration — cancelled bisa daftar ulang
