# Spesifikasi Fitur: Event Management

**Feature Branch**: `[002-event-management]`  
**Dibuat**: 2026-03-05  
**Status**: Draft  
**Input**: Deskripsi pengguna: "Feature: Event Management - Admin dapat membuat, mengubah, dan menghapus event publik; user dapat melihat daftar event publik dengan pagination dan hanya untuk event yang belum lewat."

## Clarifications

### Session 2026-03-05

- Q: Bagaimana perlakuan event dengan `registration_deadline` yang sudah lewat tetapi tanggal event belum lewat dalam daftar event publik untuk user biasa? → A: Event tetap ditampilkan di daftar event publik, tetapi harus ditandai jelas bahwa pendaftaran sudah ditutup (misalnya flag `registration_closed` atau status serupa) sehingga user tidak mengira masih bisa mendaftar.

- Q: Skema pagination apa yang HARUS digunakan untuk daftar event publik (parameter request dan bentuk respons dasar)? → A: Pagination menggunakan query parameter `page` (1-based, default 1) dan `page_size` (default wajar, misalnya 20, dengan batas maksimum yang ditentukan secara teknis), dan respons daftar event minimal berbentuk `{ "items": [...], "page": number, "page_size": number, "total_items": number, "total_pages": number }`.

- Q: Urutan default apa yang HARUS digunakan untuk menyusun daftar event publik saat tidak ada permintaan sort khusus dari client? → A: Daftar event publik HARUS diurutkan berdasarkan `date` secara ascending (event terdekat muncul lebih dulu), dan jika ada beberapa event dengan tanggal yang sama, diurutkan lagi berdasarkan `title` secara ascending sebagai tie-breaker yang deterministik.

- Q: Aturan validasi apa yang HARUS diberlakukan antara `registration_deadline` dan `date` saat membuat atau mengubah event? → A: Sistem TIDAK BOLEH menerima event dengan `registration_deadline` yang lebih besar dari `date`; `registration_deadline` HARUS selalu lebih kecil atau sama dengan `date`, dan kombinasi yang melanggar aturan ini HARUS ditolak dengan error yang jelas.

## User Scenarios & Testing *(wajib)*

### User Story 1 - Admin membuat event publik baru (Prioritas: P1)

Seorang admin ingin menjadwalkan event publik baru (misalnya webinar atau workshop) dengan mengisi judul, deskripsi, tanggal event, batas waktu pendaftaran, dan kuota peserta. Setelah data diisi dengan benar dan disimpan, event langsung tercatat dalam sistem dan dapat muncul di daftar event publik yang dapat dilihat oleh semua user.

**Alasan prioritas ini**: Tanpa kemampuan membuat event publik baru, tidak ada konten yang bisa dikonsumsi oleh user dan fitur manajemen event tidak memberikan nilai bisnis.

**Independent Test**: Story ini dapat diuji secara mandiri dengan memanggil alur pembuatan event satu kali dan memverifikasi bahwa event tersimpan lengkap dengan semua field yang diwajibkan serta dapat diambil kembali melalui daftar atau detail event.

**Acceptance Scenarios**:

1. **Given** admin terautentikasi dan memiliki hak akses manajemen event, **When** admin mengirimkan permintaan pembuatan event dengan `title`, `description`, `date`, `registration_deadline`, dan `quota` yang valid, **Then** sistem menyimpan event baru dan menandainya sebagai event publik.
2. **Given** event publik baru berhasil dibuat, **When** user umum mengambil daftar event publik, **Then** event yang baru dibuat tersebut muncul di daftar selama tanggal event belum lewat.

---

### User Story 2 - Admin mengelola event yang sudah memiliki peserta (Prioritas: P1)

Seorang admin ingin memperbarui informasi event yang sudah memiliki peserta terdaftar (misalnya mengubah judul, deskripsi, atau tanggal), tanpa mengganggu data peserta yang sudah ada. Admin juga boleh memperbesar kuota, tetapi bila mencoba menurunkan kuota menjadi lebih kecil dari jumlah peserta yang sudah terdaftar, sistem harus menolak perubahan tersebut dengan pesan yang jelas. Admin tetap dapat menghapus event bila sudah tidak relevan.

**Alasan prioritas ini**: Dalam praktik, detail event sering berubah (jam, deskripsi, kapasitas), sehingga kemampuan mengelola event yang sudah memiliki peserta adalah kebutuhan operasional utama.

**Independent Test**: Story ini dapat diuji dengan membuat event, menambahkan sejumlah peserta (melalui mekanisme pendaftaran yang diatur di fitur lain), lalu menguji berbagai kombinasi update (ubah informasi non-kuota, memperbesar kuota, mencoba memperkecil kuota di bawah jumlah peserta, dan menghapus event) dan memverifikasi perilaku sistem.

**Acceptance Scenarios**:

