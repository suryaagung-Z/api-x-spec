# Spesifikasi Fitur: Admin Reporting

**Feature Branch**: `[004-admin-reporting]`  
**Dibuat**: 2026-03-05  
**Status**: Draft  
**Input**: Deskripsi pengguna: "Feature: Admin Reporting - Admin dapat melihat statistik peserta untuk monitoring event."

## Clarifications

### Session 2026-03-05

- Q: Apa definisi tepat "event aktif" yang digunakan dalam konteks laporan reporting — apakah hanya berdasarkan `status`, atau juga mempertimbangkan `date`? → A: "Event aktif" untuk reporting didefinisikan sebagai event dengan `status=aktif` DAN `date` belum lewat pada saat query dijalankan, konsisten dengan definisi filter daftar event publik.
- Q: Apakah `total_registered` dihitung hanya dari Event Registration berstatus `aktif`, atau juga termasuk yang berstatus `dibatalkan`? → A: `total_registered` hanya menghitung Event Registration berstatus `aktif`; record berstatus `dibatalkan` tidak ikut dihitung, konsisten dengan cara kuota dihitung di fitur Event Registration.
- Q: Apakah statistik per event dan ringkasan `total_active_events` disajikan melalui satu endpoint atau dua endpoint terpisah? → A: Dua endpoint terpisah — (1) endpoint statistik per event mengembalikan daftar event aktif dengan `total_registered` dan `remaining_quota` per event (dapat dipaginasi); (2) endpoint ringkasan mengembalikan `total_active_events` sebagai angka tunggal.
- Q: Bagaimana perilaku `remaining_quota` jika nilainya negatif (misalnya `total_registered` melebihi `quota`)? → A: `remaining_quota` ditampilkan sebagai nilai aktual (`quota - total_registered`), termasuk jika hasilnya negatif, sehingga admin dapat mendeteksi anomali data tanpa sistem menyimpan atau men-clamp nilai tersebut.
- Q: Berapa target latensi terukur untuk permintaan laporan agar SC-002 dapat dijadikan acceptance criterion yang testable? → A: ≥95% permintaan laporan (p95) HARUS diselesaikan dalam ≤2 detik dengan hingga 10.000 event aktif dan data pendaftaran proporsional pada beban normal.

## User Scenarios & Testing *(wajib)*

### User Story 1 - Admin melihat statistik peserta per event (Prioritas: P1)

Seorang admin ingin memonitor performa setiap event dengan melihat berapa banyak peserta yang sudah terdaftar dan berapa sisa kuota yang masih tersedia. Admin membuka tampilan pelaporan dan memilih daftar event aktif. Untuk setiap event, sistem menampilkan informasi jumlah peserta terdaftar (total_registered) dan sisa kuota (remaining_quota), sehingga admin dapat dengan cepat mengidentifikasi event yang sudah hampir penuh atau yang masih memiliki banyak slot kosong.

**Alasan prioritas ini**: Informasi jumlah peserta dan sisa kuota per event adalah dasar utama monitoring operasional event dan menjadi dasar pengambilan keputusan (misalnya menambah promosi atau menutup pendaftaran lebih awal).

**Independent Test**: Story ini dapat diuji secara mandiri dengan menyiapkan beberapa event aktif dengan kuota dan jumlah pendaftaran yang berbeda, lalu meminta laporan dan memverifikasi bahwa nilai total_registered dan remaining_quota yang ditampilkan sesuai dengan data pendaftaran dan konfigurasi event.

**Acceptance Scenarios**:

1. **Given** terdapat beberapa event aktif dengan peserta terdaftar dan kuota masing-masing, **When** admin meminta laporan statistik event, **Then** sistem menampilkan untuk setiap event nilai total_registered (jumlah peserta yang terdaftar) dan remaining_quota (kuota dikurangi jumlah peserta) yang konsisten dengan data sebenarnya.
2. **Given** sebuah event aktif belum memiliki peserta sama sekali, **When** admin melihat laporan statistik event, **Then** sistem menampilkan total_registered = 0 dan remaining_quota sama dengan kuota event.

---

### User Story 2 - Admin melihat ringkasan jumlah event aktif (Prioritas: P2)

