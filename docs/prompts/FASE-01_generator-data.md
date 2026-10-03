# FASE-01 — Generator data tiruan

| Kolom | Isi |
|---|---|
| Versi | v1 |
| Tanggal dijalankan | 2026-10-03 |
| Dijalankan oleh | Rifandi Indrayudha Prawira |
| Alat | Claude Code |
| Commit hasil | a9be96538037d1f03ad2a60584d9dbe12093ccf3 |
| Status | Berhasil |

## Prompt (verbatim)

```text
Baca ROADMAP.md dan CLAUDE.md. Ini adalah FASE 1: generator data tiruan. Jangan menulis mesin aturan, sensor, atau dashboard di fase ini.

TUJUAN
Membangkitkan data tiruan yang realistis untuk rumah sakit, kapasitas, pasien, dan tagihan, dengan kecurangan yang disisipkan secara terkontrol dan dicatat sebagai ground truth.

SKEMA (SQLAlchemy, di backend/sentinel/models/, dengan pembuatan tabel otomatis atau migrasi sederhana)
Semua tabel punya kolom dataset_id ("utama" atau "hidden").
- rumah_sakit(id, dataset_id, nama_samaran, kelas [A/B/C/D], provinsi, kab_kota, punya_sensor)
- kapasitas(rs_id, jumlah_fisioterapis, jumlah_mesin_hd, shift_hd_per_hari, hari_operasional_hd)
- pasien(id_pseudonim, dataset_id, umur, jenis_kelamin, provinsi). ID berbentuk "P-000123"; jangan membuat apa pun yang menyerupai NIK atau nomor kartu BPJS.
- harga_acuan(kode_item, nama_item, jenis [obat_kronis/alat_bantu_dengar], harga). Nama item generik dan fiktif, bukan merek dagang.
- tagihan(id, dataset_id, rs_id, pasien_id, tanggal, layanan [fisioterapi/hemodialisa/alat_bantu_dengar/obat_kronis], kode_item, sisi_telinga nullable, jumlah, harga_satuan, total)
- riwayat_alat_bantu_dengar(pasien_id, sisi_telinga, tanggal_diberikan), mencakup 6 tahun ke belakang.
- sesi_aktual(id, dataset_id, rs_id, pasien_id, tanggal, layanan, mesin_id nullable, shift nullable): sesi yang BENAR-BENAR terjadi. Tagihan fiktif tidak punya pasangan di tabel ini. Tabel ini mewakili kenyataan fisik dan hanya boleh dibaca oleh simulator sensor (fase 3) dan evaluasi (fase 4), TIDAK oleh mesin aturan.
- ground_truth(id, dataset_id, skenario, rs_id, tanggal, tagihan_ids, keterangan): hanya boleh dibaca oleh evaluasi (fase 4).

PERILAKU NORMAL (rumah sakit jujur)
- Default: 30 rumah sakit, 90 hari mulai 2026-07-01, seed 42. Semua bisa diatur lewat argumen CLI.
- Sebar rumah sakit sehingga setiap kombinasi kelas dan provinsi berisi minimal 3 rumah sakit (dibutuhkan untuk perbandingan antar-rumah sakit di fase 2).
- Fisioterapi dan hemodialisa per hari mengikuti kapasitas dengan utilisasi realistis 50–95%, dengan pola hari kerja dan akhir pekan.
- Pasien hemodialisa datang 2–3 kali per minggu, maksimal 1 sesi per hari, dengan mesin dan shift tercatat di sesi_aktual.
- Harga obat kronis dan alat bantu dengar di sekitar harga acuan, dengan variasi kecil di bawah toleransi di config/parameter.yaml.
- Kapasitas dan durasi diambil dari config/parameter.yaml, bukan di-hardcode.
- Sertakan kontrol untuk menguji false positive: minimal 2 rumah sakit "jujur tapi sibuk" (utilisasi 95–100%, tidak pernah melewati kapasitas) dan rumah sakit kelas A bervolume tinggi yang sah.

SKENARIO KECURANGAN (setiap kejadian dicatat di ground_truth)
- KAP_FISIO: tagihan fisioterapi fiktif sehingga melebihi kapasitas terapis.
- KAP_HD: tagihan hemodialisa fiktif sehingga melebihi mesin × shift.
- ULANG_IDENTIK: tagihan duplikat persis dari tagihan yang sudah ada.
- ULANG_HARI: pasien sama ditagih 2 sesi hemodialisa di hari yang sama.
- HARGA_LEBIH: harga satuan obat kronis atau alat bantu dengar di atas harga acuan.
- ABD_DINI: alat bantu dengar ditagih untuk telinga yang sama sebelum masa penggantian.
- SENSOR_PALSU: hanya di rumah sakit punya_sensor. Sebagian sesi hemodialisa ditagih tanpa sesi_aktual, dan jumlah totalnya TIDAK melebihi kapasitas (kasus yang lolos aturan kapasitas dan hanya bisa ditangkap sensor).
Sebar skenario ke sekitar 8 rumah sakit; satu rumah sakit boleh punya lebih dari satu skenario. Tetapkan 10 rumah sakit punya_sensor = true, termasuk minimal 4 rumah sakit jujur sebagai kontrol.

MENCEGAH VALIDASI SIRKULAR
- Besar penyisipan diacak per kejadian: KAP sebesar 1–60% di atas kapasitas (sebagian sangat halus, hanya lewat 1–2 sesi), HARGA_LEBIH sebesar 15–200%.
- Hari kejadian diacak dan tidak berpola tetap.
- Opsi --hidden membangkitkan dataset_id "hidden" dengan seed berbeda (default 2026) dan distribusi penyisipan yang sedikit berbeda (rentang besaran dan jumlah rumah sakit terdampak). Dataset hidden hanya untuk evaluasi akhir.

CLI
- `python -m sentinel.generator --dataset utama --seed 42 --days 90 --rs 30` dan `--hidden`.
- `make generate` membangkitkan dataset utama dan hidden sekaligus, menghapus data lama dataset yang sama terlebih dulu.
- Cetak ringkasan: jumlah rumah sakit, pasien, tagihan per layanan, sesi_aktual, dan jumlah kejadian per skenario, untuk masing-masing dataset.

TES (pytest)
- Seed sama menghasilkan data identik; seed berbeda menghasilkan data berbeda.
- Rumah sakit tanpa skenario KAP tidak pernah melebihi kapasitas pada hari mana pun.
- Setiap tagihan hemodialisa non-fiktif punya pasangan di sesi_aktual; setiap tagihan fiktif tidak punya.
- Setiap ground_truth merujuk tagihan yang ada; setiap skenario muncul minimal sekali di kedua dataset.
- Setiap kombinasi kelas-provinsi berisi minimal 3 rumah sakit.
- Tidak ada ID yang menyerupai NIK (16 digit angka).
- Data utama dan hidden tidak saling tercampur.

SELESAI JIKA
- `make generate` berhasil dan ringkasan tercetak.
- `make test` lulus.
- Berhenti dan laporkan kepada saya: ringkasan data kedua dataset, hasil tes, dan daftar keputusan atau penyimpangan dari roadmap. Jangan commit sebelum saya setuju.

LANGKAH DOKUMENTASI WAJIB (setelah saya setujui, lakukan berurutan)
1. Commit kode: "feat(fase-1): generator data tiruan". Catat hash-nya.
2. Simpan prompt ini VERBATIM (dari "Baca ROADMAP.md" sampai baris terakhir) ke docs/prompts/FASE-01_generator-data.md dengan format arsip di ROADMAP.md. Catat juga semua pesan lanjutan saya selama fase ini secara verbatim di "Catatan hasil". Perbarui docs/prompts/README.md.
3. ROADMAP.md: status Fase 1 menjadi ✅, tambah baris di Log progres.
4. Tambahkan entri di docs/DEVLOG.md (sertakan ringkasan data dan alasan setiap dependensi baru).
5. Tambahkan entri versi 0.2.0 di CHANGELOG.md.
6. Catat penyimpangan di bagian Catatan penyimpangan ROADMAP.md.
7. Commit dokumentasi: "docs(fase-1): arsip prompt, roadmap, devlog, changelog", lalu push ke origin main.
```

