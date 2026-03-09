# Spesifikasi Fitur: Dokumentasi API dengan Swagger

**Feature Branch**: `[005-swagger-api-docs]`  
**Dibuat**: 2026-03-09  
**Status**: Draft  
**Input**: Deskripsi pengguna: "Dokumentasi API menggunakan Swagger. Buatkan dokumentasi API Swagger ini secara detail, terperinci, dan mudah dipahami pembaca."

---

## Latar Belakang

API-X adalah backend berbasis FastAPI yang menyediakan empat kelompok fungsionalitas utama: Authentication, Event Management, Event Registration, dan Admin Reporting. Saat ini dokumentasi yang tersedia di Swagger UI masih minimal — judul generik, tidak ada deskripsi endpoint, tidak ada contoh request/response, dan tidak ada panduan cara autentikasi.

Fitur ini bertujuan mengubah Swagger UI menjadi dokumentasi API kelas pertama yang lengkap, interaktif, dan mudah dipahami oleh developer consumer (pembaca baru, integrator pihak ketiga, maupun tim QA), sehingga mereka dapat memahami dan mencoba setiap endpoint tanpa harus membaca kode sumber.

---

## Clarifications

### Session 2026-03-09

- Q: Versi OpenAPI Specification yang ditargetkan dokumentasi ini — OpenAPI 3.1.0, 3.0.3, atau tidak ditentukan? → A: OpenAPI 3.1.0 (default FastAPI modern, kompatibel penuh JSON Schema 2020-12, tidak perlu konfigurasi tambahan).
- Q: Apakah Swagger UI (`/docs`) dan `/openapi.json` harus dinonaktifkan di lingkungan production? → A: Aktif di semua environment (development, staging, production); keamanan endpoint dijaga oleh mekanisme autentikasi/otorisasi yang sudah ada, tidak ada logika environment-aware untuk menonaktifkan Swagger UI.
- Q: Nama parameter pagination canonical untuk endpoint yang mengembalikan daftar (`GET /events`, `GET /reports/events`) — `page`+`size`, `skip`+`limit`, atau lainnya? → A: `page` + `size`; default `page=1`, `size=20`, maksimum `size=100`.
- Q: Apakah respons sukses endpoint yang mengembalikan daftar perlu menyertakan metadata pagination di body respons, atau cukup berupa array biasa? → A: Envelope dengan metadata — response body berupa objek `{ "data": [...], "total": N, "page": X, "size": Y }` sehingga client tahu total item dan dapat menghitung total halaman.
- Q: Apakah label peran akses di deskripsi endpoint Swagger UI harus konsisten dalam Bahasa Indonesia atau Bahasa Inggris? → A: Bahasa Indonesia konsisten — semua label akses ditulis dalam Bahasa Indonesia: "Publik", "Memerlukan token", "Khusus admin".

---

## User Scenarios & Testing *(wajib)*

### User Story 1 — Developer baru memahami API melalui Swagger UI (Prioritas: P1)

Seorang developer yang baru bergabung ingin memahami endpoint apa saja yang disediakan API-X. Ia membuka URL Swagger UI di browser. Ia melihat halaman dokumentasi yang menampilkan nama API, versi, deskripsi singkat tujuan API, dan daftar endpoint yang dikelompokkan berdasarkan domain (Auth, Events, Registrations, Reports). Setiap endpoint memiliki ringkasan satu kalimat yang menjelaskan fungsinya. Tanpa harus membaca kode, developer tersebut sudah memahami gambaran besar API.

**Alasan prioritas ini**: Pemahaman awal adalah fondasi semua interaksi berikutnya. Jika halaman pembuka sudah jelas, developer lebih cepat produktif dan risiko miskomunikasi berkurang.

**Independent Test**: Dapat diuji secara mandiri dengan membuka Swagger UI dan memverifikasi bahwa: (1) ada judul, versi, dan deskripsi API; (2) semua endpoint terkelompok dalam tag domain; (3) setiap endpoint memiliki ringkasan satu kalimat.

**Acceptance Scenarios**:

