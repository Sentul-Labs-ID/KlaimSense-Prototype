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
| Kenyataan (`models/kenyataan.py`) | `sesi_aktual` (sesi yang benar-benar terjadi) | Hanya simulator dunia fisik (`sensor/simulator.py`) dan evaluasi (fase 4) |
| Sensor (`models/sensor.py`) | `perangkat` (kunci publik), `status_sensor` (pesan valid), `sensor_anomali`, `status_mesin_harian` | Server: ingest, mesin aturan (SEN-01), dashboard |
| Hasil (`models/hasil.py`) | `temuan`, `skor` (keluaran mesin aturan) | Semua modul, termasuk dashboard |
| Keputusan (`models/keputusan.py`) | `keputusan` (keputusan petugas, dirantai hash) | Dashboard; hanya ditulis di dataset `demo` |
| Evaluasi (`models/evaluasi.py`) | `ground_truth`, `profil_rs`, `kasus_sah` | Hanya evaluasi (fase 4); tidak boleh diekspos API dashboard |

Semua tabel punya `dataset_id` (`utama` atau `hidden`). Mesin aturan hanya melihat apa yang dilihat BPJS di dunia nyata: tagihan, data master, dan pesan yang dikirim perangkat sensor. Batas ini dijaga oleh `tests/test_batas_akses.py`.

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
| **SEN-01** Sensor | Apakah jam kerja mesin cuci darah yang tercatat sensor cukup untuk sesi yang ditagih, dan apakah data sensornya utuh? | Lihat "Langkah 2: Cek sensor" di bawah. |

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

- **Bobot** tiap aturan ada di `parameter.yaml`: KAP-01 15, KAP-02 15, ULG-01 15, ULG-02 10, WJR-01 10, WJR-02 10, BAND-01 5, SEN-01 20. Jumlah bobot dijaga tepat 100, sehingga skor otomatis 0–100 (skor maksimum 100 sejak SEN-01 aktif di fase 3).
- **Keparahan** aturan KAP, ULG, dan WJR = jumlah temuan aturan itu dalam sebulan ÷ titik jenuh, maksimal 1. Contoh: titik jenuh KAP-01 = 3, maka 1 temuan = keparahan ⅓ = 5 poin, dan 3 temuan atau lebih = 15 poin.
- **Keparahan BAND-01** = (z − ambang) ÷ ambang bila z di atas ambang, maksimal 1. Dari fisioterapi dan hemodialisa diambil yang terbesar.
- **Keparahan SEN-01** = yang terbesar dari keparahan *selisih* dan keparahan *integritas*. Masing-masing = jumlah temuan kategori itu dalam sebulan ÷ titik jenuhnya (selisih 3, integritas 2), maksimal 1. Contoh: satu kejadian sensor dicabut = keparahan ½ = 10 poin; tiga hari selisih jam = 20 poin.
- **Prioritas**: skor ≥ 20 = **tinggi**, skor ≥ 10 = **sedang**, selain itu **rendah**. Ambang ini ditetapkan dari sebaran skor dataset utama (lihat DEVLOG fase 2).
- **Lantai prioritas** (sejak fase 3): bukti fisik yang berulang tidak boleh tenggelam di prioritas sedang. Jika dalam sebulan aturan **bukti fisik** mencapai titik jenuhnya, rumah sakit itu otomatis berprioritas **tinggi**, berapa pun skornya. Aturan bukti fisik: KAP-01 (sesi fisioterapi melebihi tenaga terapis), KAP-02 (sesi cuci darah melebihi mesin), dan SEN-01 kategori selisih (jam kerja mesin tidak cukup untuk sesi yang ditagih). Contoh: tiga hari dalam sebulan KAP-02 terlampaui hanya menghasilkan skor 15 (bobot KAP-02), tetapi prioritasnya tinggi. **Skor tidak berubah**; hanya label prioritas. Setiap skor menyimpan **alasan prioritasnya** (misalnya "lantai: KAP-02 jenuh" atau "ambang skor ≥ 20") agar dashboard bisa menjelaskannya. Daftar aturan bukti fisik bisa diubah di `parameter.yaml`. Ini keputusan prinsip, bukan hasil menyetel terhadap label.
- Setiap skor menyimpan **rincian per aturan** (bobot, jumlah temuan, keparahan, kontribusi), **versi aturan**, dan **hash SHA-256 `parameter.yaml`**. Dengan begitu setiap angka bisa dilacak ke aturan dan parameter yang menghasilkannya.

