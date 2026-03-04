<!--
Laporan Dampak Sinkronisasi

- Perubahan versi: none → 1.0.0 (ratifikasi awal)
- Prinsip yang diubah: (baru) I. Desain API Berbasis Spesifikasi; (baru) II. User Story yang Dapat Diuji Secara Mandiri; (baru) III. Implementasi Berbasis Rencana; (baru) IV. Teks-First, CLI & Git Native; (baru) V. Kesederhanaan, Keterlacakan & Review
- Bagian yang ditambahkan: Prinsip Inti; Batasan Dokumentasi & Template; Alur Kerja Pengembangan & Quality Gate; Tata Kelola
- Bagian yang dihapus: none
- Status template:
	- .specify/templates/plan-template.md: ✅ diperbarui (gate Constitution Check + tautan pelacakan kompleksitas)
	- .specify/templates/spec-template.md: ✅ selaras (bagian wajib sudah sesuai)
	- .specify/templates/tasks-template.md: ✅ selaras (pengelompokan dan kemandirian user story)
	- .specify/templates/checklist-template.md: ✅ selaras (tidak ada aturan khusus konstitusi)
	- .specify/templates/agent-file-template.md: ✅ selaras (hanya panduan runtime)
- TODO tertunda: none
-->

# Konstitusi API-X Spec

## Prinsip Inti

### I. Desain API Berbasis Spesifikasi (TIDAK DAPAT DITAWAR)

Pekerjaan API-X HARUS dimulai dari spesifikasi fitur tertulis di
`/specs/[###-feature-name]/spec.md`. Tidak ada pekerjaan implementasi yang
dianggap valid untuk proyek ini kecuali dapat ditelusuri kembali ke spesifikasi
dan rencana implementasi yang disetujui.

- Setiap perubahan yang memengaruhi perilaku HARUS berawal dari spesifikasi
	fitur yang tersimpan di repository.
- Spesifikasi HARUS menggunakan bagian standar dari template spesifikasi fitur:
	User Scenarios & Testing, Requirements, dan Success Criteria.
- Spesifikasi HARUS mendefinisikan setidaknya satu user story prioritas (P1)
	yang memberikan irisan nilai yang layak dan dapat diuji secara mandiri.
- Spesifikasi belum dianggap "siap" sampai kriteria keberhasilan terukur dan
	agnostik terhadap teknologi.

Alasan: Ini menjaga desain API-X tetap berniat, dapat direview, dan dapat diaudit,
serta mencegah pekerjaan ad-hoc yang tidak dapat ditelusuri ke hasil yang
dihadapi pengguna.

### II. User Story yang Dapat Diuji Secara Mandiri

User story adalah unit perencanaan utama dan HARUS dapat diuji serta dikirimkan
secara mandiri.

- Setiap user story di spec.md HARUS:
	- Diprioritaskan (P1, P2, P3, …).
	- Mendeskripsikan perjalanan pengguna yang lengkap dan dapat divalidasi
		secara terpisah.
	- Menyertakan setidaknya satu deskripsi "Independent Test" eksplisit.
- Task yang dihasilkan untuk sebuah fitur HARUS dikelompokkan per user story
	sehingga setiap story dapat diimplementasikan dan diuji tanpa bergantung pada
	selesainya story lain, kecuali fondasi bersama yang dijelaskan dengan jelas.
- Harus memungkinkan untuk mendemonstrasikan setiap story P1/P2 yang selesai
	sebagai inkremen MVP yang koheren tanpa mengasumsikan story lain yang belum
	selesai.

Alasan: Story yang mandiri memungkinkan delivery bertahap, trade-off yang lebih
jelas, dan lebih mudah memvalidasi perilaku terhadap spesifikasi.

### III. Implementasi Berbasis Rencana

Implementasi HARUS mengikuti rencana eksplisit (plan.md) yang diturunkan dari
spesifikasi.

- Setiap feature branch HARUS memiliki rencana implementasi di
	`/specs/[###-feature-name]/plan.md` sebelum pekerjaan implementasi non-spike
	dimulai.
- Rencana HARUS merangkum fitur dalam konteks proyek, mendokumentasikan
	struktur yang dipilih (single-project, web app, mobile, dll.), dan
	mengidentifikasi pekerjaan fondasi vs. pekerjaan spesifik user story.
