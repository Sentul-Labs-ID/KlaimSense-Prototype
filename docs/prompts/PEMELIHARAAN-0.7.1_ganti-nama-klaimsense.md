# PEMELIHARAAN-0.7.1 — Ganti nama produk menjadi KlaimSense

| Kolom | Isi |
|---|---|
| Versi | v1 |
| Tanggal dijalankan | 2026-10-05 |
| Dijalankan oleh | Rifandi Indrayudha Prawira |
| Alat | Claude Code |
| Commit hasil | a0d157dbd4f944af7f834f3f3da1792b4cb02877 |
| Status | Berhasil |

## Prompt (verbatim)

```text
Baca ROADMAP.md dan CLAUDE.md. Ini adalah pekerjaan PEMELIHARAAN 0.7.1: mengganti nama produk dari JKN-Sentinel menjadi KlaimSense. Repo GitHub sudah diganti nama menjadi Sentul-Labs-ID/KlaimSense-Prototype oleh pemilik repo. Jangan mengubah logika apa pun.

1. Remote git
   Perbarui remote origin ke https://github.com/Sentul-Labs-ID/KlaimSense-Prototype.git dan pastikan git fetch berhasil.

2. Ganti nama di semua bagian yang dilihat pengguna:
   - README.md: judul, deskripsi, perintah, dan tautan. Tambahkan satu kalimat bahwa proyek ini sebelumnya bernama JKN-Sentinel.
   - Frontend: judul situs, header, footer, judul tab browser, teks halaman, dan overlay naskah video.
   - API: judul aplikasi FastAPI dan pesan yang menyebut nama produk.
   - docs/ARSITEKTUR.md, docs/NASKAH_DEMO.md, CLAUDE.md, dan komentar atau docstring yang menyebut nama produk.
   - ROADMAP.md: judul dan deskripsi di bagian atas. Tambahkan catatan "Sebelumnya bernama JKN-Sentinel; diganti 2026-10-05 agar sama dengan nama proposal."

3. JANGAN diubah, karena ini catatan sejarah:
   - Arsip prompt di docs/prompts/ (harus tetap verbatim).
   - Entri lama di DEVLOG.md, CHANGELOG.md, Log progres, dan Catatan penyimpangan di ROADMAP.md.
   - Tag git proposal-m1.
   - reports/evaluasi.json, reports/log_evaluasi_hidden.json, dan reports/verifikasi_reproduksi.json.
   - Nama paket Python `sentinel` dan nama tabel atau kolom basis data. Mengganti ini berisiko merusak kode tanpa manfaat bagi pengguna; catat sebagai keputusan di DEVLOG.

4. Laporan evaluasi
   Jika reports/evaluasi.md menyebut JKN-Sentinel, render ulang HANYA teks laporannya dengan --hanya-laporan dari evaluasi.json yang sama. Dilarang menghitung ulang evaluasi hidden. Pastikan hash SHA-256 evaluasi.json dan log jalan hidden tidak berubah, dan laporkan kedua hash itu.

5. Aset
   Jalankan ulang make tangkapan-layar supaya semua tangkapan layar di assets/ memakai nama baru. Video (make rekam-demo) juga dijalankan ulang jika memakan waktu kurang dari 5 menit; jika lebih, lewati dan catat.

6. Pemeriksaan
   - Cari "JKN-Sentinel" dan "JKN Sentinel" di seluruh repo. Laporkan sisa kemunculannya beserta alasan masing-masing (harus hanya di bagian yang dilindungi pada poin 3, atau catatan "sebelumnya bernama").
   - make test, make e2e, lint, dan build frontend harus lulus. Perbarui tes yang memeriksa teks nama produk.

SELESAI JIKA semua pemeriksaan di poin 6 lulus. Laporkan: daftar berkas yang diubah, sisa kemunculan nama lama beserta alasannya, hash evaluasi.json dan log hidden, serta hasil tes. Setelah melapor, lanjutkan ke dokumentasi KECUALI ada tes gagal atau keputusan yang menyimpang dari prompt ini.

LANGKAH DOKUMENTASI WAJIB (berurutan)
1. Commit: "chore(0.7.1): ganti nama produk menjadi KlaimSense". Catat hash-nya.
2. Simpan prompt ini VERBATIM ke docs/prompts/PEMELIHARAAN-0.7.1_ganti-nama-klaimsense.md dengan format arsip di ROADMAP.md, termasuk pesan lanjutan saya. Perbarui docs/prompts/README.md.
3. ROADMAP.md: tambah baris di Log progres dan catatan penggantian nama di Catatan penyimpangan.
4. Tambah entri di docs/DEVLOG.md.
5. Tambah entri versi 0.7.1 di CHANGELOG.md.
6. Commit dokumentasi: "docs(0.7.1): arsip prompt, roadmap, devlog, changelog", lalu push ke origin main.
```

## Catatan hasil

### Pesan sebelum prompt (verbatim, 2026-10-05)

Sebelum prompt ini, pengguna mengirim satu perintah:

