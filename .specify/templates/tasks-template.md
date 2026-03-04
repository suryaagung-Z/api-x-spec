---

description: "Template daftar task untuk implementasi fitur"
---

# Tasks: [FEATURE NAME]

**Input**: Dokumen desain dari `/specs/[###-feature-name]/`
**Prerequisites**: plan.md (wajib), spec.md (wajib untuk user story), research.md, data-model.md, contracts/

**Tests**: Contoh di bawah menyertakan task untuk test. Test adalah WAJIB dan setiap task HARUS mencakup test yang cukup untuk mencapai dan menjaga 100% coverage untuk seluruh kode produksi yang ditambahkan atau diubah oleh fitur ini.

**Organisasi**: Task dikelompokkan per user story agar implementasi dan pengujian setiap story dapat dilakukan secara mandiri.

## Format: `[ID] [P?] [Story] Deskripsi`

- **[P]**: Dapat dijalankan paralel (file berbeda, tanpa dependensi)
- **[Story]**: User story mana yang menjadi konteks task ini (misalnya US1, US2, US3)
- Sertakan path file yang tepat di deskripsi

## Konvensi Path

- **Single project**: `src/`, `tests/` di root repository
- **Web app**: `backend/src/`, `frontend/src/`
- **Mobile**: `api/src/`, `ios/src/` atau `android/src/`
- Path di bawah mengasumsikan single project - sesuaikan dengan struktur di plan.md

<!-- 
  ============================================================================
  PENTING: Task di bawah ini hanyalah CONTOH untuk tujuan ilustrasi.
  
  Perintah /speckit.tasks HARUS mengganti contoh ini dengan task nyata berdasarkan:
  - User story dari spec.md (beserta prioritasnya P1, P2, P3...)
  - Requirement fitur dari plan.md
  - Entitas dari data-model.md
  - Endpoint dari contracts/
  
  Task HARUS diorganisasi per user story sehingga setiap story dapat:
  - Diimplementasikan secara mandiri
  - Diuji secara mandiri
  - Dikirim sebagai inkremen MVP
  
  JANGAN menyimpan contoh task ini di file tasks.md yang dihasilkan.
  ============================================================================
-->

## Phase 1: Setup (Infrastruktur Bersama)

**Tujuan**: Inisialisasi proyek dan struktur dasar

- [ ] T001 Buat struktur proyek sesuai rencana implementasi
- [ ] T002 Inisialisasi proyek [bahasa] dengan dependency [framework]
- [ ] T003 [P] Konfigurasi tool linting dan formatting

---

## Phase 2: Fondasi (Prerequisite yang Memblokir)

**Tujuan**: Infrastruktur inti yang HARUS selesai sebelum user story APA PUN dapat diimplementasikan

**⚠️ KRITIS**: Pekerjaan user story tidak boleh dimulai sebelum fase ini selesai

Contoh task fondasi (sesuaikan dengan proyek Anda):

- [ ] T004 Setup schema database dan framework migrasi
- [ ] T005 [P] Implementasikan framework authentication/authorization
- [ ] T006 [P] Setup routing API dan struktur middleware
- [ ] T007 Buat model/entitas dasar yang digunakan semua story
- [ ] T008 Konfigurasi infrastruktur error handling dan logging
- [ ] T009 Setup manajemen konfigurasi environment

**Checkpoint**: Fondasi siap - implementasi user story sekarang dapat dimulai secara paralel

---

## Phase 3: User Story 1 - [Judul] (Prioritas: P1) 🎯 MVP

**Goal**: [Deskripsi singkat apa yang dikirimkan oleh story ini]

**Independent Test**: [Bagaimana memverifikasi story ini bekerja sendiri]

### Test untuk User Story 1 (WAJIB) ⚠️

> **CATATAN: Tulis test ini TERLEBIH DAHULU, pastikan mereka GAGAL sebelum implementasi**

