# FASE-03 — Sensor IoT dan Edge AI (Langkah 2: Cek sensor)

| Kolom | Isi |
|---|---|
| Versi | v1 |
| Tanggal dijalankan | 2026-10-03 |
| Dijalankan oleh | Rifandi Indrayudha Prawira |
| Alat | Claude Code |
| Commit hasil | a475ca08671c814671e851b7d4b7b4aa13e394fc |
| Status | Berhasil |

## Prompt (verbatim)

```text
Baca ROADMAP.md dan CLAUDE.md. Ini adalah FASE 3: sensor IoT dan Edge AI (Langkah 2: Cek sensor), semuanya simulasi. Jangan membangun evaluasi atau dashboard di fase ini.

PRINSIP DESAIN
Ada tiga sisi yang harus terpisah tegas, seperti di dunia nyata:
- DUNIA FISIK (simulator): boleh membaca sesi_aktual untuk tahu kapan mesin benar-benar dipakai. Hanya simulator yang boleh membaca tabel ini.
- PERANGKAT (edge): hanya menerima sinyal arus dari simulator, mengklasifikasikannya, menandatangani, dan mengirim. Tidak boleh membaca database.
- SERVER (ingest dan aturan): hanya menerima pesan perangkat. Mesin aturan tetap DILARANG membaca sesi_aktual, ground_truth, profil_rs, dan kasus_sah.
Perbarui test_batas_akses.py untuk menegakkan ketiga batas ini, dan perbarui tabel batas akses di CLAUDE.md serta docs/ARSITEKTUR.md.

1. SIMULATOR SINYAL (sentinel/sensor/simulator.py)
- Untuk setiap mesin HD di RS punya_sensor, bangkitkan arus listrik per menit selama periode data, berdasarkan sesi_aktual (mesin_id, shift, tanggal).
- Tetapkan jam tiap shift (termasuk shift ke-4 darurat dari kasus sah) di konfigurasi simulasi, bukan di parameter.yaml. Durasi sesi dari parameter.yaml.
- Tiga pola: mati (sekitar 0 A), standby (rendah dan stabil), terapi (lebih tinggi dengan fluktuasi berkala dari pompa). Tambahkan noise dan sedikit tumpang tindih antara standby dan terapi supaya klasifikasi tidak trivial. Nilai ampere ILUSTRATIF; beri komentar bahwa harus dikalibrasi dengan perangkat nyata.
- Mesin yang tidak dipakai pada sebuah shift berstatus standby atau mati (acak dengan seed).
- Tagihan fiktif (termasuk SENSOR_PALSU) tidak punya sesi_aktual, sehingga mesinnya otomatis tidak menunjukkan pola terapi.

2. EDGE AI (sentinel/sensor/edge.py), berjalan "di perangkat"
- Jendela default 10 menit (bisa diatur). Hitung fitur per jendela: rata-rata, simpangan baku, puncak, dan ukuran fluktuasi berkala.
- Klasifikasikan terapi, standby, atau mati dengan decision tree scikit-learn. Latih dengan data simulasi berlabel dari seed KHUSUS PELATIHAN (bukan seed dataset utama atau hidden). Uji pada jendela yang tidak dipakai melatih.
- Simpan model ke file beserta hash SHA-256-nya. Laporkan akurasi dan confusion matrix klasifikasi di DEVLOG. Akurasi 100% sempurna kemungkinan berarti noise terlalu kecil; sesuaikan supaya realistis.
- Perangkat hanya mengirim ringkasan status per jendela, bukan sinyal mentah.

3. INTEGRITAS PESAN
- Tabel perangkat(device_id, dataset_id, rs_id, mesin_id, public_key, aktif). Setiap mesin bersensor punya satu perangkat dengan pasangan kunci Ed25519 (library cryptography). Untuk reproduksibilitas simulasi, kunci privat boleh diturunkan dari seed; dokumentasikan bahwa ini HANYA untuk simulasi. Kunci privat tidak pernah disimpan di tabel server.
- Pesan: {device_id, rs_id, mesin_id, window_start, status, confidence, seq, prev_hash, versi_model}, ditandatangani. prev_hash = SHA-256 pesan sebelumnya dari perangkat yang sama.
- Fungsi ingest memverifikasi tanda tangan dengan kunci publik terdaftar, kesinambungan seq, dan prev_hash. Pesan valid disimpan ke status_sensor. Kejanggalan disimpan ke sensor_anomali(jenis, device_id, waktu, keterangan) dengan jenis TAMPER_SIG (tanda tangan salah), TAMPER_CHAIN (rantai putus atau seq lompat), atau TAMPER_GAP (heartbeat hilang lebih dari N jendela, artinya sensor dicabut).
- Endpoint POST /sensor/ingest (satu pesan atau batch) memakai fungsi ingest yang sama. Untuk simulasi massal, panggil fungsinya langsung tanpa HTTP supaya cepat.
- Skenario gangguan di kedua dataset: satu perangkat mengirim beberapa pesan palsu (tanda tangan salah), dan satu perangkat dicabut ±2 jam di tengah shift. Catat kejadian ini di ground_truth dengan skenario TAMPER_SIG dan TAMPER_GAP.
- Simpan ringkasan untuk dashboard fase 5: status_mesin_harian(dataset_id, rs_id, mesin_id, tanggal, shift, menit_terapi, menit_standby, menit_mati, menit_tanpa_data).

4. ATURAN SEN-01 di sentinel/rules/ (level hari)
- Untuk setiap RS bersensor per hari:
  - jam_dibutuhkan = jumlah tagihan HD hari itu × durasi sesi HD
  - jam_tercatat = jumlah jendela berstatus terapi × panjang jendela, dijumlah untuk semua mesin
  - temuan selisih jika jam_tercatat < jam_dibutuhkan × (1 − toleransi_sensor)
- Jika data sensor hari itu hilang melebihi batas yang diatur di parameter.yaml, JANGAN hitung selisih (supaya tidak menuduh berdasarkan data bolong). Buat temuan integritas sebagai gantinya.
- Anomali TAMPER_SIG, TAMPER_CHAIN, dan TAMPER_GAP juga menjadi temuan integritas SEN-01.
- Keparahan SEN-01 = maksimum dari keparahan selisih dan keparahan integritas, memakai titik jenuh di parameter.yaml. Dokumentasikan di ARSITEKTUR.md.
- Penjelasan dari template. Contoh: "Hemodialisa 12 Agustus 2026: 30 sesi ditagih (butuh 120 jam-mesin terapi), sensor mencatat 84 jam terapi. Selisih 36 jam." dan "Sensor mesin HD-03 tidak mengirim data selama 2 jam 10 menit pada 20 Agustus 2026."
- Jalankan ulang perhitungan skor sehingga SEN-01 aktif (skor maksimum kini 100). Periksa ulang ambang prioritas HANYA dengan sebaran dataset utama; kalau diubah, catat alasannya.

CLI
- `make sensor`: untuk kedua dataset, jalankan simulator → edge → ingest → ringkasan harian, lalu `make rules` dijalankan ulang. Targetkan selesai < 3 menit untuk keduanya; jika lebih lambat, sesuaikan cara penyimpanan dan catat keputusannya.

TES (pytest)
- Tanda tangan valid diterima; tanda tangan palsu, rantai putus, seq lompat, dan gap terdeteksi.
- Classifier edge benar pada contoh khas setiap status; model dan hash konsisten.
- SEN-01: kasus selisih, kasus tidak selisih, kasus tepat di batas, dan kasus data bolong (tidak boleh menjadi temuan selisih).
- Uji integrasi (tes boleh membaca tabel evaluasi; kode aplikasi tidak): hari kasus sah HD_SHIFT_TAMBAHAN di RS bersensor TIDAK memicu temuan selisih SEN-01.
- Batas akses tiga sisi ditegakkan.

SELESAI JIKA
- `make sensor` dan `make test` lulus.
- Laporkan: akurasi dan confusion matrix edge, jumlah pesan dan anomali per dataset, jumlah temuan SEN-01 (selisih dan integritas), waktu jalan, perubahan sebaran skor dan ambang prioritas, serta keputusan atau penyimpangan. Sertakan juga 10 RS teratas per dataset (tanpa data evaluasi).
- Setelah melapor, lanjutkan langsung ke dokumentasi KECUALI ada tes yang gagal atau keputusan yang menyimpang dari prompt ini. Dalam dua kasus itu, berhenti dan tunggu persetujuan saya.

LANGKAH DOKUMENTASI WAJIB (berurutan)
1. Commit kode: "feat(fase-3): sensor IoT dan edge AI". Catat hash-nya.
2. Simpan prompt ini VERBATIM (dari "Baca ROADMAP.md" sampai baris terakhir) ke docs/prompts/FASE-03_sensor-iot-edge-ai.md dengan format arsip di ROADMAP.md, termasuk semua pesan lanjutan saya selama fase ini secara verbatim di "Catatan hasil". Perbarui docs/prompts/README.md.
3. ROADMAP.md: status Fase 3 menjadi ✅, tambah baris di Log progres.
4. Tambahkan entri di docs/DEVLOG.md (termasuk akurasi edge dan alasan setiap dependensi baru).
5. Tambahkan entri versi 0.4.0 di CHANGELOG.md.
6. Catat penyimpangan baru di Catatan penyimpangan ROADMAP.md.
7. Commit dokumentasi: "docs(fase-3): arsip prompt, roadmap, devlog, changelog", lalu push ke origin main.
```

