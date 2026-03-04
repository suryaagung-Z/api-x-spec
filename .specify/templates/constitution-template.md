# [PROJECT_NAME] Konstitusi
<!-- Contoh: Spec Constitution, TaskFlow Constitution, dll. -->

## Prinsip Inti

### [PRINCIPLE_1_NAME]
<!-- Contoh: I. Library-First -->
[PRINCIPLE_1_DESCRIPTION]
<!-- Contoh: Setiap fitur dimulai sebagai library mandiri; Library harus self-contained, dapat diuji secara mandiri, terdokumentasi; Tujuan jelas diperlukan - tidak ada library khusus organisasi saja -->

### [PRINCIPLE_2_NAME]
<!-- Contoh: II. Antarmuka CLI -->
[PRINCIPLE_2_DESCRIPTION]
<!-- Contoh: Setiap library mengekspos fungsionalitas lewat CLI; Protokol teks in/out: stdin/args → stdout, error → stderr; Mendukung format JSON + teks mudah dibaca manusia -->

### [PRINCIPLE_3_NAME]
<!-- Contoh: III. Test-First (TIDAK DAPAT DITAWAR) -->
[PRINCIPLE_3_DESCRIPTION]
<!-- Contoh: TDD wajib: Test ditulis → Disetujui user → Test gagal → Baru implementasi; Siklus Red-Green-Refactor ditegakkan secara ketat -->

### [PRINCIPLE_4_NAME]
<!-- Contoh: IV. Integration Testing -->
[PRINCIPLE_4_DESCRIPTION]
<!-- Contoh: Area fokus yang membutuhkan integration test: Contract test library baru, perubahan contract, komunikasi antar service, schema bersama -->

### [PRINCIPLE_5_NAME]
<!-- Contoh: V. Observability, VI. Versioning & Breaking Changes, VII. Simplicity -->
[PRINCIPLE_5_DESCRIPTION]
<!-- Contoh: I/O teks memastikan kemudahan debug; Logging terstruktur diwajibkan; Atau: format MAJOR.MINOR.BUILD; Atau: Mulai sederhana, prinsip YAGNI -->

## [SECTION_2_NAME]
<!-- Contoh: Batasan Tambahan, Kebutuhan Keamanan, Standar Performa, dll. -->

[SECTION_2_CONTENT]
<!-- Contoh: Kebutuhan technology stack, standar compliance, kebijakan deployment, dll. -->

## [SECTION_3_NAME]
<!-- Contoh: Alur Kerja Pengembangan, Proses Review, Quality Gate, dll. -->

[SECTION_3_CONTENT]
<!-- Contoh: Kebutuhan code review, gate pengujian, proses persetujuan deployment, dll. -->

## Tata Kelola
<!-- Contoh: Konstitusi menggantikan praktik lain; Amandemen butuh dokumentasi, persetujuan, dan rencana migrasi -->

[GOVERNANCE_RULES]
<!-- Contoh: Semua PR/review harus memverifikasi kepatuhan; Kompleksitas harus dibenarkan; Gunakan [GUIDANCE_FILE] untuk panduan runtime development -->

**Versi**: [CONSTITUTION_VERSION] | **Diratifikasi**: [RATIFICATION_DATE] | **Terakhir Diubah**: [LAST_AMENDED_DATE]
<!-- Contoh: Versi: 2.1.1 | Diratifikasi: 2025-06-13 | Terakhir Diubah: 2025-07-16 -->
