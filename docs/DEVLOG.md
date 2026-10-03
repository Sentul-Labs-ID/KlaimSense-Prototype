# DEVLOG — JKN-Sentinel

Satu entri per sesi kerja, **terbaru di atas**. Format:

```markdown
## YYYY-MM-DD — Fase X: judul singkat
- Dikerjakan:
- Keputusan:
- Masalah dan solusi:
- Penyimpangan dari roadmap:
- Berikutnya:
```

---

## 2026-10-03 — Fase 0: setup repo dan aturan proyek
- Dikerjakan: monorepo (`backend/` FastAPI + SQLAlchemy 2.x + psycopg, `frontend/` Next.js 16 + Tailwind, PostgreSQL 16 lewat docker-compose); `CLAUDE.md`; `config/parameter.yaml` beserta loader pydantic `sentinel.parameter.muat_parameter`; `GET /health`; Makefile (up, down, reset-db, test, placeholder fase 1–7); kerangka dokumentasi. 12 tes pytest lulus; frontend menampilkan status backend "terhubung". Repo dihubungkan ke `github.com/Sentul-Labs-ID/JKN-Sentinel-Prototype`.
- Keputusan:
  - Dependensi tambahan `pyyaml` (kecil, murni untuk membaca `parameter.yaml`; PyYAML adalah parser YAML standar de facto di Python).
  - Validasi parameter ketat (`extra="forbid"`): salah ketik nama parameter langsung gagal, bukan diam-diam memakai default.
  - Jumlah bobot aturan wajib 100 agar skor 0–100 langsung terbaca; ditinjau di fase 2.
  - Status backend dicek dari server Next.js lewat `BACKEND_URL` (`http://backend:8000` di Docker, `http://localhost:8000` di luar Docker), jadi backend belum perlu CORS.
  - Di dalam container backend, kode berada di `/repo/backend` dan `config/` di-mount ke `/repo/config`, sehingga path relatif sama dengan di repo lokal.
  - `make test` menjalankan pytest di container backend agar tidak bergantung pada Python lokal.
  - Default `ANTHROPIC_MODEL=claude-sonnet-5` (permintaan pengguna; dicek ulang sebelum fase 6).
- Masalah dan solusi:
  - `make` tidak ada di Windows → `winget install ezwinports.make` (dicatat di README).
  - `create-next-app` membuat `frontend/.git` bersarang → dihapus.
  - Starlette memperingatkan `httpx` deprecated untuk TestClient (menyarankan `httpx2`) → `httpx` tetap dipakai sesuai prompt, peringatan disaring di `pyproject.toml`.
  - Remote GitHub ternyata kosong → setelah konfirmasi, commit fase 0 menjadi commit pertama dan memuat `ROADMAP.md`.
- Penyimpangan dari roadmap: lihat `ROADMAP.md` bagian Catatan penyimpangan (10 baris bertanggal 2026-10-03).
- Berikutnya: Fase 1 — generator data tiruan berseed (skenario KAP_FISIO, KAP_HD, ULANG_IDENTIK, ULANG_HARI, HARGA_LEBIH, ABD_DINI, SENSOR_PALSU, rumah sakit jujur-tapi-sibuk), tabel `ground_truth` terpisah, dataset `--hidden`, target `make generate`.