1. **Given** Swagger UI dapat diakses, **When** developer membuka halaman dokumentasi, **Then** sistem menampilkan judul API, nomor versi, dan deskripsi singkat tujuan API beserta cara autentikasi.
2. **Given** Swagger UI dapat diakses, **When** developer melihat daftar endpoint, **Then** semua endpoint dikelompokkan dalam tag domain (Auth, Events, Registrations, Reports) dan setiap endpoint memiliki ringkasan satu kalimat yang menjelaskan fungsinya dalam bahasa yang mudah dipahami.
3. **Given** Swagger UI dapat diakses, **When** developer melihat ringkasan sebuah endpoint yang membutuhkan hak akses admin, **Then** terdapat penanda atau keterangan eksplisit bahwa endpoint tersebut hanya dapat diakses oleh admin.

---

### User Story 2 — Developer menggunakan Swagger UI untuk bereksperimen secara interaktif (Prioritas: P1)

Seorang developer ingin mencoba memanggil endpoint secara langsung dari Swagger UI tanpa menulis kode. Ia menemukan endpoint `POST /auth/login`, melihat contoh request body (`email` dan `password`) yang sudah terisi, lalu menekan tombol "Try it out" dan "Execute". Sistem mengembalikan JWT token. Developer kemudian menggunakan token tersebut dengan tombol "Authorize" untuk mengakses endpoint terproteksi lainnya, semuanya langsung dari Swagger UI.

**Alasan prioritas ini**: Kemampuan try it out adalah keunggulan utama Swagger dibanding dokumentasi statis — developer bisa memvalidasi pemahaman mereka secara instan.

**Independent Test**: Dapat diuji secara mandiri dengan: (1) memanggil `POST /auth/login` via Swagger UI menggunakan contoh yang disediakan dan memverifikasi token diterima; (2) memasukkan token ke fitur Authorize; (3) memanggil satu endpoint terproteksi dan memverifikasi respons sukses.

**Acceptance Scenarios**:

1. **Given** developer membuka detail endpoint `POST /auth/login` di Swagger UI, **When** ia menggunakan fitur "Try it out", **Then** tersedia contoh request body yang sudah terisi dengan data dummy yang valid sehingga dapat langsung dieksekusi.
2. **Given** developer telah mendapatkan JWT token dari hasil login, **When** ia memasukkan token melalui tombol "Authorize" di Swagger UI, **Then** semua endpoint terproteksi selanjutnya dapat diakses menggunakan token tersebut tanpa konfigurasi tambahan.
3. **Given** developer mencoba memanggil endpoint terproteksi tanpa memasukkan token terlebih dahulu, **When** ia mengeksekusi request, **Then** Swagger UI menampilkan respons 401 dengan body error envelope yang konsisten sesuai spesifikasi.

---

### User Story 3 — Developer memahami request dan response setiap endpoint secara detail (Prioritas: P1)

Seorang developer ingin mengetahui field apa saja yang wajib dikirim ke sebuah endpoint, apa artinya masing-masing field, dan apa yang dikembalikan oleh endpoint tersebut. Ia membuka detail endpoint `POST /events` di Swagger UI. Ia melihat schema request body lengkap dengan nama field, tipe data, apakah wajib atau opsional, deskripsi per field, dan contoh nilai. Ia juga melihat daftar kemungkinan kode respons (201 Created, 400, 401, 403, 422) beserta contoh body JSON untuk masing-masing kasus.

**Alasan prioritas ini**: Pemahaman detail request/response mencegah bug integrasi — developer tahu persis apa yang harus dikirim dan apa yang akan diterima.

**Independent Test**: Dapat diuji dengan membuka detail endpoint mana pun dan memverifikasi: (1) setiap field pada request body memiliki deskripsi dan contoh; (2) setiap kemungkinan kode respons terdaftar; (3) setiap kode respons memiliki contoh body JSON.

**Acceptance Scenarios**:

1. **Given** developer membuka detail sebuah endpoint yang memiliki request body, **When** ia melihat schema request body, **Then** setiap field ditampilkan dengan: nama field, tipe data, status wajib/opsional, deskripsi singkat, dan contoh nilai yang realistis.
2. **Given** developer membuka detail sebuah endpoint, **When** ia menelusuri bagian "Responses", **Then** setiap kemungkinan kode HTTP yang dapat dikembalikan endpoint tersebut terdaftar (misal 200, 201, 400, 401, 403, 404, 422) beserta deskripsi kondisi yang memicunya.
3. **Given** developer ingin tahu format error, **When** ia melihat respons error pada suatu endpoint, **Then** terdapat contoh body JSON yang menunjukkan struktur error envelope (`{ "error": { "code", "message", "httpStatus" } }`) dengan nilai konkret yang sesuai konteks error tersebut.