## Catatan hasil

### Yang dihasilkan

- **Skema** `backend/sentinel/models/`, dikelompokkan menurut hak baca:
  - `master.py`: `rumah_sakit`, `kapasitas`, `pasien`, `harga_acuan`.
  - `transaksi.py`: `tagihan`, `riwayat_alat_bantu_dengar`.
  - `kenyataan.py`: `sesi_aktual` (hanya sensor dan evaluasi).
  - `evaluasi.py`: `ground_truth`, `profil_rs`, `kasus_sah` (hanya evaluasi).
  - Semua tabel punya `dataset_id`. Tabel dibuat otomatis (`create_all`). Kolom foreign key diberi indeks.
- **Generator** `backend/sentinel/generator/`:
  - `bangkit.py`: inti, satu `random.Random(seed)`.
  - `profil.py`: distribusi simulasi utama dan hidden.
  - `katalog.py`: wilayah, item fiktif, tarif paket fiktif.
  - `simpan.py`: hapus dataset yang sama, lalu tulis dalam satu transaksi.
  - `ringkasan.py`: ringkasan dan sidik SHA-256.
  - `__main__.py`: CLI dengan `--dataset`, `--hidden`, `--seed`, `--days`, `--rs`, `--mulai`, `--dry-run`.
- **`make generate`** membangkitkan dataset utama (seed 42) dan hidden (seed 2026) ke PostgreSQL.
- **Tes**: 70 lulus.
  - `test_generator.py`
  - `test_simpan.py` (SQLite di memori)
  - `test_batas_akses.py`: `sentinel/rules/` dilarang menyentuh `sesi_aktual` dan tabel evaluasi; `sentinel/api/` dilarang menyentuh tabel evaluasi.
