# Spesifikasi Fitur: Authentication and Authorization

**Feature Branch**: `[001-authentication]`  
**Dibuat**: 2026-03-04  
**Status**: Draft  
**Input**: Deskripsi pengguna: "Authentication system dengan JWT dan role based access"

## Clarifications

### Session 2026-03-05

- Q: Seperti apa skema tepat error JSON yang "konsisten" untuk semua kasus error autentikasi/otorisasi? → A: Gunakan struktur `{ "error": { "code": string, "message": string, "httpStatus": number } }` di seluruh endpoint.
- Q: HTTP status code apa yang harus digunakan untuk login gagal, request tanpa token, token invalid/kedaluwarsa, akses endpoint admin-only oleh user ber-role `user`, dan registrasi dengan email yang sudah digunakan? → A: Login salah, request tanpa token, token invalid atau kedaluwarsa → 401; akses endpoint admin-only oleh user ber-role `user` → 403; registrasi dengan email yang sudah digunakan → 409.
- Q: Melalui header apa dan dengan format apa JWT HARUS dikirim untuk mengakses endpoint terproteksi? → A: JWT HARUS dikirim melalui header HTTP `Authorization` dengan skema `Bearer`, dengan format `Authorization: Bearer <token>`.
- Q: Algoritma signing apa yang HARUS digunakan untuk JWT dan claim minimum apa saja yang wajib ada di dalam token? → A: JWT HARUS ditandatangani dengan algoritma HS256 (shared secret) dan minimal memuat claim `sub` (identifier user unik), `role`, `iat`, dan `exp`.
- Q: Berapa nilai default expiration time untuk JWT access token yang diharapkan pada fitur ini? → A: JWT access token HARUS memiliki expiration time default 60 menit (1 jam) sejak waktu penerbitan, kecuali dikonfigurasi lain melalui pengaturan environment.

## User Scenarios & Testing *(wajib)*

### User Story 1 - Registrasi user baru (Prioritas: P1)

Pengguna baru ingin membuat akun dengan mengisi nama, email, dan password. Jika email belum pernah digunakan, sistem membuat akun baru, menyimpan password dalam bentuk hash bcrypt (bukan plain text), dan mengonfirmasi bahwa registrasi berhasil. Jika email sudah terdaftar, sistem menolak registrasi dengan pesan error yang jelas.

**Alasan prioritas ini**: Tanpa alur registrasi yang aman dan validasi email unik, tidak ada basis identitas yang dapat digunakan untuk autentikasi berikutnya.

**Independent Test**: Story ini dapat diuji dengan mencoba registrasi menggunakan email baru (berhasil dan password tersimpan sebagai hash bcrypt), lalu mencoba registrasi ulang dengan email yang sama (ditolak dengan error yang konsisten dalam format JSON).

**Acceptance Scenarios**:

1. **Given** pengguna belum memiliki akun dengan email tertentu, **When** ia mengirimkan permintaan registrasi dengan name, email, dan password yang valid, **Then** sistem membuat akun baru, menyimpan password dalam bentuk hash bcrypt, dan mengembalikan respons sukses.
2. **Given** sudah ada akun dengan email tertentu, **When** ada permintaan registrasi baru menggunakan email yang sama, **Then** sistem menolak registrasi dan mengembalikan error dalam format JSON yang konsisten yang menjelaskan bahwa email sudah digunakan.

---

### User Story 2 - Login dan akses endpoint terproteksi sebagai user (Prioritas: P1)

Pengguna yang sudah terdaftar melakukan login menggunakan email dan password. Jika kombinasi kredensial benar, sistem mengembalikan JWT access token. Untuk mengakses endpoint terproteksi sebagai user (misalnya melihat profil sendiri), pengguna harus mengirimkan token tersebut. Request dengan token valid dan belum kedaluwarsa akan berhasil; request tanpa token, dengan token tidak valid, atau dengan kredensial login yang salah akan ditolak dengan HTTP status code standar dan error JSON yang konsisten.

**Alasan prioritas ini**: Login dan penggunaan JWT adalah inti dari mekanisme autentikasi; tanpa ini, endpoint terproteksi tidak dapat diakses dengan aman.

