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

## 2026-10-03 — Fase 2: mesin aturan (Langkah 1: Hitung)
- Dikerjakan:
  - Paket `sentinel/rules/` dengan tujuh aturan (KAP-01, KAP-02, ULG-01, ULG-02, WJR-01, WJR-02, BAND-01), penjelasan dari template bahasa Indonesia, skor per RS per bulan, dan CLI `python -m sentinel.rules` serta `make rules`.
  - Tabel `temuan` dan `skor` (`models/hasil.py`).
  - Bagian `skor` di `parameter.yaml`: titik jenuh dan ambang prioritas.
  - `hash_parameter()` (SHA-256 isi `parameter.yaml`).
  - Definisi aturan dan rumus skor untuk juri non-teknis di `docs/ARSITEKTUR.md`.
  - 122 tes lulus.
- Hasil:

  | | utama | hidden |
  |---|---|---|
  | Temuan KAP-01 / KAP-02 / ULG-01 / ULG-02 / WJR-01 / WJR-02 / BAND-01 | 16 / 18 / 25 / 12 / 20 / 7 / 16 | 16 / 18 / 36 / 25 / 31 / 7 / 13 |
  | RS-periode skor 0; median / P90 / maks | 49 dari 90; 0 / 15 / 30 | 46 dari 90; 0 / 18,5 / 40 |
  | RS per prioritas tinggi / sedang / rendah (periode tertinggi) | 5 / 3 / 22 | 5 / 7 / 18 |

- Keputusan:
  - **Ambang prioritas: tinggi ≥ 20, sedang ≥ 10**, ditetapkan hanya dari sebaran skor dataset utama (tanpa melihat hidden maupun ground truth). Alasannya:
    - 49 dari 90 RS-periode berskor 0.
    - Skor 0 < x < 10 adalah temuan terisolasi (1–2 temuan satu aturan, atau BAND-01 saja). Jumlahnya banyak dan sebagian bisa berupa kejadian sah, jadi cukup "rendah".
    - Ada celah alami di sebaran utama: 8,33 → 10 dan 18,33 → 21,67.
    - Skor ≥ 10 berarti pelanggaran berulang pada satu aturan berbobot berat (mis. 2 temuan KAP dalam sebulan): layak diperiksa ("sedang").
    - Skor ≥ 20 butuh setara satu aturan berat yang jenuh ditambah sinyal lain: prioritas pertama ("tinggi").
  - **Titik jenuh** (temuan per bulan untuk keparahan penuh): KAP-01, KAP-02, ULG-01, ULG-02, WJR-01 = 3; WJR-02 = 2 (alat bantu dengar jauh lebih jarang); SEN-01 = 3 disiapkan untuk fase 3. Semua ILUSTRATIF.
  - **Bobot berjumlah 100 dipertahankan.** Skor = Σ bobot × keparahan sehingga otomatis 0–100. SEN-01 bernilai 0 sampai fase 3, jadi skor maksimum sementara 80.
  - **Interpretasi aturan:**
    - ULG-01 menyimpan [tagihan pertama, salinan].
    - BAND-01 = rata-rata rasio harian, robust z (1,4826), sisi atas saja, keparahan terbesar dari dua layanan.
    - WJR-02 memakai bulan kalender.
    - WJR-01 dibandingkan secara eksak (pecahan).
  - **Batas akses dibuktikan dengan tes**: tabel `sesi_aktual`, `ground_truth`, `profil_rs`, `kasus_sah` di-DROP dari SQLite lalu CLI tetap jalan. `masukan.py` adalah satu-satunya pintu data ke mesin aturan.
  - **Tidak ada dependensi baru** (`statistics`, `fractions`, `bisect`, `hashlib` dari pustaka standar Python).
- Masalah dan solusi:
  - Foreign key `temuan`/`skor` → `rumah_sakit` akan menghalangi `make generate` ulang. Solusi: generator ikut menghapus hasil aturan dataset yang sama, karena hasil itu memang basi.
  - Dua tes awal salah karena data uji (MAD 0 juga di tingkat kelas) dan toleransi pembulatan; kode tidak berubah.
  - Kecepatan: baca + hitung + simpan ±1,5 detik per dataset; indeks tambahan tidak diperlukan.
- Penyimpangan dari roadmap: tidak ada penyimpangan dari prompt. Keputusan interpretasi dicatat di `ROADMAP.md` (baris fase 2), dan catatan "bobot berjumlah 100" ditutup.
- Catatan untuk fase 4:
  - BAND-01 di data tiruan sebagian besar memakai pembanding kelas (108/180), dan di hidden 18 penilaian kelas A dilewati karena hanya ada 3 RS kelas A.
  - Kontrol sibuk diperkirakan memicu BAND-01. Ini sesuai sifatnya sebagai sinyal pendukung, dan bobotnya hanya 5.
- Berikutnya: Fase 3 — simulator sensor IoT + Edge AI, pesan bertanda tangan Ed25519 dengan hash chain, deteksi TAMPER_*, aturan SEN-01 (mengaktifkan bobot 20).

