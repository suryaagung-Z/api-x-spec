# Research: Dokumentasi API dengan Swagger

**Dibuat**: 2026-03-09
**Fase**: Phase 0 — Resolusi semua NEEDS CLARIFICATION dan keputusan teknis

---

## R-1: Perbedaan Jalur Endpoint Aktual vs Tabel Spec

### Temuan

Setelah membaca seluruh router di `src/api/routers/`, ditemukan perbedaan signifikan antara tabel "Cakupan Endpoint" di `spec.md` dan jalur endpoint yang sesungguhnya diimplementasikan:

| Spec `spec.md` | Implementasi Aktual | Keterangan |
|---------------|---------------------|------------|
| `POST /events` (Admin) | `POST /admin/events` | Prefix `/admin` di admin router |
| `GET /events/{event_id}` (Admin) | `GET /admin/events/{event_id}` | Hanya admin yang bisa get admin detail |
| `PUT /events/{event_id}` (Admin) | `PUT /admin/events/{event_id}` | Prefix `/admin` |
| `DELETE /events/{event_id}` (Admin) | `DELETE /admin/events/{event_id}` | Prefix `/admin` |
| `POST /registrations` | `POST /registrations/{event_id}` | `event_id` adalah path parameter, bukan body |
| `GET /reports/events` (Admin) | `GET /admin/reports/events/stats` | Prefix `/admin` + path berbeda |
| `GET /reports/summary` (Admin) | `GET /admin/reports/events/summary` | Prefix `/admin` + path berbeda |
| *(tidak ada di spec)* | `GET /admin/users` | Endpoint admin users ada di implementasi |

### Keputusan

- **Decision**: Dokumentasi Swagger HARUS mencerminkan 15 jalur aktual yang diimplementasikan, bukan tabel spec yang tidak akurat.
- **Rationale**: Code-first approach (FR-016 + Assumption 2) — dokumentasi harus selalu sinkron dengan implementasi, bukan sebaliknya.
- **Alternatives considered**: Mengubah implementasi agar cocok dengan tabel spec → ditolak karena akan memecahkan contract yang sudah ada dan menyebabkan breaking changes pada test suite.
- **Action**: Tabel endpoint di spec.md akan diperbarui untuk mencerminkan jalur aktual dalam proses ini.

### Inventaris Endpoint Final (15 endpoint)

| # | Method | Path | Tags | Akses |
|---|--------|------|------|-------|
| 1 | POST | `/auth/register` | auth | Publik |
| 2 | POST | `/auth/login` | auth | Publik |
| 3 | GET | `/auth/me` | auth | Memerlukan token |
| 4 | GET | `/admin/users` | admin | Khusus admin |
| 5 | POST | `/admin/events` | admin-events | Khusus admin |
| 6 | GET | `/admin/events/{event_id}` | admin-events | Khusus admin |
| 7 | PUT | `/admin/events/{event_id}` | admin-events | Khusus admin |
| 8 | DELETE | `/admin/events/{event_id}` | admin-events | Khusus admin |
| 9 | GET | `/events` | events | Publik |
| 10 | GET | `/events/{event_id}` | events | Publik |
| 11 | POST | `/registrations/{event_id}` | registrations | Memerlukan token |
| 12 | DELETE | `/registrations/{event_id}` | registrations | Memerlukan token |
| 13 | GET | `/registrations/me` | registrations | Memerlukan token |
| 14 | GET | `/admin/reports/events/stats` | Admin Reporting | Khusus admin |
| 15 | GET | `/admin/reports/events/summary` | Admin Reporting | Khusus admin |

---

## R-2: Nama Parameter Pagination — `page_size` vs `size`

### Temuan

Spec clarification (Q3) memilih `page` + `size` sebagai parameter pagination canonical. Namun implementasi aktual di `src/api/dependencies/pagination.py` menggunakan `page` + `page_size`:

```python
async def pagination_params(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaginationParams:
```

### Keputusan

- **Decision**: Dokumentasikan `page_size` sebagaimana adanya di implementasi. Tidak ada rename di scope fitur ini.
- **Rationale**: Code-first approach. Mengganti nama parameter dari `page_size` ke `size` adalah breaking change terhadap contract yang sudah ada dan akan memecahkan semua test contract yang sudah ada. Ini di luar scope fitur dokumentasi.
- **Alternatives considered**: Menambahkan alias `size` via FastAPI Query alias → teknisnya mungkin, tapi meningkatkan ambiguitas dan kompleksitas tanpa nilai signifikan.
- **Spec update**: Tabel di spec.md akan diperbarui untuk mencerminkan `page_size` (bukan `size`).
- **Actual pagination params**: `page` (integer, ≥1, default=1), `page_size` (integer, 1–100, default=20).

---

## R-3: Format Respons Envelope Pagination

