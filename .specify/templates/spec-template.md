# Spesifikasi Fitur: [FEATURE NAME]

**Feature Branch**: `[###-feature-name]`  
**Dibuat**: [DATE]  
**Status**: Draft  
**Input**: Deskripsi pengguna: "$ARGUMENTS"

## User Scenarios & Testing *(wajib)*

<!--
  PENTING: User story harus DIPRIORITASKAN sebagai perjalanan pengguna (user journey) yang diurutkan berdasarkan pentingnya.
  Setiap user story/journey harus DAPAT DIUJI SECARA MANDIRI - artinya jika Anda hanya mengimplementasikan SATU story,
  tetap harus ada MVP (Minimum Viable Product) yang memberikan nilai.
  
  Berikan prioritas (P1, P2, P3, dst.) untuk setiap story, di mana P1 adalah yang paling kritis.
  Pikirkan setiap story sebagai irisan fungsionalitas mandiri yang dapat:
  - Dikembangkan secara mandiri
  - Diuji secara mandiri
  - Dideploy secara mandiri
  - Didemonstrasikan ke pengguna secara mandiri
-->

### User Story 1 - [Judul Singkat] (Prioritas: P1)

[Jelaskan perjalanan pengguna ini dengan bahasa sederhana]

**Alasan prioritas ini**: [Jelaskan nilai yang diberikannya dan mengapa level prioritasnya demikian]

**Independent Test**: [Jelaskan bagaimana story ini dapat diuji secara mandiri - misalnya, "Dapat diuji penuh dengan [aksi spesifik] dan menghasilkan [nilai spesifik]"]

**Acceptance Scenarios**:

1. **Given** [kondisi awal], **When** [aksi], **Then** [hasil yang diharapkan]
2. **Given** [kondisi awal], **When** [aksi], **Then** [hasil yang diharapkan]

---

### User Story 2 - [Judul Singkat] (Prioritas: P2)

[Jelaskan perjalanan pengguna ini dengan bahasa sederhana]

**Alasan prioritas ini**: [Jelaskan nilai yang diberikannya dan mengapa level prioritasnya demikian]

**Independent Test**: [Jelaskan bagaimana story ini dapat diuji secara mandiri]

**Acceptance Scenarios**:

1. **Given** [kondisi awal], **When** [aksi], **Then** [hasil yang diharapkan]

---

### User Story 3 - [Judul Singkat] (Prioritas: P3)

[Jelaskan perjalanan pengguna ini dengan bahasa sederhana]

**Alasan prioritas ini**: [Jelaskan nilai yang diberikannya dan mengapa level prioritasnya demikian]

**Independent Test**: [Jelaskan bagaimana story ini dapat diuji secara mandiri]

**Acceptance Scenarios**:

1. **Given** [kondisi awal], **When** [aksi], **Then** [hasil yang diharapkan]

---

[Tambahkan user story lain bila perlu, masing-masing dengan prioritas yang jelas]

### Edge Cases

<!--
  AKSI WAJIB: Konten di bagian ini adalah placeholder.
  Gantilah dengan edge case yang relevan untuk fitur Anda.
-->

- Apa yang terjadi ketika [kondisi batas]?
- Bagaimana sistem menangani [skenario error]?

## Requirements *(wajib)*

<!--
  AKSI WAJIB: Konten di bagian ini adalah placeholder.
  Gantilah dengan requirement fungsional yang tepat.
-->

### Functional Requirements

- **FR-001**: Sistem HARUS [kapabilitas spesifik, misalnya "mengizinkan pengguna membuat akun"]
- **FR-002**: Sistem HARUS [kapabilitas spesifik, misalnya "memvalidasi alamat email"]  
- **FR-003**: Pengguna HARUS dapat [interaksi utama, misalnya "melakukan reset kata sandi"]
- **FR-004**: Sistem HARUS [kebutuhan data, misalnya "menyimpan preferensi pengguna"]
- **FR-005**: Sistem HARUS [perilaku, misalnya "mencatat semua event keamanan"]

*Contoh penandaan requirement yang belum jelas:*

- **FR-006**: Sistem HARUS melakukan autentikasi pengguna melalui [NEEDS CLARIFICATION: metode autentikasi belum ditentukan - email/password, SSO, OAuth?]
- **FR-007**: Sistem HARUS menyimpan data pengguna selama [NEEDS CLARIFICATION: periode retensi belum ditentukan]

### Key Entities *(sertakan jika fitur melibatkan data)*

- **[Entity 1]**: [Apa yang direpresentasikan, atribut kunci tanpa detail implementasi]
- **[Entity 2]**: [Apa yang direpresentasikan, relasi dengan entitas lain]

## Success Criteria *(wajib)*

<!--
  AKSI WAJIB: Definisikan kriteria keberhasilan yang terukur.
  Kriteria ini harus agnostik terhadap teknologi dan dapat diukur.
-->

### Measurable Outcomes

- **SC-001**: [Metrik terukur, misalnya "Pengguna dapat menyelesaikan pembuatan akun dalam waktu kurang dari 2 menit"]
- **SC-002**: [Metrik terukur, misalnya "Sistem menangani 1000 pengguna bersamaan tanpa degradasi yang terlihat"]
- **SC-003**: [Metrik kepuasan pengguna, misalnya "90% pengguna berhasil menyelesaikan tugas utama pada percobaan pertama"]
- **SC-004**: [Metrik bisnis, misalnya "Mengurangi tiket support terkait [X] sebesar 50%"]