---

### User Story 4 — Developer memahami alur autentikasi dari dokumentasi (Prioritas: P2)

Seorang developer yang belum pernah menggunakan API ini ingin tahu cara melakukan autentikasi. Ia membaca bagian deskripsi di halaman Swagger UI dan menemukan penjelasan langkah demi langkah: (1) daftarkan akun via `POST /auth/register`; (2) login via `POST /auth/login` untuk mendapatkan JWT; (3) masukkan token ke header `Authorization: Bearer <token>` atau gunakan tombol "Authorize" di Swagger UI; (4) akses endpoint terproteksi. Tidak ada asumsi yang perlu dibuat karena alurnya sudah dijelaskan secara eksplisit.

**Alasan prioritas ini**: Alur autentikasi adalah hambatan pertama bagi setiap developer baru — jika tidak terdokumentasi, mereka akan stuck di langkah paling dasar sebelum bisa menjelajahi fitur lain.

**Independent Test**: Dapat diuji dengan memberikan dokumentasi ke developer yang belum kenal API ini dan memverifikasi bahwa ia dapat berhasil mendapatkan token dan mengakses endpoint terproteksi hanya berdasarkan dokumentasi tanpa bantuan tambahan.

**Acceptance Scenarios**:

1. **Given** developer pertama kali membuka Swagger UI, **When** ia membaca bagian deskripsi API, **Then** terdapat penjelasan singkat cara mendapatkan token (register → login → copy token → Authorize) dalam bahasa yang tidak memerlukan pengetahuan teknis mendalam.
2. **Given** developer melihat detail endpoint yang membutuhkan autentikasi, **When** ia melihat bagian metadata endpoint tersebut, **Then** terdapat indikator atau ikon kunci (lock) yang menandakan endpoint tersebut memerlukan Bearer token.
3. **Given** developer melihat definisi security scheme di Swagger UI, **When** ia membuka detail skema tersebut, **Then** terdapat penjelasan bahwa token diperoleh dari `POST /auth/login` dan cara menggunakannya di header `Authorization`.

---

### User Story 5 — Admin memahami endpoint khusus admin (Prioritas: P2)

Seorang admin atau developer yang ingin menggunakan fitur admin ingin tahu endpoint mana saja yang khusus untuk admin dan apa yang bisa dilakukan. Ia membuka Swagger UI dan menemukan bahwa endpoint-endpoint admin (manajemen event, laporan statistik) sudah diberi label atau keterangan "Requires admin role". Informasi ini membantu developer mempersiapkan kredensial admin yang sesuai sebelum mencoba endpoint tersebut.

**Alasan prioritas ini**: Kejelasan tentang hak akses mencegah percobaan yang sia-sia dan membantu developer mempersiapkan environment yang benar sejak awal.

**Independent Test**: Dapat diuji dengan memverifikasi bahwa setiap endpoint admin memiliki keterangan eksplisit tentang kebutuhan role admin, baik di ringkasan maupun di bagian detail deskripsi endpoint.

**Acceptance Scenarios**:

1. **Given** developer membuka daftar endpoint di Swagger UI, **When** ia melihat endpoint `POST /events` (create event, admin only), **Then** terdapat keterangan eksplisit — baik di ringkasan, deskripsi, atau tag — bahwa endpoint ini memerlukan akun dengan role admin.
2. **Given** developer menggunakan token user biasa (non-admin) untuk memanggil endpoint admin-only via Swagger UI, **When** ia mengeksekusi request, **Then** Swagger UI menampilkan respons 403 Forbidden dengan body error envelope yang menjelaskan bahwa permission tidak mencukupi.

---

### Edge Cases

