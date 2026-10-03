# FASE-07 — Paket demo, tangkapan layar, video, dan README final

| Kolom | Isi |
|---|---|
| Versi | v1 |
| Tanggal dijalankan | 2026-10-03 |
| Dijalankan oleh | Rifandi Indrayudha Prawira |
| Alat | Claude Code |
| Commit hasil | 87ac7b4b5fcd8a4bfa34997831b8928b6b50a32f |
| Status | Berhasil |

## Prompt (verbatim)

```text
Baca ROADMAP.md dan CLAUDE.md. Ini adalah FASE 7: paket demo, tangkapan layar, video, dan README final. Fase 6 (RAG) BELUM dikerjakan; urutan 7 sebelum 6 adalah keputusan sadar agar paket proposal siap lebih dulu. Catat ini sebagai penyimpangan urutan di ROADMAP.

ATURAN
- Jangan mengubah logika generator, aturan, sensor, evaluasi, atau parameter. Fase ini hanya pengemasan.
- `make demo` dan semua target fase ini DILARANG menjalankan evaluasi hidden dan DILARANG menulis ke reports/ atau ke log jalan hidden. Angka resmi tetap dari jalan tunggal 2026-10-03T06:02:34Z.

1. `make demo`
   Dari repo bersih (setelah clone dan salin .env.example ke .env): build, jalankan layanan dengan DEMO_MODE=true, generate (utama dan hidden), sensor, rules, demo-reset. Jangan menjalankan eval. Di akhir, cetak alamat dashboard dan langkah demo singkat. Uji sendiri dari clone baru di folder sementara.

2. `make verifikasi-reproduksi` (pemeriksaan kepercayaan)
   - Bangkitkan ulang semua data di basis data atau skema terpisah yang tidak menimpa data aktif, jalankan sensor, rules, dan perhitungan evaluasi.
   - Bandingkan angka hasilnya dengan reports/evaluasi.json (semua pembilang, penyebut, dan metrik). Hasilnya harus identik.
   - Tulis hasilnya ke reports/verifikasi_reproduksi.json beserta waktu dan hash commit. Jangan mengubah evaluasi.json atau log jalan hidden.
   - Tegaskan di keluaran bahwa ini verifikasi reproduksi dengan kode dan parameter yang sudah dibekukan, bukan penyetelan.
   - Jika makan waktu lebih dari 10 menit untuk dibangun, lewati dan laporkan.

3. Tangkapan layar otomatis (Playwright, 1920×1080, ke assets/)
   - 01_daftar-periksa.png: beranda dengan ringkasan prioritas.
   - 02_detail-rs.png: detail RS prioritas tinggi yang punya temuan kapasitas dan SEN-01, menampilkan kartu skor, alasan prioritas, temuan, dan grafik harian.
   - 03_grid-sensor.png: grid sensor dengan hasil "Verifikasi tanda tangan" terlihat.
   - 04_demo-sebelum-sesudah.png: panel demo setelah sisipan KAP_FISIO 3 hari (skor dan prioritas sebelum/sesudah).
   - 05_keputusan.png: panel keputusan setelah "Minta klarifikasi" tercatat.
   - 06_audit.png: halaman audit dengan status rantai utuh dan waktu WIB.
   Salin juga reports/recall_per_skenario.png dan reports/prioritas_hidden.png ke assets/. Perintah: `make tangkapan-layar` (menjalankan demo-reset dulu agar hasilnya bersih dan dapat diulang).

4. Video demo otomatis
   - `make rekam-demo`: skrip Playwright yang menjalankan alur demo langkah demi langkah dengan jeda yang nyaman ditonton dan merekam video 1920×1080 ke assets/demo.webm. Jika ffmpeg tersedia, konversi juga ke assets/demo.mp4.
   - Alur: daftar periksa (semua tagihan sudah dihitung) → RS prioritas rendah → panel demo, sisipkan KAP_FISIO 3 hari → prioritas naik menjadi tinggi → detail RS: temuan, grafik, alasan prioritas → grid sensor dan verifikasi tanda tangan pada RS bersensor → keputusan "Minta klarifikasi" → audit dengan rantai utuh.
   - Durasi total 75–100 detik.
   - Tampilkan teks keterangan singkat di layar pada setiap langkah (overlay bahasa Indonesia), supaya video tetap bisa dipahami tanpa suara.

5. docs/NASKAH_DEMO.md
   Naskah narasi bahasa Indonesia yang selaras dengan video: tabel waktu (detik), apa yang tampil di layar, dan kalimat narasi. Bahasa awam, tanpa istilah teknis yang tidak dijelaskan. Akhiri dengan kalimat: "Skor adalah prioritas pemeriksaan, bukan penetapan kecurangan. Keputusan selalu di tangan petugas."

6. README.md final (bahasa Indonesia)
   - Satu paragraf penjelasan JKN-Sentinel untuk orang awam.
   - Alur empat langkah dan teknologi yang dipakai beserta statusnya (RAG dan multi-agent: tahap berikutnya).
   - Hasil evaluasi ringkas dari reports/evaluasi.md (angka hidden beserta pembilang/penyebut), dengan tautan ke laporan lengkap dan bagian keterbatasan.
   - Cara menjalankan: prasyarat, make demo, make test, make e2e, make verifikasi-reproduksi.
   - Pernyataan tegas: seluruh data adalah data tiruan; tidak ada data peserta JKN asli.
   - Tautan ke ROADMAP.md, docs/ARSITEKTUR.md, dan arsip prompt docs/prompts/.
   - Tangkapan layar 01 dan 02 ditampilkan di README.

7. Pemeriksaan akhir keamanan dan privasi
   - Pindai seluruh repo untuk: pola menyerupai NIK (16 digit), nomor kartu BPJS (13 digit), kunci API (misalnya "sk-ant-"), kunci privat (PEM), dan berkas .env. Laporkan hasilnya; tidak boleh ada temuan.
   - Pastikan kunci privat sensor tidak tersimpan di berkas mana pun yang di-commit.

SELESAI JIKA
- `make demo` berhasil dari clone baru, `make test` dan `make e2e` lulus.
- assets/ berisi 6 tangkapan layar, 2 grafik evaluasi, dan video.
- Laporkan: daftar berkas di assets/ beserta ukurannya, durasi video, hasil verifikasi reproduksi (identik atau tidak), hasil pemindaian keamanan, dan keputusan atau penyimpangan.
- Setelah melapor, lanjutkan langsung ke dokumentasi KECUALI ada tes gagal, verifikasi reproduksi tidak identik, temuan pemindaian keamanan, atau keputusan yang menyimpang dari prompt ini. Dalam kasus itu, berhenti dan tunggu persetujuan saya.

LANGKAH DOKUMENTASI WAJIB (berurutan)
1. Commit kode dan assets: "feat(fase-7): paket demo". Catat hash-nya.
2. Simpan prompt ini VERBATIM (dari "Baca ROADMAP.md" sampai baris terakhir) ke docs/prompts/FASE-07_paket-demo.md dengan format arsip di ROADMAP.md, termasuk semua pesan lanjutan saya selama fase ini secara verbatim di "Catatan hasil". Perbarui docs/prompts/README.md.
3. ROADMAP.md: status Fase 7 menjadi ✅, status Fase 6 tetap ⬜ dengan catatan "dikerjakan setelah fase 7 jika waktu memungkinkan", tambah baris di Log progres, dan tandai milestone M1 siap.
4. Tambahkan entri di docs/DEVLOG.md.
5. Tambahkan entri versi 0.7.0 di CHANGELOG.md.
6. Catat penyimpangan urutan (fase 7 sebelum fase 6) dan penyimpangan lain di Catatan penyimpangan ROADMAP.md.
7. Commit dokumentasi: "docs(fase-7): arsip prompt, roadmap, devlog, changelog". Buat tag beranotasi "proposal-m1" pada commit ini dengan pesan "Snapshot prototype untuk submit proposal Healthkathon 2026". Push ke origin main beserta tag-nya.
```

