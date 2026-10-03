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

## 2026-10-03 — Fase 3: sensor IoT dan edge AI (Langkah 2: Cek sensor)
- Dikerjakan:
  - Tiga sisi terpisah tegas:
    - **dunia fisik** `sensor/simulator.py`: satu-satunya modul aplikasi yang membaca `sesi_aktual`;
    - **perangkat** `sensor/edge.py` + `protokol.py`: tanpa basis data; tes membuktikan `sqlalchemy`/`psycopg` tidak termuat;
    - **server** `sensor/ingest.py`, `ringkasan.py`, `POST /sensor/ingest`, SEN-01.
  - Harness `sensor/pipeline.py` + `gangguan.py` (TAMPER_SIG/TAMPER_GAP dicatat di ground truth) dan pabrik model `sensor/latih.py`.
  - Tabel `perangkat`, `status_sensor`, `sensor_anomali`, `status_mesin_harian`.
  - `make sensor`.
  - Lantai prioritas bukti fisik.
  - 172 tes lulus.
- **Akurasi edge AI.** Pohon keputusan kedalaman 6. Fitur per jendela 10 menit: rata-rata, simpangan baku, puncak, rata-rata selisih mutlak antar-menit (fluktuasi pompa). Dilatih dengan seed khusus pelatihan 7001 (bukan 42/2026) pada 280 mesin-hari simulasi; diuji pada 120 mesin-hari lain (17.280 jendela). **Akurasi uji 97,75%.** Confusion matrix (baris = asli, kolom = prediksi):

  | | mati | standby | terapi |
  |---|---|---|---|
  | **mati** | 9.347 | 1 | 0 |
  | **standby** | 0 | 2.634 | 242 |
  | **terapi** | 0 | 145 | 4.911 |

  Model pertama mencapai 99,6% (terlalu bersih). Tumpang tindih standby–terapi diperbesar: lonjakan pemanas saat standby, baseline terapi lebih rendah, noise lebih besar. Kesalahan tersisa ada di batas standby/terapi, seperti yang diharapkan pada perangkat nyata. Hash model: `b5f9f57d0e586f714cf9e1f800992ae18baa4d7b6999980ebd22393a254f9baf`.
- Hasil:

  | | utama | hidden |
  |---|---|---|
  | Perangkat / pesan | 113 / 1.461.560 | 115 / 1.487.544 |
  | Ditolak / anomali | 6 / TAMPER_SIG 6, TAMPER_GAP 1 | 5 / TAMPER_SIG 5, TAMPER_GAP 1 |
  | SEN-01 selisih / integritas | 22 / 2 | 12 / 2 |
  | Skor maks | 50 (fase 2: 30) | 40 (fase 2: 40) |
  | RS tinggi/sedang/rendah | 8/2/20 (fase 2: 5/3/22) | 7/6/17 (fase 2: 5/7/18) |

  `make sensor` (kedua dataset + `make rules`) selesai dalam 2 menit 40–53 detik.
- Keputusan:
  - **Ambang prioritas tetap tinggi ≥ 20, sedang ≥ 10.** Diperiksa ulang hanya dengan sebaran skor dataset utama: celah 8,33 → 10 dan 18,33 → 21,67 masih ada. Dengan ambang ini:
    - satu temuan integritas sensor (10 poin) = "sedang";
    - satu hari selisih jam (6,67) = "rendah";
    - tiga hari selisih (20) = "tinggi".
  - **Lantai prioritas** (permintaan pengguna, keputusan prinsip, bukan hasil melihat label). Aturan bukti fisik (KAP-01, KAP-02, SEN-01 selisih) yang jenuh dalam satu periode membuat prioritas minimal "tinggi". Skor tidak berubah; `skor.alasan_prioritas` menjelaskan labelnya. Efek: 3 RS-periode di utama dan 1 di hidden naik ke "tinggi".
  - **Kunci perangkat diturunkan dari seed HANYA untuk simulasi.** Server hanya menyimpan kunci publik.
  - **SEN-01 tidak menuduh dari data bolong.** Bila data hilang > 5% (perangkat × 1.440 menit), hari itu menjadi temuan integritas, bukan selisih.
  - **Paralel per perangkat** (16 proses). Rantai tiap perangkat independen dan keacakan diturunkan dari (seed, ID perangkat), jadi hasilnya deterministik di urutan proses mana pun.
