# Arsitektur JKN-Sentinel

> Seluruh data adalah data tiruan. Sistem memberi prioritas pemeriksaan, bukan vonis.

## Alur empat langkah

| Langkah | Nama | Pertanyaan | Siapa yang mengerjakan |
|---|---|---|---|
| 1 | **Hitung** | Apakah tagihan mungkin terjadi dan wajar menurut kapasitas dan aturan? | Mesin aturan deterministik (`sentinel/rules/`) |
| 2 | **Cek sensor** | Apakah mesin benar-benar dipakai sebanyak sesi yang ditagih? | Sensor IoT + Edge AI simulasi (`sentinel/sensor/`) |
| 3 | **Rangkum** | Apa temuannya dan apa dasar aturannya, dalam bahasa sederhana? | Agen perangkum + RAG korpus lokal (`sentinel/agents/`) |
| 4 | **Putuskan** | Perlu diperiksa lebih lanjut atau tidak? | Petugas BPJS di dashboard (`frontend/`) |

Skor hanya dihasilkan langkah 1 dan 2. Langkah 3 (AI) hanya merangkum dan mengutip, tidak mengubah skor. Langkah 4 selalu manusia.

## Diagram

```
                    config/parameter.yaml (batas & bobot, ilustratif)
                                   │
                                   ▼
 ┌──────────────┐   tagihan   ┌──────────────┐  temuan +  ┌──────────────┐
 │  Generator   │────────────▶│ 1. HITUNG    │──skor─────▶│              │
 │  data tiruan │  kapasitas  │ mesin aturan │            │              │
 │  (berseed)   │             └──────────────┘            │  PostgreSQL  │
 │              │   sinyal    ┌──────────────┐  SEN-01 +  │  (temuan,    │
 │              │────────────▶│ 2. CEK SENSOR│──tamper───▶│   skor,      │
 └──────┬───────┘   sensor    │ Ed25519+hash │            │   audit)     │
        │                     └──────────────┘            │              │
        │ ground_truth                                    └──────┬───────┘
        │ (hanya untuk evaluasi)                                 │
        ▼                                                        ▼
 ┌──────────────┐                                  ┌──────────────────────┐
 │  Evaluasi    │                                  │ 3. RANGKUM           │
 │  recall,     │                                  │ agen + RAG           │
 │  presisi,FPR │                                  │ data/regulasi/       │
 └──────────────┘                                  └──────────┬───────────┘
                                                              ▼
                                                 ┌──────────────────────┐
                                                 │ 4. PUTUSKAN          │
                                                 │ dashboard petugas    │
                                                 │ (FastAPI ⇄ Next.js)  │
                                                 └──────────────────────┘
```

## Layanan

| Layanan | Teknologi | Port |
|---|---|---|
| `db` | PostgreSQL 16 | 5432 |
| `backend` | Python 3.11+, FastAPI, SQLAlchemy 2.x, psycopg | 8000 |
| `frontend` | Next.js (App Router, TypeScript, Tailwind) | 3000 |

Konfigurasi rahasia dan koneksi dibaca dari environment (`sentinel/config.py`, lihat `.env.example`). Parameter aturan dibaca dari `config/parameter.yaml` dan divalidasi oleh `sentinel/parameter.py`.

## Tabel dan batas akses

| Kelompok | Tabel | Boleh dibaca |
|---|---|---|
| Master (`models/master.py`) | `rumah_sakit`, `kapasitas`, `pasien`, `harga_acuan` | Semua modul |
| Transaksi (`models/transaksi.py`) | `tagihan`, `riwayat_alat_bantu_dengar` | Semua modul |
| Kenyataan (`models/kenyataan.py`) | `sesi_aktual` (sesi yang benar-benar terjadi) | Hanya sensor (fase 3) dan evaluasi (fase 4) |
| Hasil (`models/hasil.py`) | `temuan`, `skor` (keluaran mesin aturan) | Semua modul, termasuk dashboard |
| Evaluasi (`models/evaluasi.py`) | `ground_truth`, `profil_rs`, `kasus_sah` | Hanya evaluasi (fase 4); tidak boleh diekspos API dashboard |

Semua tabel punya `dataset_id` (`utama` atau `hidden`). Mesin aturan hanya melihat apa yang dilihat BPJS di dunia nyata: tagihan dan data master. Batas ini dijaga oleh `tests/test_batas_akses.py`.