## 2026-10-03 — Fase 1: generator data tiruan
- Dikerjakan:
  - Skema SQLAlchemy di `backend/sentinel/models/`, dikelompokkan menurut hak baca:
    - `master`, `transaksi`: dibaca semua modul.
    - `kenyataan` (`sesi_aktual`): hanya sensor dan evaluasi.
    - `evaluasi` (`ground_truth`, `profil_rs`, `kasus_sah`): hanya evaluasi.
  - Generator berseed `python -m sentinel.generator` (+ `--hidden`, `--dry-run`) dan `make generate`.
  - 7 skenario kecurangan, kontrol (2 jujur-sibuk, 1 kelas A volume tinggi, ≥4 RS jujur bersensor), dan 3 jenis kasus sah.
  - 70 tes lulus.
- Ringkasan data:

  | | utama (seed 42) | hidden (seed 2026) |
  |---|---|---|
  | RS (sensor) / profil jujur-sibuk-volume-disisipi | 30 (10) / 19-2-1-8 | 30 (10) / 17-2-1-10 |
  | Pasien | 9.721 | 9.961 |
  | Tagihan (fisio / HD / ABD / obat) | 121.398 (51.495 / 41.863 / 192 / 27.848) | 123.655 (50.867 / 43.895 / 192 / 28.701) |
  | Sesi aktual (fisio / HD) | 93.065 (51.339 / 41.726) | 94.227 (50.516 / 43.711) |
  | Kejadian KAP_FISIO / KAP_HD / ULANG_IDENTIK / ULANG_HARI / HARGA_LEBIH / ABD_DINI / SENSOR_PALSU | 13 / 14 / 8 / 9 / 7 / 7 / 14 | 14 / 14 / 7 / 17 / 13 / 7 / 14 |
  | Kasus sah HD_SHIFT_TAMBAHAN / FISIO_LEMBUR (hari) | 4 / 3 | 4 / 2 |
  | Kasus sah HARGA_ACUAN_LAMA (tagihan) | 7 | 9 |

  Utilisasi RS normal rata-rata 53–90% (puncak harian ≤95%); kontrol sibuk 97–99% (puncak 100%).
- Keputusan:
  - **Kasus sah di area batas** (`kasus_sah`: shift HD darurat, terapis lembur, harga acuan lama) sengaja dibuat untuk dua tujuan:
    - **Evaluasi yang jujur.** Tanpa kasus ini, false positive di fase 4 akan 0% dan tidak realistis. Kasus sah dihitung sebagai tuduhan keliru dan dilaporkan terpisah sebagai "kasus sah yang perlu klarifikasi".
    - **Demo human-in-the-loop.** Sistem menandai, lalu petugas mengklarifikasi dan memutuskan (prinsip 7).
  - **Batas akses tabel** dijaga `tests/test_batas_akses.py` sejak sekarang, sebelum mesin aturan ditulis.
  - **ID tagihan diberikan setelah penyisipan** dan diacak per (RS, tanggal), supaya mesin aturan tidak bisa "curang" lewat urutan ID.
  - **Determinisme.** Satu `random.Random(seed)`, tanpa iterasi `set`. Dites lintas proses dengan `PYTHONHASHSEED` berbeda. Sidik data sama antara Python 3.13 (lokal) dan 3.12 (container).
  - **Distribusi simulasi** di `sentinel/generator/profil.py`; batas aturan tetap dari `config/parameter.yaml`.
  - **Tidak ada dependensi baru.** Generator memakai pustaka standar Python (`random`, `hashlib`, `json`). Tes penyimpanan memakai SQLite bawaan Python.
- Masalah dan solusi:
  - Utilisasi harian RS normal sempat menyentuh 100% (pembulatan pada kapasitas kecil; pola jadwal HD memenuhi satu hari). Solusi: pembulatan ke bawah dan batas isian 95% per hari kerja untuk RS normal.
  - `make generate` kedua butuh ±3 menit per dataset karena penghapusan baris induk memindai `tagihan`/`sesi_aktual` tanpa indeks. Solusi: indeks pada kolom foreign key, lalu `make reset-db`. Kini ±10 detik.
  - Skrip penambal besar gagal lewat heredoc bash. Solusi: skrip ditulis ke berkas sementara.
- Penyimpangan dari roadmap: lihat `ROADMAP.md` bagian Catatan penyimpangan (baris fase 1).
- **Keterbatasan untuk laporan evaluasi fase 4.** Data non-sah memakai margin aman dari batas aturan: harga normal ≤60% toleransi, ABD normal ≥ masa penggantian + 60 hari, ABD_DINI ≤ masa penggantian − 60 hari. Ketepatan aturan tepat di titik batas tidak teruji oleh data normal. Hanya `kasus_sah` yang menguji area tepat di atas batas.
- Berikutnya: Fase 2 — mesin aturan KAP-01, KAP-02, ULG-01, ULG-02, WJR-01, WJR-02, BAND-01, dengan tabel temuan dan skor 0–100. Tinjau ulang aturan jumlah bobot = 100.

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