## Catatan hasil

### Pengiriman pertama (terpotong)

Pengiriman pertama prompt ini terpotong. Isinya sama persis dengan prompt di atas dari "Baca ROADMAP.md" sampai baris:

```text
- Jika data sensor hari itu hilang melebihi batas yang diatur di parameter.yaml,
```

lalu berhenti. Claude tidak mengerjakan apa pun dan meminta sisa prompt. Prompt lengkap (di atas) dikirim ulang.

### Yang dihasilkan

- **Tiga sisi terpisah:**
  - **Dunia fisik** `sensor/simulator.py`: satu-satunya modul aplikasi yang membaca `sesi_aktual`.
  - **Perangkat** `sensor/edge.py` + `sensor/protokol.py`: tanpa basis data; dibuktikan tes bahwa `sqlalchemy`/`psycopg` tidak termuat.
  - **Server** `sensor/ingest.py`, `sensor/ringkasan.py`, `api/sensor.py`.
  - **Harness** `sensor/pipeline.py`, `sensor/gangguan.py` (mencatat TAMPER_SIG/TAMPER_GAP di ground truth).
  - **Pabrik model** `sensor/latih.py`.
- **Tabel server** (`models/sensor.py`): `perangkat`, `status_sensor`, `sensor_anomali`, `status_mesin_harian`.
- **Model edge** (pohon keputusan, kedalaman 6, fitur: rata-rata, simpangan baku, puncak, fluktuasi berkala) disimpan di `backend/sentinel/sensor/model/` beserta hash SHA-256 `b5f9f57d0e586f714cf9e1f800992ae18baa4d7b6999980ebd22393a254f9baf` dan metadata.
  - Akurasi uji **97,75%**. Seed latih 7001; uji pada 120 mesin-hari yang tidak dipakai melatih.
  - Confusion matrix (baris = asli, kolom = prediksi; mati/standby/terapi): `[[9347, 1, 0], [0, 2634, 242], [0, 145, 4911]]`.
