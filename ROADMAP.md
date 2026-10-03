# ROADMAP — JKN-Sentinel Prototype

Prototype untuk proposal **BPJS Kesehatan Healthkathon 2026**, kategori Efisiensi Risiko pada Fasilitas Kesehatan.
Tim: Sentul Labs (Rifandi Indrayudha Prawira, Joesavat Donovan, Akbar).

JKN-Sentinel memeriksa setiap tagihan (klaim) rumah sakit ke BPJS dengan dua pertanyaan:

1. **Mungkinkah layanan ini terjadi** dengan kapasitas nyata rumah sakit (tenaga, mesin, tempat tidur)?
2. **Wajarkah tagihannya** menurut aturan (harga acuan, masa penggantian alat, batas jumlah)?

Alur kerja empat langkah: **Hitung → Cek sensor → Rangkum → Putuskan**.

---

## Status

Legenda: ⬜ belum mulai · 🟡 sedang berjalan · ✅ selesai · ⏭️ ditunda ke tahap berikutnya

| Fase | Nama | Status | PIC | Target | Wajib untuk M1 |
|---|---|---|---|---|---|
| 0 | Setup repo dan aturan proyek | ✅ | Rifandi | 2 Okt 2026 | Ya |
| 1 | Generator data tiruan | ⬜ | Rifandi | 2 Okt 2026 | Ya |
| 2 | Mesin aturan (Langkah 1: Hitung) | ⬜ | Rifandi | 2 Okt 2026 | Ya |
| 3 | Sensor IoT + Edge AI simulasi (Langkah 2) | ⬜ | Rifandi | 3 Okt 2026 | Ya |
| 4 | Evaluasi akurasi | ⬜ | Rifandi | 3 Okt 2026 | Ya |
| 5 | Dashboard petugas (Langkah 4: Putuskan) | ⬜ | Rifandi | 3 Okt 2026 | Ya |
| 6 | RAG dan agen perangkum (Langkah 3: Rangkum) | ⬜ | Joesavat | 3 Okt 2026 | Opsional |
| 7 | Paket demo, screenshot, naskah video | ⬜ | Rifandi | 4 Okt 2026 pagi | Ya |

Validasi parameter klinis dan isi proposal: **Akbar** (lihat bagian Parameter).

---

## Milestone

| Milestone | Tanggal | Isi |
|---|---|---|
| **M1 — Submit proposal** | 4 Okt 2026 | Fase 0–5 dan 7 selesai. Fase 6 jika sempat. Screenshot, angka evaluasi, dan video demo masuk ke proposal. |
| **M2 — Hackathon Event** | Diumumkan panitia (±3 minggu) | Multi-agent penuh, Edge AI dikalibrasi, pengecekan tempat tidur dan beban dokter, semua skenario uji. |
| **M3 — Demo Day / Grand Final** | Diumumkan panitia | Demo dari tagihan masuk sampai keputusan petugas, plus laporan hasil uji. |

---

## Prinsip proyek

Prinsip ini juga ditulis di `CLAUDE.md` dan wajib dipatuhi di semua fase.

1. **Hanya data tiruan.** Tidak memakai, mengunduh, atau meminta data peserta JKN asli.
2. **Skor dihitung deterministik.** Aturan tetap dan statistik. AI tidak menghitung, mengubah, atau menebak skor.
3. **AI hanya merangkum dan mengutip.** Kutipan regulasi wajib berasal dari korpus lokal; kutipan tanpa sumber tidak ditampilkan.
4. **Parameter tidak di-hardcode.** Semua batas ada di `config/parameter.yaml`, dengan catatan bahwa nilai default bersifat ilustratif.
5. **Level hari.** Pengecekan dilakukan per tanggal, sesuai bentuk data klaim.
6. **Ground truth terpisah.** Label kecurangan hanya boleh dibaca modul evaluasi, tidak oleh mesin aturan.
7. **Manusia memutuskan.** Sistem memberi prioritas pemeriksaan, bukan vonis.
8. **Bisa direproduksi.** Data acak memakai seed; data yang sama selalu menghasilkan skor yang sama.

---

## Rincian fase