1. **Given** sebuah event publik yang sudah memiliki peserta terdaftar, **When** admin mengubah field non-kuota (misalnya `title` atau `description`) dengan data valid, **Then** sistem memperbarui event tanpa memengaruhi data peserta.
2. **Given** sebuah event publik dengan jumlah peserta saat ini `N`, **When** admin mencoba mengubah `quota` menjadi nilai yang lebih kecil dari `N`, **Then** sistem menolak perubahan tersebut dan mengembalikan pesan error yang jelas tanpa mengubah data event.
3. **Given** sebuah event publik apa pun, **When** admin mengirimkan permintaan untuk menghapus event tersebut, **Then** sistem menghapus event sehingga tidak lagi muncul di daftar event publik dan tidak dapat lagi didaftarkan oleh peserta baru.

---

### User Story 3 - User menelusuri dan melihat daftar event publik (Prioritas: P2)

Seorang user (baik yang terautentikasi maupun pengunjung dengan hak akses lihat) ingin melihat daftar event publik yang akan datang untuk memilih event yang ingin diikuti. Daftar event ditampilkan dalam bentuk halaman (pagination) agar mudah dinavigasi, dan hanya menampilkan event yang tanggalnya belum lewat. User dapat beralih halaman untuk melihat lebih banyak event dan membuka detail satu event untuk memahami informasi lengkapnya.

**Alasan prioritas ini**: Kemampuan menelusuri daftar event publik yang relevan secara efisien sangat penting untuk memastikan user dapat menemukan dan memilih event yang ingin mereka ikuti.

**Independent Test**: Story ini dapat diuji dengan menyiapkan kumpulan event publik dengan berbagai tanggal, kemudian memanggil daftar event publik dengan parameter pagination yang berbeda dan memastikan hanya event yang belum lewat yang muncul, serta bahwa navigasi antar halaman berjalan konsisten.

**Acceptance Scenarios**:

1. **Given** terdapat banyak event publik yang akan datang dan beberapa event yang sudah lewat tanggalnya, **When** user meminta daftar event publik, **Then** sistem hanya mengembalikan event dengan tanggal event yang belum lewat dan menyusun hasil dalam bentuk halaman (misalnya page 1, page 2, dst.).
2. **Given** daftar event publik dengan pagination aktif, **When** user berpindah ke halaman berikutnya atau sebelumnya, **Then** sistem mengembalikan kumpulan event publik yang sesuai dengan halaman yang diminta tanpa mengulang atau melewatkan event.
3. **Given** user melihat satu item event di daftar, **When** user membuka detail event tersebut, **Then** sistem menampilkan informasi lengkap event (judul, deskripsi, tanggal event, batas pendaftaran, dan kuota total) selama event belum lewat atau belum dihapus admin.

---

### Edge Cases

- Event dengan tanggal event sudah lewat: event tersebut tetap dapat dikelola oleh admin (misalnya untuk keperluan audit), tetapi tidak boleh muncul lagi di daftar event publik yang dilihat user biasa.
- Event dengan registration_deadline lewat tetapi tanggal event belum lewat: event tetap tidak boleh menerima peserta baru (diatur oleh fitur pendaftaran), tetap dapat ditampilkan kepada admin, dan HARUS tetap terlihat di daftar event publik sebagai event yang akan berlangsung namun dengan indikasi jelas bahwa pendaftaran sudah ditutup.
- Penghapusan event yang sudah memiliki peserta: setelah event dihapus oleh admin, user tidak boleh lagi melihat event di daftar publik atau mendaftar ke event tersebut, dan sistem harus menjaga agar data peserta tidak mengarah ke event yang sudah tidak tersedia.
- Permintaan daftar event dengan kombinasi parameter pagination yang ekstrem (misalnya page terlalu besar atau page size sangat besar): sistem harus memberikan respons yang konsisten (misalnya halaman kosong untuk page di luar jangkauan) tanpa menurunkan stabilitas.

## Requirements *(wajib)*

### Functional Requirements

- **FR-001**: Sistem HARUS menyediakan kemampuan bagi admin untuk membuat event publik baru dengan field minimal `title`, `description`, `date`, `registration_deadline`, dan `quota`.
- **FR-002**: Sistem HARUS memastikan bahwa setiap event publik yang berhasil dibuat dapat diambil kembali melalui daftar atau detail event selama event belum lewat atau belum dihapus admin.
- **FR-003**: Sistem HARUS mengizinkan admin untuk mengedit informasi event (termasuk `title`, `description`, `date`, `registration_deadline`, dan `quota`) meskipun event tersebut sudah memiliki peserta terdaftar, selama perubahan tidak melanggar aturan kuota.
- **FR-004**: Sistem TIDAK BOLEH menerima perubahan `quota` menjadi nilai yang lebih kecil daripada jumlah peserta yang sudah terdaftar; dalam kasus ini sistem HARUS menolak update dan mengembalikan pesan error yang jelas tanpa mengubah data event.
- **FR-005**: Sistem HARUS menyediakan kemampuan bagi admin untuk menghapus event publik, termasuk event yang sudah memiliki peserta, dan memastikan event yang dihapus tidak lagi muncul di daftar event publik atau dapat didaftarkan oleh peserta baru.
- **FR-006**: Sistem HARUS menyediakan cara bagi user untuk mengambil daftar event publik dalam bentuk halaman (pagination), dengan parameter yang memungkinkan penentuan halaman dan ukuran halaman dalam batas yang wajar.
- **FR-007**: Sistem HARUS memastikan bahwa daftar event publik yang ditampilkan kepada user hanya berisi event dengan tanggal event yang belum lewat pada saat permintaan dilakukan.
- **FR-008**: Sistem HARUS menyediakan tampilan atau representasi detail satu event publik yang dapat diakses oleh semua user selama event belum lewat atau belum dihapus admin.

