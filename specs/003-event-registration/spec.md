# Spesifikasi Fitur: Event Registration

**Feature Branch**: `[003-event-registration]`  
**Dibuat**: 2026-03-05  
**Status**: Draft  
**Input**: Deskripsi pengguna: "Feature: Event Registration - User dapat mendaftar dan membatalkan pendaftaran ke event publik dengan pembatasan kuota dan batas waktu."

## Clarifications

### Session 2026-03-05

- Q: Sampai kapan user boleh membatalkan pendaftaran event? → A: Pembatalan hanya boleh dilakukan selama `registration_deadline` event belum lewat; setelah batas waktu pendaftaran ditutup, permintaan pembatalan HARUS ditolak dengan pesan error yang jelas.
- Q: Apakah data Event Registration benar-benar dihapus (hard delete) atau hanya diubah statusnya (soft delete) saat user membatalkan pendaftaran? → A: Soft delete — saat user membatalkan, status record Event Registration diubah menjadi `dibatalkan`; record tetap ada dan jumlah peserta aktif event hanya dihitung dari record berstatus `aktif`.
- Q: Apakah user yang sudah pernah membatalkan pendaftaran boleh mendaftar ulang ke event yang sama? → A: Ya, user boleh mendaftar ulang ke event yang sama setelah membatalkan, selama `registration_deadline` belum lewat dan kuota masih tersedia. Yang diblokir sebagai duplikasi hanya jika sudah ada record berstatus `aktif` untuk kombinasi user dan event yang sama; record `dibatalkan` tidak memblokir pendaftaran baru.
- Q: Apakah user dapat melihat daftar pendaftarannya sendiri, dan apakah ini termasuk scope fitur ini? → A: Ya, dalam scope fitur ini — user dapat mengambil daftar Event Registration miliknya sendiri, mencakup record berstatus `aktif` maupun `dibatalkan`; user tidak dapat melihat pendaftaran milik user lain.
- Q: HTTP status code apa yang HARUS digunakan untuk setiap skenario penolakan pendaftaran dan pembatalan? → A: Event tidak ditemukan → 404; deadline pendaftaran sudah lewat → 422; kuota penuh → 422; user sudah memiliki pendaftaran aktif (duplikasi) → 409; tidak ada pendaftaran aktif untuk dibatalkan → 404; permintaan pembatalan setelah `registration_deadline` → 422.

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

Seorang user yang sudah terdaftar sebagai peserta suatu event publik memutuskan untuk batal mengikuti event tersebut. Ia mengirimkan permintaan pembatalan pendaftaran. Sistem harus mengubah status pendaftarannya menjadi `dibatalkan` dan mengurangi jumlah peserta aktif event sehingga kuota kembali tersedia untuk peserta lain (selama ketentuan waktu pendaftaran mendukung hal ini; record pendaftaran tetap tersimpan — soft delete).

**Alasan prioritas ini**: Pembatalan pendaftaran memberikan fleksibilitas bagi user dan memungkinkan kuota dimanfaatkan oleh peserta lain, meningkatkan pemakaian kapasitas event.

**Independent Test**: Story ini dapat diuji secara mandiri dengan menyiapkan user yang sudah terdaftar pada suatu event, lalu mengirimkan permintaan pembatalan dan memverifikasi bahwa status record Event Registration berubah menjadi `dibatalkan` (soft delete — record tetap ada) dan jumlah peserta aktif event berkurang satu.

**Acceptance Scenarios**:

1. **Given** user sudah terdaftar sebagai peserta pada sebuah event publik, **When** user mengirimkan permintaan pembatalan pendaftaran, **Then** sistem mengubah status record Event Registration menjadi `dibatalkan` dan mengurangi jumlah peserta aktif event.
2. **Given** user tidak memiliki pendaftaran aktif untuk suatu event, **When** user mengirimkan permintaan pembatalan untuk event tersebut, **Then** sistem menolak permintaan dengan pesan yang menjelaskan bahwa tidak ada pendaftaran yang dapat dibatalkan.
3. **Given** user pernah membatalkan pendaftaran ke suatu event dan `registration_deadline` belum lewat serta kuota masih tersedia, **When** user mengirimkan permintaan pendaftaran baru ke event yang sama, **Then** sistem menerima pendaftaran dan membuat record `aktif` baru, sehingga user kembali tercatat sebagai peserta aktif event tersebut.