- Endpoint yang memiliki parameter path (misal `GET /events/{event_id}`): parameter `event_id` harus memiliki deskripsi, tipe data, dan contoh nilai sehingga developer tahu format apa yang harus diisi.
- Field yang bersifat opsional vs wajib harus dibedakan secara eksplisit di schema — kesalahan di sini dapat menyebabkan developer mengirim request yang salah.
- Endpoint yang mengembalikan daftar dengan pagination (`GET /events` dan `GET /admin/reports/events/stats`): parameter `page` (integer, ≥1, default=1) dan `page_size` (integer, 1–100, default=20) harus terdokumentasi secara eksplisit di Swagger UI beserta nilai default dan batas maksimumnya.
- Kode error seperti 422 Unprocessable Entity (validation error) harus mencantumkan contoh format body yang dikembalikan FastAPI/sistem, bukan hanya kode HTTP-nya.
- Perubahan pada kode sumber yang menambah atau mengubah endpoint harus secara otomatis tercermin di Swagger UI tanpa perlu pembaruan dokumentasi manual terpisah — ini memastikan dokumentasi tidak pernah out-of-sync dengan implementasi.

---

## Requirements *(wajib)*

### Functional Requirements

- **FR-001**: Swagger UI HARUS dapat diakses melalui URL yang jelas dan terdokumentasi (misal `/docs`) tanpa memerlukan autentikasi untuk membuka halamannya.

- **FR-002**: Halaman utama Swagger UI HARUS menampilkan informasi header API yang lengkap, meliputi: (1) nama/judul API, (2) nomor versi, (3) deskripsi singkat tujuan dan cakupan API, (4) penjelasan cara mendapatkan dan menggunakan Bearer token untuk autentikasi.

- **FR-003**: Semua endpoint HARUS dikelompokkan dalam tag domain berdasarkan fungsionalitasnya, mencakup enam tag yang sesuai dengan struktur router aktual: `auth` (registrasi dan login), `admin` (manajemen pengguna oleh admin), `admin-events` (manajemen event oleh admin), `events` (penjelajahan event publik), `registrations` (pendaftaran peserta ke event), dan `admin-reporting` (laporan statistik, khusus admin).

- **FR-004**: Setiap tag domain HARUS memiliki deskripsi singkat yang menjelaskan ruang lingkup dan tujuan kelompok endpoint tersebut.

- **FR-005**: Setiap endpoint HARUS memiliki ringkasan (summary) satu kalimat yang menjelaskan apa yang dilakukan endpoint tersebut dalam bahasa yang mudah dipahami oleh non-developer sekalipun. Ringkasan ditulis dalam Bahasa Indonesia.

- **FR-006**: Setiap endpoint HARUS memiliki deskripsi (description) yang lebih panjang dari summary, menjelaskan: (1) tujuan dan konteks bisnis endpoint, (2) siapa yang berhak mengaksesnya menggunakan label Bahasa Indonesia — "Publik" (tanpa token), "Memerlukan token" (user terdaftar), atau "Khusus admin" (role admin), (3) aturan bisnis atau batasan penting yang berlaku.

- **FR-007**: Setiap field pada request body HARUS terdokumentasi dengan: (1) nama field, (2) tipe data, (3) status wajib atau opsional, (4) deskripsi singkat makna field, (5) contoh nilai yang realistis, (6) batasan nilai jika ada (misal panjang minimum/maksimum, format email, nilai enum).

- **FR-008**: Setiap endpoint yang menerima parameter path atau query HARUS mendokumentasikan setiap parameter dengan: (1) nama, (2) tipe data, (3) deskripsi, (4) apakah wajib atau opsional, (5) nilai default jika ada, (6) contoh nilai. Untuk endpoint yang mengembalikan daftar dengan pagination (`GET /events` dan `GET /admin/reports/events/stats`), parameter `page` (integer, ≥1, default=1) dan `page_size` (integer, 1–100, default=20) HARUS terdokumentasi secara eksplisit beserta constraint dan nilai defaultnya.

- **FR-009**: Setiap endpoint HARUS mendaftarkan semua kemungkinan kode respons HTTP yang dapat dikembalikannya, beserta deskripsi kondisi yang memicunya (misal "200 OK — Login berhasil, token dikembalikan", "401 Unauthorized — Kredensial tidak valid").