## Catatan hasil

### Yang dihasilkan

- **`make demo`.** Build, layanan dengan `DEMO_MODE=true`, data utama dan hidden, sensor, aturan, lalu `make demo-reset`; mencetak alamat dashboard dan 4 langkah demo. Tidak menjalankan evaluasi, tidak menulis ke `reports/`.
  - Diuji dari clone baru di folder sementara (salin `.env.example` → `.env`), dengan nama proyek compose terpisah (`jknuji`) agar volume data aktif tidak tersentuh: **berhasil dalam 5 menit 0 detik** (dengan cache image Docker).
  - Dashboard dalam mode demo; `reports/` di clone tidak berubah; `make e2e` dari clone lulus (`npm install` baru). Stack clone diturunkan beserta volumenya.
- **`make verifikasi-reproduksi`** (`backend/sentinel/reproduksi.py`).
  - Membangkitkan ulang semua data di basis data terpisah `sentinel_verifikasi` (dibuat lalu dihapus), menjalankan sensor, aturan, dan perhitungan evaluasi, lalu membandingkan seluruh isi bagian `utama`, `hidden`, `edge_ai`, dan `proposal` dengan `reports/evaluasi.json`.
  - Hasil akhir pada commit bersih `87ac7b4`: **IDENTIK di keempat bagian**, 169,3 detik. Ditulis ke `reports/verifikasi_reproduksi.json` dengan pernyataan "verifikasi reproduksi dengan kode dan parameter yang sudah dibekukan, bukan penyetelan".
  - `reports/evaluasi.json` (dicek sha256) dan `reports/log_evaluasi_hidden.json` (tetap 1 jalan, 2026-10-03T06:02:34Z) tidak berubah.