Seorang admin ingin mendapatkan gambaran cepat mengenai seberapa banyak event yang sedang aktif dalam sistem. Ia membuka tampilan pelaporan dan melihat ringkasan berupa total jumlah event aktif tanpa harus memeriksa setiap event satu per satu. Informasi ini bisa digunakan untuk memantau beban operasional atau perencanaan ke depan.

**Alasan prioritas ini**: Ringkasan jumlah event aktif membantu admin memahami skala kegiatan yang sedang berjalan dan mendukung perencanaan kapasitas serta sumber daya.

**Independent Test**: Story ini dapat diuji secara mandiri dengan menyiapkan beberapa event dengan status berbeda (aktif, non-aktif, dihapus), lalu memverifikasi bahwa total event aktif yang ditampilkan hanya menghitung event yang berstatus aktif.

**Acceptance Scenarios**:

1. **Given** terdapat N event yang berstatus aktif dan beberapa event lain yang non-aktif atau dihapus, **When** admin meminta ringkasan jumlah event aktif, **Then** sistem menampilkan total event aktif = N.
2. **Given** tidak ada event yang berstatus aktif, **When** admin meminta ringkasan jumlah event aktif, **Then** sistem menampilkan total event aktif = 0 tanpa error.

---

### User Story 3 - Pembatasan akses pelaporan hanya untuk admin (Prioritas: P1)

User biasa (non-admin) tidak boleh dapat mengakses laporan statistik peserta event karena informasi ini dianggap sensitif. Ketika user biasa mencoba memanggil endpoint atau tampilan pelaporan, sistem harus menolak akses tersebut dengan cara yang konsisten dan tidak mengembalikan data statistik apa pun.

**Alasan prioritas ini**: Laporan statistik peserta termasuk informasi sensitif yang hanya relevan bagi admin dan tidak boleh dibagikan kepada user biasa demi alasan keamanan dan privasi.

**Independent Test**: Story ini dapat diuji secara mandiri dengan melakukan permintaan laporan menggunakan kredensial admin (berhasil) dan menggunakan kredensial user biasa (ditolak), serta memverifikasi bahwa user biasa tidak pernah menerima data statistik.

**Acceptance Scenarios**:

1. **Given** akun dengan role admin, **When** admin memanggil endpoint atau tampilan pelaporan, **Then** sistem mengizinkan akses dan mengembalikan data statistik sesuai definisi fitur.
2. **Given** akun dengan role user biasa, **When** user tersebut mencoba memanggil endpoint atau tampilan pelaporan, **Then** sistem menolak akses dengan respons otorisasi standar tanpa mengembalikan data statistik.

---

### Edge Cases

- Event dengan kuota 0 (misalnya event khusus undangan) tetapi memiliki peserta yang tercatat: sistem tetap harus menampilkan `total_registered` sesuai jumlah peserta aktif dan `remaining_quota` sebagai nilai aktual (`quota - total_registered`), yang dapat bernilai negatif, tanpa menyebabkan error pada laporan.
- Event yang statusnya berubah (misalnya dari aktif menjadi non-aktif atau dihapus) di saat laporan sedang diambil: sistem harus menetapkan aturan konsisten mengenai definisi "event aktif" dan hanya menghitung event yang memenuhi kriteria tersebut pada saat query dijalankan.
- Jumlah event dan pendaftaran yang sangat besar: laporan tetap harus dapat diambil tanpa waktu respon yang tidak wajar, dengan mengandalkan perhitungan agregasi yang efisien.

## Requirements *(wajib)*

### Functional Requirements

