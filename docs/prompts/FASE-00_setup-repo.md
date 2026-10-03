# FASE-00 — Setup repo dan aturan proyek

| Kolom | Isi |
|---|---|
| Versi | v1 |
| Tanggal dijalankan | 2026-10-02 (prompt lanjutan 2026-10-03) |
| Dijalankan oleh | Rifandi Indrayudha Prawira |
| Alat | Claude Code |
| Commit hasil | bd5ee146d4d86000f517ed9d7e92cae9d6aa591b |
| Status | Berhasil |

## Prompt (verbatim)

```text
Konteks: repo ini adalah prototype JKN-Sentinel untuk proposal BPJS Kesehatan Healthkathon 2026. Sebelum mulai, baca ROADMAP.md di root sampai habis. Ikuti prinsip proyek, struktur repo target, dan konvensi dokumentasi yang tertulis di sana.

Ini adalah FASE 0: setup repo dan aturan proyek. Jangan menulis logika bisnis (generator data, aturan, sensor, dashboard) di fase ini. Cukup kerangka yang bisa berjalan.

TUGAS

1. CLAUDE.md di root
   Tulis aturan proyek yang wajib dipatuhi di semua fase berikutnya, diambil dari bagian "Prinsip proyek" di ROADMAP.md, ditambah:
   - Selalu baca ROADMAP.md dan CLAUDE.md di awal setiap sesi.
   - Bahasa antarmuka pengguna: Indonesia. Nama variabel dan kode: boleh Indonesia atau Inggris, tapi konsisten per modul.
   - Setiap fitur wajib punya tes pytest.
   - Jangan menambah dependensi besar tanpa menyebutkan alasannya di DEVLOG.
   - Setiap fase diakhiri dengan langkah dokumentasi wajib sesuai ROADMAP.md.

2. Backend (backend/)
   - Python 3.11+, FastAPI, SQLAlchemy 2.x, psycopg, pydantic-settings, pytest, httpx. Kelola dependensi dengan pyproject.toml.
   - Paket utama: backend/sentinel/ dengan subfolder kosong (berisi __init__.py) untuk modul berikutnya: generator/, rules/, sensor/, evaluation/, agents/, api/.
   - Konfigurasi dibaca dari environment lewat pydantic-settings: DATABASE_URL, ANTHROPIC_API_KEY, ANTHROPIC_MODEL, DEMO_MODE.
   - Endpoint GET /health mengembalikan {"status": "ok", "versi": "0.1.0"}.
   - Tes: backend/tests/test_health.py.

3. Frontend (frontend/)
   - Next.js (TypeScript, App Router) dengan Tailwind.
   - Halaman beranda sederhana bertuliskan "JKN-Sentinel" dan subjudul "Setiap klaim harus mungkin terjadi dan wajar tagihannya", serta status koneksi ke backend /health.

4. Konfigurasi parameter: config/parameter.yaml
   Isi semua parameter dari tabel "Parameter yang wajib divalidasi" di ROADMAP.md dengan nilai default-nya. Setiap parameter diberi komentar: arti, satuan, dan catatan "ILUSTRATIF, wajib divalidasi bersama BPJS dan organisasi profesi". Tambahkan juga bagian bobot skor per aturan (KAP-01, KAP-02, ULG-01, ULG-02, WJR-01, WJR-02, BAND-01, SEN-01) dengan nilai awal yang wajar dan komentar bahwa bobot akan disetel di fase 2. Sediakan loader Python yang memvalidasi file ini (pydantic) beserta tesnya.

5. Infrastruktur
   - docker-compose.yml: postgres:16 (dengan volume), backend (port 8000), frontend (port 3000).
   - .env.example berisi semua variabel environment tanpa nilai rahasia. .env masuk .gitignore.
   - .gitignore untuk Python, Node, .env, data hasil generate, dan reports sementara.
   - Makefile dengan target: up, down, reset-db, test, generate, rules, sensor, eval, demo. Target yang belum diimplementasikan cukup mencetak "Belum tersedia: diimplementasikan di fase N".

6. Kerangka dokumentasi
   - docs/ARSITEKTUR.md: alur empat langkah (Hitung, Cek sensor, Rangkum, Putuskan), diagram teks sederhana, dan daftar modul per fase.
   - docs/DEVLOG.md: judul dan format entri sesuai ROADMAP.md.
   - CHANGELOG.md: format Keep a Changelog.
   - docs/prompts/README.md: indeks arsip prompt (tabel: fase, versi, file, tanggal, status).
   - README.md: deskripsi singkat proyek, cara menjalankan (make up, make test), dan pernyataan bahwa seluruh data adalah data tiruan.

SELESAI JIKA
- `make up` menjalankan ketiga layanan, http://localhost:8000/health merespons, dan halaman frontend menampilkan status backend "terhubung".
- `make test` lulus.
- Laporkan hasil kedua perintah itu kepada saya sebelum langkah dokumentasi.

LANGKAH DOKUMENTASI WAJIB (lakukan berurutan)
1. Commit kode dengan pesan "feat(fase-0): setup repo dan aturan proyek". Catat hash commit ini.
2. Simpan prompt ini VERBATIM, dari kalimat "Konteks:" sampai baris terakhir, ke docs/prompts/FASE-00_setup-repo.md dengan format arsip di ROADMAP.md. Isi "Dijalankan oleh" dari `git config user.name`, "Commit hasil" dengan hash dari langkah 1, dan bagian "Catatan hasil" dengan apa yang dibuat, masalah yang muncul, dan penyimpangan. Perbarui docs/prompts/README.md.
3. Di ROADMAP.md: ubah status Fase 0 menjadi ✅ dan tambahkan baris di "Log progres".
4. Tambahkan entri di docs/DEVLOG.md.
5. Tambahkan entri versi 0.1.0 di CHANGELOG.md.
6. Jika ada keputusan yang berbeda dari ROADMAP.md, catat di bagian "Catatan penyimpangan".
7. Commit dokumentasi dengan pesan "docs(fase-0): arsip prompt, roadmap, devlog, changelog".
```

