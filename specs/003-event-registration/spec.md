# Spesifikasi Fitur: Event Registration

**Feature Branch**: `[003-event-registration]`  
**Dibuat**: 2026-03-05  
**Status**: Draft  
**Input**: Deskripsi pengguna: "Feature: Event Registration - User dapat mendaftar dan membatalkan pendaftaran ke event publik dengan pembatasan kuota dan batas waktu."

## User Scenarios & Testing *(wajib)*

### User Story 1 - User mendaftar ke event publik (Prioritas: P1)

Seorang user yang tertarik pada sebuah event publik ingin melakukan pendaftaran. Ia memilih salah satu event publik yang masih tersedia, lalu mengirimkan permintaan pendaftaran. Jika event ditemukan, belum melewati batas waktu pendaftaran (registration_deadline), dan kuota masih tersedia, sistem mencatat pendaftaran user tersebut sebagai peserta event dan memastikan tidak terjadi pendaftaran ganda untuk kombinasi user dan event yang sama.

**Alasan prioritas ini**: Tanpa kemampuan user untuk mendaftar ke event publik, fitur event menjadi pasif dan tidak memberikan nilai utama bagi user maupun penyelenggara.

**Independent Test**: Story ini dapat diuji secara mandiri dengan menyiapkan satu event publik yang masih dalam periode pendaftaran dan memiliki kuota cukup, lalu mengirimkan permintaan pendaftaran dari user yang belum pernah terdaftar dan memverifikasi bahwa status pendaftaran tersimpan dengan benar sebagai peserta event.

**Acceptance Scenarios**:

1. **Given** terdapat sebuah event publik yang valid, belum melewati `registration_deadline`, dan kuotanya belum penuh, **When** user yang belum terdaftar mengirimkan permintaan pendaftaran untuk event tersebut, **Then** sistem mencatat pendaftaran baru dan menambah jumlah peserta event.
2. **Given** user telah terdaftar pada suatu event publik, **When** user mencoba mendaftar lagi ke event yang sama, **Then** sistem menolak pendaftaran kedua dan mengembalikan pesan error yang jelas bahwa user sudah terdaftar.

---

### User Story 2 - Sistem menolak pendaftaran yang tidak memenuhi syarat (Prioritas: P1)

Seorang user mencoba mendaftar ke event publik, tetapi kondisi event tidak lagi memenuhi syarat pendaftaran (misalnya event tidak ditemukan, sudah melewati batas waktu pendaftaran, atau kuota sudah penuh). Dalam kasus seperti ini, sistem harus menolak pendaftaran dengan pesan yang jelas, tanpa mengubah jumlah peserta dan tanpa mencatat pendaftaran baru.

**Alasan prioritas ini**: Penolakan yang konsisten dan aman mencegah overbooking, menghindari kebingungan user, dan menjaga integritas data event.

**Independent Test**: Story ini dapat diuji secara mandiri dengan menyiapkan beberapa skenario terpisah: event tidak ada, event sudah lewat batas waktu pendaftaran, kuota sudah penuh, dan user sudah terdaftar; lalu mengirimkan permintaan pendaftaran dan memverifikasi bahwa semua permintaan tersebut ditolak tanpa menambah jumlah peserta.

**Acceptance Scenarios**:

1. **Given** tidak ada event dengan identifier yang diminta, **When** user mengirimkan permintaan pendaftaran untuk event tersebut, **Then** sistem menolak pendaftaran dan mengembalikan pesan bahwa event tidak ditemukan.
2. **Given** sebuah event publik telah melewati `registration_deadline`, **When** user mengirimkan permintaan pendaftaran baru, **Then** sistem menolak pendaftaran dan menjelaskan bahwa periode pendaftaran sudah berakhir.
3. **Given** sebuah event publik dengan kuota penuh (jumlah peserta sekarang sudah sama dengan kuota), **When** user baru mencoba mendaftar, **Then** sistem menolak pendaftaran dan menjelaskan bahwa kuota sudah penuh.
4. **Given** user sudah memiliki pendaftaran aktif pada event tertentu, **When** user mengirimkan permintaan pendaftaran lagi ke event yang sama, **Then** sistem menolak pendaftaran karena user sudah terdaftar.