- Bagian "Constitution Check" di plan.md HARUS diisi dan dijaga tetap mutakhir;
	bagian ini bertindak sebagai gate pemblokir sebelum riset Fase 0 dan HARUS
	di-validasi ulang setelah desain Fase 1.
- Setiap deviasi atau kompleksitas tambahan yang disengaja (misalnya layer
	tambahan, project tambahan, pola non-trivial) HARUS didokumentasikan dalam
	tabel "Complexity Tracking" di plan.md dengan justifikasi yang jelas.

Alasan: Rencana membuat implementasi menjadi lebih terprediksi, dapat
direview, dan selaras dengan spesifikasi serta konstitusi ini.

### IV. Teks-First, CLI & Git Native

Proyek ini dioptimalkan untuk workflow berbasis teks, tool CLI, dan Git.

- Semua pengetahuan proyek yang bersifat permanen (spec, plan, tasks,
	checklist, guideline) HARUS disimpan dalam file teks/Markdown yang
	terversi di repository ini.
- Otomasi (misalnya perintah `/speckit.*`) HARUS berkomunikasi melalui I/O teks:
	argumen/stdin sebagai input, Markdown atau teks terstruktur sebagai output.
- Tidak boleh ada state proyek penting yang hanya ada di tool eksternal, UI,
	atau memori agen; jika penting, HARUS ditulis kembali ke file yang
	terlacak.
- File yang dihasilkan otomatis HARUS tetap mudah dibaca manusia dan aman
	untuk direview dalam workflow Git biasa.

Alasan: Workflow berbasis teks dan Git menjaga sistem tetap transparan,
mudah di-diff, dan mudah diaudit dari waktu ke waktu.

### V. Kesederhanaan, Keterlacakan & Review

Pendekatan paling sederhana yang memenuhi spesifikasi dan konstitusi ini HARUS
diprioritaskan, dan semua pekerjaan HARUS dapat ditelusuri dari kode kembali ke
spesifikasi.

- Fitur HARUS dapat ditelusuri melalui nama branch, spec.md, plan.md, dan
	tasks.md; PR HARUS menautkan ke folder spesifikasi yang relevan.
- Template dan dokumen yang dihasilkan HARUS menghindari abstraksi yang tidak
	diperlukan; hanya struktur yang membantu kejelasan, pengujian, atau delivery
	yang diperbolehkan.
- Setiap peningkatan kompleksitas struktural atau proses (layer tambahan,
	framework lintas-lapisan, alur non-standar) HARUS:
	- Dicatat di tabel "Complexity Tracking" pada plan.md.
	- Menyertakan alasan yang jelas dan alternatif yang lebih sederhana yang
		ditolak.
- Reviewer HARUS menolak perubahan yang secara material meningkatkan
	kompleksitas tanpa justifikasi terdokumentasi yang kredibel.

Alasan: Menegakkan kesederhanaan dan keterlacakan menjaga proyek tetap mudah
dipelihara dan mempermudah diagnosis regresi.

## Batasan Dokumentasi & Template

Bagian ini membatasi bagaimana template dokumentasi di `.specify/templates/`
digunakan dan dikembangkan.

- Dokumentasi fitur untuk sebuah branch HARUS berada di bawah
	`/specs/[###-feature-name]/` dengan minimal:
	- spec.md (spesifikasi fitur),
	- plan.md (rencana implementasi),
	- tasks.md (task implementasi),
	- file checklist opsional yang dibuat lewat `/speckit.checklist`.
- Bagian-bagian wajib di spec.md (User Scenarios & Testing, Requirements,
	Success Criteria) HARUS diisi dengan konten konkret sebelum fitur dianggap
	siap untuk diimplementasikan.
- File plan yang dihasilkan dari template plan HARUS mempertahankan bagian
	Constitution Check dan Complexity Tracking lalu memperbaruinya, bukan
	menghapusnya.
- File tasks yang dihasilkan dari template tasks HARUS mengorganisasi
	pekerjaan berdasarkan user story (US1, US2, …) dan dengan jelas menandai
	pekerjaan fondasi yang memblokir user story.
- Konten contoh di template (yang ditandai sebagai contoh atau ilustratif
	saja) TIDAK BOLEH ikut masuk ke dokumentasi fitur yang dikomit.

Alasan: Batasan ini menjaga semua artefak fitur tetap konsisten, dapat
dianalisis, dan selaras dengan prinsip di atas.

