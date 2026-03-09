# Quickstart: Menambahkan Dokumentasi ke FastAPI (005-swagger-api-docs)

**Dibuat**: 2026-03-09
**Tujuan**: Panduan langkah-demi-langkah cara mengimplementasikan metadata Swagger UI di kode FastAPI API-X.

---

## Prasyarat

- Python 3.11+, FastAPI ≥0.111.0, Pydantic v2 — semua sudah ada di `pyproject.toml`
- Tidak ada library baru yang perlu diinstall
- Server berjalan: `uvicorn src.main:app --reload`
- Swagger UI tersedia di: [http://localhost:8000/docs](http://localhost:8000/docs)
- Skema OpenAPI tersedia di: [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)

---

## Langkah 1: Buat File Konstanta Metadata (`src/api/docs_metadata.py`)

Pisahkan metadata dokumentasi dari logika aplikasi agar `src/main.py` tetap bersih.

```python
# src/api/docs_metadata.py
"""Konstanta metadata untuk Swagger UI / OpenAPI."""

API_TITLE = "API-X"
API_VERSION = "0.1.0"

API_DESCRIPTION = """
**API-X** adalah backend REST API untuk manajemen event dan pendaftaran peserta,
dilengkapi dengan autentikasi berbasis JWT dan laporan statistik untuk admin.

## Cara Menggunakan API Ini

1. **Daftar akun** — Panggil `POST /auth/register` dengan nama, email, dan kata sandi.
2. **Login** — Panggil `POST /auth/login` untuk mendapatkan JWT access token.
3. **Salin token** — Dari respons login, salin nilai `access_token`.
4. **Masukkan token** — Klik tombol **Authorize** di atas, lalu masukkan token dalam format:
   `Bearer <token>`
5. **Akses endpoint** — Semua endpoint terproteksi kini dapat digunakan langsung dari halaman ini.

## Peran Pengguna

| Peran | Keterangan |
|-------|-----------|
| **Publik** | Dapat diakses tanpa autentikasi |
| **Memerlukan token** | Memerlukan JWT token pengguna terdaftar |
| **Khusus admin** | Memerlukan JWT token dengan role `admin` |
"""

OPENAPI_TAGS = [
    {
        "name": "auth",
        "description": (
            "**Autentikasi dan otorisasi pengguna.** "
            "Endpoint untuk mendaftarkan akun baru, login untuk mendapatkan JWT token, "
            "dan melihat profil pengguna yang sedang login."
        ),
    },
    {
        "name": "admin",
        "description": (
            "**Manajemen pengguna oleh admin.** *(Khusus admin)* "
            "Memerlukan token dengan role `admin`."
        ),
    },
    {
        "name": "admin-events",
        "description": (
            "**Manajemen event oleh admin** *(Khusus admin)* — "
            "Buat, baca detail, perbarui, dan hapus event. "
            "Memerlukan token dengan role `admin`. "
            "Endpoint publik untuk menjelajahi event tersedia di grup **events**."
        ),
    },
    {
        "name": "events",
        "description": (
            "**Penjelajahan event publik.** "
            "Daftar event tersedia dan detail satu event. "
            "Dapat diakses tanpa autentikasi."
        ),
    },
    {
        "name": "registrations",
        "description": (
            "**Pendaftaran peserta ke event.** *(Memerlukan token)* "
            "Daftar ke event, batalkan pendaftaran, dan lihat daftar pendaftaran Anda. "
            "Memerlukan JWT token pengguna terdaftar."
        ),
    },
    {
        "name": "Admin Reporting",
        "description": (
            "**Laporan statistik event untuk admin.** *(Khusus admin)* "
            "Statistik peserta per event aktif dan ringkasan jumlah event aktif. "
            "Memerlukan token dengan role `admin`."
        ),
    },
]
```

---

## Langkah 2: Perbarui Konstruktor FastAPI di `src/main.py`

```python
# src/main.py — ubah baris ini:
app = FastAPI(title="API-X Authentication", version="1.0.0")

# Menjadi:
from src.api.docs_metadata import API_DESCRIPTION, API_TITLE, API_VERSION, OPENAPI_TAGS

app = FastAPI(
    title=API_TITLE,
    version=API_VERSION,
    description=API_DESCRIPTION,
    openapi_tags=OPENAPI_TAGS,
)
```

**Verifikasi**: Buka [http://localhost:8000/docs](http://localhost:8000/docs) — judul, versi, deskripsi, dan kelompok tag sudah muncul di halaman utama.

---

## Langkah 3: Anotasi Schema Pydantic dengan `Field`

### Pola Umum

```python
from pydantic import BaseModel, Field

class ContohRequest(BaseModel):
    nama_field: str = Field(
        ...,                              # ... = wajib; atau berikan default value
        description="Deskripsi field.",   # muncul di schema Swagger UI
        examples=["contoh nilai"],        # muncul di schema preview
        min_length=1,                     # constraint (jika ada)
    )
```

### Contoh: `src/api/schemas/auth.py`

```python
class RegisterRequest(BaseModel):
    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Nama lengkap pengguna.",
        examples=["Budi Santoso"],
    )
    email: EmailStr = Field(
        ...,
        description="Alamat email unik yang digunakan untuk login.",
        examples=["budi@contoh.com"],
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=72,
        description=(
            "Kata sandi (minimal 8 karakter). "
            "Disimpan sebagai hash bcrypt — tidak pernah plain text."
        ),
        examples=["R4h4sia!Kuat"],
    )
```

### Contoh: `src/api/schemas/events.py`

```python
class EventCreate(BaseModel):
    title: str = Field(
        ..., min_length=1, max_length=255,
        description="Judul event yang akan ditampilkan kepada peserta.",
        examples=["Workshop Python Lanjutan"],
    )
    description: str = Field(
        ..., min_length=1,
        description="Deskripsi lengkap event, termasuk agenda dan informasi pembicara.",
        examples=["Workshop intensif satu hari tentang FastAPI dan Pydantic v2."],
    )
    date: AwareDatetime = Field(
        ...,
        description="Tanggal dan waktu pelaksanaan event (ISO 8601 dengan timezone).",
        examples=["2026-06-15T09:00:00+07:00"],
    )
    registration_deadline: AwareDatetime = Field(
        ...,
        description="Batas waktu pendaftaran. Harus sebelum atau sama dengan `date`.",
        examples=["2026-06-10T23:59:59+07:00"],
    )
    quota: int = Field(
        ..., ge=1,
        description="Kapasitas maksimum peserta. Harus minimal 1.",
        examples=[50],
    )
```

> **Catatan**: Lakukan hal yang sama untuk semua schema di `auth.py`, `events.py`, `registrations.py`, `reports.py`, `pagination.py`, dan `errors.py`. Rujuk ke [data-model.md](../data-model.md) untuk daftar lengkap deskripsi dan contoh per field.

---

## Langkah 4: Anotasi Router Operation dengan Docstring dan `responses`

### Pola Umum

```python
@router.post(
    "/path",
    response_model=ResponseSchema,
    status_code=201,
    summary="Ringkasan satu kalimat",  # baris pertama docstring juga bisa dipakai
    responses={
        409: {
            "description": "Kondisi error yang memicu 409.",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "KODE_ERROR",
                            "message": "Pesan error.",
                            "httpStatus": 409,
                        }
                    }
                }
            },
        },
    },
)
async def nama_operasi(body: RequestSchema, ...) -> ResponseSchema:
    """Ringkasan satu kalimat (menjadi summary Swagger).

    Deskripsi panjang yang menjelaskan tujuan endpoint, siapa yang berhak mengakses,
    dan aturan bisnis yang berlaku.

    **Akses**: Publik | Memerlukan token | Khusus admin.
    """
    ...
```

### Contoh: `src/api/routers/auth.py`

```python
@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    responses={
        409: {
            "description": "Email sudah digunakan oleh akun lain.",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "EMAIL_ALREADY_EXISTS",
                            "message": "An account with this email already exists.",
                            "httpStatus": 409,
                        }
                    }
                }
            },
        },
        422: {
            "description": "Data request tidak valid (format email salah, kata sandi terlalu pendek).",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "VALIDATION_ERROR",
                            "message": "value is not a valid email address",
                            "httpStatus": 422,
                        }
                    }
                }
            },
        },
    },
)
async def register(body: RegisterRequest, ...) -> UserRead:
    """Daftarkan akun pengguna baru.

    Membuat akun pengguna baru dengan nama, email, dan kata sandi.

    **Akses**: Publik — tidak memerlukan autentikasi.

    **Aturan**:
    - Email harus unik; tidak boleh sama dengan email yang sudah terdaftar.
    - Kata sandi disimpan sebagai hash bcrypt (tidak pernah plain text).
    - Akun baru secara default memiliki role `user`.
    """
    ...
```

### Contoh Multiple Examples (`responses` dengan `examples`):

```python
responses={
    409: {
        "description": "Pendaftaran gagal karena salah satu kondisi.",
        "content": {
            "application/json": {
                "examples": {
                    "duplicate": {
                        "summary": "Sudah terdaftar ke event ini",
                        "value": {
                            "error": {
                                "code": "DUPLICATE_REGISTRATION",
                                "message": "You already have an active registration for this event.",
                                "httpStatus": 409,
                            }
                        },
                    },
                    "quota_full": {
                        "summary": "Kuota event sudah penuh",
                        "value": {
                            "error": {
                                "code": "QUOTA_FULL",
                                "message": "Event quota is full.",
                                "httpStatus": 409,
                            }
                        },
                    },
                }
            }
        },
    }
}
```

---

## Langkah 5: Tambahkan Example pada Model Response (`json_schema_extra`)

Untuk model response (bukan request body), tambahkan contoh di level model:

```python
class TokenResponse(BaseModel):
    access_token: str = Field(
        ...,
        description="JWT access token. Berlaku 60 menit.",
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."],
    )
    token_type: str = Field(
        default="bearer",
        description="Tipe token. Selalu 'bearer'.",
        examples=["bearer"],
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJmNDdhYzEwYiIsInJvbGUiOiJ1c2VyIn0.sig",
                    "token_type": "bearer",
                }
            ]
        }
    }
```

---

## Langkah 6: Verifikasi Kelengkapan Dokumentasi

### Cara Cepat via `/openapi.json`

```bash
# Download schema
curl http://localhost:8000/openapi.json | python -m json.tool > openapi_output.json

# Cek semua operasi punya summary
python -c "
import json
with open('openapi_output.json') as f:
    spec = json.load(f)
for path, methods in spec.get('paths', {}).items():
    for method, op in methods.items():
        if method == 'parameters': continue
        summary = op.get('summary', '')
        if not summary:
            print(f'MISSING SUMMARY: {method.upper()} {path}')
"
```

### Checklist Verifikasi Manual

Buka [http://localhost:8000/docs](http://localhost:8000/docs) dan verifikasi:

- [ ] Halaman utama menampilkan judul "API-X", versi "0.1.0", dan deskripsi dengan panduan autentikasi
- [ ] Tombol "Authorize" tersedia di kanan atas halaman
- [ ] Semua 6 tag terlihat: auth, admin, admin-events, events, registrations, Admin Reporting
- [ ] Setiap tag memiliki deskripsi (klik panah di sebelah nama tag)
- [ ] Setiap endpoint memiliki ringkasan satu kalimat
- [ ] Endpoint terproteksi menampilkan ikon kunci (🔒) di sebelah namanya
- [ ] Klik salah satu endpoint → buka "Request body" → setiap field punya deskripsi dan contoh
- [ ] Klik salah satu endpoint → buka "Responses" → kode 401/403/404/422 terdaftar
- [ ] Setiap kode respons error memiliki contoh body JSON dengan `error.code`

### Test Otomatis (pytest)

Buat `tests/unit/test_openapi_schema.py`:

```python
"""Snapshot test: verifikasi kelengkapan metadata OpenAPI."""
import pytest
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)


def get_openapi():
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    return resp.json()


def test_api_metadata():
    spec = get_openapi()
    assert spec["info"]["title"] == "API-X"
    assert spec["info"]["version"] == "0.1.0"
    assert "Authorize" in spec["info"]["description"] or "Bearer" in spec["info"]["description"]


def test_all_operations_have_summary():
    spec = get_openapi()
    missing = []
    for path, methods in spec.get("paths", {}).items():
        for method, op in methods.items():
            if method == "parameters":
                continue
            if not op.get("summary"):
                missing.append(f"{method.upper()} {path}")
    assert not missing, f"Operasi tanpa summary: {missing}"


def test_all_operations_have_description():
    spec = get_openapi()
    missing = []
    for path, methods in spec.get("paths", {}).items():
        for method, op in methods.items():
            if method == "parameters":
                continue
            if not op.get("description"):
                missing.append(f"{method.upper()} {path}")
    assert not missing, f"Operasi tanpa description: {missing}"


def test_protected_operations_have_security():
    """Endpoint yang bukan publik harus punya security scheme."""
    PUBLIC_OPERATIONS = {
        ("post", "/auth/register"),
        ("post", "/auth/login"),
        ("get", "/events"),
        ("get", "/events/{event_id}"),
    }
    spec = get_openapi()
    missing_security = []
    for path, methods in spec.get("paths", {}).items():
        for method, op in methods.items():
            if method == "parameters":
                continue
            if (method, path) in PUBLIC_OPERATIONS:
                continue
            if not op.get("security"):
                missing_security.append(f"{method.upper()} {path}")
    assert not missing_security, f"Endpoint terproteksi tanpa security: {missing_security}"


def test_bearer_auth_scheme_defined():
    spec = get_openapi()
    schemes = spec.get("components", {}).get("securitySchemes", {})
    assert "BearerAuth" in schemes
    assert schemes["BearerAuth"]["scheme"] == "bearer"


def test_error_responses_have_examples():
    """Setiap respons 4xx harus punya contoh body."""
    spec = get_openapi()
    missing = []
    for path, methods in spec.get("paths", {}).items():
        for method, op in methods.items():
            if method == "parameters":
                continue
            for status_code, resp in op.get("responses", {}).items():
                if not str(status_code).startswith("4"):
                    continue
                content = resp.get("content", {}).get("application/json", {})
                has_example = content.get("example") or content.get("examples")
                if not has_example:
                    missing.append(f"{method.upper()} {path} → {status_code}")
    assert not missing, f"Respons error tanpa contoh: {missing}"
```

---

## Urutan Implementasi yang Disarankan

1. **`src/api/docs_metadata.py`** — Buat file baru (tidak ada breaking change)
2. **`src/main.py`** — Update konstruktor `FastAPI()` (perubahan kecil, tidak ada breaking change)
3. **`src/api/schemas/errors.py`** — Tambah `json_schema_extra` ke `ErrorEnvelope`
4. **`src/api/schemas/auth.py`** — Tambah `Field(description=..., examples=[...])`
5. **`src/api/schemas/events.py`** — Tambah `Field(description=..., examples=[...])`
6. **`src/api/schemas/registrations.py`** — Tambah `Field(description=..., examples=[...])`
7. **`src/api/schemas/reports.py`** — Tambah `Field(description=..., examples=[...])`
8. **`src/api/schemas/pagination.py`** — Tambah `Field(description=..., examples=[...])`
9. **`src/api/routers/auth.py`** — Tambah docstring + `responses=` ke 3 operasi
10. **`src/api/routers/events.py`** — Tambah docstring + `responses=` ke 6 operasi
11. **`src/api/routers/registrations.py`** — Tambah docstring + `responses=` ke 3 operasi
12. **`src/api/routers/reports.py`** — Lengkapi docstring + tambah `responses=` ke 2 operasi
13. **`src/api/routers/admin.py`** — Tambah docstring + `responses=` ke 1 operasi
14. **`tests/unit/test_openapi_schema.py`** — Buat test suite validasi

---

## Tips & Gotcha

### `Field(examples=[...])` vs `Field(example=...)`

- Pydantic v2 + OpenAPI 3.1.0: gunakan `examples=[...]` (list) bukan `example=...` (deprecated di 3.1).
- FastAPI ≥0.111.0 dengan OpenAPI 3.1.0 mendukung `examples` list di Field secara native.

### Docstring Operasi

- Baris pertama docstring menjadi **summary** di Swagger UI.
- Paragraf selanjutnya menjadi **description** (mendukung Markdown).
- Jika `summary=` juga diberikan di decorator, nilainya akan meng-override baris pertama docstring.

### `responses=` Tidak Menggantikan `response_model`

- `response_model=Foo` mendefinisikan schema sukses (2xx).
- `responses={4xx: {...}}` mendefinisikan dokumentasi error responses.
- Keduanya diperlukan untuk dokumentasi yang lengkap.

### Security Inheritance di FastAPI

- Endpoint dengan `dependencies=[Depends(require_role("admin"))]` di level router **tidak otomatis** mendapat `security` di schema — perlu ditambahkan secara eksplisit di decorator atau via `openapi_extra`.
- Cara eksplisit: tambahkan `security=[{"BearerAuth": []}]` di decorator operasi.
- Cara via router: gunakan `router = APIRouter(... openapi_extra={"security": [{"BearerAuth": []}]})` — tidak selalu didukung.
- **Rekomendasi**: Tambahkan `security=[{"BearerAuth": []}]` secara eksplisit di setiap decorator operasi yang terproteksi.