---

### User Story 3 - User membatalkan pendaftaran event (Prioritas: P2)

Seorang user yang sudah terdaftar sebagai peserta suatu event publik memutuskan untuk batal mengikuti event tersebut. Ia mengirimkan permintaan pembatalan pendaftaran. Sistem harus menghapus data pendaftarannya dan mengurangi jumlah peserta event sehingga kuota kembali tersedia untuk peserta lain (selama ketentuan waktu pendaftaran dan kebijakan event mendukung hal ini).

**Alasan prioritas ini**: Pembatalan pendaftaran memberikan fleksibilitas bagi user dan memungkinkan kuota dimanfaatkan oleh peserta lain, meningkatkan pemakaian kapasitas event.

**Independent Test**: Story ini dapat diuji secara mandiri dengan menyiapkan user yang sudah terdaftar pada suatu event, lalu mengirimkan permintaan pembatalan dan memverifikasi bahwa data pendaftaran user terhapus dan jumlah peserta event berkurang satu.

**Acceptance Scenarios**:

1. **Given** user sudah terdaftar sebagai peserta pada sebuah event publik, **When** user mengirimkan permintaan pembatalan pendaftaran, **Then** sistem menghapus data registrasi user untuk event tersebut dan mengurangi jumlah peserta event.
2. **Given** user tidak memiliki pendaftaran aktif untuk suatu event, **When** user mengirimkan permintaan pembatalan untuk event tersebut, **Then** sistem menolak permintaan dengan pesan yang menjelaskan bahwa tidak ada pendaftaran yang dapat dibatalkan.

---

### Edge Cases

- Kondisi beberapa user melakukan pendaftaran ke event yang sama secara hampir bersamaan ketika sisa kuota sangat terbatas: sistem tetap harus menjaga agar jumlah peserta akhir tidak melebihi kuota, dan hanya sejumlah user yang sesuai kuota yang berhasil terdaftar.
- User mengirimkan permintaan pembatalan tepat setelah kuota penuh dan sebelum peserta lain mencoba mendaftar: setelah pembatalan berhasil, kuota seharusnya kembali tersedia sehingga pendaftaran baru dapat diterima selama `registration_deadline` belum lewat.
- Permintaan pendaftaran atau pembatalan dikirimkan mendekati atau tepat pada saat `registration_deadline`: sistem harus menggunakan aturan waktu yang konsisten untuk menentukan apakah pendaftaran masih diperbolehkan atau sudah ditutup.
- User mencoba melihat daftar peserta event: sistem harus menolak atau tidak menyediakan endpoint yang mengembalikan daftar peserta kepada user biasa, untuk menjaga privasi peserta.

## Requirements *(wajib)*

### Functional Requirements

- **FR-001**: Sistem HARUS menyediakan kemampuan bagi user untuk mendaftar ke event publik yang valid, belum melewati `registration_deadline`, dan belum mencapai kuota penuh.
- **FR-002**: Sistem HARUS menolak pendaftaran ketika event yang diminta tidak ditemukan dan mengembalikan pesan error yang menjelaskan bahwa event tidak tersedia.
- **FR-003**: Sistem HARUS menolak pendaftaran ketika `registration_deadline` event sudah lewat dan mengembalikan pesan error yang menjelaskan bahwa periode pendaftaran sudah berakhir.
- **FR-004**: Sistem HARUS menolak pendaftaran ketika jumlah peserta saat ini sudah mencapai kuota event dan mengembalikan pesan error yang menjelaskan bahwa kuota sudah penuh.
- **FR-005**: Sistem HARUS menolak pendaftaran ganda untuk kombinasi user dan event yang sama dan mengembalikan pesan error bahwa user sudah terdaftar.
- **FR-006**: Sistem HARUS memastikan bahwa setiap proses pendaftaran yang berhasil menambah jumlah peserta event secara konsisten dan tidak menyebabkan jumlah peserta melebihi kuota, bahkan dalam kondisi banyak pendaftaran terjadi hampir bersamaan.
- **FR-007**: Sistem HARUS menyediakan kemampuan bagi user untuk membatalkan pendaftarannya terhadap event publik yang ia ikuti, selama masih diperbolehkan oleh kebijakan pendaftaran event.
- **FR-008**: Sistem HARUS menghapus data registrasi user untuk event yang dibatalkan dan mengurangi jumlah peserta event ketika pembatalan berhasil.
- **FR-009**: Sistem TIDAK BOLEH menyediakan kepada user biasa kemampuan untuk melihat daftar lengkap peserta suatu event (misalnya nama atau identitas peserta lain), guna menjaga privasi peserta.

