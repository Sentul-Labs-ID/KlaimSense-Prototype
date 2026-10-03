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
| 1 | Generator data tiruan | ✅ | Rifandi | 2 Okt 2026 | Ya |
| 2 | Mesin aturan (Langkah 1: Hitung) | ✅ | Rifandi | 2 Okt 2026 | Ya |
| 3 | Sensor IoT + Edge AI simulasi (Langkah 2) | ✅ | Rifandi | 3 Okt 2026 | Ya |
| 4 | Evaluasi akurasi | ✅ | Rifandi | 3 Okt 2026 | Ya |
| 5 | Dashboard petugas (Langkah 4: Putuskan) | ✅ | Rifandi | 3 Okt 2026 | Ya |
| 6 | RAG dan agen perangkum (Langkah 3: Rangkum) | ⬜ dikerjakan setelah fase 7 jika waktu memungkinkan | Joesavat | 3 Okt 2026 | Opsional |
| 7 | Paket demo, screenshot, naskah video | ✅ | Rifandi | 4 Okt 2026 pagi | Ya |

Validasi parameter klinis dan isi proposal: **Akbar** (lihat bagian Parameter).

---

## Milestone

| Milestone | Tanggal | Isi | Status |
|---|---|---|---|
| **M1 — Submit proposal** | 4 Okt 2026 | Fase 0–5 dan 7 selesai. Fase 6 jika sempat. Screenshot, angka evaluasi, dan video demo masuk ke proposal. | ✅ **Siap** (2026-10-03, tag `proposal-m1`): fase 0–5 dan 7 selesai; fase 6 belum |
| **M2 — Hackathon Event** | Diumumkan panitia (±3 minggu) | Multi-agent penuh, Edge AI dikalibrasi, pengecekan tempat tidur dan beban dokter, semua skenario uji. | ⬜ |
| **M3 — Demo Day / Grand Final** | Diumumkan panitia | Demo dari tagihan masuk sampai keputusan petugas, plus laporan hasil uji. | ⬜ |

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
| 2026-10-03 | 0 | Bobot skor per aturan "nilai awal yang wajar" | Jumlah bobot divalidasi harus = 100 (KAP-01 15, KAP-02 15, ULG-01 15, ULG-02 10, WJR-01 10, WJR-02 10, BAND-01 5, SEN-01 20) | Skor 0–100 per rumah sakit langsung terbaca. **Ditutup di fase 2:** jumlah bobot 100 dipertahankan; skor = Σ bobot × keparahan (0–1) sehingga otomatis 0–100; keparahan = min(1, temuan per bulan ÷ titik jenuh) untuk KAP/ULG/WJR dan min(1, (z − ambang) ÷ ambang) untuk BAND-01; SEN-01 = 0 sampai fase 3 (maks sementara 80) |
| 2026-10-03 | 0 | Default `ANTHROPIC_MODEL` tidak ditentukan | `claude-sonnet-5` (awalnya `claude-opus-5-5`) | Diminta pengguna; ID model dicek ulang di dokumentasi Anthropic sebelum fase 6 |
| 2026-10-03 | 0 | Frontend menampilkan status koneksi `/health` | Dicek dari server Next.js lewat `BACKEND_URL`, bukan dari browser | Tidak perlu CORS; jalan di jaringan Docker |
| 2026-10-03 | 0 | Tes dengan `httpx` | `httpx` tetap dipakai; peringatan deprecation Starlette (menyarankan `httpx2`) disaring di pytest | Mengikuti prompt; ditinjau jika `httpx` berhenti didukung |
| 2026-10-03 | 0 | Struktur repo target | Ditambah `.gitattributes` (LF), `frontend/AGENTS.md` + `frontend/CLAUDE.md` bawaan Next.js 16, `.gitkeep` di `data/regulasi/`, `reports/`, `assets/` | Konsistensi line ending lintas OS; panduan API Next.js 16; folder target ada sejak awal |
| 2026-10-03 | 0 | Python 3.11+ | Image Docker `python:3.12-slim`; venv lokal Python 3.13 | Keduanya memenuhi 3.11+ |
| 2026-10-03 | 0 | Remote GitHub sudah berisi commit ROADMAP.md | Repo remote ternyata kosong; `ROADMAP.md` masuk lewat commit pertama `feat(fase-0)` | ROADMAP.md sebelumnya hanya ada di folder lokal dan belum pernah di-push |
| 2026-10-03 | 0 | `make` tersedia | GNU Make dipasang di Windows lewat `winget install ezwinports.make`; dicatat di README | Windows tidak menyertakan `make` |
| 2026-10-03 | 1 | Skema 8 tabel | Ditambah `profil_rs` (label kontrol) dan `kasus_sah` (kasus sah di area batas), keduanya hanya untuk evaluasi | `profil_rs` untuk menghitung false positive pada kontrol; `kasus_sah` diminta pengguna agar evaluasi tidak terlalu bersih |
| 2026-10-03 | 1 | Semua batas di `config/parameter.yaml` | Batas aturan tetap dibaca dari `parameter.yaml`; distribusi simulasi (utilisasi, besaran sisipan, profil hidden) di `sentinel/generator/profil.py` | Distribusi simulasi bukan batas aturan; memisahkannya menjaga `parameter.yaml` tetap untuk validasi klinis |
| 2026-10-03 | 1 | Definisi skenario umum | ULANG_IDENTIK hanya fisioterapi dan obat kronis; ULANG_HARI = tagihan HD kedua identik di hari yang sama; HARGA_LEBIH mengubah tagihan yang ada (bukan fiktif); hari kejadian tidak bertumpuk per kelompok layanan; skenario non-KAP tidak melewati kapasitas | Setiap kejadian punya satu penyebab yang jelas agar evaluasi per skenario jujur |
| 2026-10-03 | 1 | ID bebas | Hidden memakai offset ID (`RS-501…`, `P-500001…`, baris mulai 50.000.001); ID tagihan diberikan setelah penyisipan dan diacak di dalam (RS, tanggal) | Utama dan hidden tidak bertabrakan; ID tidak membocorkan tagihan sisipan |
| 2026-10-03 | 1 | `kode_item` untuk semua tagihan | Fisioterapi dan hemodialisa memakai tarif paket fiktif per kelas, `kode_item` kosong | `harga_acuan` hanya untuk obat kronis dan alat bantu dengar sesuai skema |
| 2026-10-03 | 1 | `hari_operasional_hd` tanpa definisi | Hari buka per minggu (6 atau 7); pasien HD punya slot tetap (mesin, shift), 70% 2x/minggu, absen 3%, ada pergantian pasien dan pasien terdaftar tidak aktif | Meniru jadwal unit hemodialisa sungguhan; kapasitas fisik tidak mungkin terlampaui sesi nyata |
| 2026-10-03 | 1 | Data normal di sekitar batas | Margin aman tetap untuk data non-sah: harga normal ≤60% toleransi, ABD normal ≥ masa + 60 hari, ABD_DINI ≤ masa − 60 hari | **Keterbatasan**: ketepatan di titik batas tidak teruji oleh data normal; wajib ditulis di laporan evaluasi fase 4. Diimbangi `kasus_sah` |
| 2026-10-03 | 1 | Hanya rumah sakit jujur tidak pernah melewati kapasitas | Rumah sakit jujur hanya melewati kapasitas pada hari kasus sah (HD_SHIFT_TAMBAHAN, FISIO_LEMBUR) | Diminta pengguna agar false positive tidak 0% yang tidak realistis |
| 2026-10-03 | 1 | Sebaran wilayah bebas | Dengan 30 RS hanya 3 provinsi (9 kombinasi kelas-provinsi, masing-masing ≥3 RS); kelas A hanya di Jawa Barat | Syarat minimal 3 RS per kombinasi untuk BAND-01 |
| 2026-10-03 | 1 | Argumen CLI bebas | Minimal 20 RS dan 28 hari | Agar semua skenario dan kontrol bisa ditempatkan |
| 2026-10-03 | 1 | Akses tabel | `test_batas_akses.py` melarang `sentinel/rules/` menyentuh `sesi_aktual` dan tabel evaluasi, serta `sentinel/api/` menyentuh tabel evaluasi | Menjaga prinsip 6 sejak awal |
| 2026-10-03 | 2 | ULG-01: setiap salinan menjadi temuan | `tagihan_ids` temuan berisi [tagihan pertama, salinan] | Pencocokan dengan ground truth di fase 4 tidak bergantung pada tagihan mana yang ber-ID lebih kecil |
| 2026-10-03 | 2 | BAND-01: "rasio utilisasi rata-rata" | Rata-rata rasio harian (sesi ÷ kapasitas) atas hari yang punya tagihan layanan itu; HD hanya hari unit buka; robust z dengan konstanta 1,4826; hanya sisi atas; keparahan = terbesar dari fisio dan HD; temuan: `nilai_teramati` = z, `batas` = ambang, `tagihan_ids` kosong | Definisi tidak ditentukan prompt; fisioterapi tidak punya kolom hari operasional |
| 2026-10-03 | 2 | BAND-01 kelas-provinsi | Dengan 3 RS per kombinasi, leave-one-out menyisakan 2 pembanding sehingga 108/180 penilaian turun ke kelas; di hidden kelas A hanya 3 RS sehingga 18 penilaian dilewati | Konsekuensi sebaran data tiruan; dicatat untuk laporan evaluasi fase 4 |
| 2026-10-03 | 2 | WJR-02: "selisih < masa penggantian" | Masa dihitung dalam bulan kalender (tanggal sama 5 tahun kemudian tidak melanggar); riwayat dihitung bila sebelum tanggal tagihan; tagihan ABD sebelumnya urut (tanggal, ID) | Definisi tepat-di-batas yang tidak bergantung pada panjang tahun kabisat |
| 2026-10-03 | 2 | WJR-01: perbandingan harga | Eksak dengan pecahan (bukan float) | Harga tepat di batas (mis. Rp462 untuk acuan Rp420, toleransi 10%) tidak boleh tertandai karena galat pembulatan |
| 2026-10-03 | 2 | Generator tidak menyentuh hasil aturan | `generator/simpan.py` ikut menghapus `temuan` dan `skor` dataset yang sama saat data dibangkitkan ulang | Hasil aturan menjadi basi; foreign key ke `rumah_sakit` juga menghalangi penghapusan |
| 2026-10-03 | 3 | `sensor_anomali(jenis, device_id, waktu, keterangan)` | Ditambah `dataset_id` dan `durasi_menit` (disetujui pengguna) | Konvensi `dataset_id` di semua tabel; durasi untuk template TAMPER_GAP tanpa mengurai teks |
| 2026-10-03 | 3 | Skema `temuan` fase 2 | Ditambah kolom `kategori` (`selisih`/`integritas`, khusus SEN-01) lewat migrasi `ALTER TABLE` (disetujui pengguna) | Dua keparahan SEN-01 dihitung dari kategori temuan |
| 2026-10-03 | 3 | `status_sensor` = pesan valid | Juga menyimpan `hash` dan `tanda_tangan` (bytea) (disetujui pengguna) | Pesan bisa diverifikasi ulang untuk audit |
| 2026-10-03 | 3 | **Prioritas fase 2 = ambang skor saja** | **Lantai prioritas**: aturan bukti fisik (`skor.aturan_bukti_fisik`: KAP-01, KAP-02, SEN-01-selisih) yang jenuh dalam satu periode membuat prioritas minimal "tinggi"; skor tidak berubah; `skor.alasan_prioritas` menyimpan alasannya | Diminta pengguna: kapasitas fisik yang terlampaui berulang kali adalah bukti terkuat dan tidak boleh berakhir di "sedang" hanya karena bobot satu aturan maksimal 15. Keputusan prinsip, bukan hasil melihat label |
| 2026-10-03 | 3 | N jendela TAMPER_GAP dan batas data hilang tidak ditentukan | `sensor.gap_maks_jendela: 3` dan `sensor.batas_data_hilang_persen: 5` (dari jumlah perangkat × 1.440 menit) di `parameter.yaml`; titik jenuh `SEN-01-selisih: 3`, `SEN-01-integritas: 2` | Semua batas di `parameter.yaml` (prinsip 4) |
| 2026-10-03 | 3 | Jadwal shift bebas | 05:00 / 09:50 / 14:40 / 19:30–24:00 (shift 4 darurat) di `sensor/konfigurasi.py`; semua slot dalam satu tanggal | Sesi tidak melintasi tengah malam; batas slot kelipatan 10 menit |
| 2026-10-03 | 3 | Kebijakan ingest tidak ditentukan rinci | Pesan seq maju dengan rantai putus tetap disimpan (TAMPER_CHAIN); pesan ulangan ditolak; perangkat tak terdaftar atau identitas tak cocok = TAMPER_SIG | Data bertanda tangan sah tidak dibuang; replay tidak boleh menggandakan jam terapi |
| 2026-10-03 | 3 | `make sensor` < 3 menit | Pipeline paralel per perangkat (16 proses); Dockerfile memasang dependensi sebelum kode | Verifikasi Ed25519 satu inti ±4,5 menit untuk 2,95 juta pesan; build ulang setelah ubah kode turun dari ±1 menit ke ±3,5 detik |
| 2026-10-03 | 3 | Model dan hash konsisten | Model "firmware" di-commit (`backend/sentinel/sensor/model/`), `scikit-learn==1.9.1` dipatok, metadata mencatat lingkungan latih | Byte pickle bergantung pada versi Python/numpy; struktur pohon identik di lokal (3.13) dan container (3.12) |
| 2026-10-03 | 3 | `make generate` mandiri | `make generate` juga menghapus data sensor dataset itu; urutan kerja menjadi `make generate` → `make sensor` | Data sensor basi setelah data dibangkitkan ulang; foreign key ke `rumah_sakit` |
| 2026-10-03 | 4 | Kondisi RS-periode: bermasalah / hanya kasus sah / bersih | **Kondisi keempat "hanya gangguan sensor"** (RS-periode yang hanya berisi TAMPER), tidak dihitung sebagai tuduhan keliru; matriks prioritas PNG 4 kolom; definisi harfiah tetap dihitung dan dicantumkan sebagai catatan kaki (tuduhan keliru hidden 1/26) (disetujui pengguna) | Sensor yang dicabut atau dipalsukan adalah masalah nyata, bukan tuduhan keliru; prompt meminta TAMPER dilaporkan terpisah |
| 2026-10-03 | 4 | Presisi: "benar" = cocok dengan kejadian ground truth | Temuan "benar" bila memuat tagihan kecurangan mana pun, atau temuan integritas pada RS-tanggal gangguan sensor; top-k memakai urutan petugas (prioritas, lalu skor) | Mis. ULG-01 yang menangkap duplikat HD dari ULANG_HARI memang menangkap kecurangan nyata |
| 2026-10-03 | 4 | Angka proposal (4 baris + Edge AI) | Ditambah "periode bermasalah masuk daftar periksa" (23/28) dan "terdeteksi tetapi berprioritas rendah" (5/28); bagian "Analisis pasca-jalan hidden" dari `reports/catatan_pasca_hidden.md` (diminta pengguna, render ulang tanpa menghitung ulang hidden) | Angka recall level kejadian (83/86) saja melebih-lebihkan apa yang sampai ke daftar periksa petugas |
| 2026-10-03 | 4 | Infrastruktur evaluasi | `matplotlib`; `./reports` di-mount ke container; log jalan hidden permanen `reports/log_evaluasi_hidden.json`; opsi `--hanya-laporan` | Grafik PNG; keluaran ditulis ke repo; bukti berapa kali hidden dibandingkan dengan label |
| 2026-10-03 | 5 | Daftar endpoint API dashboard | Endpoint tambahan **`GET /meta`** (dataset tersedia, periode, daftar RS, status mode demo) (disetujui pengguna) | Navigasi, pemilih periode, dan panel demo butuh data ini tanpa memuat seluruh daftar periksa |
| 2026-10-03 | 5 | `POST /demo/sisipkan {rs_id, skenario, jumlah_hari}` | Field opsional **`periode`** agar hari sisipan berada di bulan yang sama (disetujui pengguna) | Alur demo harus pasti: 3 hari KAP di satu bulan mencapai titik jenuh sehingga lantai prioritas terpicu |
| 2026-10-03 | 5 | Dataset demo identik dengan utama (bangkit ulang atau salin) | **Dibangkitkan ulang** dengan seed 42 dari profil kembar utama; ID digeser (`RS-901…`, `P-900001…`, baris 90.000.001+), nama samaran sama; kunci acak sensor dipetakan ke mesin utama; skor dan prioritas 90/90 identik (disetujui pengguna) | ID adalah kunci global sehingga tidak bisa disalin apa adanya; menyalin pesan sensor dengan ID baru akan merusak tanda tangannya |
| 2026-10-03 | 5 | Waktu di dashboard | Ditampilkan dalam WIB (Asia/Jakarta); basis data dan API tetap UTC (permintaan pengguna) | Petugas dan juri membaca waktu lokal |
| 2026-10-03 | 5 | Infrastruktur dashboard | `DEMO_MODE` default `false` (panel demo: `DEMO_MODE=true make up`); `make demo-reset` dalam satu container; `make test` me-mount `frontend/` baca-saja; `make e2e`; dependensi dev `@playwright/test`; grafik SVG tanpa pustaka baru | Target demo-reset < 2 menit; tes batas akses frontend; uji asap dan tangkapan layar fase 7 |
| 2026-10-03 | 7 | **Urutan fase 0 → 7, fase 6 sesudahnya** | **Fase 7 dikerjakan sebelum fase 6 (RAG).** Fase 6 tetap ⬜, dikerjakan setelah fase 7 jika waktu memungkinkan; README dan proposal menyebut RAG dan multi-agent sebagai tahap berikutnya | Keputusan sadar pengguna agar paket proposal (M1) siap lebih dulu |
| 2026-10-03 | 7 | `02_detail-rs.png` 1920×1080 memuat kartu skor, alasan prioritas, temuan, dan grafik harian | **Pilihan (b)** (disetujui pengguna): `02_detail-rs.png` (kartu skor, alasan prioritas, temuan) dan `02b_grafik-harian.png` (grafik harian, hari temuan ditandai), keduanya 1920×1080; versi panjang `02_detail-rs-penuh.png` (1920×2493) dipakai di README | Semua isi itu tidak muat dalam satu layar 1920×1080 |
| 2026-10-03 | 7 | `make demo` berhasil dari clone baru | Baris `@echo.` (sintaks cmd untuk baris kosong) di target `demo` Makefile dihapus setelah `make demo` pertama di clone gagal di langkah terakhir; `make demo` diulang penuh sampai berhasil (5 menit 0 detik, dengan cache image Docker) | `sh` yang dipakai make tidak mengenal `echo.` |
| 2026-10-03 | 7 | Konversi video ke `assets/demo.mp4` jika ffmpeg tersedia | mp4 tidak dibuat; `assets/demo.webm` dipakai untuk unggahan video; konversi mp4 hanya opsional (pengguna) | ffmpeg tidak ada di PATH dan ffmpeg bawaan Playwright tidak punya encoder H.264 |
| 2026-10-03 | 7 | `make verifikasi-reproduksi` tidak menulis selain `reports/verifikasi_reproduksi.json` | Menghitung ulang angka hidden di basis data terpisah `sentinel_verifikasi` (dibuat lalu dihapus); hanya menulis `verifikasi_reproduksi.json`; tidak dicatat sebagai jalan evaluasi hidden di `log_evaluasi_hidden.json`; dijalankan ulang setelah commit `feat(fase-7)` agar hash bersih (`87ac7b4`) | Verifikasi kode dan parameter yang dibekukan, bukan penyetelan; log hidden tetap bukti 1 jalan |
| 2026-10-03 | 7 | Isi `assets/`: 6 tangkapan layar, 2 grafik, video | Ditambah `02b_grafik-harian.png`, `02_detail-rs-penuh.png`, dan `assets/demo_waktu.json` (waktu per langkah video untuk naskah); skrip Playwright pengemasan di `frontend/paket/` dengan `playwright.paket.config.ts` | Pilihan (b); naskah selaras dengan video; uji asap `make e2e` tidak ikut menjalankan pengemasan |
| 2026-10-03 | 7 | Uji `make demo` dari clone baru | Clone di folder sementara dengan `COMPOSE_PROJECT_NAME=jknuji` (volume terpisah), memakai cache image Docker; stack clone diturunkan beserta volumenya | Data aktif tidak tersentuh; build tanpa cache lebih lama dari ±5 menit |