### Fase 0 — Setup repo dan aturan proyek
- **Tujuan:** struktur monorepo siap, aturan proyek tertulis.
- **Keluaran:** `backend/` (FastAPI, PostgreSQL), `frontend/` (Next.js), `config/parameter.yaml`, `docker-compose.yml`, `Makefile`, `CLAUDE.md`, `docs/ARSITEKTUR.md`, kerangka dokumentasi.
- **Selesai jika:** `make up` berjalan, `/health` merespons, `make test` lulus.

### Fase 1 — Generator data tiruan
- **Tujuan:** data rumah sakit, kapasitas, pasien pseudonim, tagihan, dan harga acuan, dengan kecurangan yang disisipkan.
- **Skenario:** KAP_FISIO, KAP_HD, ULANG_IDENTIK, ULANG_HARI, HARGA_LEBIH, ABD_DINI, SENSOR_PALSU, plus rumah sakit jujur-tapi-sibuk sebagai kontrol.
- **Keluaran:** CLI generator berseed, tabel `ground_truth` terpisah, dataset `--hidden` untuk evaluasi akhir.
- **Selesai jika:** seed sama menghasilkan data identik; rumah sakit jujur tidak pernah melebihi kapasitas.

### Fase 2 — Mesin aturan (Langkah 1)
- **Tujuan:** pengecekan otomatis yang bisa dijelaskan.
- **Aturan:** KAP-01 (fisioterapi), KAP-02 (hemodialisa), ULG-01 (tagihan identik), ULG-02 (sesi ganda sehari), WJR-01 (harga di atas acuan), WJR-02 (alat bantu dengar sebelum masa penggantian), BAND-01 (perbandingan rumah sakit sejenis).
- **Keluaran:** tabel temuan dengan penjelasan template, skor 0–100 per rumah sakit per periode.
- **Selesai jika:** satu tes per aturan lulus; hasil identik saat dijalankan ulang.

### Fase 3 — Sensor IoT + Edge AI (Langkah 2)
- **Tujuan:** bukti pemakaian mesin hemodialisa yang sulit dipalsukan.
- **Keluaran:** simulator arus listrik, klasifikasi status di perangkat (terapi/standby/mati), pesan bertanda tangan Ed25519 dengan hash chain, deteksi TAMPER_SIG/TAMPER_CHAIN/TAMPER_GAP, aturan SEN-01 (jam-mesin terapi vs sesi ditagih).
- **Selesai jika:** rumah sakit skenario SENSOR_PALSU tertandai; pesan palsu dan sensor dicabut terdeteksi.

### Fase 4 — Evaluasi akurasi
- **Tujuan:** angka jujur untuk slide 16 proposal.
- **Keluaran:** `reports/evaluasi.md`, `reports/evaluasi.json`, `reports/confusion_matrix.png`; recall, presisi, dan false positive rate per skenario, untuk dataset utama dan hidden.
- **Selesai jika:** angka dataset hidden tercetak terpisah dan bagian keterbatasan tertulis.

### Fase 5 — Dashboard petugas (Langkah 4)
- **Tujuan:** tampilan yang bisa didemokan ke juri.
- **Keluaran:** beranda daftar rumah sakit, halaman detail (temuan, grafik sesi vs kapasitas, grid sensor, tombol keputusan), halaman audit dengan verifikasi hash chain, panel demo "Sisipkan kecurangan".
- **Selesai jika:** alur demo berjalan dari beranda sampai keputusan tercatat di audit.

### Fase 6 — RAG dan agen perangkum (Langkah 3) — opsional untuk M1
- **Tujuan:** berkas bukti berbahasa sederhana dengan dasar aturan bersumber.
- **Prasyarat:** teks regulasi publik di `data/regulasi/`.
- **Keluaran:** retrieval BM25, empat agen (PengumpulTagihan, PembacaData, PencariAturan, PenulisLaporan), validator kutipan verbatim, `agent_log`, fallback tanpa API key.
- **Jika tidak sempat:** ubah status RAG dan Multi-Agent di slide 14 proposal menjadi "Tahap hackathon".

### Fase 7 — Paket demo
- **Tujuan:** siap direkam dan dimasukkan ke proposal.
- **Keluaran:** `make demo` dari nol, screenshot Playwright di `assets/`, `docs/NASKAH_DEMO.md` (video 90 detik), README lengkap, pemeriksaan tidak ada data menyerupai data asli.
- **Selesai jika:** `make demo` berjalan dari repo bersih.

---

## Konvensi dokumentasi