- **Aturan SEN-01** (`rules/aturan_sensor.py`), kategori selisih dan integritas; skor maksimum kini 100.
- **Lantai prioritas** (prompt lanjutan 1): kolom `skor.alasan_prioritas`, daftar `skor.aturan_bukti_fisik` di `parameter.yaml`.
- **Parameter baru:** `sensor.batas_data_hilang_persen: 5`, `sensor.gap_maks_jendela: 3`, titik jenuh `SEN-01-selisih: 3` dan `SEN-01-integritas: 2`, serta `aturan_bukti_fisik`.
- **`make sensor`**: kedua dataset lalu `make rules`, 2 menit 40–53 detik (16 proses).
- **Tes: 172 lulus.**
- **Hasil per dataset:**

| | utama | hidden |
|---|---|---|
| Perangkat | 113 | 115 |
| Pesan (diterima / ditolak) | 1.461.560 (1.461.554 / 6) | 1.487.544 (1.487.539 / 5) |
| Anomali | TAMPER_SIG 6, TAMPER_GAP 1 | TAMPER_SIG 5, TAMPER_GAP 1 |
| SEN-01 selisih / integritas | 22 / 2 | 12 / 2 |
| Waktu simulasi sensor | ±70 detik | ±76 detik |
| Skor maks (fase 2 → fase 3) | 30 → 50 | 40 → 40 |
| RS tinggi/sedang/rendah: fase 2 | 5 / 3 / 22 | 5 / 7 / 18 |
| RS tinggi/sedang/rendah: SEN-01 aktif | 6 / 4 / 20 | 6 / 7 / 17 |
| RS tinggi/sedang/rendah: + lantai prioritas | **8 / 2 / 20** | **7 / 6 / 17** |
| RS-periode dinaikkan lantai | 3 | 1 |