- **FR-009**: Sistem HARUS menyertakan informasi dalam daftar dan detail event publik apakah pendaftaran masih dibuka atau sudah ditutup berdasarkan `registration_deadline`, sehingga event dengan `registration_deadline` lewat tetapi tanggal event belum lewat tetap muncul di daftar namun jelas ditandai sebagai pendaftaran ditutup.

- **FR-010**: Sistem HARUS menggunakan pola pagination berbasis query parameter `page` (1-based, default 1) dan `page_size` (default wajar, misalnya 20, dengan batas maksimum yang didefinisikan di desain teknis), dan respons daftar event publik minimal memuat `items`, `page`, `page_size`, `total_items`, dan `total_pages` untuk mendukung navigasi yang konsisten.

- **FR-011**: Sistem HARUS menggunakan urutan default daftar event publik berdasarkan `date` secara ascending (event dengan tanggal terdekat muncul lebih dulu), dan jika terdapat event dengan `date` yang sama, hasil diurutkan lagi berdasarkan `title` secara ascending untuk menjamin urutan yang deterministik tanpa pengulangan atau lompatan saat pagination.

- **FR-012**: Sistem HARUS memvalidasi bahwa `registration_deadline` untuk setiap event tidak boleh lebih besar daripada `date` event tersebut. Permintaan pembuatan atau pembaruan event dengan `registration_deadline` yang lebih besar dari `date` HARUS ditolak dengan pesan error yang jelas tanpa mengubah data event yang sudah tersimpan.

### Non-Functional Requirements

- **NFR-001**: Pengambilan daftar event publik dengan pagination HARUS tetap memberikan pengalaman responsif bagi user (misalnya user merasakan daftar muncul hampir seketika) pada skenario beban normal.
- **NFR-002**: Sistem penyimpanan data HARUS dioptimalkan sehingga query berdasarkan `date` dan `registration_deadline` tetap memiliki waktu respon yang konsisten meskipun jumlah event publik bertambah besar.

### Key Entities *(sertakan jika fitur melibatkan data)*

- **Event**: Merepresentasikan satu kegiatan publik yang dapat dilihat user. Atribut kunci meliputi identifier unik, `title`, `description`, `date`, `registration_deadline`, `quota`, status (aktif/non-aktif/dihapus), informasi jumlah peserta saat ini, serta indikasi apakah pendaftaran masih dibuka atau sudah ditutup (misalnya field turunan `registration_open`/`registration_closed`).
- **Participant/Event Registration**: Merepresentasikan hubungan antara user dan event yang diikutinya. Entitas ini menyimpan referensi ke `Event` dan ke identitas peserta, serta digunakan untuk menghitung jumlah peserta yang sedang terdaftar.

## Success Criteria *(wajib)*

### Measurable Outcomes

- **SC-001**: 100% percobaan pembuatan event publik dengan data valid dalam automated test menghasilkan event baru yang dapat muncul di daftar event publik untuk user (selama tanggal event belum lewat).
- **SC-002**: 100% percobaan mengubah `quota` menjadi nilai yang lebih kecil daripada jumlah peserta saat ini dalam automated test ditolak dengan pesan error yang jelas dan tanpa perubahan pada data event.
- **SC-003**: 100% permintaan daftar event publik yang diuji secara otomatis tidak pernah menampilkan event dengan tanggal event yang sudah lewat pada saat permintaan dilakukan.
- **SC-004**: Pada environment uji yang representatif, setidaknya 95% permintaan daftar event publik (dengan hingga ribuan event aktif) diselesaikan dalam waktu yang dirasakan user sebagai "segera" (misalnya di bawah beberapa detik) pada beban normal.

## Assumptions & Dependencies

- Alur pendaftaran peserta ke event (bagaimana peserta ditambahkan atau dibatalkan) diatur oleh fitur terpisah; fitur ini hanya mengandalkan adanya informasi jumlah peserta saat ini untuk keperluan validasi kuota.
- Zona waktu dan aturan penentuan "tanggal event sudah lewat" akan mengikuti konfigurasi global sistem (misalnya memakai timezone server atau organisasi) dan digunakan secara konsisten di seluruh fitur.
- Detil teknis terkait bentuk API, struktur database, maupun library yang digunakan untuk mengimplementasikan pagination dan optimisasi query akan ditentukan pada tahap perencanaan teknis, selama tetap memenuhi requirement yang berfokus pada perilaku di atas.
- Fitur ini bergantung pada mekanisme autentikasi dan otorisasi yang sudah didefinisikan di spesifikasi `001-authentication` untuk memastikan hanya admin yang dapat membuat, mengubah, dan menghapus event publik.