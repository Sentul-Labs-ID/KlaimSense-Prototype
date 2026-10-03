# FASE-05 — Dashboard petugas (Langkah 4: Putuskan)

| Kolom | Isi |
|---|---|
| Versi | v1 |
| Tanggal dijalankan | 2026-10-03 |
| Dijalankan oleh | Rifandi Indrayudha Prawira |
| Alat | Claude Code |
| Commit hasil | b12f6e6446b731e1142c8198c2a5fe478fc44be8 |
| Status | Berhasil |

## Prompt (verbatim)

```text
Baca ROADMAP.md dan CLAUDE.md. Ini adalah FASE 5: dashboard petugas (Langkah 4: Putuskan). Jangan membangun RAG atau agen AI di fase ini.

BATAS AKSES (wajib)
- API dan frontend DILARANG membaca atau mengekspos ground_truth, profil_rs, kasus_sah, dan sesi_aktual, termasuk secara tidak langsung (misalnya label "jujur" atau nama skenario). Perluas test_batas_akses.py untuk menegakkan ini di sentinel/api/ dan pastikan tidak ada respons API yang memuat kolom dari tabel-tabel tersebut.
- Dataset utama dan hidden beserta reports/ TIDAK BOLEH berubah oleh dashboard. Semua aksi tulis (keputusan petugas, sisipan demo) hanya terjadi pada dataset_id "demo".

DATASET DEMO
- `make demo-reset` membuat dataset_id "demo" yang isinya identik dengan dataset utama (boleh dibangkitkan ulang dengan seed 42 atau disalin dari utama, pilih yang lebih cepat), lengkap dengan data sensor, temuan, dan skor. Targetkan < 2 menit. Reset juga menghapus keputusan dan sisipan demo sebelumnya.
- Dashboard secara default menampilkan dataset "demo". Pemilih dataset hanya untuk "demo" dan "utama" (utama baca-saja); hidden tidak ditampilkan.

API (FastAPI, di sentinel/api/)
- GET /rs?dataset=&periode= → daftar RS-periode: nama samaran, kelas, provinsi, periode, skor, prioritas, alasan prioritas, jumlah temuan per aturan.
- GET /rs/{rs_id}?dataset=&periode= → skor dan rincian per aturan, temuan beserta penjelasan template, data harian (sesi ditagih vs kapasitas untuk fisioterapi dan HD), status_mesin_harian (jika RS bersensor), anomali sensor, dan keputusan sebelumnya.
- POST /sensor/verifikasi → untuk satu perangkat dan satu tanggal, verifikasi ulang tanda tangan dan hash chain dari status_sensor yang tersimpan, kembalikan hasilnya (jumlah pesan valid, putus, gagal).
- POST /keputusan → {dataset (harus "demo"), rs_id, periode, keputusan: setujui | minta_klarifikasi | rujuk_audit, alasan (wajib, minimal 10 karakter), petugas}. Simpan ke tabel keputusan dengan prev_hash (SHA-256 dari entri sebelumnya) dan hash entri ini.
- GET /audit?dataset= → riwayat keputusan beserta status verifikasi rantai (utuh atau rusak, dan di entri mana rusaknya).
- POST /demo/sisipkan → {rs_id, skenario: KAP_FISIO | KAP_HD | ULANG_HARI | HARGA_LEBIH, jumlah_hari 1–5}. Hanya aktif jika DEMO_MODE=true dan hanya pada dataset "demo". Sisipkan tagihan fiktif memakai logika generator, jalankan ulang mesin aturan untuk dataset demo, lalu kembalikan skor dan prioritas sebelum dan sesudah. Sisipan demo tidak ditulis ke ground_truth.
- Semua respons dan pesan galat berbahasa Indonesia.

FRONTEND (Next.js, memakai BACKEND_URL)
1. Beranda "Daftar periksa":
   - Tabel RS-periode urut prioritas lalu skor: nama samaran, kelas, provinsi, periode, skor, label prioritas berwarna, alasan prioritas, jumlah temuan.
   - Filter periode dan prioritas.
   - Ringkasan di atas: jumlah RS-periode per prioritas dan jumlah tagihan yang diperiksa.
2. Detail RS:
   - Kartu skor dengan rincian per aturan dan alasan prioritas, dalam bahasa sederhana.
   - Daftar temuan dengan penjelasan template, dikelompokkan per aturan.
   - Grafik garis harian: sesi ditagih vs garis kapasitas (fisioterapi dan HD), dengan hari temuan ditandai.
   - Grid sensor (jika RS bersensor): baris mesin, kolom shift, warna terapi/standby/mati/tanpa data, untuk tanggal yang dipilih. Tombol "Verifikasi tanda tangan" memanggil /sensor/verifikasi dan menampilkan hasilnya.
   - Panel "Ringkasan": untuk fase ini tampilkan ringkasan otomatis berbasis template dari temuan (beri label "Ringkasan otomatis (template)"). Siapkan tempat untuk ringkasan AI dari fase 6.
   - Panel keputusan: tombol Setujui / Minta klarifikasi / Rujuk ke audit, isian alasan wajib, nama petugas.
   - Catatan tetap: "Skor adalah prioritas pemeriksaan, bukan penetapan kecurangan. Rumah sakit diberi kesempatan menjelaskan sebelum audit."
3. Halaman Audit: daftar keputusan dan status rantai hash (utuh atau rusak).
4. Panel Demo (hanya jika DEMO_MODE): pilih RS, skenario, dan jumlah hari, lalu tombol "Sisipkan kecurangan". Tampilkan skor dan prioritas sebelum dan sesudah, dengan tautan ke detail RS.

DESAIN
Bersih, resmi, dan mudah dibaca juri non-teknis. Warna utama navy (#0E2A47) dan hijau (#1E7A52), aksen oranye (#A8540F) untuk prioritas tinggi atau peringatan. Semua teks berbahasa Indonesia, tanpa istilah teknis yang tidak dijelaskan. Rapi di layar 1920×1080, karena fase 7 mengambil screenshot di resolusi itu.

TES
- pytest untuk API: daftar dan detail RS, /keputusan (validasi alasan, hanya dataset demo, hash chain benar), /audit mendeteksi rantai yang sengaja dirusak dalam tes, /demo/sisipkan (menolak jika DEMO_MODE mati atau dataset bukan demo; skor naik setelah sisipan KAP), /sensor/verifikasi (valid dan rusak).
- Tes bahwa tidak ada respons API yang memuat kolom tabel evaluasi.
- Tes bahwa dataset utama, hidden, dan reports/ tidak berubah setelah seluruh alur demo dijalankan (jumlah baris dan hash file sama).
- Frontend: `npm run build` dan lint lulus. Tambahkan satu uji asap Playwright yang membuka beranda, detail RS, dan audit, lalu memastikan tidak ada galat.

SELESAI JIKA
- `make demo-reset`, `make up`, dan `make test` lulus, dan uji asap Playwright lulus.
- Alur demo berjalan: beranda → pilih RS prioritas rendah → panel demo sisipkan KAP_FISIO 3 hari → prioritas naik menjadi tinggi (lantai bukti fisik) → detail RS menampilkan temuan dan grafik → keputusan "Minta klarifikasi" → tercatat di audit dengan rantai utuh.
- Laporkan: daftar halaman dan endpoint, hasil tes, hasil alur demo di atas (skor dan prioritas sebelum/sesudah), dan keputusan atau penyimpangan.
- Setelah melapor, lanjutkan langsung ke dokumentasi KECUALI ada tes gagal atau keputusan yang menyimpang dari prompt ini. Dalam dua kasus itu, berhenti dan tunggu persetujuan saya.

LANGKAH DOKUMENTASI WAJIB (berurutan)
1. Commit kode: "feat(fase-5): dashboard petugas". Catat hash-nya.
2. Simpan prompt ini VERBATIM (dari "Baca ROADMAP.md" sampai baris terakhir) ke docs/prompts/FASE-05_dashboard.md dengan format arsip di ROADMAP.md, termasuk semua pesan lanjutan saya selama fase ini secara verbatim di "Catatan hasil". Perbarui docs/prompts/README.md.
3. ROADMAP.md: status Fase 5 menjadi ✅, tambah baris di Log progres.
4. Tambahkan entri di docs/DEVLOG.md.
5. Tambahkan entri versi 0.6.0 di CHANGELOG.md.
6. Catat penyimpangan baru di Catatan penyimpangan ROADMAP.md.
7. Commit dokumentasi: "docs(fase-5): arsip prompt, roadmap, devlog, changelog", lalu push ke origin main.
```