- **Ambang prioritas tetap tinggi ≥ 20, sedang ≥ 10.** Sebaran skor utama masih punya celah 8,33 → 10 dan 18,33 → 21,67.

### Masalah yang muncul

- **Prompt terpotong** pada pengiriman pertama (lihat di atas).
- **Verifikasi Ed25519 lambat.** Di satu inti ±11.000 pesan/detik, jadi ±4,5 menit untuk 2,95 juta pesan. Solusi: pipeline paralel per perangkat (rantai tiap perangkat independen), 16 proses, kunci acak per perangkat dari seed dan ID agar tetap deterministik.
- **Akurasi model awal 99,6%** (terlalu bersih). Tumpang tindih standby–terapi diperbesar hingga 97,75%.
- **Byte pickle berbeda antar-lingkungan.** Byte pickle model bergantung pada keadaan proses dan versi Python/numpy (struktur pohon tetap identik). Tes hash latih ulang dibuat di proses baru dan hanya bila lingkungan sama dengan yang tercatat di metadata model.
- **Dockerfile.** Kode disalin sebelum `pip install`, sehingga setiap perubahan kode memasang ulang semua dependensi (`make sensor` sempat 3 menit 56 detik). Urutan layer diperbaiki; build ulang setelah ubah kode kini ±3,5 detik.
- **Dua tes awal salah.** Pesan palsu yang *menggantikan* pesan asli juga memicu TAMPER_CHAIN; skenario yang benar adalah *menyisipkan*.
- **Ringkasan CLI aturan** sempat memilih periode berskor tertinggi untuk prioritas per RS, padahal lantai bisa berlaku di periode lain. Diperbaiki: prioritas tertinggi dulu, lalu skor.

### Pemeriksaan kalibrasi (di luar kode aplikasi)

- Rasio jam terapi tercatat ÷ jam sesi nyata pada hari jujur di dataset **utama**: rata-rata 1,02, P05 0,96, minimum 0,917 (di atas batas 0,90).
- Semua 22 temuan selisih utama jatuh pada hari kejadian yang memang disisipkan.
- Pemeriksaan ini membuka `sesi_aktual` dan `ground_truth` langsung di basis data, **hanya pada dataset utama**, sebagai pemeriksaan kewarasan. Tidak ada parameter yang diubah berdasarkan pemeriksaan ini.

### Penyimpangan dari prompt atau roadmap

Dicatat juga di `ROADMAP.md`. Poin 1–3 disetujui pengguna (prompt lanjutan 1).