- Dependensi baru dan alasannya:
  - **`cryptography`**: tanda tangan Ed25519 perangkat. Pustaka kriptografi standar Python, berbasis OpenSSL; jangan pernah menulis kriptografi sendiri.
  - **`scikit-learn==1.9.1`**: pohon keputusan edge, sesuai prompt. Versi dipatok tepat agar file model (pickle) dan hash-nya konsisten di lokal dan container.
  - **`numpy`**: simulasi arus per menit dan fitur jendela secara vektor. Juga dependensi scikit-learn; tanpa numpy, simulasi 33 juta menit per dataset terlalu lambat.
- Masalah dan solusi:
  - Prompt pertama terpotong; pekerjaan baru dimulai setelah prompt lengkap diterima.
  - Verifikasi Ed25519 satu inti ±11.000 pesan/detik (±4,5 menit untuk 2,95 juta pesan). Solusi: paralel per perangkat.
  - Byte pickle model berbeda antar-lingkungan (Python 3.13 lokal vs 3.12 container) dan antar-keadaan proses, walau struktur pohon identik. Tes membandingkan struktur, dan hash hanya di proses baru dengan lingkungan sama.
  - Dockerfile menyalin kode sebelum `pip install`, sehingga setiap ubah kode memasang ulang dependensi (`make sensor` sempat 3 menit 56 detik). Urutan layer diperbaiki.
  - Ringkasan CLI aturan memilih periode berskor tertinggi untuk prioritas per RS. Diperbaiki menjadi prioritas tertinggi dulu, lalu skor.
- **Keterbukaan soal pemeriksaan kalibrasi sensor:**
  - Pemeriksaan kalibrasi dilakukan dengan membuka `sesi_aktual` dan `ground_truth` **langsung di basis data, pada dataset UTAMA saja**, hanya sebagai pemeriksaan kewarasan.
  - Hasilnya: rasio jam terapi tercatat ÷ jam sesi nyata pada hari jujur rata-rata 1,02 (P05 0,96, minimum 0,917, di atas batas 0,90), dan 22 temuan selisih utama jatuh pada hari kejadian yang disisipkan.
  - **Tidak ada parameter yang diubah berdasarkan pemeriksaan itu.** Pengaturan noise dan model sudah final sebelum pemeriksaan; ambang dan titik jenuh tidak berubah.
- **Status dataset hidden terhadap labelnya (dinyatakan akurat):**
  - **Sejak mesin aturan dibuat di fase 2, keluaran dataset hidden (temuan, skor, data sensor) belum pernah dibandingkan dengan labelnya**, dan tidak ada parameter aturan, skor, atau sensor yang berasal dari hidden.
  - Satu catatan jujur: di fase 1, saat memvalidasi generator (sebelum ada mesin aturan), profil per RS, daftar skenario per RS, dan besaran kejadian KAP dataset hidden sempat dicetak sekali. Ringkasan jumlah kejadian per skenario hidden juga dilaporkan di fase 1.
  - Hal ini perlu disebut di laporan evaluasi fase 4.
- Penyimpangan dari roadmap: lihat `ROADMAP.md` bagian Catatan penyimpangan (baris fase 3), termasuk lantai prioritas sebagai penyimpangan dari rumus prioritas fase 2.
- Berikutnya: Fase 4 — evaluasi akurasi (recall, presisi, FPR per skenario; kasus sah dilaporkan terpisah sebagai "kasus sah yang perlu klarifikasi"; dataset hidden dicetak terpisah; keterbatasan: margin aman data non-sah, pembanding BAND-01 terbatas, catatan paparan hidden di fase 1).

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