### Temuan

Dua schema pagination berbeda digunakan:

**`Page[T]`** (dipakai oleh `GET /events`):
```python
class Page(BaseModel, Generic[T]):
    items: list[T]
    total_items: int
    page: int
    page_size: int
    total_pages: int  # computed
```

**`EventStatsPage`** (dipakai oleh `GET /admin/reports/events/stats`):
```python
class EventStatsPage(BaseModel):
    items: list[EventStatItem]
    total: int
    page: int
    size: int
    pages: int
```

Spec clarification Q4 memilih "envelope dengan metadata" (bukan array biasa), yang sesuai dengan kedua implementasi. Namun field name-nya berbeda dari yang diasumsikan spec (`data`/`total`/`page`/`size`).

### Keputusan

- **Decision**: Dokumentasikan kedua schema aktual apa adanya. `Page[T]` dengan field `items`/`total_items`/`page`/`page_size`/`total_pages` untuk events list; `EventStatsPage` dengan field `items`/`total`/`page`/`size`/`pages` untuk reports stats.
- **Rationale**: Code-first. Mengubah field name schema adalah breaking change. Dokumentasi harus akurat, bukan aspirasional.
- **Alternatives considered**: Unifikasi ke satu schema → scope separate refactoring, bukan scope dokumentasi.

---

## R-4: Versi OpenAPI

### Temuan

FastAPI ≥0.100.0 menghasilkan OpenAPI 3.1.0 secara default. Project ini menggunakan `fastapi>=0.111.0` yang berarti OpenAPI 3.1.0 sudah aktif tanpa konfigurasi apa pun.

Verifikasi: FastAPI merujuk ke `openapi_version = "3.1.0"` di source internal sejak versi 0.100.

### Keputusan

- **Decision**: OpenAPI 3.1.0 dikonfirmasi. Tidak ada konfigurasi tambahan diperlukan.
- **Rationale**: Sudah default di versi yang dipakai.
- **Implementation note**: Jika ingin eksplisit, bisa tambahkan `openapi_version="3.1.0"` ke konstruktor `FastAPI()`, tapi ini redundan dan tidak wajib.

---

## R-5: Tag Unification — 6 Tag vs 4 Domain

### Temuan

Router saat ini mendefinisikan 6 tag berbeda:
- `auth` — Auth endpoints
- `admin` — Admin users endpoint
- `admin-events` — Admin event CRUD
- `events` — Public event browse
- `registrations` — Registration endpoints
- `Admin Reporting` — Reports endpoints (huruf kapital di "Admin", spasi)

Spec mendefinisikan 4 tag domain: Auth, Events, Registrations, Reports. Ini berbeda dari 6 tag aktual.

### Keputusan

- **Decision**: Pertahankan 6 tag aktual yang sudah ada. Tambahkan deskripsi untuk setiap tag via `openapi_tags` di `FastAPI()`. **Koreksi naming**: tag `Admin Reporting` diubah menjadi `admin-reporting` (lowercase, hyphenated) agar konsisten dengan konvensi naming tag lainnya. Perubahan ini memerlukan update `tags=["Admin Reporting"]` → `tags=["admin-reporting"]` di `src/api/routers/reports.py` — dilakukan bersamaan dengan T001.
- **Rationale**: Konsistensi penamaan — semua tag lain menggunakan lowercase hyphenated (`auth`, `admin`, `admin-events`, `events`, `registrations`). Tidak ada test atau client yang bergantung pada string eksak `"Admin Reporting"` (diverifikasi: grep di `tests/` hanya menemukan match di docstring komentar, bukan assertion).
- **Tag names dan descriptions**:
  - `auth` → "Autentikasi dan otorisasi pengguna. Endpoint untuk registrasi akun, login, dan melihat profil pengguna yang sedang login."
  - `admin` → "Manajemen pengguna oleh admin. **Khusus admin** — memerlukan token dengan role `admin`."
  - `admin-events` → "Manajemen event oleh admin (buat, baca, perbarui, hapus). **Khusus admin** — memerlukan token dengan role `admin`."
  - `events` → "Penjelajahan event publik. Dapat diakses tanpa autentikasi."
  - `registrations` → "Pendaftaran peserta ke event. Memerlukan autentikasi sebagai pengguna terdaftar."
  - `admin-reporting` → "Laporan statistik event untuk admin. **Khusus admin** — memerlukan token dengan role `admin`."

---

## R-6: Centralize Tag Constants dan Metadata API

### Temuan

Saat ini `src/main.py` berisi:
```python
app = FastAPI(title="API-X Authentication", version="1.0.0")
```

Judul "API-X Authentication" terlalu sempit — API-X sudah mencakup Event Management, Registration, dan Reporting. `openapi_tags` belum ada.

### Keputusan