- **`make tangkapan-layar`** (`frontend/paket/tangkapan-layar.spec.ts`, demo-reset dulu) menghasilkan:
  - 01_daftar-periksa;
  - 02_detail-rs (1920×1080);
  - 02b_grafik-harian (1920×1080);
  - 02_detail-rs-penuh (1920×2493, dipakai di README);
  - 03_grid-sensor (hasil verifikasi "Semua 144 pesan bertanda tangan sah");
  - 04_demo-sebelum-sesudah (RS Tiruan 012: 3,3 rendah → 18,3 tinggi);
  - 05_keputusan;
  - 06_audit (rantai utuh, waktu WIB);
  - salinan recall_per_skenario.png dan prioritas_hidden.png.
- **`make rekam-demo`** (`frontend/paket/rekam-demo.spec.ts`, demo-reset dulu) menghasilkan `assets/demo.webm`: 1920×1080, VP8, 7,0 MB, **89,6 detik** (alur ±84 detik lalu keterangan penutup ditahan).
  - Keterangan bahasa Indonesia di setiap langkah.
  - Waktu tiap langkah di `assets/demo_waktu.json`.
  - Diperiksa per bingkai.
- **`docs/NASKAH_DEMO.md`**: tabel detik / tampilan / narasi, dengan kalimat penutup yang diminta.
- **README.md final.**
- **Pemindaian keamanan** (138 berkas tracked + untracked, tanpa `node_modules`/`.venv`): **tidak ada temuan**.
  - Tidak ada pola 16 digit atau 13 digit, kunci API, maupun kunci privat PEM.
  - Satu-satunya berkas env adalah `.env.example` tanpa isi rahasia; `.env` diabaikan git.
  - Kunci privat sensor hanya diturunkan di memori (`edge.py`, kunci penyerang di `gangguan.py`); tabel `perangkat` hanya berisi `public_key`.
- **Tes:** `make test` 204 lulus; `make e2e` lulus.

### Masalah yang muncul

