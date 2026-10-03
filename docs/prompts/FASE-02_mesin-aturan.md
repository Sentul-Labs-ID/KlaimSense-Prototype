# FASE-02 — Mesin aturan (Langkah 1: Hitung)

| Kolom | Isi |
|---|---|
| Versi | v1 |
| Tanggal dijalankan | 2026-10-03 |
| Dijalankan oleh | Rifandi Indrayudha Prawira |
| Alat | Claude Code |
| Commit hasil | 7e1f8f955c5905f411fd817488a6bbd600486324 |
| Status | Berhasil |

## Prompt (verbatim)

```text
Baca ROADMAP.md dan CLAUDE.md. Ini adalah FASE 2: mesin aturan (Langkah 1: Hitung). Jangan membangun sensor, evaluasi, atau dashboard di fase ini.

BATAS AKSES (wajib)
Mesin aturan hanya boleh membaca: rumah_sakit, kapasitas, pasien, harga_acuan, tagihan, riwayat_alat_bantu_dengar, dan config/parameter.yaml. DILARANG membaca sesi_aktual, ground_truth, profil_rs, dan kasus_sah. Pastikan test_batas_akses.py tetap lulus.

ATURAN (semua batas dari parameter.yaml; pengecekan per hari; kasus tepat sama dengan batas TIDAK dianggap melanggar)
- KAP-01 Fisioterapi: jumlah sesi fisioterapi per RS per hari > jumlah_fisioterapis × sesi wajar per terapis.
- KAP-02 Hemodialisa: jumlah sesi HD per RS per hari > jumlah_mesin_hd × shift_hd_per_hari, ATAU ada sesi HD pada hari unit tidak beroperasi. Pakai definisi hari operasional yang sama dengan generator, dan tuliskan definisinya di docs/ARSITEKTUR.md.
- ULG-01 Tagihan identik: kombinasi (rs, pasien, tanggal, layanan, kode_item, jumlah, harga_satuan) muncul lebih dari sekali. Setiap salinan setelah yang pertama menjadi temuan.
- ULG-02 Sesi ganda: pasien yang sama punya lebih dari satu tagihan HD di RS yang sama pada hari yang sama.
- WJR-01 Harga: harga_satuan > harga_acuan × (1 + toleransi_harga).
- WJR-02 Alat bantu dengar: selisih tanggal dengan pemberian sebelumnya untuk pasien dan telinga yang sama (dari riwayat_alat_bantu_dengar dan tagihan ABD sebelumnya) < masa penggantian.
- BAND-01 Perbandingan: rasio utilisasi rata-rata per RS per layanan (fisioterapi, HD) per periode dibanding RS sejenis (kelas dan provinsi sama), dengan robust z-score (median dan MAD) memakai leave-one-out (RS yang dinilai tidak ikut menghitung pembandingnya). Jika pembanding < 3 RS atau MAD = 0, turun ke kelompok kelas saja; jika tetap tidak memadai, lewati dan catat alasannya. BAND-01 adalah sinyal pendukung, bukan bukti utama.

KELUARAN
1. Tabel temuan(id, dataset_id, aturan_id, rs_id, tanggal nullable, periode, layanan, tagihan_ids, nilai_teramati, batas, selisih, penjelasan, versi_aturan).
   Penjelasan dibuat dari TEMPLATE teks bahasa Indonesia, bukan LLM. Contoh:
   - "Fisioterapi 5 Agustus 2026: 75 sesi ditagih, kapasitas 32 (4 terapis × 8 sesi). Selisih 43 sesi."
   - "Alat bantu dengar telinga kiri pasien P-000123 ditagih 2 tahun 1 bulan setelah pemberian sebelumnya; masa penggantian 5 tahun."
2. Tabel skor(dataset_id, rs_id, periode, skor, prioritas, rincian_per_aturan JSON, versi_aturan, hash_parameter).
   - Periode = bulan kalender (YYYY-MM).
   - Rumus: skor = Σ bobot_aturan × keparahan_aturan, dengan keparahan 0–1. Karena total bobot 100, skor otomatis 0–100.
   - Keparahan: untuk KAP, ULG, dan WJR = min(1, jumlah temuan dalam periode ÷ titik_jenuh_aturan). Untuk BAND-01 = min(1, (z − ambang) ÷ ambang) jika z > ambang, selain itu 0. Titik jenuh per aturan masuk ke parameter.yaml dengan komentar ILUSTRATIF.
   - Bobot SEN-01 tetap ada tetapi keparahannya 0 sampai fase 3. Catat bahwa skor maksimum sementara adalah 80.
   - Prioritas: tinggi, sedang, atau rendah, berdasarkan ambang di parameter.yaml. Tetapkan ambang awal HANYA dengan melihat sebaran skor dataset utama, jangan dataset hidden. Tulis alasannya di DEVLOG.
   - hash_parameter = SHA-256 dari isi parameter.yaml, supaya setiap skor bisa dilacak ke parameter yang menghasilkannya.
3. Tulis rumus skor dan definisi tiap aturan di docs/ARSITEKTUR.md dengan bahasa yang bisa dipahami juri non-teknis.

CLI
- `python -m sentinel.rules --dataset utama` dan `--dataset hidden`. Hapus hasil lama untuk dataset yang sama sebelum menulis.
- `make rules` menjalankan keduanya dan mencetak 10 RS dengan skor tertinggi per dataset, beserta aturan yang memicunya. Jangan mencetak apa pun dari tabel evaluasi.

TES (pytest)
- Untuk setiap aturan: kasus melanggar, kasus tidak melanggar, dan kasus tepat di batas (tidak melanggar), memakai data kecil buatan tangan.
- WJR-02 memakai riwayat dan tagihan ABD sebelumnya sebagai pembanding.
- BAND-01: leave-one-out benar, dan fallback saat pembanding kurang atau MAD = 0.
- Skor selalu 0–100. SEN-01 memberi kontribusi 0. Skor identik bila dijalankan dua kali dengan data dan parameter yang sama.
- hash_parameter berubah bila parameter.yaml berubah.
- Satu kali jalan per dataset selesai dalam waktu wajar (targetkan < 30 detik); tambahkan indeks bila perlu.

SELESAI JIKA
- `make rules` dan `make test` lulus.
- Laporkan: sebaran skor dan jumlah RS per prioritas di kedua dataset, jumlah temuan per aturan, contoh 3 penjelasan temuan, ambang prioritas beserta alasannya, dan keputusan atau penyimpangan.
- Setelah melapor, lanjutkan langsung ke langkah dokumentasi KECUALI ada tes yang gagal atau keputusan yang menyimpang dari prompt ini. Dalam dua kasus itu, berhenti dan tunggu persetujuan saya.

LANGKAH DOKUMENTASI WAJIB (berurutan)
1. Commit kode: "feat(fase-2): mesin aturan". Catat hash-nya.
2. Simpan prompt ini VERBATIM (dari "Baca ROADMAP.md" sampai baris terakhir) ke docs/prompts/FASE-02_mesin-aturan.md dengan format arsip di ROADMAP.md, termasuk semua pesan lanjutan saya selama fase ini secara verbatim di "Catatan hasil". Perbarui docs/prompts/README.md.
3. ROADMAP.md: status Fase 2 menjadi ✅, tambah baris di Log progres. Tutup catatan penyimpangan "bobot berjumlah 100" dengan keputusan rumus skor fase ini.
4. Tambahkan entri di docs/DEVLOG.md.
5. Tambahkan entri versi 0.3.0 di CHANGELOG.md.
6. Catat penyimpangan baru di Catatan penyimpangan ROADMAP.md.
7. Commit dokumentasi: "docs(fase-2): arsip prompt, roadmap, devlog, changelog", lalu push ke origin main.
```