- **FR-001**: Sistem HARUS menyediakan kemampuan bagi admin untuk melihat jumlah peserta terdaftar (total_registered) untuk setiap event yang memenuhi definisi "event aktif", yaitu event dengan `status=aktif` DAN `date` belum lewat pada saat query dijalankan.
- **FR-002**: Sistem HARUS menampilkan remaining_quota untuk setiap event aktif sebagai selisih antara kuota event dan jumlah peserta yang terdaftar; definisi "event aktif" mengikuti FR-001 (`status=aktif` DAN `date` belum lewat).
- **FR-003**: Sistem HARUS menyediakan ringkasan total jumlah event aktif (`status=aktif` DAN `date` belum lewat) yang dapat dilihat admin tanpa harus menelusuri satu per satu event.
- **FR-004**: Sistem HARUS hanya mengizinkan akun dengan role admin untuk mengakses endpoint atau tampilan pelaporan ini; permintaan dari user biasa atau pihak yang tidak berotorisasi HARUS ditolak.
- **FR-005**: Sistem HARUS mengambil data statistik peserta (total_registered dan remaining_quota) berdasarkan data event dan pendaftaran peserta yang sudah ada, sehingga nilai yang ditampilkan selalu konsisten dengan sumber data utama. *(Catatan: requirement ini secara implisit dicakup oleh FR-001 dan FR-002; dipertahankan secara eksplisit untuk keterlacakan dan sebagai penegasan bahwa cache atau lapisan data terpisah tidak diperbolehkan.)*
- **FR-006**: Sistem HARUS menghitung `total_registered` hanya dari Event Registration berstatus `aktif`; record berstatus `dibatalkan` TIDAK BOLEH ikut dihitung dalam nilai `total_registered` maupun dalam perhitungan `remaining_quota`.
- **FR-007**: Sistem HARUS menyediakan dua endpoint pelaporan terpisah untuk admin: (1) endpoint statistik per event yang mengembalikan daftar event aktif dengan `total_registered` dan `remaining_quota` untuk masing-masing event, dengan dukungan pagination; (2) endpoint ringkasan yang mengembalikan `total_active_events` sebagai nilai tunggal.
- **FR-008**: Sistem HARUS menghitung dan menampilkan `remaining_quota` sebagai nilai aktual (`quota - total_registered`), termasuk jika hasilnya bernilai negatif; sistem TIDAK BOLEH men-clamp nilai ini ke 0 sehingga admin dapat mendeteksi anomali data.

### Non-Functional Requirements

- **NFR-001**: Query untuk menghasilkan laporan statistik peserta per event dan total event aktif HARUS efisien dan tidak menimbulkan pola akses N+1 yang mengakibatkan banyak query kecil berulang.
- **NFR-002**: Sistem HARUS menggunakan mekanisme agregasi data pada lapisan penyimpanan (misalnya perhitungan agregat di database) untuk menghitung jumlah peserta dan event aktif, sehingga kinerja tetap stabil meskipun jumlah data bertambah besar.

### Key Entities *(sertakan jika fitur melibatkan data)*

- **Event**: Entitas event publik yang sudah didefinisikan pada fitur Event Management, menyediakan informasi kuota, status (aktif/non-aktif/dihapus), dan atribut lain yang digunakan untuk menentukan apakah event dihitung sebagai aktif.
- **Event Registration**: Entitas yang merepresentasikan pendaftaran peserta ke event, digunakan sebagai dasar perhitungan total_registered per event.

## Success Criteria *(wajib)*

### Measurable Outcomes

- **SC-001**: 100% percobaan uji otomatis yang membandingkan nilai total_registered dan remaining_quota di laporan dengan data dasar event dan pendaftaran menunjukkan hasil yang konsisten.
- **SC-002**: Dalam skenario uji dengan hingga 10.000 event aktif dan data pendaftaran proporsional, setidaknya 95% permintaan laporan (p95) diselesaikan dalam waktu ≤ 2 detik pada beban normal.
- **SC-003**: 100% percobaan akses laporan yang dilakukan oleh user biasa (non-admin) dalam automated test ditolak dan tidak pernah mengembalikan data statistik event.

## Assumptions & Dependencies

- Definisi "event aktif" untuk fitur ini adalah event dengan `status=aktif` DAN `date` belum lewat pada saat query dijalankan, konsisten dengan filter daftar event publik di spesifikasi Event Management.
- Fitur ini bergantung pada data yang dihasilkan oleh fitur Event Management dan Event Registration, termasuk kuota event, status event, dan data pendaftaran peserta.
- Detail teknis mengenai struktur query, indeks, dan mekanisme agregasi yang digunakan untuk menghitung statistik akan ditentukan pada tahap desain teknis, selama tetap memenuhi requirement tentang efisiensi dan menghindari N+1 problem.
- Mekanisme autentikasi dan otorisasi mengikuti spesifikasi `001-authentication` untuk membedakan role admin dan user biasa.
- Nilai status yang digunakan dalam spec ini (`aktif`, `non-aktif`, `dibatalkan`) merupakan istilah fungsional; pemetaan ke nilai enum database aktual (`active`, `inactive`, `cancelled`) didefinisikan secara kanonik dalam `data-model.md`.
