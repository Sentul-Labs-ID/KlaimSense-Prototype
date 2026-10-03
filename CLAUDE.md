# CLAUDE.md — Aturan proyek JKN-Sentinel

Aturan ini wajib dipatuhi di **semua fase**. Jika ada konflik dengan instruksi lain, hentikan dan tanyakan.

## Di awal setiap sesi

1. Baca `ROADMAP.md` sampai habis (status fase, prinsip, konvensi dokumentasi).
2. Baca file ini (`CLAUDE.md`).
3. Untuk pekerjaan di `frontend/`, baca juga `frontend/AGENTS.md`: versi Next.js yang dipakai punya perubahan API, jadi cek dokumentasi di `frontend/node_modules/next/dist/docs/` sebelum menulis kode.

## Prinsip proyek (dari ROADMAP.md)

1. **Hanya data tiruan.** Tidak memakai, mengunduh, atau meminta data peserta JKN asli.
2. **Skor dihitung deterministik.** Aturan tetap dan statistik. AI tidak menghitung, mengubah, atau menebak skor.
3. **AI hanya merangkum dan mengutip.** Kutipan regulasi wajib berasal dari korpus lokal (`data/regulasi/`); kutipan tanpa sumber tidak ditampilkan.
4. **Parameter tidak di-hardcode.** Semua batas ada di `config/parameter.yaml` (dibaca lewat `sentinel.parameter.muat_parameter`), dengan catatan bahwa nilai default bersifat ilustratif.
5. **Level hari.** Pengecekan dilakukan per tanggal, sesuai bentuk data klaim.
6. **Ground truth terpisah.** Label kecurangan hanya boleh dibaca modul evaluasi (`sentinel/evaluation/`), tidak oleh mesin aturan.
7. **Manusia memutuskan.** Sistem memberi prioritas pemeriksaan, bukan vonis. Hindari kata "curang/terbukti" di antarmuka; pakai "perlu diperiksa", "temuan", "prioritas".
8. **Bisa direproduksi.** Data acak memakai seed; data yang sama selalu menghasilkan skor yang sama.

## Aturan kerja

- **Bahasa antarmuka pengguna: Indonesia.** Semua teks yang dilihat petugas, juri, atau pembaca laporan ditulis dalam bahasa Indonesia.
- **Nama variabel dan kode:** boleh Indonesia atau Inggris, tetapi **konsisten per modul**. Jangan mencampur dua bahasa untuk konsep yang sama di satu modul.
- **Setiap fitur wajib punya tes pytest** di `backend/tests/`. `make test` harus lulus sebelum commit.
- **Dependensi besar** (library baru di luar yang sudah ada di `backend/pyproject.toml` / `frontend/package.json`) tidak boleh ditambahkan tanpa menyebutkan alasannya di `docs/DEVLOG.md`.
- **Batas akses tabel** (lihat `backend/sentinel/models/` dan `docs/ARSITEKTUR.md`), dijaga oleh `tests/test_batas_akses.py`:
  - **Dunia fisik**: `sesi_aktual` hanya boleh dibaca `sensor/simulator.py` (dan evaluasi). Generator yang menciptakannya juga boleh menulisnya.
  - **Perangkat** (`sensor/edge.py`, `sensor/protokol.py`): tidak boleh menyentuh basis data sama sekali; hanya menerima larik arus dan mengirim pesan bertanda tangan.
  - **Server** (ingest, ringkasan, API, mesin aturan): hanya membaca tabel `master`, `transaksi`, `sensor` (data dari perangkat), dan `hasil`. DILARANG membaca `sesi_aktual`, `ground_truth`, `profil_rs`, `kasus_sah`.
  - **Tabel evaluasi** (`ground_truth`, `profil_rs`, `kasus_sah`) hanya boleh dibaca evaluasi dan tidak boleh diekspos API dashboard. Yang boleh menulisnya hanya generator dan harness gangguan sensor (`sensor/gangguan.py`).
- **Kejujuran evaluasi**: dataset utama untuk mengembangkan; dataset hidden hanya dijalankan setelah kode evaluasi selesai, setiap jalannya tercatat di `reports/log_evaluasi_hidden.json`. Dilarang mengubah parameter, bobot, ambang, atau aturan berdasarkan hasil hidden. Bug aturan/sensor yang ditemukan saat evaluasi tidak boleh diperbaiki diam-diam: laporkan, minta persetujuan, catat, dan ungkapkan di laporan.
- **Konfigurasi rahasia** hanya lewat environment (`.env`, lihat `.env.example`). Jangan commit `.env` atau kunci API.

## Akhir setiap fase: langkah dokumentasi wajib

Sesuai `ROADMAP.md` bagian "Konvensi dokumentasi":

1. Commit kode: `feat(fase-N): ...` / `fix(fase-N): ...` / `test(fase-N): ...`.
2. Simpan prompt fase **verbatim** ke `docs/prompts/FASE-XX_nama.md` (format arsip di ROADMAP.md), perbarui `docs/prompts/README.md`. Jangan menimpa prompt lama; buat `_v2`, `_v3` jika diulang.
3. Perbarui status fase dan "Log progres" di `ROADMAP.md`.
4. Tambahkan entri di `docs/DEVLOG.md` (terbaru di atas).
5. Naikkan versi dan tambahkan entri di `CHANGELOG.md` (Fase N selesai = `0.(N+1).0`).
6. Catat penyimpangan dari roadmap di `ROADMAP.md` bagian "Catatan penyimpangan".
7. Commit dokumentasi terpisah: `docs(fase-N): ...`.

## Perintah

| Perintah | Fungsi |
|---|---|
| `make up` | Bangun dan jalankan db, backend (:8000), frontend (:3000) |
| `make down` | Hentikan layanan |
| `make reset-db` | Hapus dan buat ulang database kosong |
| `make test` | Jalankan pytest backend di container |
| `make generate` | Bangkitkan dataset tiruan `utama` (seed 42) dan `hidden` (seed 2026) ke database; menghapus hasil aturan dan data sensor dataset itu, jadi lanjutkan dengan `make sensor` |
| `make rules` | Jalankan mesin aturan (utama dan hidden), tulis `temuan` dan `skor`, cetak 10 RS teratas |
| `make sensor` | Simulasi sensor IoT + edge AI (kedua dataset), lalu `make rules` ulang |
| `make eval` | Evaluasi akurasi (utama lalu hidden) → `reports/evaluasi.md`, `.json`, grafik PNG |
| `make demo` | Diisi di fase 7 |

Tes cepat tanpa Docker: `cd backend && python -m venv .venv && .venv/Scripts/pip install -e ".[dev]" && .venv/Scripts/python -m pytest` (Windows; di Linux/macOS pakai `.venv/bin/`).