## Catatan hasil

### Yang dihasilkan

- **Paket `backend/sentinel/rules/`:**
  - `masukan.py`: satu-satunya pintu data. Hanya membaca `rumah_sakit`, `kapasitas`, `harga_acuan`, `tagihan`, `riwayat_alat_bantu_dengar`.
  - `aturan.py`: KAP-01, KAP-02, ULG-01, ULG-02, WJR-01, WJR-02.
  - `banding.py`: BAND-01, robust z dengan leave-one-out dan fallback.
  - `skor.py`: rumus skor dan prioritas.
  - `teks.py`: template bahasa Indonesia untuk tanggal, rupiah, persen, dan selang "X tahun Y bulan".
  - `mesin.py`: orkestrasi; `VERSI_ATURAN = "1.0.0"`.
  - `simpan.py`: hapus hasil lama dataset yang sama, lalu tulis.
  - `__main__.py`: CLI dan ringkasan 10 RS teratas.
- **Tabel `temuan` dan `skor`** di `backend/sentinel/models/hasil.py`.
- **`config/parameter.yaml`** mendapat bagian `skor`: `titik_jenuh` (KAP/ULG/WJR-01 = 3, WJR-02 = 2, SEN-01 = 3 untuk fase 3) dan `prioritas` (tinggi ≥ 20, sedang ≥ 10), dengan komentar ILUSTRATIF.
- **`sentinel.parameter.hash_parameter()`**: SHA-256 isi file.
- **`make rules`** dan bagian "Langkah 1: Hitung" di `docs/ARSITEKTUR.md`: definisi aturan, definisi hari operasional HD, BAND-01, dan rumus skor dalam bahasa non-teknis.
- **Tes: 122 lulus.**
  - `test_rules.py`: setiap aturan melanggar, tidak melanggar, dan tepat di batas; leave-one-out; fallback; rumus skor; determinisme; hash; kecepatan.
  - `test_rules_db.py`: keempat tabel terlarang di-DROP lalu CLI dijalankan; jalan ulang mengganti hasil; `generate` ulang menghapus hasil basi.
  - Tes validasi bagian `skor`.