1. `sensor_anomali` mendapat kolom tambahan `dataset_id` (konvensi semua tabel) dan `durasi_menit` (untuk template TAMPER_GAP).
2. `temuan` mendapat kolom `kategori` (`selisih`/`integritas`, khusus SEN-01) lewat migrasi sederhana `ALTER TABLE`.
3. `status_sensor` juga menyimpan `hash` dan `tanda_tangan` (bytea) agar pesan bisa diverifikasi ulang untuk audit.
4. **Lantai prioritas** (prompt lanjutan 1): menyimpang dari rumus prioritas fase 2, yang hanya memakai ambang skor. Aturan bukti fisik (KAP-01, KAP-02, SEN-01 selisih) yang jenuh dalam satu periode membuat prioritas minimal "tinggi". `skor.alasan_prioritas` ditambahkan.
5. **Keputusan lain:**
   - Jadwal shift 05:00 / 09:50 / 14:40 / 19:30–24:00 (shift 4 darurat), semua dalam satu tanggal.
   - Batas data hilang dihitung dari jumlah perangkat × 1.440 menit.
   - Pesan dengan seq maju tetapi rantai putus tetap disimpan (ditandai TAMPER_CHAIN); pesan ulangan ditolak; perangkat tak terdaftar atau identitas tak cocok = TAMPER_SIG.
   - Model "firmware" di-commit, dan `scikit-learn==1.9.1` dipatok.
   - Dockerfile memasang dependensi sebelum kode.
   - `make generate` juga menghapus data sensor (urutan: generate → sensor).
   - Pipeline menerima filter `rs_ids` untuk uji integrasi.

### Prompt lanjutan 1 (verbatim, 2026-10-03)

```text
Penyimpangan 1–3 disetujui.

Satu perubahan sebelum dokumentasi: tambahkan LANTAI PRIORITAS. Aturan bukti fisik (KAP-01, KAP-02, dan SEN-01 kategori selisih) yang keparahannya mencapai 1 (sudah di titik jenuh) dalam satu periode membuat prioritas RS tersebut minimal "tinggi", berapa pun skornya. Skor tidak berubah; hanya label prioritas. Alasan desain: kapasitas fisik yang terlampaui berulang kali adalah bukti terkuat di sistem, sehingga tidak boleh berakhir di prioritas sedang hanya karena bobot satu aturan maksimal 15. Ini keputusan prinsip, bukan hasil melihat label.
- Daftar aturan bukti fisik ditaruh di parameter.yaml (bisa diubah), dengan komentar alasannya.
- Tabel skor menyimpan alasan prioritas (misalnya "lantai: KAP-02 jenuh" atau "ambang skor"), supaya dashboard bisa menjelaskannya.
- Tes: aturan bukti fisik jenuh memicu lantai; keparahan di bawah 1 tidak memicu; aturan non-fisik yang jenuh tidak memicu.
- Dokumentasikan di ARSITEKTUR.md dengan bahasa non-teknis.
- Jalankan ulang make rules dan laporkan jumlah RS per prioritas di kedua dataset setelah perubahan.

Di DEVLOG, catat secara terbuka bahwa pemeriksaan kalibrasi sensor dilakukan dengan membuka sesi_aktual dan ground_truth langsung di database pada dataset UTAMA saja, hanya sebagai pemeriksaan kewarasan, dan tidak ada parameter yang diubah berdasarkan pemeriksaan itu. Tegaskan juga bahwa dataset hidden belum pernah dilihat terhadap labelnya.

Setelah itu lanjutkan 7 langkah dokumentasi fase 3. Catat pesan ini verbatim di arsip prompt, dan catat lantai prioritas sebagai penyimpangan dari rumus prioritas fase 2.
```

Hasil:
- Lantai prioritas diterapkan, dengan 6 tes baru (lantai terpicu, keparahan < 1 tidak memicu, aturan non-fisik jenuh tidak memicu, daftar bisa diubah, validasi parameter).
- `make rules`: RS tinggi/sedang/rendah utama 8/2/20 (3 RS-periode dinaikkan lantai), hidden 7/6/17 (1 RS-periode dinaikkan lantai).
- `make test` 172 lulus.

**Koreksi atas pernyataan "dataset hidden belum pernah dilihat terhadap labelnya".** Saat memvalidasi generator di fase 1, sebelum mesin aturan ada, Claude sekali mencetak profil per RS, daftar skenario per RS, dan besaran kejadian KAP dataset hidden. Ringkasan jumlah kejadian per skenario hidden juga dilaporkan di fase 1. Sejak mesin aturan dibuat (fase 2), keluaran hidden (temuan, skor, sensor) **belum pernah** dibandingkan dengan labelnya, dan tidak ada parameter aturan, skor, atau sensor yang berasal dari hidden. DEVLOG mencatat versi yang akurat ini.