```text
git remote set-url origin https://github.com/Sentul-Labs-ID/KlaimSense-Prototype.git
```

Perintah itu dijalankan. Remote baru sudah berisi `main` dan tag `proposal-m1` yang sama dengan lokal (`3325dd8`); `git fetch` berhasil.

### Yang dihasilkan

- **Nama diganti** di semua bagian yang dilihat pengguna:
  - README (judul, deskripsi, perintah clone, kalimat "sebelumnya bernama JKN-Sentinel");
  - ROADMAP (judul, deskripsi, catatan nama lama);
  - frontend (judul tab dan header di `layout.tsx`; pesan galat koneksi di `lib/api.ts` dan proksi `app/api/[...jalur]/route.ts`);
  - judul aplikasi FastAPI dan docstring paket;
  - deskripsi CLI generator, aturan, dan evaluasi;
  - judul `docs/ARSITEKTUR.md`, `docs/NASKAH_DEMO.md`, `docs/DEVLOG.md`, `CLAUDE.md`;
  - komentar `config/parameter.yaml`, `.env.example`, dan `Makefile`.
- **Nama infrastruktur diganti:** nama proyek Docker Compose (`jkn-sentinel` → `klaimsense`, volume `klaimsense_pgdata` di `make reset-db`) dan nama distribusi Python di `pyproject.toml` (`jkn-sentinel` → `klaimsense`). Nama paket impor `sentinel`, basis data `sentinel`, serta tabel dan kolom tidak diubah.
- **Footer dan overlay video** tidak pernah menyebut nama produk, jadi tidak ada teks yang diubah. Video tetap direkam ulang karena header dashboard di dalamnya memuat nama baru.
- **Laporan evaluasi.** `reports/evaluasi.md` dirender ulang dengan `--hanya-laporan` dari `evaluasi.json` yang sama; hanya judul dan kalimat slide yang berubah. Evaluasi hidden tidak dihitung ulang.
  - Berkas `reports/` lainnya tetap identik per byte: `evaluasi.json`, `log_evaluasi_hidden.json`, `verifikasi_reproduksi.json`, `catatan_pasca_hidden.md`, dan kedua PNG.
  - SHA-256 `evaluasi.json`: `80d697c5d4aaec374e46424473163e46d4b38a8d986e3414f64a8a93f5740678`
  - SHA-256 `log_evaluasi_hidden.json`: `5c52179bfac2f78749ff459b649136151b0f520aecdaa1b6b2de954b52048351` (tetap 1 jalan, 2026-10-03T06:02:34Z)
- **Aset.**
  - `make tangkapan-layar` dijalankan ulang (122 detik). Enam tangkapan layar yang memuat header berubah. `02b_grafik-harian.png` dan `03_grid-sensor.png` identik per byte karena posisi gulirnya tidak memuat header.
  - `make rekam-demo` dijalankan ulang (3 menit 36 detik, di bawah 5 menit). `demo.webm` 88,4 detik (alur 83,7 detik); waktu langkah bergeser ≤ 0,3 detik, sehingga naskah tetap selaras.
- **Pemeriksaan.**
  - `make test` 204 lulus (juga 204 di venv lokal).
  - `make e2e` lulus; lint dan build frontend lulus.
  - Judul tab dan judul OpenAPI: "KlaimSense".
  - `make demo` di bawah nama proyek baru berhasil (6 menit 40 detik, termasuk build image dengan nama baru).
- **Sisa kemunculan "JKN-Sentinel"** (berkas tracked dan untracked):

  | Lokasi | Alasan sisa |
  |---|---|
  | `README.md` | catatan "sebelumnya bernama" |
  | `ROADMAP.md` | catatan "sebelumnya bernama" |
  | `docs/DEVLOG.md` | entri lama Fase 0 (catatan sejarah) |
  | `docs/prompts/FASE-00`, `FASE-04`, `FASE-07` | arsip prompt verbatim |

### Masalah yang muncul

- Docker Desktop belum berjalan saat mulai; dinyalakan dulu.
- Nama proyek compose yang baru membuat volume baru. Stack lama (`jkn-sentinel`) dihentikan tanpa menghapus volumenya, lalu `make demo` membangun ulang data tanpa menjalankan evaluasi.
- Volume lama `jkn-sentinel_pgdata` dan image lama masih tersimpan di mesin lokal; boleh dihapus manual bila tidak diperlukan.
- Venv lokal dipasang ulang dengan nama distribusi baru (`klaimsense.egg-info` menggantikan `jkn_sentinel.egg-info`; keduanya diabaikan git).
- Folder `.kilo/worktrees/` (worktree alat lain, diabaikan lewat `.git/info/exclude`) tidak disentuh dan tidak termasuk pemindaian.

### Penyimpangan dari prompt

Tidak ada. Keputusan yang perlu dicatat:

- **Nama infrastruktur juga diganti.** Nama proyek compose dan nama distribusi Python diganti agar pencarian nama lama hanya menyisakan bagian yang dilindungi.
- **Yang sengaja dipertahankan:** nama paket impor `sentinel`, nama basis data, tabel, dan kolom.
