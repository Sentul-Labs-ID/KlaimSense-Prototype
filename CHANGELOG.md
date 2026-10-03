# Changelog

Semua perubahan penting pada proyek ini dicatat di file ini.

Format mengikuti [Keep a Changelog](https://keepachangelog.com/id-ID/1.1.0/), dan proyek ini memakai [Semantic Versioning](https://semver.org/lang/id/). Versi `0.x.0` naik setiap fase selesai (Fase 0 = 0.1.0, Fase 1 = 0.2.0, dan seterusnya).

## [Unreleased]

## [0.5.0] - 2026-10-03

Fase 4: evaluasi akurasi.

### Added
- Modul evaluasi `backend/sentinel/evaluation/` (satu-satunya pembaca label; hanya membaca, transaksi READ ONLY):
  - recall per skenario (aturan pasangan dan aturan apa pun);
  - presisi tiga kelas per aturan (benar / kasus sah / keliru);
  - metrik prioritas di level RS-periode: presisi dan recall tinggi dan tinggi+sedang, top-5/top-10, matriks prioritas × kondisi, sebaran per profil, alasan prioritas;
  - integritas sensor dan ringkasan BAND-01;
  - interval kepercayaan 95% Wilson untuk setiap proporsi.
- `make eval`: evaluasi utama lalu hidden. Keluaran `reports/evaluasi.md` (bahasa Indonesia, termasuk "Angka untuk proposal", analisis pasca-jalan hidden, dan keterbatasan), `reports/evaluasi.json`, `reports/recall_per_skenario.png`, `reports/prioritas_hidden.png`.
- Log permanen jalan evaluasi hidden (`reports/log_evaluasi_hidden.json`) dan opsi `--hanya-laporan` untuk merender ulang tanpa menghitung ulang.
- Tes metrik pada data buatan tangan, Wilson terhadap nilai acuan, pemetaan skenario, evaluasi tidak menulis ke tabel mana pun, dan konsistensi kalimat slide; total 189 tes.

### Changed
- `docker-compose.yml`: `reports/` di-mount ke container backend.
- Dependensi baru: `matplotlib`.

## [0.4.0] - 2026-10-03

Fase 3: sensor IoT dan edge AI (Langkah 2: Cek sensor), seluruhnya simulasi.

### Added
- Simulator dunia fisik `sensor/simulator.py`: arus listrik per menit per mesin hemodialisa dari sesi yang benar-benar terjadi. Pola mati/standby/terapi dengan noise dan tumpang tindih; nilai ampere ilustratif.
- Edge AI `sensor/edge.py`:
  - fitur per jendela 10 menit;
  - pohon keputusan scikit-learn (akurasi uji 97,75%, dilatih dengan seed khusus pelatihan);
  - pesan ringkasan status per jendela, ditandatangani Ed25519 dan dirantai hash.
- Model edge tersimpan sebagai "firmware" (`backend/sentinel/sensor/model/`) beserta hash SHA-256 dan metadata; `python -m sentinel.sensor latih` untuk melatih ulang.
- Server:
  - fungsi `ingest` dan endpoint `POST /sensor/ingest` (satu pesan atau batch) dengan deteksi TAMPER_SIG, TAMPER_CHAIN, TAMPER_GAP;
  - tabel `perangkat`, `status_sensor`, `sensor_anomali`, `status_mesin_harian`.
- Skenario gangguan di kedua dataset (pesan palsu, sensor dicabut ±2 jam), dicatat di ground truth.
- Aturan SEN-01 (selisih jam-mesin terapi dan integritas data sensor); skor maksimum kini 100.
- Lantai prioritas: aturan bukti fisik yang jenuh (KAP-01, KAP-02, SEN-01 selisih) membuat prioritas minimal "tinggi"; kolom `skor.alasan_prioritas`.
- Parameter baru: `sensor.batas_data_hilang_persen`, `sensor.gap_maks_jendela`, titik jenuh SEN-01 per kategori, `skor.aturan_bukti_fisik`.
- `make sensor` (kedua dataset paralel per perangkat, lalu `make rules`).
- Tes integritas pesan, edge AI, SEN-01, uji integrasi kasus sah shift darurat, dan batas akses tiga sisi; total 172 tes.

### Changed
- `temuan` mendapat kolom `kategori`; `skor` mendapat kolom `alasan_prioritas` (migrasi otomatis).
- `make generate` juga menghapus data sensor dataset itu; urutan kerja: `make generate` → `make sensor`.
- Dockerfile memasang dependensi sebelum menyalin kode (build ulang cepat).
- Dependensi baru: `cryptography`, `scikit-learn==1.9.1`, `numpy`.

## [0.3.0] - 2026-10-03

Fase 2: mesin aturan (Langkah 1: Hitung).

### Added
- Mesin aturan `backend/sentinel/rules/`: KAP-01 (fisioterapi), KAP-02 (hemodialisa, termasuk sesi pada hari unit tutup), ULG-01 (tagihan identik), ULG-02 (sesi HD ganda sehari), WJR-01 (harga di atas acuan + toleransi), WJR-02 (alat bantu dengar sebelum masa penggantian), BAND-01 (robust z-score leave-one-out terhadap RS sejenis, dengan fallback ke kelas).
- Tabel `temuan` (penjelasan dari template bahasa Indonesia) dan `skor` (per RS per bulan, 0–100, rincian per aturan, versi aturan, hash parameter).
- Bagian `skor` di `config/parameter.yaml`: titik jenuh per aturan dan ambang prioritas (tinggi ≥ 20, sedang ≥ 10), semuanya ilustratif.
- `sentinel.parameter.hash_parameter()` (SHA-256 isi `parameter.yaml`).
- CLI `python -m sentinel.rules --dataset utama|hidden` dan `make rules` (10 RS teratas per dataset beserta aturan pemicunya).
- Tes per aturan (melanggar, tidak melanggar, tepat di batas), BAND-01, rumus skor, determinisme, hash, kecepatan, dan batas akses tabel lewat database; total 122 tes.
- Definisi aturan dan rumus skor untuk pembaca non-teknis di `docs/ARSITEKTUR.md`.

### Changed
- `make generate` kini juga menghapus `temuan` dan `skor` dataset yang dibangkitkan ulang.

## [0.2.0] - 2026-10-03

Fase 1: generator data tiruan.

### Added
- Skema database `backend/sentinel/models/` dengan kolom `dataset_id` di semua tabel:
  - `master`: `rumah_sakit`, `kapasitas`, `pasien`, `harga_acuan`.
  - `transaksi`: `tagihan`, `riwayat_alat_bantu_dengar`.
  - `kenyataan`: `sesi_aktual`.
  - `evaluasi`: `ground_truth`, `profil_rs`, `kasus_sah`.
- Generator data tiruan berseed `python -m sentinel.generator`:
  - Opsi `--dataset`, `--hidden`, `--seed`, `--days`, `--rs`, `--mulai`, `--dry-run`.
  - Ringkasan per dataset dan sidik SHA-256.
- Tujuh skenario kecurangan tercatat di `ground_truth`: KAP_FISIO, KAP_HD, ULANG_IDENTIK, ULANG_HARI, HARGA_LEBIH, ABD_DINI, SENSOR_PALSU.
- Rumah sakit kontrol (jujur-sibuk, kelas A volume tinggi, RS jujur bersensor) dan kasus sah di area batas (HD_SHIFT_TAMBAHAN, FISIO_LEMBUR, HARGA_ACUAN_LAMA).
- Dataset `hidden` (seed 2026) dengan distribusi penyisipan berbeda untuk evaluasi akhir.
- `make generate` membangkitkan dataset utama dan hidden ke PostgreSQL, mengganti data lama dataset yang sama.
- Tes generator, penyimpanan (SQLite), dan penjaga batas akses tabel (`test_batas_akses.py`); total 70 tes.

### Changed
- `CLAUDE.md` dan `docs/ARSITEKTUR.md`: aturan batas akses tabel dan perintah `make generate`.

## [0.1.0] - 2026-10-03

Fase 0: setup repo dan aturan proyek.

### Added
- `CLAUDE.md` berisi prinsip proyek dan aturan kerja untuk semua fase.
- Backend FastAPI (`backend/sentinel/`): settings dari environment (`DATABASE_URL`, `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`, `DEMO_MODE`, `PARAMETER_PATH`), koneksi SQLAlchemy 2.x + psycopg, endpoint `GET /health`, kerangka modul `generator`, `rules`, `sensor`, `evaluation`, `agents`, `api`.
- `config/parameter.yaml` berisi parameter kapasitas, kewajaran, perbandingan, sensor, dan bobot skor 8 aturan (semua ilustratif), serta loader tervalidasi `sentinel.parameter.muat_parameter`.
- Frontend Next.js (App Router, TypeScript, Tailwind) dengan beranda yang menampilkan status koneksi backend lewat `BACKEND_URL`.
- `docker-compose.yml` (PostgreSQL 16 dengan volume, backend :8000, frontend :3000), `.env.example`, `.gitignore`, `.gitattributes`.
- `Makefile` dengan target `up`, `down`, `reset-db`, `test`, serta placeholder `generate`, `rules`, `sensor`, `eval`, `demo`.
- Tes pytest: `/health`, settings, dan validasi parameter (12 tes).
- Dokumentasi: `README.md`, `docs/ARSITEKTUR.md`, `docs/DEVLOG.md`, `docs/prompts/` (arsip prompt FASE-00), `CHANGELOG.md`.