## Catatan hasil

### Yang dihasilkan

- **Dataset `demo`** (`make demo-reset`, 1 menit 42–55 detik).
  - Kembar dataset utama: profil generator `demo` = profil utama, seed 42, ID digeser (`RS-901…`, `P-900001…`, baris mulai 90.000.001), nama samaran sama.
  - Sinyal sensornya memakai kunci acak mesin padanan di utama, sehingga skor dan prioritas 90/90 RS-periode identik dengan utama.
  - Sidik data utama dan hidden tidak berubah.
  - Reset menghapus keputusan dan sisipan demo.
- **API** (`sentinel/api/`):
  - `GET /meta`, `GET /rs`, `GET /rs/{rs_id}` (`dashboard.py`);
  - `POST /keputusan`, `GET /audit` (`keputusan.py`, rantai SHA-256);
  - `POST /sensor/verifikasi` (`sensor.py`);
  - `POST /demo/sisipkan` (`demo.py` + `generator/sisipan.py`);
  - galat validasi dan HTTP diterjemahkan ke bahasa Indonesia (`main.py`).
- **Tabel `keputusan`** (`models/keputusan.py`).
- **Frontend** Next.js 16:
  - Daftar periksa (`/`), Detail RS (`/rs/[id]`), Audit (`/audit`), Panel demo (`/demo`).
  - Proksi `app/api/[...jalur]` hanya untuk tiga jalur POST.
  - Grafik harian dan grid sensor dengan SVG/HTML biasa.
  - Warna navy/hijau/oranye; tata letak diperiksa di 1920×1080.
  - Waktu ditampilkan dalam WIB (prompt lanjutan 1).