Skor adalah **urutan prioritas pemeriksaan, bukan vonis**. Temuan bisa berasal dari kejadian sah (misalnya shift darurat atau harga acuan yang belum diperbarui) yang perlu diklarifikasi petugas.

## Langkah 2: Cek sensor

Sensor membuktikan hal yang tidak bisa dibuktikan dari tagihan saja: **apakah mesin cuci darah benar-benar bekerja** sebanyak sesi yang ditagih. Seluruhnya simulasi.

### Tiga sisi yang terpisah tegas

```
 DUNIA FISIK (simulator)          PERANGKAT (edge, di mesin)            SERVER (BPJS)
 ───────────────────────          ──────────────────────────            ─────────────
 sesi_aktual ──► arus listrik ──► fitur per jendela 10 menit ──► pesan ──► ingest: cek tanda tangan,
 (kapan mesin   per menit        pohon keputusan:                ber-      seq, prev_hash, jeda
  benar dipakai) mati/standby/    mati/standby/terapi            tanda        │
                 terapi + noise   tanda tangan Ed25519           tangan       ▼
                                  rantai hash (prev_hash)                status_sensor, sensor_anomali
                                  TANPA akses basis data                     │
                                                                             ▼
                                                                 status_mesin_harian ──► SEN-01
```

- **Dunia fisik** (`sensor/simulator.py`): satu-satunya modul aplikasi yang membaca `sesi_aktual`. Dari sesi yang benar-benar terjadi, simulator membangkitkan arus listrik per menit untuk setiap mesin di rumah sakit bersensor. Polanya: **mati** (≈0 A), **standby** (rendah, stabil, sesekali lonjakan pemanas), dan **terapi** (lebih tinggi, berdenyut karena pompa, sesekali jeda). Noise dan tumpang tindih standby–terapi disengaja; nilai ampere ilustratif dan wajib dikalibrasi dengan perangkat nyata. **Tagihan fiktif tidak punya sesi, jadi mesinnya tidak menunjukkan pola terapi.**
- **Perangkat** (`sensor/edge.py`): hanya menerima larik arus, menghitung fitur per jendela (rata-rata, simpangan baku, puncak, fluktuasi berkala), mengklasifikasikan status dengan pohon keputusan, lalu mengirim **ringkasan status per jendela** (bukan sinyal mentah). Setiap pesan ditandatangani Ed25519 dan memuat `prev_hash` = SHA-256 pesan sebelumnya, sehingga pesan yang dihapus, diubah, atau disisipkan ketahuan.
- **Server** (`sensor/ingest.py`, `sensor/ringkasan.py`, `POST /sensor/ingest`): memverifikasi tanda tangan dengan kunci publik terdaftar, kesinambungan `seq` dan `prev_hash`, serta jeda heartbeat. Kejanggalan dicatat sebagai **TAMPER_SIG** (tanda tangan salah, perangkat tak dikenal), **TAMPER_CHAIN** (rantai putus, seq lompat, pesan ulangan), atau **TAMPER_GAP** (lebih dari 3 jendela berturut-turut tanpa data, artinya sensor dicabut). Pesan valid diringkas per mesin per shift per hari di `status_mesin_harian`.

**Kunci perangkat.** Dalam simulasi, kunci privat diturunkan dari seed agar hasil bisa direproduksi. **Ini hanya untuk simulasi**: perangkat sungguhan membuat kunci di dalam *secure element* dan kunci privat tidak pernah keluar dari perangkat. Server hanya menyimpan kunci publik.

**Model edge.** Pohon keputusan dilatih dengan data simulasi dari seed khusus pelatihan (7001, bukan seed dataset utama 42 maupun hidden 2026), diuji pada mesin-hari yang tidak dipakai melatih, lalu disimpan sebagai "firmware" di `backend/sentinel/sensor/model/` beserta hash SHA-256 dan metadatanya. Versi model (12 karakter pertama hash) ikut di setiap pesan.

**Jadwal shift unit** (konfigurasi simulasi, bukan `parameter.yaml`): shift 1 05:00–09:50, shift 2 09:50–14:40, shift 3 14:40–19:30, shift 4 (darurat) 19:30–24:00; di luar itu "shift 0". Durasi satu sesi diambil dari `parameter.yaml` (4 jam).

### SEN-01 (per rumah sakit bersensor, per hari)