---

### Edge Cases

- Kondisi beberapa user melakukan pendaftaran ke event yang sama secara hampir bersamaan ketika sisa kuota sangat terbatas: sistem tetap harus menjaga agar jumlah peserta akhir tidak melebihi kuota, dan hanya sejumlah user yang sesuai kuota yang berhasil terdaftar.
- User mengirimkan permintaan pembatalan tepat setelah kuota penuh dan sebelum peserta lain mencoba mendaftar: setelah pembatalan berhasil, kuota seharusnya kembali tersedia sehingga pendaftaran baru dapat diterima selama `registration_deadline` belum lewat.
- Permintaan pendaftaran atau pembatalan dikirimkan mendekati atau tepat pada saat `registration_deadline`: sistem harus menggunakan aturan waktu yang konsisten untuk menentukan apakah pendaftaran maupun pembatalan masih diperbolehkan atau sudah ditutup — batas yang sama (`registration_deadline`) berlaku untuk keduanya.
- User mencoba melihat daftar peserta event: sistem harus menolak atau tidak menyediakan endpoint yang mengembalikan daftar peserta kepada user biasa, untuk menjaga privasi peserta.

## Requirements *(wajib)*

### Functional Requirements

- **FR-001**: Sistem HARUS menyediakan kemampuan bagi user untuk mendaftar ke event publik yang valid, belum melewati `registration_deadline`, dan belum mencapai kuota penuh.
- **FR-002**: Sistem HARUS menolak pendaftaran ketika event yang diminta tidak ditemukan dan mengembalikan pesan error yang menjelaskan bahwa event tidak tersedia.
- **FR-003**: Sistem HARUS menolak pendaftaran ketika `registration_deadline` event sudah lewat dan mengembalikan pesan error yang menjelaskan bahwa periode pendaftaran sudah berakhir. Batas waktu bersifat tertutup (*closed boundary*): kondisi `datetime.now(UTC) >= registration_deadline` dianggap sudah lewat dan permintaan ditolak, termasuk saat nilai `now` tepat sama dengan `registration_deadline`.
- **FR-004**: Sistem HARUS menolak pendaftaran ketika jumlah peserta saat ini sudah mencapai kuota event dan mengembalikan pesan error yang menjelaskan bahwa kuota sudah penuh.
- **FR-005**: Sistem HARUS menolak pendaftaran ganda untuk kombinasi user dan event yang sama hanya jika sudah terdapat record berstatus `aktif` untuk kombinasi tersebut; jika record sebelumnya berstatus `dibatalkan`, pendaftaran baru HARUS diperbolehkan selama syarat lain (deadline belum lewat, kuota tersedia) terpenuhi.
- **FR-006**: Sistem HARUS memastikan bahwa setiap proses pendaftaran yang berhasil menambah jumlah peserta event secara konsisten dan tidak menyebabkan jumlah peserta melebihi kuota, bahkan dalam kondisi banyak pendaftaran terjadi hampir bersamaan.
- **FR-007**: Sistem HARUS menyediakan kemampuan bagi user untuk membatalkan pendaftarannya terhadap event publik yang ia ikuti, selama `registration_deadline` event belum lewat. Permintaan pembatalan setelah `registration_deadline` HARUS ditolak dengan pesan error yang jelas.
- **FR-008**: Sistem HARUS mengubah status record Event Registration menjadi `dibatalkan` (soft delete) ketika pembatalan berhasil, dan jumlah peserta aktif event HARUS berkurang satu sehingga kuota kembali tersedia; record pembatalan tetap disimpan dan tidak dihapus secara permanen.
- **FR-009**: Sistem TIDAK BOLEH menyediakan kepada user biasa kemampuan untuk melihat daftar lengkap peserta suatu event (misalnya nama atau identitas peserta lain), guna menjaga privasi peserta.
- **FR-010**: Sistem HARUS menyediakan kemampuan bagi user untuk mengambil daftar Event Registration miliknya sendiri, termasuk record berstatus `aktif` maupun `dibatalkan`, dan memastikan bahwa user hanya dapat melihat record miliknya sendiri.
- **FR-011**: Sistem HARUS menggunakan HTTP status code berikut untuk setiap skenario penolakan pendaftaran dan pembatalan: event tidak ditemukan (pendaftaran maupun pembatalan) → 404 Not Found; `registration_deadline` sudah lewat atau kuota penuh atau permintaan pembatalan setelah `registration_deadline` → 422 Unprocessable Entity; user sudah memiliki pendaftaran aktif untuk event yang sama (duplikasi) → 409 Conflict; tidak ada pendaftaran aktif untuk dibatalkan → 404 Not Found.