## Alur Kerja Pengembangan & Quality Gate

Workflow ujung-ke-ujung untuk sebuah fitur HARUS mengikuti gate berikut.

1. **Spec Gate**
	- Fitur baru dimulai dengan spec.md yang disusun menggunakan template spec.
	- Setidaknya satu story P1 dengan deskripsi independent test HARUS
		didefinisikan.
	- Kriteria keberhasilan HARUS terukur dan berfokus pada hasil pengguna atau
		sistem, bukan detail implementasi.

2. **Plan Gate**
	- Rencana implementasi (plan.md) HARUS dibuat dari template plan.
	- Bagian Constitution Check HARUS diisi sebelum riset Fase 0 berjalan.
	- Struktur proyek dan fondasi yang dipilih HARUS didokumentasikan.

3. **Tasks Gate**
	- Task (tasks.md) HARUS dibuat atau ditulis menggunakan template tasks.
	- Task HARUS dikelompokkan berdasarkan user story dan mencerminkan
		kemandirian story yang ditetapkan di spec.
	- Setiap pengujian yang diminta HARUS tercantum sebagai task eksplisit dan
		ditulis sebelum pekerjaan implementasi yang mengklaim memenuhi pengujian
		tersebut.

4. **Review Gate**
	- PR yang mengubah spec, plan, atau tasks HARUS direview untuk
		kepatuhan terhadap konstitusi.
	- Review HARUS memverifikasi: keterlacakan (spec → plan → tasks →
		implementasi), kepatuhan terhadap prinsip kesederhanaan, dan dokumentasi
		setiap kompleksitas di Complexity Tracking.

5. **Validation Gate**
	- Sebelum fitur dianggap selesai, Independent Tests yang didokumentasikan
		untuk setiap story yang selesai dan Success Criteria HARUS benar-benar
		terpenuhi.

Alasan: Gate eksplisit mencegah pekerjaan yang belum terspesifikasi dengan
baik atau tidak dapat ditelusuri masuk ke sistem dan menegakkan kualitas yang
konsisten.

## Tata Kelola

Konstitusi ini mengatur bagaimana spesifikasi, rencana, task, dan artefak
terkait dibuat dan dikelola untuk API-X.

- **Otoritas**
	- Konstitusi ini menggantikan praktik ad-hoc terkait cara menyusun spec,
		plan, dan tasks di repository ini.
	- Semua perintah `/speckit.*` dan panduan pengembangan apa pun yang
		diturunkan darinya HARUS menghormati prinsip-prinsip ini.

- **Amandemen**
	- Amandemen HARUS diajukan melalui pull request yang:
		- Mengedit file konstitusi ini.
		- Memperbarui template yang terdampak di `.specify/templates/`.
		- Menyertakan ringkasan singkat mengenai alasan dan dampaknya di deskripsi
			PR.
	- Versi mengikuti semantic versioning:
		- MAJOR: Perubahan prinsip yang tidak kompatibel ke belakang atau
			penghapusan.
		- MINOR: Prinsip baru atau perluasan panduan yang material.
		- PATCH: Klarifikasi, perbaikan bahasa, atau penyempurnaan non-semantik.
	- Laporan Dampak Sinkronisasi di bagian atas file ini HARUS diperbarui pada
		setiap amandemen untuk mencerminkan perubahan versi dan bagian yang
		terpengaruh.

- **Kepatuhan & Review**
	- Semua PR yang menyentuh file spec, plan, tasks, atau checklist HARUS
		dievaluasi terhadap konstitusi ini.
	- Placeholder di dokumen fitur yang dikomit HARUS diselesaikan atau dengan
		jelas ditandai sebagai `NEEDS CLARIFICATION` beserta penjelasannya.
	- File panduan yang dibuat agen (misalnya development guidelines yang
		berdasarkan agent-file-template.md) HARUS tetap konsisten dengan prinsip
		yang didefinisikan di sini dan TIDAK BOLEH mendefinisikan ulang tata
		kelola.

- **Panduan Runtime**
	- Praktik pengembangan harian SEBAIKNYA merujuk ke development guidelines
		yang dihasilkan dari `agent-file-template.md`, tetapi guideline tersebut
		HARUS tetap berada di bawah konstitusi ini.

**Versi**: 1.0.0 | **Diratifikasi**: 2026-03-04 | **Terakhir Diubah**: 2026-03-04