- **Ringkasan data akhir:**

| | utama (seed 42) | hidden (seed 2026) |
|---|---|---|
| Rumah sakit (punya sensor) | 30 (10) | 30 (10) |
| Profil jujur / sibuk / volume tinggi / disisipi | 19 / 2 / 1 / 8 | 17 / 2 / 1 / 10 |
| Pasien | 9.721 | 9.961 |
| Tagihan (fisio / HD / ABD / obat) | 121.398 (51.495 / 41.863 / 192 / 27.848) | 123.655 (50.867 / 43.895 / 192 / 28.701) |
| Sesi aktual (fisio / HD) | 93.065 (51.339 / 41.726) | 94.227 (50.516 / 43.711) |
| Riwayat ABD | 706 | 704 |
| KAP_FISIO / KAP_HD | 13 / 14 kejadian | 14 / 14 kejadian |
| ULANG_IDENTIK / ULANG_HARI | 8 / 9 kejadian | 7 / 17 kejadian |
| HARGA_LEBIH / ABD_DINI / SENSOR_PALSU | 7 / 7 / 14 kejadian | 13 / 7 / 14 kejadian |
| Kasus sah HD_SHIFT_TAMBAHAN | 4 hari, 21 tagihan, 4 RS | 4 hari, 46 tagihan, 3 RS |
| Kasus sah FISIO_LEMBUR | 3 hari, 23 tagihan, 3 RS | 2 hari, 8 tagihan, 2 RS |
| Kasus sah HARGA_ACUAN_LAMA | 7 tagihan, 7 RS | 9 tagihan, 5 RS |
| Sidik data | `b3e5eb6f7e5ed80e…` | `249050480b8442dc…` |

### Masalah yang muncul