- [ ] T010 [P] [US1] Contract test untuk [endpoint] di tests/contract/test_[name].py
- [ ] T011 [P] [US1] Integration test untuk [user journey] di tests/integration/test_[name].py

### Implementasi untuk User Story 1

- [ ] T012 [P] [US1] Buat model [Entity1] di src/models/[entity1].py
- [ ] T013 [P] [US1] Buat model [Entity2] di src/models/[entity2].py
- [ ] T014 [US1] Implementasikan [Service] di src/services/[service].py (bergantung pada T012, T013)
- [ ] T015 [US1] Implementasikan [endpoint/feature] di src/[location]/[file].py
- [ ] T016 [US1] Tambahkan validasi dan error handling
- [ ] T017 [US1] Tambahkan logging untuk operasi user story 1

**Checkpoint**: Pada titik ini, User Story 1 seharusnya sudah fungsional penuh dan dapat diuji secara mandiri

---

## Phase 4: User Story 2 - [Judul] (Prioritas: P2)

**Goal**: [Deskripsi singkat apa yang dikirimkan oleh story ini]

**Independent Test**: [Bagaimana memverifikasi story ini bekerja sendiri]

### Test untuk User Story 2 (WAJIB) ⚠️

- [ ] T018 [P] [US2] Contract test untuk [endpoint] di tests/contract/test_[name].py
- [ ] T019 [P] [US2] Integration test untuk [user journey] di tests/integration/test_[name].py

### Implementasi untuk User Story 2

- [ ] T020 [P] [US2] Buat model [Entity] di src/models/[entity].py
- [ ] T021 [US2] Implementasikan [Service] di src/services/[service].py
- [ ] T022 [US2] Implementasikan [endpoint/feature] di src/[location]/[file].py
- [ ] T023 [US2] Integrasi dengan komponen User Story 1 (jika diperlukan)

**Checkpoint**: Pada titik ini, User Story 1 DAN 2 seharusnya keduanya bekerja secara mandiri

---

## Phase 5: User Story 3 - [Judul] (Prioritas: P3)

**Goal**: [Deskripsi singkat apa yang dikirimkan oleh story ini]

**Independent Test**: [Bagaimana memverifikasi story ini bekerja sendiri]

### Test untuk User Story 3 (WAJIB) ⚠️

- [ ] T024 [P] [US3] Contract test untuk [endpoint] di tests/contract/test_[name].py
- [ ] T025 [P] [US3] Integration test untuk [user journey] di tests/integration/test_[name].py

### Implementasi untuk User Story 3

- [ ] T026 [P] [US3] Buat model [Entity] di src/models/[entity].py
- [ ] T027 [US3] Implementasikan [Service] di src/services/[service].py
- [ ] T028 [US3] Implementasikan [endpoint/feature] di src/[location]/[file].py

**Checkpoint**: Semua user story sekarang seharusnya fungsional secara mandiri

---

[Tambahkan fase user story lain bila perlu, mengikuti pola yang sama]

---

## Phase N: Polish & Cross-Cutting Concerns

**Tujuan**: Peningkatan yang memengaruhi banyak user story

- [ ] TXXX [P] Pembaruan dokumentasi di docs/
- [ ] TXXX Code cleanup dan refactoring
- [ ] TXXX Optimasi performa lintas semua story
- [ ] TXXX [P] Tambahan unit test (jika diminta) di tests/unit/
- [ ] TXXX Penguatan aspek keamanan
- [ ] TXXX Jalankan validasi quickstart.md

---

## Dependensi & Urutan Eksekusi

### Dependensi Antar Fase

- **Setup (Phase 1)**: Tanpa dependensi - dapat dimulai segera
- **Fondasi (Phase 2)**: Bergantung pada selesainya Setup - MEMBLOKIR semua user story
- **User Story (Phase 3+)**: Semua bergantung pada selesainya fase Fondasi
  - User story kemudian dapat berjalan paralel (jika resource tim cukup)
  - Atau berurutan sesuai prioritas (P1 → P2 → P3)