- **FR-010**: Setiap kode respons pada setiap endpoint HARUS menyertakan contoh body JSON yang lengkap dan realistis — baik untuk respons sukses maupun untuk setiap jenis error yang mungkin terjadi. Untuk endpoint yang mengembalikan daftar (`GET /events` dan `GET /admin/reports/events/stats`), contoh respons sukses HARUS menggunakan format envelope sesuai schema aktual masing-masing — bukan array langsung: `GET /events` menggunakan `Page[EventResponse]` dengan field `{ "items": [...], "total_items": N, "page": X, "page_size": Y, "total_pages": Z }`; `GET /admin/reports/events/stats` menggunakan `EventStatsPage` dengan field `{ "items": [...], "total": N, "page": X, "size": Y, "pages": Z }`.

- **FR-011**: Semua error response HARUS menggunakan contoh body yang mengikuti struktur error envelope standar: `{ "error": { "code": "<KODE_ERROR>", "message": "<pesan>", "httpStatus": <angka> } }`, dengan nilai `code` yang spesifik per jenis error (misal `UNAUTHORIZED`, `NOT_FOUND`, `QUOTA_FULL`, `VALIDATION_ERROR`).

- **FR-012**: Swagger UI HARUS menampilkan dan mendukung tombol "Authorize" yang memungkinkan developer memasukkan Bearer token secara global, sehingga semua endpoint terproteksi dapat dipanggil langsung dari UI tanpa konfigurasi per-request.

- **FR-013**: Security scheme `BearerAuth` (HTTP Bearer JWT) HARUS terdefinisi dan terdokumentasi di Swagger UI, termasuk penjelasan cara mendapatkan token (dari endpoint `POST /auth/login`) dan format pengirimannya (`Authorization: Bearer <token>`).

- **FR-014**: Setiap endpoint yang memerlukan autentikasi HARUS ditandai secara eksplisit di Swagger UI dengan ikon atau keterangan yang menunjukkan bahwa Bearer token diperlukan.

- **FR-015**: Setiap endpoint yang hanya dapat diakses oleh admin HARUS memiliki keterangan eksplisit di deskripsinya menggunakan label **"Khusus admin"** (Bahasa Indonesia) sehingga developer yang menggunakan token user biasa dapat memahami mengapa mereka mendapat respons 403.

- **FR-016**: Dokumentasi HARUS dihasilkan secara otomatis dari kode sumber (code-first approach) sehingga perubahan pada endpoint, schema, atau validasi di kode secara langsung tercermin di Swagger UI tanpa pembaruan dokumentasi manual terpisah.

- **FR-017**: Semua schema request dan response yang digunakan oleh lebih dari satu endpoint HARUS didefinisikan sebagai reusable component di bagian `components/schemas` sehingga tidak ada duplikasi definisi schema.

- **FR-018**: Endpoint publik dan endpoint terproteksi HARUS dapat dibedakan secara visual di Swagger UI — endpoint yang memerlukan autentikasi menampilkan ikon kunci (lock) tertutup, sedangkan endpoint publik tidak.

### Non-Functional Requirements

- **NFR-001**: Swagger UI (`/docs`) dan endpoint skema OpenAPI (`/openapi.json`) HARUS aktif dan dapat diakses di semua environment (development, staging, production) — tidak ada logika environment-aware untuk menonaktifkannya. Keamanan data dijamin oleh mekanisme autentikasi/otorisasi pada endpoint individual, bukan dengan menyembunyikan dokumentasi.

### Key Entities

- **Tag**: Label pengelompokan endpoint berdasarkan domain fungsional. Setiap tag memiliki nama dan deskripsi yang menggambarkan kelompok endpoint yang dinaunginya.
- **Endpoint Operation**: Kombinasi metode HTTP dan path yang mendefinisikan satu operasi API. Setiap operasi memiliki summary, description, parameter, request body, dan daftar respons.
- **Schema**: Definisi struktur data (request body atau response body) yang dapat bersifat reusable. Schema mendefinisikan field, tipe data, constraint, dan contoh nilai.
- **Paginated Response Envelope**: Ada dua schema pagination yang digunakan (berbeda implementasi, unifikasi di luar scope fitur ini):
  - `Page[EventResponse]` — digunakan oleh `GET /events`: `{ "items": [...], "total_items": <total>, "page": <halaman>, "page_size": <ukuran halaman>, "total_pages": <total halaman> }`
  - `EventStatsPage` — digunakan oleh `GET /admin/reports/events/stats`: `{ "items": [...], "total": <total>, "page": <halaman>, "size": <ukuran halaman>, "pages": <total halaman> }`