- **Utilisasi di atas 95%.** Pada versi awal, rumah sakit normal kadang mencapai 100% per hari: pembulatan ke atas pada kapasitas kecil (8 sesi), dan pola jadwal hemodialisa yang memenuhi satu hari kerja. Solusi: pembulatan ke bawah untuk fisioterapi dan batas isian 95% per hari kerja untuk hemodialisa (kontrol sibuk boleh 100%).
- **Heredoc gagal.** Skrip penambal berukuran besar gagal dijalankan lewat heredoc bash. Solusi: skrip ditulis ke berkas sementara lalu dijalankan.
- **`make generate` kedua lambat.** Menyimpan ulang memakan ±3 menit per dataset, karena menghapus baris `pasien` dan `rumah_sakit` memicu pemindaian penuh `tagihan` dan `sesi_aktual` (kolom foreign key tanpa indeks). Solusi: indeks pada `rs_id` dan `pasien_id` di `tagihan` dan `sesi_aktual`, serta `rs_id` di `ground_truth` dan `kasus_sah`. Setelah `make reset-db`, penyimpanan ulang kembali ±10 detik per dataset.
- **Reproduksibilitas terverifikasi.** Sidik data sama antara Python 3.13 lokal dan Python 3.12 di container, juga antar proses dengan `PYTHONHASHSEED` berbeda.

### Penyimpangan dari prompt atau roadmap

Dicatat juga di `ROADMAP.md` bagian Catatan penyimpangan. Poin 1–6 dan 8–11 disetujui pengguna; poin 7 diganti dengan kasus sah (prompt lanjutan 1).

1. Tabel tambahan `profil_rs` (label kontrol untuk false positive), hanya untuk evaluasi.
2. Distribusi simulasi ada di `sentinel/generator/profil.py`; `parameter.yaml` tetap hanya berisi batas aturan, dan batas itu dibaca generator.
3. Definisi skenario dipertegas:
   - ULANG_IDENTIK hanya untuk fisioterapi dan obat kronis.
   - ULANG_HARI adalah tagihan HD kedua yang identik di hari yang sama.
   - HARGA_LEBIH mengubah tagihan yang ada, jadi bukan tagihan fiktif.
   - Satu baris ground truth = (skenario, RS, tanggal).
   - Hari kejadian tidak bertumpuk per kelompok layanan.
   - Skenario non-KAP tidak pernah melewati kapasitas.
4. Skema ID:
   - Hidden memakai offset (`RS-501…`, `P-500001…`, ID baris mulai 50.000.001).
   - ID tagihan diberikan setelah penyisipan, diacak di dalam (RS, tanggal).
5. Fisioterapi dan hemodialisa memakai tarif paket fiktif per kelas; `kode_item` kosong.
6. Interpretasi dan perilaku hemodialisa:
   - `hari_operasional_hd` = hari buka per minggu (6 atau 7).
   - Pasien HD punya slot tetap (mesin, shift): 70% datang 2x per minggu, absen 3%, ada pergantian pasien.
   - Ada pasien HD terdaftar yang sedang tidak aktif, dan juga ada di RS jujur.
7. **Diubah:** margin aman tetap berlaku untuk data non-sah (harga normal ≤60% toleransi; ABD normal ≥ masa penggantian + 60 hari; ABD_DINI ≤ masa penggantian − 60 hari). Ini akan ditulis sebagai keterbatasan di laporan evaluasi fase 4. Sebagai penyeimbang, ditambahkan tabel `kasus_sah` dengan kasus sah di area batas.
8. Dengan 30 RS hanya 3 provinsi yang terpakai (9 kombinasi kelas-provinsi); kelas A hanya di Jawa Barat.
9. Validasi argumen: minimal 20 RS dan 28 hari.
10. Tidak ada dependensi baru.
11. Perubahan berkas lain: `CLAUDE.md` (batas akses tabel, `make generate`), `docs/ARSITEKTUR.md` (tabel batas akses), status Fase 1 sempat 🟡 di ROADMAP.
12. Keputusan pelaksanaan kasus sah (sesuai prompt lanjutan 1):
    - Rumah sakit `jujur_volume_tinggi` tidak dipakai untuk kasus sah, mengikuti pesan ("jujur dan jujur-tapi-sibuk").
    - HD_SHIFT_TAMBAHAN memakai nomor shift `shift_hd_per_hari + 1` (shift darurat), paling banyak satu sesi per mesin, dengan pasien terdaftar yang tidak terjadwal hari itu.
    - FISIO_LEMBUR paling banyak 2 sesi lembur per terapis.
    - HARGA_ACUAN_LAMA berada di toleransi + 0,5 sampai 4,5 poin persen, dibulatkan ke atas, sehingga tetap ≤ toleransi + 5 poin persen.
    - Satu baris `kasus_sah` = (jenis, RS, tanggal).