**Independent Test**: Story ini dapat diuji dengan melakukan registrasi user, login menggunakan email dan password, memverifikasi bahwa sistem mengembalikan JWT, lalu memanggil endpoint terproteksi dengan dan tanpa token untuk melihat perbedaan hasil.

**Acceptance Scenarios**:

1. **Given** pengguna terdaftar dengan email dan password yang benar, **When** ia melakukan login dengan kredensial tersebut, **Then** sistem mengembalikan JWT access token dalam respons JSON.
2. **Given** request ke endpoint terproteksi tanpa header otorisasi yang berisi JWT atau dengan token yang rusak/kedaluwarsa, **When** request diproses, **Then** sistem menolak request dengan HTTP status code standar (misalnya unauthorized/forbidden) dan body error JSON yang konsisten.

---

### User Story 3 - Akses endpoint khusus admin (Prioritas: P2)

Sistem memiliki dua role: user dan admin. Admin dapat mengakses endpoint tertentu (misalnya manajemen user atau konfigurasi), sedangkan user biasa tidak boleh mengaksesnya. Ketika admin login, JWT yang diterbitkan memuat informasi role admin sehingga endpoint dapat memverifikasi hak akses. Jika user biasa mencoba mengakses endpoint khusus admin, sistem menolak dengan error otorisasi.

**Alasan prioritas ini**: Pemisahan hak akses antara admin dan user adalah inti dari authorization dan diperlukan untuk menjaga keamanan fitur-fitur sensitif.

**Independent Test**: Story ini dapat diuji dengan membuat satu akun ber-role admin dan satu akun ber-role user, melakukan login untuk masing-masing, lalu memanggil endpoint admin-only dengan kedua token dan memastikan hanya token admin yang diterima.

**Acceptance Scenarios**:

1. **Given** akun dengan role admin, **When** admin login dan memanggil endpoint admin-only dengan JWT yang valid, **Then** sistem mengizinkan akses dan menjalankan operasi admin.
2. **Given** akun dengan role user biasa, **When** user tersebut login dan mencoba memanggil endpoint admin-only dengan JWT-nya, **Then** sistem menolak akses dengan HTTP status code standar dan error JSON yang konsisten yang menjelaskan bahwa permission tidak mencukupi.

---

### Edge Cases

- Token secara struktur valid tetapi tanda tangan tidak cocok atau claim diubah secara manual: sistem harus menganggap token tidak valid dan menolak akses tanpa mengungkap detail teknis sensitif.
- Request ke endpoint terproteksi menggunakan token dengan role user ke endpoint yang hanya boleh diakses admin: sistem harus menolak akses dengan respons otorisasi standar.
- Token digunakan setelah melewati expiration time yang dikonfigurasi: sistem harus menolak token dan meminta user untuk login kembali.
- Percobaan login berulang dengan kredensial yang salah: sistem harus mengembalikan error yang konsisten tanpa mengungkap apakah email atau password yang salah.

## Requirements *(wajib)*

### Functional Requirements