- **Uji asap Playwright** `frontend/e2e/asap.spec.ts` (`make e2e`).
- **Tes:** `make test` 201 lulus.
  - API: daftar, detail, validasi keputusan, rantai hash dan audit mendeteksi perusakan, sisipan (mode demo mati / bukan demo / KAP menaikkan skor dan prioritas), verifikasi sensor valid dan rusak.
  - Respons tanpa kolom atau nilai evaluasi.
  - Utama, hidden, dan `reports/` tidak berubah setelah alur demo.
  - Batas akses diperluas ke `generator/sisipan.py` dan frontend.
- **Alur demo** (UI sungguhan, 1920×1080):
  1. RS Tiruan 012, Agustus 2026: **skor 3,3, rendah**.
  2. Sisipkan KAP_FISIO 3 hari (4, 11, 12 Agustus; 40 tagihan baru).
  3. Hasil: **skor 18,3, tinggi**, alasan "Bukti fisik berulang: kapasitas fisioterapi terlampaui berkali-kali dalam sebulan" (murni lantai, karena skor < 20).
  4. Detail RS menampilkan 3 temuan KAP-01 dan grafik.
  5. Keputusan "Minta klarifikasi" tercatat; audit: **rantai utuh**; tanpa galat konsol.

### Masalah yang muncul

- **Uji asap pertama gagal** karena `getByRole("alert")` menangkap pengumum rute bawaan Next.js; pemeriksaan diganti ke teks kotak galat.
- **Skrip alur demo sempat mengklik judul**, bukan tombol "Sisipkan kecurangan"; diganti ke pemilih peran tombol. API sendiri bekerja (±2,7 detik per sisipan).
- **`make demo-reset` sempat 2 menit 10 detik** saat menimpa data demo lama (menghapus 1,46 juta pesan sensor). Ketiga langkah digabung ke satu container, sehingga menjadi 1 menit 55 detik.
- **Tes batas akses frontend** butuh berkas `frontend/` di container; `make test` me-mount `frontend/` baca-saja.
- **Tata letak:** nama dan periode di tabel beranda terbungkus, dan kolom angka di rincian skor rapat; diperbaiki setelah pemeriksaan tangkapan layar.

### Penyimpangan dari prompt atau roadmap

Disetujui pengguna; dicatat juga di `ROADMAP.md`.

1. **Endpoint tambahan `GET /meta`** (dataset tersedia, daftar periode, daftar RS, status mode demo) untuk navigasi dan panel demo.
2. **Field opsional `periode` di `POST /demo/sisipkan`** agar hari sisipan berada di bulan yang sama (alur demo pasti mencapai titik jenuh); tanpa field ini, sisipan diambil dari seluruh periode.
3. **Cara pembuatan dataset demo:** dibangkitkan ulang dengan seed 42 sebagai kembar utama dengan ID digeser (ID adalah kunci global). Kunci acak sensor dipetakan ke mesin utama agar sinyalnya identik. Generator juga menulis label evaluasi untuk demo, tetapi API tidak membacanya.
4. **Keputusan lain:**
   - `DEMO_MODE` default tetap `false` (panel demo: `DEMO_MODE=true make up`).
   - `make test` me-mount `frontend/` baca-saja.
   - Dependensi dev `@playwright/test`.
   - Grafik tanpa pustaka baru.

### Prompt lanjutan 1 (verbatim, 2026-10-03)

```text
Keputusan 1–3 disetujui.

Satu perubahan kecil sebelum dokumentasi: tampilkan semua waktu di frontend (halaman audit dan panel keputusan) dalam zona Asia/Jakarta dengan label "WIB". Penyimpanan di database dan respons API tetap UTC. Pastikan lint, build, uji asap Playwright, dan make test tetap lulus.

Setelah itu lanjutkan 7 langkah dokumentasi fase 5. Catat pesan ini verbatim di arsip prompt, dan catat endpoint /meta, field periode di demo/sisipkan, dan cara pembuatan dataset demo sebagai penyimpangan yang disetujui.
```

Hasil:
- Fungsi `waktuWIB` di `frontend/lib/teks.ts` membaca waktu API sebagai UTC dan menampilkannya dalam zona Asia/Jakarta dengan label "WIB".
- Dipakai di halaman audit (kolom "Waktu (WIB)") dan di riwayat keputusan pada panel keputusan. Contoh: API `2026-10-03T06:50:33` tampil sebagai "3 Oktober 2026 13.50 WIB".
- Basis data dan respons API tetap UTC.
- Uji asap kini juga memeriksa kolom "Waktu (WIB)".
- Lint, build, uji asap, dan `make test` (201) lulus.
- Waktu anomali sensor tetap ditampilkan sebagai tanggal (waktu jendela simulasi, bukan waktu pencatatan server).