## Catatan hasil

### Yang dihasilkan

- `CLAUDE.md`: 8 prinsip proyek dari ROADMAP.md ditambah aturan kerja (baca ROADMAP/CLAUDE di awal sesi, UI berbahasa Indonesia, konsistensi bahasa kode per modul, tes pytest wajib, alasan dependensi di DEVLOG, langkah dokumentasi wajib).
- `backend/`: paket `sentinel` (FastAPI, SQLAlchemy 2.x, psycopg, pydantic-settings) dengan subpaket kosong `generator/`, `rules/`, `sensor/`, `evaluation/`, `agents/`, `api/`; `config.py` (settings dari environment), `db.py` (engine dan `Base`), `parameter.py` (loader dan validasi `config/parameter.yaml`), `main.py` (`GET /health`). Dependensi dikelola di `pyproject.toml`; Dockerfile berbasis `python:3.12-slim`.
- Tes: `test_health.py` (1), `test_parameter.py` (9), `test_config.py` (2) = **12 tes lulus**.
- `frontend/`: Next.js 16.3.8 (App Router, TypeScript, Tailwind v4), output `standalone`. Beranda menampilkan judul, subjudul, dan status backend yang dicek dari sisi server per permintaan.
- `config/parameter.yaml`: 7 parameter dari tabel ROADMAP (8 kunci, karena masa penggantian alat bantu dengar dipisah menjadi tahun dan flag per telinga), masing-masing dengan arti, satuan, aturan terkait, dan catatan ILUSTRATIF; bobot 8 aturan berjumlah 100.
- Infrastruktur: `docker-compose.yml` (db postgres:16 + volume `pgdata`, backend :8000, frontend :3000, healthcheck), `.env.example`, `.gitignore`, `.gitattributes`, `Makefile` (up, down, reset-db, test, dan placeholder generate/rules/sensor/eval/demo).
- Dokumentasi: `docs/ARSITEKTUR.md`, `docs/DEVLOG.md`, `CHANGELOG.md`, `docs/prompts/README.md`, `README.md`.
- Verifikasi: `make up` → ketiga layanan *healthy*; `/health` → `{"status":"ok","versi":"0.1.0"}`; frontend menampilkan "terhubung (versi 0.1.0)"; `make test` → 12 passed; `make reset-db` dan target placeholder berjalan di Git Bash maupun PowerShell.

### Masalah yang muncul

- `make` tidak terpasang di mesin Windows. Solusi: `winget install ezwinports.make`; PATH baru aktif setelah terminal dibuka ulang. Cara pasang dicatat di README.
- Folder proyek belum berupa repo git. Solusi: `git init -b main`.
- `create-next-app` membuat repo git bersarang di `frontend/.git` walau diberi `--skip-git`. Solusi: folder itu dihapus.
- Starlette terbaru memberi peringatan bahwa `httpx` untuk TestClient deprecated (disarankan `httpx2`). `httpx` tetap dipakai sesuai prompt; peringatan disaring di konfigurasi pytest.
- Repo GitHub `Sentul-Labs-ID/JKN-Sentinel-Prototype` ternyata kosong (tidak ada branch), berbeda dengan prompt lanjutan pertama yang menyebut sudah ada commit ROADMAP.md. Pekerjaan dihentikan dan dikonfirmasi ke pengguna; keputusan: commit fase 0 menjadi commit pertama.

### Penyimpangan dari prompt atau roadmap

Dicatat juga di `ROADMAP.md` bagian Catatan penyimpangan.