- **Decision**: Buat file `src/api/docs_metadata.py` yang berisi konstanta metadata API (deskripsi, tag list, kontak, dll.) agar `main.py` tetap bersih dan metadata mudah diupdate tanpa menyentuh logika aplikasi.
- **Rationale**: Separation of concerns ringan. Metadata dokumentasi bisa cukup panjang (terutama `description` multi-paragraph); memisahkannya ke modul sendiri menjaga `main.py` bersih.
- **Alternatives considered**: Langsung inline di `main.py` → lebih sederhana tapi `main.py` jadi panjang.
- **Content `docs_metadata.py`**:
  - `API_TITLE = "API-X"`
  - `API_VERSION = "0.1.0"`
  - `API_DESCRIPTION` — multi-line string dengan deskripsi API dan panduan autentikasi
  - `OPENAPI_TAGS` — list tag dengan name + description

---

## R-7: Penambahan `responses={}` pada Router Operation

### Temuan

FastAPI mendukung dua cara mendokumentasikan error responses:
1. **`responses=` parameter di decorator** — mendokumentasikan kode HTTP dengan deskripsi dan contoh content
2. **`openapi_extra` dict** — override langsung pada OpenAPI spec

Contoh penggunaan `responses=`:
```python
@router.post(
    "/register",
    responses={
        409: {
            "description": "Email sudah digunakan",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "EMAIL_ALREADY_EXISTS",
                            "message": "An account with this email already exists.",
                            "httpStatus": 409
                        }
                    }
                }
            }
        }
    }
)
```

### Keputusan

- **Decision**: Gunakan parameter `responses=` di setiap route decorator untuk mendokumentasikan error responses. Gunakan docstring operasi untuk `description`; parameter `summary=` di decorator untuk ringkasan.
- **Rationale**: Native FastAPI API, type-safe, tidak memerlukan manipulasi dict raw. Lebih mudah di-maintain daripada `openapi_extra`.
- **Alternatives considered**: `openapi_extra` → lebih verbose, lebih error-prone.
- **Model example via `model_config`**: Untuk Pydantic v2, tambahkan `model_config = {"json_schema_extra": {"examples": [...]}}` pada model respons untuk menyediakan contoh default.

---

## R-8: Keputusan Teknis OAuth2PasswordBearer vs HTTP Bearer

### Temuan

Auth dependency menggunakan `OAuth2PasswordBearer(tokenUrl="/auth/login")` tapi login endpoint (`POST /auth/login`) menerima JSON body, bukan form data. Ini adalah pola non-standard yang umum di FastAPI untuk kemudahan penggunaan.

Implikasi Swagger UI:
- Tombol "Authorize" akan menampilkan form username+password (karena `OAuth2PasswordBearer`)
- Tapi endpoint `/auth/login` menerima JSON, bukan form
- Swagger UI akan gagal langsung login via "Authorize" dialog karena format berbeda

### Keputusan

- **Decision**: Tambahkan `HTTPBearer` sebagai security scheme di `main.py` dan dokumentasikan bahwa untuk mendapatkan token, developer harus memanggil `POST /auth/login` secara manual via "Try it out", copy token, lalu paste ke dialog "Authorize". Pertahankan `OAuth2PasswordBearer` di dependency (tidak diubah — bukan scope fitur ini).
- **Rationale**: Mengubah dependency auth ke `HTTPBearer` adalah refactoring yang di luar scope fitur dokumentasi. Penjelasan workaround di description API sudah cukup untuk FR-002 dan FR-013.
- **Alternatives considered**: Mengganti `OAuth2PasswordBearer` ke `HTTPBearer` sepenuhnya → breaking change potensial, di luar scope.

---

## Ringkasan Keputusan

| # | Item | Keputusan |
|---|------|-----------|
| R-1 | Jalur endpoint | Dokumentasikan 15 jalur aktual; perbarui tabel spec |
| R-2 | Pagination param | Dokumentasikan `page_size` (bukan `size`); tidak ada rename |
| R-3 | Pagination envelope | Dokumentasikan `Page` dan `EventStatsPage` aktual apa adanya |
| R-4 | OpenAPI version | 3.1.0 dikonfirmasi, tidak perlu konfigurasi tambahan |
| R-5 | Tag strategy | Pertahankan 6 tag aktual, tambahkan deskripsi via `openapi_tags`; rename `Admin Reporting` → `admin-reporting` (lowercase) |
| R-6 | Konstanta metadata | Buat `src/api/docs_metadata.py` untuk isolasi metadata dari logika app |
| R-7 | Error responses | Gunakan `responses=` parameter di decorator + docstring untuk deskripsi |
| R-8 | OAuth2 vs Bearer | Pertahankan `OAuth2PasswordBearer`; dokumentasikan workaround manual login |