- **Polish (Fase Akhir)**: Bergantung pada selesainya semua user story yang diinginkan

### Dependensi User Story

- **User Story 1 (P1)**: Dapat dimulai setelah Fondasi (Phase 2) - Tanpa dependensi pada story lain
- **User Story 2 (P2)**: Dapat dimulai setelah Fondasi (Phase 2) - Dapat berintegrasi dengan US1 namun tetap harus dapat diuji secara mandiri
- **User Story 3 (P3)**: Dapat dimulai setelah Fondasi (Phase 2) - Dapat berintegrasi dengan US1/US2 namun tetap harus dapat diuji secara mandiri

### Di Dalam Setiap User Story

- Test HARUS ditulis dan GAGAL sebelum implementasi
- Model dibuat sebelum service
- Service dibuat sebelum endpoint
- Implementasi inti sebelum integrasi
- Story dinyatakan selesai sebelum pindah ke prioritas berikutnya

### Peluang Paralel

- Semua task Setup yang ditandai [P] dapat dijalankan paralel
- Semua task Fondasi yang ditandai [P] dapat dijalankan paralel (di dalam Phase 2)
- Setelah fase Fondasi selesai, semua user story dapat dimulai paralel (jika kapasitas tim memungkinkan)
- Semua test untuk sebuah user story yang ditandai [P] dapat dijalankan paralel
- Model dalam sebuah story yang ditandai [P] dapat dikerjakan paralel
- User story yang berbeda dapat dikerjakan paralel oleh anggota tim yang berbeda

---

## Contoh Paralel: User Story 1

```bash
# Jalankan semua test untuk User Story 1 bersama-sama (jika test diminta):
Task: "Contract test untuk [endpoint] di tests/contract/test_[name].py"
Task: "Integration test untuk [user journey] di tests/integration/test_[name].py"

# Jalankan semua model untuk User Story 1 bersama-sama:
Task: "Buat model [Entity1] di src/models/[entity1].py"
Task: "Buat model [Entity2] di src/models/[entity2].py"
```

---

## Strategi Implementasi

### MVP First (Hanya User Story 1)

1. Selesaikan Phase 1: Setup
2. Selesaikan Phase 2: Fondasi (KRITIS - memblokir semua story)
3. Selesaikan Phase 3: User Story 1
4. **BERHENTI dan VALIDASI**: Uji User Story 1 secara mandiri
5. Deploy/demo bila sudah siap

### Delivery Bertahap (Incremental Delivery)

1. Selesaikan Setup + Fondasi → Fondasi siap
2. Tambahkan User Story 1 → Uji secara mandiri → Deploy/Demo (MVP!)
3. Tambahkan User Story 2 → Uji secara mandiri → Deploy/Demo
4. Tambahkan User Story 3 → Uji secara mandiri → Deploy/Demo
5. Setiap story menambah nilai tanpa merusak story sebelumnya

### Strategi Tim Paralel

Jika ada beberapa developer:

1. Tim menyelesaikan Setup + Fondasi bersama-sama
2. Setelah Fondasi selesai:
   - Developer A: User Story 1
   - Developer B: User Story 2
   - Developer C: User Story 3
3. Setiap story selesai dan terintegrasi secara mandiri

---

## Catatan

- Task bertanda [P] = file berbeda, tanpa dependensi
- Label [Story] memetakan task ke user story tertentu untuk keterlacakan
- Setiap user story sebaiknya dapat diselesaikan dan diuji secara mandiri
- Pastikan test gagal sebelum implementasi
- Lakukan commit setelah setiap task atau grup logis
- Berhenti di setiap checkpoint untuk memvalidasi story secara mandiri
- Hindari: task yang terlalu umum, konflik di file yang sama, dependensi lintas story yang merusak kemandirian