1. **Jam dibutuhkan** = jumlah tagihan hemodialisa hari itu × durasi sesi (4 jam).
2. **Jam tercatat** = jumlah menit berstatus terapi dari semua mesin rumah sakit itu ÷ 60 (sama dengan jumlah jendela terapi × panjang jendela).
3. **Temuan selisih** bila jam tercatat **kurang dari** jam dibutuhkan × (1 − toleransi 10%). Tepat di batas tidak melanggar.
4. **Data bolong**: bila data sensor rumah sakit itu pada hari itu hilang lebih dari 5% (dari jumlah perangkat × 1.440 menit), selisih **tidak dihitung**, supaya tidak menuduh dari data yang tidak lengkap. Sebagai gantinya dibuat **temuan integritas**.
5. Setiap anomali TAMPER_SIG, TAMPER_CHAIN, dan TAMPER_GAP juga menjadi **temuan integritas**, dikelompokkan per perangkat, jenis, dan tanggal.

Contoh penjelasan: "Hemodialisa 12 Agustus 2026: 30 sesi ditagih (butuh 120 jam-mesin terapi), sensor mencatat 84 jam terapi. Selisih 36 jam." dan "Sensor mesin HD-03 tidak mengirim data selama 2 jam 10 menit pada 20 Agustus 2026."

Kasus sah "shift darurat" (sesi tambahan yang benar-benar terjadi) tetap tertandai KAP-02 karena melewati kapasitas, tetapi **tidak** tertandai SEN-01 karena mesinnya memang bekerja. Ini membantu petugas membedakan "sibuk sungguhan" dari "tagihan tanpa kerja mesin".

## Evaluasi akurasi (fase 4)

`sentinel/evaluation/` adalah satu-satunya modul yang membaca label (`ground_truth`, `profil_rs`, `kasus_sah`). Modul ini **hanya membaca**: di PostgreSQL transaksinya dibuka READ ONLY dan selalu di-rollback.

**Pasangan skenario dan aturan.** KAP_FISIO → KAP-01, KAP_HD → KAP-02, ULANG_IDENTIK → ULG-01, ULANG_HARI → ULG-02, HARGA_LEBIH → WJR-01, ABD_DINI → WJR-02, SENSOR_PALSU → SEN-01 (selisih), TAMPER_SIG dan TAMPER_GAP → SEN-01 (integritas). BAND-01 tidak dipasangkan dan dilaporkan terpisah sebagai sinyal pendukung.

**Apa yang diukur:**

- **Kejadian tertangkap (recall).** Sebuah kejadian kecurangan dihitung tertangkap bila aturan pasangannya menandai rumah sakit dan tanggal yang sama. Untuk aturan per tagihan (ULG, WJR), temuannya harus memuat tagihan kejadian itu.
- **Ketepatan temuan.** Setiap temuan dimasukkan ke salah satu dari tiga kelompok:
  - **benar**: memuat tagihan kecurangan, atau temuan integritas pada hari gangguan sensor;
  - **kasus sah**: kejadian sah di dekat batas aturan yang memang perlu klarifikasi;
  - **keliru**: selain keduanya.
- **Prioritas** diukur di level yang dilihat petugas, yaitu **rumah sakit × bulan**. Setiap RS-periode berada di salah satu kondisi:
  - **bermasalah**: memuat kecurangan;
  - **hanya gangguan sensor**: dilaporkan terpisah dan tidak dihitung sebagai tuduhan keliru;
  - **hanya kasus sah**;
  - **bersih**.
- **Setiap angka** ditulis bersama jumlahnya (misalnya 13/14) dan interval kepercayaan 95% Wilson, karena jumlah kejadian kecil.

**Kejujuran.** Dataset utama dipakai untuk mengembangkan kode evaluasi. Dataset hidden dijalankan setelah kodenya selesai; waktu jalan pertamanya dicatat di `reports/log_evaluasi_hidden.json` dan di laporan. Parameter, bobot, ambang, dan aturan tidak diubah berdasarkan hasil hidden.

## Langkah 4: Putuskan — dashboard petugas (fase 5)

Dashboard membantu petugas BPJS memutuskan tindak lanjut. **Sistem hanya memberi prioritas pemeriksaan; keputusan selalu di tangan petugas**, dan rumah sakit diberi kesempatan menjelaskan sebelum audit.