Setiap fase **wajib** meninggalkan jejak lengkap. Prompt tidak boleh hanya ada di riwayat chat.

### 1. Arsip prompt — `docs/prompts/`

Setiap prompt yang dijalankan di Claude Code disimpan **verbatim** sebagai file terpisah:

```
docs/prompts/
├── README.md                  # indeks semua prompt
├── FASE-00_setup-repo.md
├── FASE-01_generator-data.md
├── FASE-01_generator-data_v2.md   # jika prompt diperbaiki/diulang
└── ...
```

Format setiap file prompt:

```markdown
# FASE-XX — Nama fase

| Kolom | Isi |
|---|---|
| Versi | v1 |
| Tanggal dijalankan | YYYY-MM-DD |
| Dijalankan oleh | Nama |
| Alat | Claude Code |
| Commit hasil | <hash> |
| Status | Berhasil / Sebagian / Diulang (lihat v2) |

## Prompt (verbatim)

<salinan persis prompt yang dikirim>

## Catatan hasil

- Apa yang dihasilkan
- Masalah yang muncul
- Penyimpangan dari prompt atau roadmap
```

Aturan arsip:
- **Jangan menimpa** prompt lama. Jika prompt diperbaiki, buat versi baru (`_v2`, `_v3`) dan tulis alasannya.
- Prompt lanjutan kecil di tengah fase (misalnya perbaikan bug) dicatat di bagian "Catatan hasil" pada file fase yang sama, juga verbatim.
- Perbarui `docs/prompts/README.md` setiap ada file baru.

### 2. Log pengembangan — `docs/DEVLOG.md`

Satu entri per sesi kerja, terbaru di atas:

```markdown
## YYYY-MM-DD — Fase X: judul singkat
- Dikerjakan:
- Keputusan:
- Masalah dan solusi:
- Penyimpangan dari roadmap:
- Berikutnya:
```

### 3. Changelog — `CHANGELOG.md`

Format Keep a Changelog, versi `0.x.0` naik setiap fase selesai (Fase 0 = 0.1.0, Fase 1 = 0.2.0, dan seterusnya).

### 4. Roadmap — file ini

- Perbarui kolom **Status** di tabel setiap fase dimulai atau selesai.
- Catat setiap penyimpangan di bagian **Catatan penyimpangan** di bawah.

### 5. Commit

- Kode: `feat(fase-N): ...`, `fix(fase-N): ...`, `test(fase-N): ...`
- Dokumentasi: `docs(fase-N): ...`

### Langkah dokumentasi wajib di akhir setiap prompt

Setiap prompt fase diakhiri dengan instruksi ini:

1. Simpan prompt fase ini verbatim ke `docs/prompts/FASE-XX_nama.md` dengan format di atas, dan perbarui indeksnya.
2. Perbarui status fase di `ROADMAP.md`.
3. Tambahkan entri di `docs/DEVLOG.md`.
4. Naikkan versi dan tambahkan entri di `CHANGELOG.md`.
5. Catat penyimpangan dari roadmap (jika ada) di `ROADMAP.md` bagian Catatan penyimpangan.
6. Commit dokumentasi terpisah dengan pesan `docs(fase-N): ...`.

---

## Parameter yang wajib divalidasi

Semua parameter ada di `config/parameter.yaml`. Nilai default hanya ilustratif sampai divalidasi.

| Parameter | Default | Divalidasi oleh | Status |
|---|---|---|---|
| Sesi fisioterapi wajar per terapis per hari | 8 | Akbar | ⬜ |
| Durasi satu sesi hemodialisa | 4 jam | Akbar | ⬜ |
| Shift hemodialisa per hari | 3 | Akbar | ⬜ |
| Toleransi harga di atas harga acuan | 10% | Akbar | ⬜ |
| Masa penggantian alat bantu dengar | 5 tahun per telinga | Akbar (cocokkan dengan regulasi) | ⬜ |
| Ambang perbandingan antar-rumah sakit | robust z-score 3 | Rifandi | ⬜ |
| Toleransi selisih jam-mesin sensor | 10% | Rifandi | ⬜ |

---

## Keluaran untuk proposal