---

## Log progres

| Tanggal | Fase | Status | Catatan |
|---|---|---|---|
| 2026-10-03 | 0 | ✅ | Kerangka monorepo jalan: `make up` (db, backend :8000, frontend :3000), `/health` OK, frontend "terhubung", `make test` 12 lulus. Commit `bd5ee14`. Versi 0.1.0. |
| 2026-10-03 | 1 | ✅ | Generator data tiruan berseed: dataset utama (121.398 tagihan, 72 kejadian kecurangan, 14 kejadian kasus sah) dan hidden (123.655 tagihan, 86 kejadian kecurangan, 15 kejadian kasus sah). `make generate` dan `make test` 70 lulus. Commit `a9be965`. Versi 0.2.0. |
| 2026-10-03 | 2 | ✅ | Mesin aturan KAP-01, KAP-02, ULG-01, ULG-02, WJR-01, WJR-02, BAND-01; tabel `temuan` dan `skor` (per RS per bulan, 0–100, maks sementara 80). Utama: 114 temuan, RS tinggi/sedang/rendah 5/3/22. Hidden: 146 temuan, 5/7/18. `make rules` ±1,5 detik per dataset; `make test` 122 lulus. Commit `7e1f8f9`. Versi 0.3.0. |
| 2026-10-03 | 3 | ✅ | Sensor IoT + edge AI simulasi: tiga sisi terpisah (dunia/perangkat/server), pohon keputusan akurasi uji 97,75%, Ed25519 + rantai hash, TAMPER_SIG/CHAIN/GAP, SEN-01 (selisih + integritas), lantai prioritas bukti fisik. 2,95 juta pesan; RS tinggi/sedang/rendah utama 8/2/20, hidden 7/6/17. `make sensor` < 3 menit; `make test` 172 lulus. Commit `a475ca0`. Versi 0.4.0. |
| 2026-10-03 | 4 | ✅ | Evaluasi akurasi; hidden pertama kali dibandingkan dengan label 2026-10-03T06:02:34Z (1 jalan). Hidden: kecurangan terdeteksi 83/86, periode bermasalah masuk daftar periksa 23/28, tuduhan keliru 0/26, kasus sah 2/26, RS jujur ditandai 3/60, Edge AI 97,8%. Tidak ada bug ditemukan; tidak ada parameter diubah. `make test` 189 lulus. Commit `ce4f9eb`. Versi 0.5.0. |
| 2026-10-03 | 5 | ✅ | Dashboard petugas: daftar periksa, detail RS (rincian skor, temuan, grafik harian, grid sensor + verifikasi tanda tangan, ringkasan template), keputusan berantai hash, audit, panel demo; dataset `demo` kembar utama. Alur demo: RS Tiruan 012 Agustus 2026 rendah 3,3 → tinggi 18,3 (lantai bukti fisik) → minta klarifikasi → audit utuh. `make test` 201, uji asap Playwright lulus. Commit `b12f6e6`. Versi 0.6.0. |
| 2026-10-03 | 7 | ✅ | Paket demo (dikerjakan sebelum fase 6): `make demo` berhasil dari clone baru (5 menit 0 detik), `make verifikasi-reproduksi` IDENTIK di keempat bagian (komit `87ac7b4`, 169,3 detik; `evaluasi.json` dan log hidden tidak berubah), 8 tangkapan layar + 2 grafik + video `demo.webm` 1920×1080 89,6 detik, `docs/NASKAH_DEMO.md`, README final, pemindaian keamanan bersih. `make test` 204, `make e2e` lulus. Commit `87ac7b4`. Versi 0.7.0. **M1 siap** (tag `proposal-m1`). |