- **`make demo` pertama di clone gagal di akhir** karena baris `@echo.` (sintaks cmd untuk baris kosong) tidak dikenal `sh`. Baris itu dihapus dan `make demo` diulang penuh sampai berhasil.
- **ffmpeg tidak ada di PATH.** ffmpeg bawaan Playwright tidak memiliki encoder H.264, sehingga mp4 tidak dibuat. Menurut pengguna mp4 tidak diperlukan; webm dipakai untuk unggahan video.
- **Tangkapan layar 02 tidak muat 1920×1080** bila harus memuat kartu skor sampai grafik. Dipecah menjadi 02, 02b, dan versi penuh (pilihan b).
- **Verifikasi reproduksi pertama tercatat `b1934bb-dirty`** (kode fase 7 belum di-commit). Diulang setelah commit `feat(fase-7)` dengan ROADMAP disimpan sementara (stash), sehingga hash bersih `87ac7b4` dan hasil tetap identik.
- **`make demo` dan uji clone memakai cache image Docker.** Build tanpa cache akan lebih lama.

### Penyimpangan dari prompt atau roadmap

Dicatat juga di `ROADMAP.md`.

1. **Urutan fase:** Fase 7 dikerjakan sebelum Fase 6 (RAG), keputusan sadar agar paket proposal siap lebih dulu.
2. **Pilihan (b) untuk tangkapan layar 02** (disetujui pengguna): 02 dan 02b berukuran 1920×1080; versi panjang 02_detail-rs-penuh.png dipakai di README.
3. **Perbaikan baris `@echo.` di Makefile** (`make demo`).
4. **Keputusan lain:**
   - mp4 tidak dibuat (opsional; webm dipakai);
   - berkas tambahan `assets/demo_waktu.json`;
   - verifikasi reproduksi menghitung ulang angka hidden sesuai permintaan, hanya menulis `reports/verifikasi_reproduksi.json`, dan tidak dicatat sebagai jalan evaluasi hidden di log;
   - skrip Playwright pengemasan di `frontend/paket/` dengan konfigurasi `playwright.paket.config.ts`.

### Prompt lanjutan 1 (verbatim, 2026-10-03)

```text
Untuk tangkapan layar 02, pilih (b):
- 02_detail-rs.png (1920×1080): kartu skor, alasan prioritas, dan daftar temuan.
- 02b_grafik-harian.png (1920×1080): kartu grafik harian sesi vs kapasitas dengan hari temuan ditandai.
- Simpan versi panjang yang sekarang sebagai 02_detail-rs-penuh.png dan pakai versi itu di README.
Perbarui skrip tangkapan layar agar hasil ini dapat diulang, lalu jalankan ulang make tangkapan-layar.

mp4 tidak diperlukan; webm dipakai untuk unggahan video. Hapus rencana konversi mp4 dari dokumentasi, atau tulis sebagai opsional.

Urutan penutupan:
1. Commit kode dan assets: "feat(fase-7): paket demo".
2. Jalankan ulang make verifikasi-reproduksi setelah commit itu, supaya reports/verifikasi_reproduksi.json merujuk ke hash commit yang bersih (tanpa "-dirty"). Pastikan hasilnya tetap IDENTIK dan log jalan hidden tetap tidak berubah.
3. Lanjutkan langkah dokumentasi 2–7 seperti di prompt. Ikutkan verifikasi_reproduksi.json yang baru di commit dokumentasi, catat pesan ini verbatim di arsip prompt, dan catat pilihan (b) serta perbaikan baris @echo. di Makefile sebagai penyimpangan. Buat tag proposal-m1 di commit dokumentasi, lalu push beserta tag-nya.
```

Hasil:
- Skrip tangkapan layar diperbarui dan `make tangkapan-layar` dijalankan ulang: 02_detail-rs.png dan 02b_grafik-harian.png 1920×1080, 02_detail-rs-penuh.png 1920×2493; README memakai versi penuh.
- Konversi mp4 dicatat sebagai opsional; dokumentasi tidak menjanjikan mp4.
- Commit `feat(fase-7): paket demo` = `87ac7b4`.
- `make verifikasi-reproduksi` dijalankan ulang di pohon kerja bersih: komit `87ac7b4`, IDENTIK di keempat bagian. Log jalan hidden dan `evaluasi.json` tidak berubah.
- `reports/verifikasi_reproduksi.json` yang baru ikut di commit dokumentasi, dan tag beranotasi `proposal-m1` dibuat pada commit itu.