**Dataset.** Dashboard menampilkan dataset `demo` (bawaan) dan `utama` (baca-saja). Dataset hidden tidak tersedia di dashboard. `demo` adalah kembar dataset utama: dibangkitkan dengan seed yang sama, hanya ID-nya yang digeser (`RS-901…`), dan sinyal sensornya memakai kunci acak mesin padanannya, sehingga skor dan prioritasnya identik dengan utama. Semua aksi tulis (keputusan petugas, sisipan demo) hanya boleh ke `demo`. `make demo-reset` mengembalikannya ke keadaan awal.

**Halaman:**

| Halaman | Isi |
|---|---|
| Daftar periksa (`/`) | Rumah sakit × bulan, urut prioritas lalu skor; ringkasan jumlah per prioritas dan jumlah tagihan yang diperiksa; filter periode dan prioritas. |
| Detail RS (`/rs/{id}`) | Rincian skor per aturan dalam bahasa sederhana dan alasan prioritas; temuan per aturan; grafik harian sesi ditagih vs kapasitas (hari temuan ditandai); grid sensor per mesin × shift dengan tombol verifikasi tanda tangan; ringkasan otomatis (template); panel keputusan. |
| Audit (`/audit`) | Riwayat keputusan dan status rantai hash (utuh atau rusak, di entri mana). |
| Panel demo (`/demo`) | Hanya bila `DEMO_MODE=true`: sisipkan kecurangan ke dataset demo dan lihat skor/prioritas sebelum dan sesudah. |

**API (FastAPI):** `GET /meta`, `GET /rs`, `GET /rs/{rs_id}`, `POST /sensor/verifikasi`, `POST /keputusan`, `GET /audit`, `POST /demo/sisipkan`, serta `POST /sensor/ingest` dari fase 3. Semua respons dan pesan galat berbahasa Indonesia. Peramban memanggil aksi tulis lewat proksi `frontend/app/api/[...jalur]` yang hanya meneruskan tiga jalur POST.

**Rantai keputusan.** Setiap keputusan menyimpan `prev_hash` (hash keputusan sebelumnya di dataset yang sama) dan `hash` = SHA-256 isi entri. Mengubah alasan satu keputusan lama, atau memutus sambungannya, langsung terlihat sebagai "rusak" di halaman audit.

**Verifikasi sensor.** Tombol verifikasi memeriksa ulang setiap pesan tersimpan satu mesin pada satu tanggal: tanda tangan Ed25519 dengan kunci publik terdaftar, kecocokan isi dengan hash, dan sambungan `prev_hash`/`seq` ke pesan sebelumnya.

**Sisipan demo.** Memakai logika generator (tarif paket, besaran lewat kapasitas, harga acuan dan toleransi). Sisipan masuk ke periode yang dipilih, lalu mesin aturan dijalankan ulang untuk dataset demo. Sisipan tidak dicatat sebagai label evaluasi.

## Modul per fase

| Fase | Modul | Isi |
|---|---|---|
| 0 | `sentinel/main.py`, `config.py`, `db.py`, `parameter.py` | Kerangka API, `/health`, settings, loader parameter |
| 1 | `sentinel/models/`, `sentinel/generator/` | Skema tabel; generator data tiruan berseed, `sesi_aktual`, `ground_truth`, dataset `--hidden` |
| 2 | `sentinel/rules/`, `sentinel/models/hasil.py` | KAP-01, KAP-02, ULG-01, ULG-02, WJR-01, WJR-02, BAND-01; tabel `temuan` dan `skor` 0–100 |
| 3 | `sentinel/sensor/`, `sentinel/models/sensor.py`, `sentinel/rules/aturan_sensor.py` | Simulator arus (dunia), edge AI + Ed25519 + hash chain (perangkat), ingest + ringkasan harian + `POST /sensor/ingest` (server), SEN-01, TAMPER_* |
| 4 | `sentinel/evaluation/` | Recall per skenario, presisi tiga kelas per aturan, metrik prioritas RS-periode, integritas sensor, interval Wilson; laporan `reports/evaluasi.md`, `.json`, grafik; satu-satunya modul yang membaca label |
| 5 | `sentinel/api/`, `sentinel/models/keputusan.py`, `sentinel/generator/sisipan.py`, `frontend/` | API dashboard, keputusan berantai hash, audit, verifikasi sensor, sisipan demo; halaman daftar periksa, detail RS, audit, panel demo; dataset `demo` |
| 6 | `sentinel/agents/` | RAG BM25, empat agen, validator kutipan verbatim, fallback tanpa API key |
| 7 | `Makefile`, `assets/`, `docs/NASKAH_DEMO.md` | `make demo`, screenshot, naskah video |