- **Security Scheme**: Definisi mekanisme autentikasi yang digunakan API. Pada API-X, satu-satunya security scheme adalah BearerAuth (HTTP Bearer JWT).
- **Response Example**: Contoh konten JSON konkret untuk setiap kode respons yang dikembalikan oleh endpoint, digunakan untuk memudahkan developer memahami format output.
- **Error Envelope**: Struktur JSON standar untuk semua respons error: `{ "error": { "code": string, "message": string, "httpStatus": number } }`. Konsisten di semua endpoint.

---

## Cakupan Endpoint yang Harus Terdokumentasi

Dokumentasi Swagger HARUS mencakup seluruh 15 endpoint berikut dengan kelengkapan yang didefinisikan di Requirements:

### Tag: `auth` — Autentikasi dan Otorisasi

| Method | Path | Akses | Ringkasan |
|--------|------|-------|-----------|
| POST | `/auth/register` | Publik | Mendaftarkan akun pengguna baru |
| POST | `/auth/login` | Publik | Login dan mendapatkan JWT access token |
| GET | `/auth/me` | Memerlukan token | Melihat profil pengguna yang sedang login |

### Tag: `admin` — Manajemen Pengguna

| Method | Path | Akses | Ringkasan |
|--------|------|-------|-----------|
| GET | `/admin/users` | Khusus admin | Mendapatkan daftar semua pengguna terdaftar |

### Tag: `admin-events` — Manajemen Event (Admin)

| Method | Path | Akses | Ringkasan |
|--------|------|-------|-----------|
| POST | `/admin/events` | Khusus admin | Membuat event baru |
| GET | `/admin/events/{event_id}` | Khusus admin | Mendapatkan detail satu event (tampilan admin) |
| PUT | `/admin/events/{event_id}` | Khusus admin | Memperbarui informasi event |
| DELETE | `/admin/events/{event_id}` | Khusus admin | Menghapus event |

### Tag: `events` — Penjelajahan Event Publik

| Method | Path | Akses | Ringkasan |
|--------|------|-------|-----------|
| GET | `/events` | Publik | Mendapatkan daftar event yang tersedia |
| GET | `/events/{event_id}` | Publik | Mendapatkan detail satu event |

### Tag: `registrations` — Pendaftaran Peserta

| Method | Path | Akses | Ringkasan |
|--------|------|-------|-----------|
| POST | `/registrations/{event_id}` | Memerlukan token | Mendaftar ke sebuah event |
| DELETE | `/registrations/{event_id}` | Memerlukan token | Membatalkan pendaftaran dari sebuah event |
| GET | `/registrations/me` | Memerlukan token | Melihat daftar event yang sudah didaftarkan |

### Tag: `admin-reporting` — Laporan Admin

| Method | Path | Akses | Ringkasan |
|--------|------|-------|-----------|
| GET | `/admin/reports/events/stats` | Khusus admin | Mendapatkan statistik peserta per event aktif |
| GET | `/admin/reports/events/summary` | Khusus admin | Mendapatkan ringkasan jumlah event aktif |

---

## Success Criteria *(wajib)*

### Measurable Outcomes

- **SC-001**: 100% endpoint yang terdaftar pada bagian "Cakupan Endpoint" di atas tercantum di Swagger UI dengan summary, description, dan contoh response yang sesuai — dapat diverifikasi dengan membuka dan menelusuri setiap endpoint secara manual atau melalui snapshot test terhadap output `/openapi.json`.

- **SC-002** *(Manual pre-release gate — tidak dapat diotomatisasi di CI)*: Developer baru yang tidak pernah menggunakan API-X sebelumnya mampu berhasil mendapatkan JWT token dan memanggil setidaknya satu endpoint terproteksi hanya dengan membaca Swagger UI, tanpa bantuan eksternal, dalam waktu tidak lebih dari 10 menit. Verifikasi: uji keterbacaan manual oleh seorang developer fresh sebelum rilis (lihat T029). **Proxy otomatis di CI**: semua acceptance scenario US4 lulus — `test_bearer_auth_scheme_defined` dan `test_protected_operations_have_security` di `tests/unit/test_openapi_schema.py`.