- **FR-001**: Sistem HARUS menyediakan endpoint registrasi yang menerima name, email, dan password untuk membuat akun user baru.
- **FR-002**: Sistem HARUS memastikan email bersifat unik; permintaan registrasi dengan email yang sudah terdaftar HARUS ditolak.
- **FR-003**: Sistem HARUS melakukan hashing password menggunakan bcrypt sebelum menyimpannya dan TIDAK BOLEH menyimpan password dalam bentuk plain text.
- **FR-004**: Sistem HARUS menyediakan endpoint login yang menerima email dan password, memverifikasi keduanya terhadap data tersimpan, dan menolak login ketika kombinasi tidak valid.
- **FR-005**: Sistem HARUS mengembalikan JWT access token pada login yang berhasil, yang memuat setidaknya identifier user dan role-nya.
- **FR-006**: Sistem HARUS mewajibkan penggunaan JWT access token untuk mengakses endpoint terproteksi melalui header HTTP `Authorization` dengan skema `Bearer` (format `Authorization: Bearer <token>`).
- **FR-007**: Sistem HARUS mendukung minimal dua role: `user` dan `admin`.
- **FR-008**: Sistem HARUS membatasi akses ke endpoint tertentu hanya untuk role `admin`; permintaan dari role lain HARUS ditolak dengan error otorisasi.
- **FR-009**: Sistem HARUS menerapkan expiration time pada JWT sehingga token hanya berlaku dalam rentang waktu tertentu dan token yang kedaluwarsa HARUS ditolak. Nilai default expiration time untuk JWT access token HARUS 60 menit (1 jam) sejak waktu penerbitan, dengan kemungkinan untuk dioverride melalui konfigurasi environment.
- **FR-010**: Sistem HARUS menggunakan HTTP status code standar yang konsisten untuk semua respons autentikasi dan otorisasi. Minimal: login dengan kredensial salah, request tanpa token, token invalid atau kedaluwarsa HARUS menggunakan 401 Unauthorized; akses endpoint admin-only oleh user ber-role `user` HARUS menggunakan 403 Forbidden; registrasi dengan email yang sudah digunakan HARUS menggunakan 409 Conflict.
- **FR-011**: Sistem HARUS mengembalikan error response dalam format JSON yang konsisten dengan struktur `{"error": {"code": string, "message": string, "httpStatus": number}}`, sehingga minimal memuat kode error terstruktur, pesan yang dapat dipahami, dan HTTP status yang merefleksikan respons.
- **FR-012**: JWT access token HARUS ditandatangani menggunakan algoritma HS256 dengan shared secret yang aman dan minimal memuat claim `sub` (identifier user unik), `role`, `iat`, dan `exp`.

### Key Entities *(sertakan jika fitur melibatkan data)*

- **User**: Merepresentasikan akun individu yang dapat melakukan autentikasi. Atribut kunci meliputi identifier unik, name, email (unik), password yang sudah di-hash (bcrypt), status aktivasi, dan role.
- **Role**: Merepresentasikan kelompok permission bernama (`user` dan `admin`). Role dikaitkan dengan user dan menentukan endpoint/operator mana yang boleh diakses.
- **Auth Token (JWT)**: Merepresentasikan JWT access token yang diterbitkan saat login berhasil dan digunakan pada request ke endpoint terproteksi. Token ini mengenkapsulasi identitas user, informasi role, dan expiration time, serta dapat diverifikasi integritasnya. JWT HARUS ditandatangani menggunakan algoritma HS256 (shared secret) dan minimal memuat claim `sub` (identifier user unik), `role`, `iat`, dan `exp`.

## Success Criteria *(wajib)*

### Measurable Outcomes

- **SC-001**: Setidaknya 95% pengguna baru yang mengisi name, email, dan password yang valid dapat menyelesaikan registrasi dan login pertama kali dalam waktu kurang dari 5 detik pada beban normal.
- **SC-002**: 100% percobaan registrasi dengan email yang sudah terdaftar dalam automated test menghasilkan penolakan dengan HTTP status code standar dan error JSON yang konsisten yang menjelaskan konflik email.
- **SC-003**: 100% request ke endpoint terproteksi tanpa token, dengan token kedaluwarsa, atau dengan token yang tidak valid dalam automated test ditolak tanpa mengekspos detail teknis sensitif dalam body JSON.
- **SC-004**: 100% request ke endpoint admin-only yang dikirim dengan JWT ber-role `user` dalam automated test ditolak, sementara request dengan JWT ber-role `admin` berhasil.

## Assumptions & Dependencies

- Implementasi detail penyimpanan data (misalnya jenis database) dan pemilihan library konkret untuk bcrypt dan JWT akan ditentukan pada tahap perencanaan teknis, namun harus mendukung requirement di atas.
- Integrasi dengan sistem manajemen pengguna yang lebih luas (misalnya manajemen profil lanjutan, verifikasi email, atau pemulihan password) berada di luar cakupan fitur ini kecuali secara eksplisit ditambahkan.
- Kebijakan keamanan tambahan (misalnya kewajiban compliance atau regulasi perlindungan data) dapat memengaruhi nilai default expiration time token serta detail isi error message, dan akan dikonfirmasi dengan stakeholder keamanan.