### Non-Functional Requirements

- **NFR-001**: Sistem HARUS menjaga integritas data pendaftaran sehingga tidak terjadi duplikasi pendaftaran untuk kombinasi user dan event yang sama, dan hal ini harus terjamin meskipun terdapat permintaan pendaftaran paralel.
- **NFR-002**: Sistem HARUS menangani proses pendaftaran dan pembatalan dengan mekanisme konsistensi data yang aman terhadap kondisi paralel (misalnya konkurensi tinggi), sehingga tidak menimbulkan overbooking atau ketidaksesuaian jumlah peserta yang tercatat.

### Key Entities *(sertakan jika fitur melibatkan data)*

- **Event Registration**: Merepresentasikan satu pendaftaran user ke sebuah event publik. Entitas ini menghubungkan `user` dengan `event`, menyimpan status pendaftaran (`aktif` / `dibatalkan` — disimpan sebagai nilai string `'active'` / `'cancelled'` sesuai enum `RegistrationStatus` pada implementasi), dan hanya record berstatus `aktif` yang dihitung dalam jumlah peserta event serta diperhitungkan dalam validasi kuota. Record tidak pernah dihapus secara permanen (soft delete).
- **Event**: Entitas event publik yang sudah didefinisikan pada spesifikasi Event Management dan menyediakan informasi kuota, batas waktu pendaftaran, dan jumlah peserta saat ini yang digunakan dalam validasi pendaftaran.

## Success Criteria *(wajib)*

### Measurable Outcomes

- **SC-001**: 100% percobaan pendaftaran ke event yang memenuhi semua syarat (event ditemukan, belum lewat `registration_deadline`, kuota masih tersedia, dan user belum terdaftar) dalam automated test menghasilkan pendaftaran yang berhasil dan tercatat sebagai peserta event.
- **SC-002**: 100% percobaan pendaftaran yang melanggar salah satu kondisi (event tidak ditemukan, lewat `registration_deadline`, kuota penuh, atau user sudah terdaftar) dalam automated test ditolak dan tidak menambah jumlah peserta event.
- **SC-003**: 100% percobaan pembatalan pendaftaran yang valid dalam automated test menghasilkan status record Event Registration berubah menjadi `dibatalkan` dan jumlah peserta aktif event berkurang satu sesuai harapan (soft delete — record tetap tersimpan dan tidak dihapus secara permanen).
- **SC-004**: Dalam skenario uji dengan pendaftaran paralel ke event dengan kuota terbatas, tidak ada kasus di mana jumlah peserta akhir melampaui kuota yang ditentukan.

## Assumptions & Dependencies

- Fitur ini bergantung pada spesifikasi **002-event-management** (yang menyediakan entitas Event dengan informasi kuota, jumlah peserta saat ini, dan `registration_deadline` yang digunakan dalam validasi pendaftaran).
- Mekanisme autentikasi dan otorisasi mengikuti spesifikasi `001-authentication`, sehingga hanya user yang teridentifikasi yang dapat melakukan pendaftaran dan pembatalan pendaftaran event atas nama dirinya sendiri.
- Kebijakan pembatalan telah disepakati (lihat Clarifications 2026-03-05): pembatalan hanya diperbolehkan selama `registration_deadline` belum lewat; permintaan pembatalan setelah batas waktu tersebut ditolak (FR-007, kode 422).
- Detail teknis telah ditetapkan dalam plan.md: PostgreSQL 15+ dengan SQLAlchemy 2.x async, atomic UPDATE untuk manajemen kuota (`UPDATE events SET current_participants + 1 WHERE current_participants < quota RETURNING id`), dan partial unique index `uq_active_registration (user_id, event_id) WHERE status='active'` untuk pencegahan duplikasi aktif.