`kasus_sah` berisi kejadian sah di area batas aturan (shift hemodialisa darurat, terapis lembur, harga acuan lama) di rumah sakit jujur. Mesin aturan memang diharapkan menandainya; evaluasi menghitungnya sebagai tuduhan keliru dan melaporkannya terpisah sebagai "kasus sah yang perlu klarifikasi". Kasus ini juga menjadi bahan demo human-in-the-loop: sistem menandai, petugas mengklarifikasi.

## Langkah 1: Hitung — aturan dan skor

Mesin aturan hanya melihat apa yang juga dilihat BPJS di dunia nyata: data rumah sakit, kapasitasnya, harga acuan, tagihan, dan riwayat alat bantu dengar. Semua batas diambil dari `config/parameter.yaml` (nilainya ilustratif sampai divalidasi). Pengecekan dilakukan **per hari**, sesuai bentuk data klaim. Nilai yang **tepat sama** dengan batas **tidak** dianggap melanggar.

### Aturan

| Kode | Pertanyaan sederhana | Kapan menjadi temuan |
|---|---|---|
| **KAP-01** Fisioterapi | Apakah jumlah sesi fisioterapi sehari masuk akal untuk jumlah terapisnya? | Sesi ditagih dalam satu hari **lebih dari** jumlah terapis × sesi wajar per terapis (default 8). |
| **KAP-02** Hemodialisa | Apakah jumlah cuci darah sehari muat di mesin yang ada, dan apakah unitnya buka? | Sesi ditagih dalam satu hari **lebih dari** jumlah mesin × shift per hari, **atau** ada sesi pada hari unit tidak beroperasi. |
| **ULG-01** Tagihan identik | Apakah tagihan yang sama persis dikirim dua kali? | Rumah sakit, pasien, tanggal, layanan, kode item, jumlah, dan harga satuan sama persis. Salinan kedua dan seterusnya masing-masing menjadi satu temuan. |
| **ULG-02** Sesi ganda | Apakah satu pasien ditagih cuci darah dua kali di hari yang sama? | Pasien yang sama punya lebih dari satu tagihan hemodialisa di rumah sakit yang sama pada hari yang sama. |
| **WJR-01** Harga | Apakah harga obat atau alat jauh di atas harga acuan? | Harga satuan **lebih dari** harga acuan × (1 + toleransi), default toleransi 10%. Dibandingkan secara eksak, tanpa galat pembulatan. |
| **WJR-02** Alat bantu dengar | Apakah alat bantu dengar diganti sebelum waktunya? | Untuk pasien dan telinga yang sama, tagihan datang **sebelum** masa penggantian (default 5 tahun) sejak pemberian sebelumnya. Pemberian sebelumnya diambil dari riwayat dan dari tagihan alat bantu dengar sebelumnya. Masa dihitung dalam bulan kalender: tepat 5 tahun (tanggal yang sama) tidak melanggar. |
| **BAND-01** Perbandingan | Apakah rumah sakit ini jauh lebih sibuk dibanding rumah sakit sejenis? | Lihat penjelasan di bawah. **Sinyal pendukung, bukan bukti utama.** |
| **SEN-01** Sensor | Apakah jam kerja mesin sesuai dengan sesi yang ditagih? | Diisi di fase 3. Sampai saat itu kontribusinya 0. |

**Definisi hari operasional hemodialisa** (sama dengan generator data): kolom `hari_operasional_hd` berisi jumlah hari unit buka per minggu, dihitung dari Senin. Nilai 6 berarti Senin–Sabtu (Minggu tutup), 7 berarti setiap hari. Secara teknis: unit buka jika `weekday(tanggal) < hari_operasional_hd`, dengan Senin = 0.

**Fisioterapi** tidak punya kolom hari operasional. KAP-01 memeriksa setiap tanggal yang punya tagihan fisioterapi.

### BAND-01: perbandingan dengan rumah sakit sejenis