### Non-Functional Requirements

- **NFR-001**: Sistem HARUS menjaga integritas data pendaftaran sehingga tidak terjadi duplikasi pendaftaran untuk kombinasi user dan event yang sama, dan hal ini harus terjamin meskipun terdapat permintaan pendaftaran paralel.
- **NFR-002**: Sistem HARUS menangani proses pendaftaran dan pembatalan dengan mekanisme konsistensi data yang aman terhadap kondisi paralel (misalnya konkurensi tinggi), sehingga tidak menimbulkan overbooking atau ketidaksesuaian jumlah peserta yang tercatat.

### Key Entities *(sertakan jika fitur melibatkan data)*

- **Event Registration**: Merepresentasikan satu pendaftaran user ke sebuah event publik. Entitas ini menghubungkan `user` dengan `event`, menyimpan status pendaftaran (aktif/dibatalkan), dan menjadi dasar perhitungan jumlah peserta event.
- **Event**: Entitas event publik yang sudah didefinisikan pada spesifikasi Event Management dan menyediakan informasi kuota, batas waktu pendaftaran, dan jumlah peserta saat ini yang digunakan dalam validasi pendaftaran.

## Success Criteria *(wajib)*

### Measurable Outcomes

- **SC-001**: 100% percobaan pendaftaran ke event yang memenuhi semua syarat (event ditemukan, belum lewat `registration_deadline`, kuota masih tersedia, dan user belum terdaftar) dalam automated test menghasilkan pendaftaran yang berhasil dan tercatat sebagai peserta event.
- **SC-002**: 100% percobaan pendaftaran yang melanggar salah satu kondisi (event tidak ditemukan, lewat `registration_deadline`, kuota penuh, atau user sudah terdaftar) dalam automated test ditolak dan tidak menambah jumlah peserta event.
- **SC-003**: 100% percobaan pembatalan pendaftaran yang valid dalam automated test menghapus data pendaftaran user dan mengurangi jumlah peserta event sesuai harapan.
- **SC-004**: Dalam skenario uji dengan pendaftaran paralel ke event dengan kuota terbatas, tidak ada kasus di mana jumlah peserta akhir melampaui kuota yang ditentukan.

## Assumptions & Dependencies

- Fitur ini bergantung pada spesifikasi Event Management (003-event-registration mengasumsikan bahwa entitas Event sudah memiliki informasi kuota, jumlah peserta saat ini, dan `registration_deadline`).
- Mekanisme autentikasi dan otorisasi mengikuti spesifikasi `001-authentication`, sehingga hanya user yang teridentifikasi yang dapat melakukan pendaftaran dan pembatalan pendaftaran event atas nama dirinya sendiri.
- Kebijakan bisnis terkait apakah pembatalan boleh dilakukan setelah `registration_deadline` atau mendekati waktu event akan disepakati pada tahap perencanaan, selama implementasi tetap memenuhi requirement tentang konsistensi kuota dan data pendaftaran.
- Detail teknis terkait bentuk API, jenis database, atau teknik konkret untuk menjaga konsistensi data (misalnya penggunaan transaksi atau mekanisme sinkronisasi lain) akan ditentukan pada desain teknis, selama tetap menjamin tidak terjadi overbooking dan duplikasi pendaftaran.
