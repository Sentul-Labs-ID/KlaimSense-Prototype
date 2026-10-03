# JKN-Sentinel Prototype

> **Seluruh data di repositori ini adalah data tiruan.** Tidak ada data peserta JKN, rumah sakit, atau klaim asli yang dipakai, diunduh, atau disimpan.

Prototipe untuk proposal **BPJS Kesehatan Healthkathon 2026**, kategori Efisiensi Risiko pada Fasilitas Kesehatan, oleh tim Sentul Labs.

JKN-Sentinel memeriksa setiap tagihan (klaim) rumah sakit ke BPJS dengan dua pertanyaan:

1. **Mungkinkah layanan ini terjadi** dengan kapasitas nyata rumah sakit (tenaga, mesin, tempat tidur)?
2. **Wajarkah tagihannya** menurut aturan (harga acuan, masa penggantian alat, batas jumlah)?

Alur kerja empat langkah: **Hitung → Cek sensor → Rangkum → Putuskan**. Sistem memberi prioritas pemeriksaan; keputusan tetap di tangan petugas.

## Prasyarat

| Alat | Versi | Dipakai untuk |
|---|---|---|
| Docker + Docker Compose | Docker 24+, Compose v2 | Menjalankan db, backend, frontend (`make up`, `make test`) |
| GNU Make | 4.x | Perintah `make ...` |
| Node.js + npm | 22 LTS | Menjalankan/mengembangkan frontend di luar Docker |
| Python | 3.11+ | Menjalankan backend dan tes di luar Docker |

**Memasang `make` di Windows** (tidak tersedia bawaan):

```powershell
winget install ezwinports.make
```

Tutup lalu buka ulang terminal agar `make` masuk ke PATH. Di macOS `make` sudah ada lewat Xcode Command Line Tools (`xcode-select --install`); di Linux pasang paket `make`/`build-essential`.

## Menjalankan

```bash
cp .env.example .env   # opsional, nilai default sudah cukup untuk lokal
make up                # db (5432), backend (8000), frontend (3000)
make test              # pytest backend
make down
```

- Backend: <http://localhost:8000/health> → `{"status": "ok", "versi": "0.1.0"}`
- Frontend: <http://localhost:3000> → menampilkan status koneksi backend

### Tanpa Docker (pengembangan)

```bash
# Backend (perlu PostgreSQL; set DATABASE_URL dengan host localhost di .env)
cd backend
python -m venv .venv
.venv/Scripts/pip install -e ".[dev]"     # Linux/macOS: .venv/bin/pip
.venv/Scripts/python -m pytest
.venv/Scripts/uvicorn sentinel.main:app --reload

# Frontend (BACKEND_URL default http://localhost:8000)
cd frontend
npm install
npm run dev
```

Frontend memanggil backend lewat variabel environment `BACKEND_URL`: `http://backend:8000` di docker-compose, `http://localhost:8000` jika dijalankan di luar Docker.

Parameter aturan ada di [`config/parameter.yaml`](config/parameter.yaml). **Semua nilai default ilustratif** dan wajib divalidasi bersama BPJS dan organisasi profesi.

## Dokumentasi

- [ROADMAP.md](ROADMAP.md): fase, status, prinsip proyek
- [CLAUDE.md](CLAUDE.md): aturan kerja proyek
- [docs/ARSITEKTUR.md](docs/ARSITEKTUR.md): alur dan modul
- [docs/DEVLOG.md](docs/DEVLOG.md), [CHANGELOG.md](CHANGELOG.md), [docs/prompts/](docs/prompts/README.md)