- **Hasil `make rules`:**

| | utama | hidden |
|---|---|---|
| Temuan KAP-01 / KAP-02 / ULG-01 / ULG-02 / WJR-01 / WJR-02 / BAND-01 | 16 / 18 / 25 / 12 / 20 / 7 / 16 | 16 / 18 / 36 / 25 / 31 / 7 / 13 |
| Penilaian BAND-01 (pembanding kelas saja / dilewati) | 180 (108 / 0) | 180 (108 / 18) |
| RS-periode skor 0 | 49 dari 90 | 46 dari 90 |
| Skor median / P90 / maks | 0 / 15 / 30 | 0 / 18,5 / 40 |
| RS-periode tinggi / sedang / rendah | 7 / 10 / 73 | 9 / 15 / 66 |
| RS per prioritas (periode tertinggi) | 5 / 3 / 22 | 5 / 7 / 18 |
| Waktu baca + hitung + simpan | ±1,5 detik | ±1,5 detik |

- **Contoh penjelasan:**
  - "Hemodialisa 24 Agustus 2026: 28 sesi ditagih, kapasitas 27 (9 mesin × 3 shift). Selisih 1 sesi."
  - "Alat bantu dengar telinga kanan pasien P-009721 ditagih 4 tahun 9 bulan setelah pemberian sebelumnya; masa penggantian 5 tahun."
  - "Obat kronis OBK-004 (Tablet antihipertensi generik 50 mg) 4 September 2026: harga satuan Rp1.025, harga acuan Rp900, batas toleransi 10% = Rp990. Lebih Rp35 (13,9% di atas harga acuan)."

### Ambang prioritas

Tinggi ≥ 20, sedang ≥ 10. Ditetapkan hanya dari sebaran skor dataset utama (tanpa melihat hidden atau ground truth):
- 49 dari 90 RS-periode berskor 0.
- Skor di bawah 10 adalah temuan terisolasi: 1–2 temuan satu aturan, atau BAND-01 saja.
- Ada celah alami 8,33 → 10 dan 18,33 → 21,67.
- Skor ≥ 10 berarti pelanggaran berulang pada satu aturan berat.
- Skor ≥ 20 butuh setara satu aturan berat yang jenuh ditambah sinyal lain.

### Masalah yang muncul

- **Dua tes awal salah**, keduanya karena kesalahan pada tes, bukan pada kode:
  - Data uji fallback MAD = 0 ternyata juga ber-MAD 0 di tingkat kelas; satu RS pembanding ditambahkan.
  - Toleransi `approx` tidak memperhitungkan keparahan yang disimpan dengan 4 desimal.
- **Foreign key `temuan`/`skor` ke `rumah_sakit`** akan menghalangi `make generate` ulang. Solusi: `generator/simpan.py` ikut menghapus `temuan` dan `skor` dataset yang sama, karena hasil itu memang basi bila data dibangkitkan ulang.
- **Pembanding BAND-01 sangat terbatas di data tiruan.**
  - Dengan 3 RS per kombinasi kelas-provinsi, leave-one-out hanya menyisakan 2 pembanding, sehingga 108 dari 180 penilaian turun ke pembanding kelas.
  - Di hidden, kelas A hanya 3 RS, sehingga 18 penilaian kelas A dilewati.

### Penyimpangan dari prompt atau roadmap

Tidak ada penyimpangan dari prompt. Keputusan interpretasi yang dicatat (juga di `ROADMAP.md` dan `docs/DEVLOG.md`):

1. **ULG-01**: setiap salinan menjadi satu temuan; `tagihan_ids` berisi [tagihan pertama, salinan] agar pencocokan fase 4 tidak bergantung pada urutan ID.
2. **BAND-01**:
   - Utilisasi = rata-rata rasio harian atas hari yang punya tagihan layanan itu (HD hanya pada hari unit buka).
   - Robust z memakai konstanta 1,4826 dan hanya sisi atas.
   - Keparahan diambil yang terbesar dari fisioterapi dan hemodialisa.
   - Temuan BAND-01: `nilai_teramati` = z, `batas` = ambang, `tagihan_ids` kosong.
3. **WJR-02**: masa penggantian dihitung dalam bulan kalender (tanggal yang sama 5 tahun kemudian tidak melanggar). Riwayat dihitung bila tanggalnya sebelum tanggal tagihan; tagihan ABD sebelumnya diurutkan menurut (tanggal, ID).
4. **WJR-01**: perbandingan eksak dengan pecahan agar harga tepat di batas tidak tertandai karena galat float.
5. **KAP-01/KAP-02**: temuan memuat semua `tagihan_ids` hari itu; fisioterapi tidak punya kolom hari operasional, sehingga diperiksa di setiap tanggal bertagihan.
6. **`hash_parameter`**: SHA-256 byte file apa adanya; perubahan komentar pun mengubah hash.
7. **Bobot berjumlah 100** dipertahankan sebagai bagian rumus skor (menutup catatan penyimpangan fase 0).