- **SC-003**: 100% field pada request body di setiap endpoint memiliki deskripsi dan contoh nilai — dapat diverifikasi dengan mengambil output `/openapi.json` dan memeriksa bahwa tidak ada field schema yang tidak memiliki properti `description` dan `example`.

- **SC-004**: 100% endpoint yang memerlukan autentikasi memiliki konfigurasi security scheme yang terpasang — dapat diverifikasi dengan memeriksa output `/openapi.json` dan memastikan setiap operasi yang terproteksi memiliki entri `security: [{ BearerAuth: [] }]`.

- **SC-005**: Tidak ada ketidaksesuaian antara schema yang terdokumentasi di Swagger UI dan perilaku aktual endpoint — dapat diverifikasi dengan menjalankan test suite contract yang memanggil endpoint menggunakan contoh data dari dokumentasi dan memverifikasi bahwa semua respons sesuai dengan kode dan format yang terdokumentasi.

- **SC-006**: Setiap kode respons error pada setiap endpoint menyertakan contoh body yang menggunakan struktur error envelope standar dengan nilai `code` yang spesifik — dapat diverifikasi dengan memeriksa output `/openapi.json` untuk keberadaan `examples` pada setiap respons error.

---

## Assumptions *(asumsi yang digunakan dalam spesifikasi ini)*

1. **Platform dokumentasi**: Swagger UI yang tersedia di `/docs` adalah media utama dokumentasi karena sudah terintegrasi dengan FastAPI secara bawaan. Tidak ada tooling dokumentasi eksternal yang diperlukan.

2. **Pendekatan code-first**: Dokumentasi dihasilkan dari kode sumber (anotasi, schema Pydantic, docstring) — bukan file OpenAPI YAML terpisah yang dikelola secara manual. Ini memastikan dokumentasi selalu sinkron dengan implementasi.

3. **Versi OpenAPI**: Dokumentasi HARUS menghasilkan schema OpenAPI 3.1.0 — versi default FastAPI modern yang kompatibel penuh dengan JSON Schema 2020-12. Tidak diperlukan konfigurasi downgrade ke OpenAPI 3.0.x.

4. **Bahasa dokumentasi**: Semua deskripsi, ringkasan, dan label akses di Swagger UI ditulis dalam Bahasa Indonesia secara konsisten. Label akses standar yang digunakan: **"Publik"** (endpoint tanpa autentikasi), **"Memerlukan token"** (endpoint yang memerlukan Bearer token user terdaftar), **"Khusus admin"** (endpoint yang hanya dapat diakses role admin). Istilah teknis yang tidak memiliki padanan Indonesia yang umum (misal "Bearer token", "JWT", "endpoint") tetap menggunakan istilah Inggris.

5. **Ketersediaan Swagger UI di semua environment**: Swagger UI (`/docs`) dan `/openapi.json` aktif di semua environment tanpa pembatasan berbasis environment variable. Tidak diperlukan logika kondisional untuk menonaktifkan Swagger di production — keamanan resource dijamin oleh autentikasi Bearer pada masing-masing endpoint.

6. **Autentikasi Swagger UI sendiri**: Swagger UI di `/docs` dapat diakses secara publik tanpa login — autentikasi hanya diperlukan saat memanggil endpoint individual yang memang membutuhkannya.

7. **Daftar endpoint**: Daftar endpoint pada bagian "Cakupan Endpoint" didasarkan pada router yang sudah diimplementasikan (auth, events, registrations, reports). Jika ada endpoint yang belum diimplementasikan saat fitur ini dikerjakan, endpoint tersebut tidak perlu didokumentasikan.

8. **ReDoc**: Selain Swagger UI di `/docs`, FastAPI secara bawaan juga menyediakan ReDoc di `/redoc`. Spesifikasi ini tidak mengatur tampilan ReDoc secara khusus; kualitas ReDoc bergantung pada kualitas metadata yang sama yang digunakan Swagger UI.
