# Changelog

Semua perubahan penting pada proyek ini dicatat di file ini.

Format mengikuti [Keep a Changelog](https://keepachangelog.com/id-ID/1.1.0/), dan proyek ini memakai [Semantic Versioning](https://semver.org/lang/id/). Versi `0.x.0` naik setiap fase selesai (Fase 0 = 0.1.0, Fase 1 = 0.2.0, dan seterusnya).

## [Unreleased]

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
