"""Konstanta metadata API untuk konstruktor FastAPI dan OpenAPI tags."""

from __future__ import annotations

API_TITLE = "API-X"
API_VERSION = "0.1.0"
API_DESCRIPTION = """\
API manajemen event dan pendaftaran peserta.

## Cara Menggunakan

1. **Register** — `POST /auth/register` untuk membuat akun baru.
2. **Login** — `POST /auth/login` untuk mendapatkan JWT token.
3. **Authorize** — Klik tombol **Authorize** di kanan atas, masukkan token dengan format `Bearer <token>`.
4. Setelah diotorisasi, endpoint yang memerlukan autentikasi dapat langsung dicoba melalui "Try it out".

## Tag Domain

| Tag | Deskripsi |
|-----|-----------|
| `auth` | Registrasi, login, dan profil pengguna |
| `admin` | Manajemen pengguna (khusus admin) |
| `admin-events` | CRUD event (khusus admin) |
| `events` | Daftar dan detail event (publik) |
| `registrations` | Pendaftaran dan pembatalan event (memerlukan token) |
| `admin-reporting` | Laporan statistik event (khusus admin) |
"""

OPENAPI_TAGS: list[dict] = [
    {
        "name": "auth",
        "description": (
            "Endpoint autentikasi: registrasi akun baru, login untuk mendapatkan JWT token, "
            "dan mendapatkan profil pengguna yang sedang login."
        ),
    },
    {
        "name": "admin",
        "description": (
            "Endpoint manajemen pengguna khusus admin: melihat daftar semua pengguna terdaftar."
        ),
    },
    {
        "name": "admin-events",
        "description": (
            "Endpoint CRUD event khusus admin: membuat, melihat detail, memperbarui, "
            "dan menghapus event."
        ),
    },
    {
        "name": "events",
        "description": (
            "Endpoint publik untuk menelusuri event: melihat daftar event aktif "
            "dengan pagination dan mendapatkan detail event tertentu."
        ),
    },
    {
        "name": "registrations",
        "description": (
            "Endpoint pendaftaran event: mendaftar ke event, membatalkan pendaftaran, "
            "dan melihat daftar pendaftaran pengguna yang sedang login."
        ),
    },
    {
        "name": "admin-reporting",
        "description": (
            "Endpoint laporan statistik khusus admin: statistik peserta per event aktif "
            "dan ringkasan jumlah event aktif."
        ),
    },
]