| Slide proposal | Diisi dari | Fase |
|---|---|---|
| 13 — Langkah 3 dan 4 | Kutipan pasal nyata dari hasil RAG | 6 |
| 14 — Teknologi | Status tiap teknologi sesuai fase yang selesai | 3, 6 |
| 16 — Kematangan | Checklist komponen, angka `reports/evaluasi.md` (dataset hidden), screenshot `assets/`, QR video | 4, 5, 7 |

---

## Struktur repo target

```
JKN-Sentinel-Prototype/
├── ROADMAP.md
├── README.md
├── CHANGELOG.md
├── CLAUDE.md
├── Makefile
├── docker-compose.yml
├── config/parameter.yaml
├── backend/sentinel/        # generator, aturan, sensor, evaluasi, agen, API
├── frontend/                # dashboard Next.js
├── data/regulasi/           # teks regulasi publik untuk RAG
├── reports/                 # hasil evaluasi
├── assets/                  # screenshot demo
└── docs/
    ├── ARSITEKTUR.md
    ├── DEVLOG.md
    ├── NASKAH_DEMO.md
    └── prompts/             # arsip prompt verbatim
```

---

## Catatan penyimpangan

Catat di sini setiap keputusan yang berbeda dari roadmap.

| Tanggal | Fase | Rencana awal | Yang dilakukan | Alasan |
|---|---|---|---|---|
| 2026-10-03 | 0 | Dependensi backend: FastAPI, SQLAlchemy, psycopg, pydantic-settings, pytest, httpx | Ditambah `pyyaml` | Dibutuhkan loader `config/parameter.yaml` |
| 2026-10-03 | 0 | Env: DATABASE_URL, ANTHROPIC_API_KEY, ANTHROPIC_MODEL, DEMO_MODE | Ditambah `PARAMETER_PATH` (opsional) dan `BACKEND_URL` (frontend) | Lokasi file parameter bisa diganti; alamat backend frontend berbeda di dalam/luar Docker |
| 2026-10-03 | 0 | Bobot skor per aturan "nilai awal yang wajar" | Jumlah bobot divalidasi harus = 100 (KAP-01 15, KAP-02 15, ULG-01 15, ULG-02 10, WJR-01 10, WJR-02 10, BAND-01 5, SEN-01 20) | Skor 0–100 per rumah sakit langsung terbaca; **keputusan ditinjau di fase 2** |
| 2026-10-03 | 0 | Default `ANTHROPIC_MODEL` tidak ditentukan | `claude-sonnet-5` (awalnya `claude-opus-5-5`) | Diminta pengguna; ID model dicek ulang di dokumentasi Anthropic sebelum fase 6 |
| 2026-10-03 | 0 | Frontend menampilkan status koneksi `/health` | Dicek dari server Next.js lewat `BACKEND_URL`, bukan dari browser | Tidak perlu CORS; jalan di jaringan Docker |
| 2026-10-03 | 0 | Tes dengan `httpx` | `httpx` tetap dipakai; peringatan deprecation Starlette (menyarankan `httpx2`) disaring di pytest | Mengikuti prompt; ditinjau jika `httpx` berhenti didukung |
| 2026-10-03 | 0 | Struktur repo target | Ditambah `.gitattributes` (LF), `frontend/AGENTS.md` + `frontend/CLAUDE.md` bawaan Next.js 16, `.gitkeep` di `data/regulasi/`, `reports/`, `assets/` | Konsistensi line ending lintas OS; panduan API Next.js 16; folder target ada sejak awal |
| 2026-10-03 | 0 | Python 3.11+ | Image Docker `python:3.12-slim`; venv lokal Python 3.13 | Keduanya memenuhi 3.11+ |
| 2026-10-03 | 0 | Remote GitHub sudah berisi commit ROADMAP.md | Repo remote ternyata kosong; `ROADMAP.md` masuk lewat commit pertama `feat(fase-0)` | ROADMAP.md sebelumnya hanya ada di folder lokal dan belum pernah di-push |
| 2026-10-03 | 0 | `make` tersedia | GNU Make dipasang di Windows lewat `winget install ezwinports.make`; dicatat di README | Windows tidak menyertakan `make` |

---

## Log progres

| Tanggal | Fase | Status | Catatan |
|---|---|---|---|
| 2026-10-03 | 0 | ✅ | Kerangka monorepo jalan: `make up` (db, backend :8000, frontend :3000), `/health` OK, frontend "terhubung", `make test` 12 lulus. Commit `bd5ee14`. Versi 0.1.0. |