13. Indeks pada kolom foreign key (perbaikan performa, lihat Masalah).

### Prompt lanjutan 1 (verbatim, 2026-10-03)

```text
Keputusan 1–6 dan 8–11 disetujui. Untuk poin 7, saya tidak ingin data terlalu bersih di sekitar batas, karena evaluasi fase 4 akan menghasilkan false positive 0% yang tidak realistis. Tambahkan KASUS SAH DI AREA BATAS sebelum commit:

1. Tabel baru kasus_sah(id, dataset_id, jenis, rs_id, tanggal, tagihan_ids, keterangan). Aksesnya sama dengan ground_truth dan profil_rs: hanya boleh dibaca evaluasi, tidak boleh oleh mesin aturan, dan nanti tidak boleh diekspos lewat API dashboard. Perbarui test_batas_akses.py dan tabel batas akses di CLAUDE.md serta docs/ARSITEKTUR.md.

2. Jenis kasus sah, disebar di rumah sakit jujur dan jujur-tapi-sibuk (bukan di rumah sakit yang disisipi kecurangan), pada kedua dataset:
   - HD_SHIFT_TAMBAHAN: 2–4 hari per dataset, sesi hemodialisa melewati kapasitas 1–2 sesi karena shift tambahan darurat. Sesi ini benar-benar terjadi dan tercatat di sesi_aktual.
   - FISIO_LEMBUR: 2–4 hari per dataset, fisioterapi melewati kapasitas 1–3 sesi karena terapis lembur. Juga benar-benar terjadi di sesi_aktual.
   - HARGA_ACUAN_LAMA: 5–10 tagihan per dataset dengan harga sedikit di atas toleransi (maksimal toleransi + 5 poin persen) karena harga acuan belum diperbarui.
   Besaran dan hari diacak dengan seed.

3. Kasus sah ini memang diharapkan tertandai oleh mesin aturan. Di fase 4, mereka dihitung sebagai tuduhan keliru, dan dilaporkan terpisah sebagai "kasus sah yang perlu klarifikasi".

4. Perbarui tes: kasus sah hanya muncul di rumah sakit jujur/sibuk, tidak bertumpuk dengan hari kejadian kecurangan, dan HD_SHIFT_TAMBAHAN/FISIO_LEMBUR punya pasangan di sesi_aktual. Sesuaikan juga tes lama yang mengasumsikan rumah sakit jujur tidak pernah melewati kapasitas: sekarang yang berlaku adalah "rumah sakit jujur hanya melewati kapasitas pada hari kasus sah".

5. Catat di DEVLOG bahwa kasus sah ini dibuat untuk evaluasi yang jujur dan untuk skenario demo human-in-the-loop. Catat poin 7 (margin aman pada kasus non-sah) sebagai keterbatasan yang akan ditulis di laporan evaluasi fase 4.

Jalankan ulang make generate dan make test, tunjukkan ringkasan kasus sah per dataset, lalu lanjutkan 7 langkah dokumentasi fase 1 tanpa perlu menunggu persetujuan saya lagi, kecuali ada tes yang gagal atau keputusan baru yang menyimpang dari pesan ini.
```

Hasil:
- Tabel `kasus_sah` dan ketiga jenis kasus sah ditambahkan. Kasus sah dibangkitkan setelah skenario kecurangan, sehingga angka skenario tidak berubah.
- Tes kapasitas lama diganti dengan "RS jujur hanya melewati kapasitas pada hari kasus sah" dan "tagihan melewati kapasitas hanya pada hari KAP atau kasus sah". Ada 6 tes baru untuk kasus sah.
- `test_batas_akses.py` diperluas ke `sentinel/api/`.
- `make generate` dan `make test` (70 lulus) berhasil. Ringkasan kasus sah ada di tabel di atas.