1. **Utilisasi** setiap rumah sakit dihitung per layanan (fisioterapi, hemodialisa) per bulan: rata-rata dari (sesi ditagih ÷ kapasitas harian), atas hari yang punya tagihan layanan itu. Untuk hemodialisa hanya hari unit buka; sesi di hari tutup sudah ditangani KAP-02.
2. Rumah sakit itu dibandingkan dengan **rumah sakit sejenis**: kelas dan provinsi yang sama. Rumah sakit yang dinilai **tidak ikut** menghitung pembandingnya (*leave-one-out*), supaya angka yang aneh tidak menutupi dirinya sendiri.
3. Ukuran "seberapa jauh dari kebiasaan" memakai **robust z-score**: (utilisasi − median pembanding) ÷ (1,4826 × MAD pembanding). MAD adalah median selisih mutlak terhadap median. Median dan MAD tidak mudah tergeser oleh satu-dua rumah sakit ekstrem. Konstanta 1,4826 membuat angkanya setara simpangan baku untuk data normal.
4. Jika pembanding kurang dari 3 rumah sakit atau MAD = 0, pembanding diperluas ke **kelas yang sama di semua provinsi**. Jika tetap tidak memadai, penilaian dilewati dan alasannya dicatat di rincian skor.
5. Hanya utilisasi yang **lebih tinggi** dari kebiasaan yang ditandai, yaitu z > ambang (default 3).

Dengan 3 rumah sakit per kombinasi kelas-provinsi, *leave-one-out* hanya menyisakan 2 pembanding. Karena itu, pada data tiruan sebagian besar penilaian BAND-01 memakai pembanding kelas saja.

### Skor prioritas

Skor dihitung **per rumah sakit per bulan**, 0–100:

> **skor = Σ (bobot aturan × keparahan aturan)**, dengan keparahan antara 0 dan 1.

- **Bobot** tiap aturan ada di `parameter.yaml`: KAP-01 15, KAP-02 15, ULG-01 15, ULG-02 10, WJR-01 10, WJR-02 10, BAND-01 5, SEN-01 20. Jumlah bobot dijaga tepat 100, sehingga skor otomatis 0–100.
- **Keparahan** aturan KAP, ULG, dan WJR = jumlah temuan aturan itu dalam sebulan ÷ titik jenuh, maksimal 1. Contoh: titik jenuh KAP-01 = 3, maka 1 temuan = keparahan ⅓ = 5 poin, dan 3 temuan atau lebih = 15 poin.
- **Keparahan BAND-01** = (z − ambang) ÷ ambang bila z di atas ambang, maksimal 1. Dari fisioterapi dan hemodialisa diambil yang terbesar.
- **SEN-01** keparahannya 0 sampai fase 3, sehingga **skor maksimum sementara 80**.
- **Prioritas**: skor ≥ 20 = **tinggi**, skor ≥ 10 = **sedang**, selain itu **rendah**. Ambang ini ditetapkan dari sebaran skor dataset utama (lihat DEVLOG fase 2).
- Setiap skor menyimpan **rincian per aturan** (bobot, jumlah temuan, keparahan, kontribusi), **versi aturan**, dan **hash SHA-256 `parameter.yaml`**. Dengan begitu setiap angka bisa dilacak ke aturan dan parameter yang menghasilkannya.

Skor adalah **urutan prioritas pemeriksaan, bukan vonis**. Temuan bisa berasal dari kejadian sah (misalnya shift darurat atau harga acuan yang belum diperbarui) yang perlu diklarifikasi petugas.

## Modul per fase

| Fase | Modul | Isi |
|---|---|---|
| 0 | `sentinel/main.py`, `config.py`, `db.py`, `parameter.py` | Kerangka API, `/health`, settings, loader parameter |
| 1 | `sentinel/models/`, `sentinel/generator/` | Skema tabel; generator data tiruan berseed, `sesi_aktual`, `ground_truth`, dataset `--hidden` |
| 2 | `sentinel/rules/`, `sentinel/models/hasil.py` | KAP-01, KAP-02, ULG-01, ULG-02, WJR-01, WJR-02, BAND-01; tabel `temuan` dan `skor` 0–100 |
| 3 | `sentinel/sensor/` | Simulator arus, klasifikasi Edge AI, Ed25519 + hash chain, SEN-01, TAMPER_* |
| 4 | `sentinel/evaluation/` | Recall, presisi, FPR per skenario; satu-satunya modul yang membaca ground truth |
| 5 | `sentinel/api/`, `frontend/` | Endpoint dashboard, halaman beranda/detail/audit, panel demo |
| 6 | `sentinel/agents/` | RAG BM25, empat agen, validator kutipan verbatim, fallback tanpa API key |
| 7 | `Makefile`, `assets/`, `docs/NASKAH_DEMO.md` | `make demo`, screenshot, naskah video |