1. Dependensi tambahan `pyyaml` (tidak ada di daftar prompt) untuk membaca `parameter.yaml`.
2. Variabel environment opsional tambahan `PARAMETER_PATH` (default `config/parameter.yaml`).
3. Variabel environment tambahan `BACKEND_URL` untuk frontend (diminta di prompt lanjutan 1).
4. Jumlah bobot aturan divalidasi harus = 100. Keputusan ini akan ditinjau di fase 2.
5. Default `ANTHROPIC_MODEL` awalnya `claude-opus-5-5`, diubah ke `claude-sonnet-5` lewat prompt lanjutan 1; ID model dicek ulang sebelum fase 6.
6. Status backend di frontend dicek dari server Next.js (bukan dari browser), sehingga backend tidak perlu CORS.
7. File `frontend/AGENTS.md` dan `frontend/CLAUDE.md` bawaan Next.js 16 dipertahankan (peringatan perubahan API Next.js).
8. Tambahan `.gitattributes` (LF) dan folder `data/regulasi/`, `reports/`, `assets/` berisi `.gitkeep`.
9. Image backend memakai Python 3.12; venv lokal untuk tes cepat memakai Python 3.13.
10. Repo remote kosong, sehingga `ROADMAP.md` masuk lewat commit pertama (`feat(fase-0)`), bukan lewat commit yang sudah ada di remote.

### Prompt lanjutan 1 (verbatim, 2026-10-03)

```text
Hasil fase 0 sudah sesuai. Sebelum langkah dokumentasi, lakukan tiga penyesuaian ini dulu:

1. Hubungkan ke repo GitHub sebelum commit pertama. Remote: https://github.com/Sentul-Labs-ID/JKN-Sentinel-Prototype.git. Di sana sudah ada commit berisi ROADMAP.md. Tambahkan remote origin, fetch, lalu jadikan origin/main sebagai dasar branch main lokal tanpa menghapus file kerja (misalnya git reset origin/main tanpa --hard). Pastikan ROADMAP.md lokal sama dengan versi di remote; jika berbeda, tunjukkan perbedaannya kepada saya sebelum melanjutkan. Jangan force push.

2. Jadikan alamat backend yang dipakai frontend sebagai variabel environment BACKEND_URL (default http://backend:8000 di docker-compose, dan http://localhost:8000 jika frontend dijalankan di luar Docker). Tambahkan ke .env.example. Di README, tambahkan bagian prasyarat: Docker, Node, Python, dan make (sebutkan cara pasang make di Windows lewat winget).

3. Ubah default ANTHROPIC_MODEL menjadi claude-sonnet-5 (tetap bisa diubah lewat .env).

Jalankan ulang make test dan pastikan frontend tetap menampilkan status "terhubung". Lalu lanjutkan 7 langkah dokumentasi fase 0. Di arsip prompt FASE-00, catat pesan ini secara verbatim di bagian "Catatan hasil" sebagai prompt lanjutan, dan masukkan semua penyimpangan yang kamu laporkan (termasuk bobot berjumlah 100 sebagai keputusan yang akan ditinjau di fase 2) ke bagian Catatan penyimpangan di ROADMAP.md. Setelah kedua commit selesai, push ke origin main.
```

Hasil: remote ditambahkan, tetapi repo kosong sehingga langkah reset ke `origin/main` tidak bisa dilakukan; pekerjaan dihentikan untuk konfirmasi. Penyesuaian 2 dan 3 selesai: `BACKEND_URL` di docker-compose, `.env.example`, dan README (bagian Prasyarat dan menjalankan tanpa Docker); default model `claude-sonnet-5`; tes baru `test_config.py`. `make test` → 12 passed; frontend tetap "terhubung".

### Prompt lanjutan 2 (verbatim, 2026-10-03)

```text
Pilih opsi 2. Repo GitHub memang masih kosong; ROADMAP.md sebelumnya hanya ada di folder lokal dan belum pernah di-push. Jadikan dua commit fase 0 sebagai commit pertama, dengan ROADMAP.md ikut di commit feat. Lanjutkan 7 langkah dokumentasi fase 0, lalu push ke origin main dengan push biasa (tanpa force).

Di arsip prompt FASE-00, bagian "Catatan hasil", catat verbatim pesan lanjutan saya sebelumnya (tiga penyesuaian) dan pesan ini. Catat di Catatan penyimpangan bahwa repo remote ternyata kosong sehingga ROADMAP.md masuk lewat commit pertama.

Soal model: tetap pakai claude-sonnet-5 untuk sekarang. Tambahkan komentar di .env.example bahwa ID model perlu dicek ulang di dokumentasi resmi Anthropic sebelum fase 6.
```

Hasil: komentar pengecekan ID model ditambahkan di `.env.example`; commit `feat(fase-0)` (bd5ee14) menjadi commit pertama dan memuat `ROADMAP.md`; langkah dokumentasi dilanjutkan dan kedua commit di-push ke `origin main` tanpa force.
