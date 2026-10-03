# FASE-04 — Evaluasi akurasi

| Kolom | Isi |
|---|---|
| Versi | v1 |
| Tanggal dijalankan | 2026-10-03 |
| Dijalankan oleh | Rifandi Indrayudha Prawira |
| Alat | Claude Code |
| Commit hasil | ce4f9eb083787b6bae826af796449cab22fc22bd |
| Status | Berhasil |

## Prompt (verbatim)

```text
Baca ROADMAP.md dan CLAUDE.md. Ini adalah FASE 4: evaluasi akurasi. Jangan membangun dashboard di fase ini.

BATAS AKSES
Hanya modul sentinel/evaluation/ yang boleh membaca ground_truth, profil_rs, kasus_sah, dan sesi_aktual. Modul ini hanya MEMBACA; dilarang mengubah tabel aturan, skor, atau sensor. Batas akses untuk rules dan api tetap berlaku dan tesnya harus tetap lulus.

ATURAN KEJUJURAN EVALUASI (wajib)
- Dataset utama boleh dipakai untuk mengembangkan dan memeriksa kode evaluasi.
- Dataset hidden dijalankan SEKALI setelah kode evaluasi selesai dan dites pada utama. Catat waktu jalannya di laporan sebagai "perbandingan pertama keluaran hidden terhadap label".
- Dilarang mengubah parameter, bobot, ambang, atau aturan berdasarkan hasil hidden. Jika hasil hidden buruk, laporkan apa adanya.
- Jika saat evaluasi ditemukan BUG di mesin aturan atau sensor (implementasi tidak sesuai definisi di ARSITEKTUR.md), JANGAN memperbaikinya diam-diam. Berhenti dan laporkan kepada saya. Perbaikan bug harus disetujui, dicatat, dan diungkapkan di laporan.

PEMETAAN SKENARIO KE ATURAN
KAP_FISIO → KAP-01; KAP_HD → KAP-02; ULANG_IDENTIK → ULG-01; ULANG_HARI → ULG-02; HARGA_LEBIH → WJR-01; ABD_DINI → WJR-02; SENSOR_PALSU → SEN-01 kategori selisih; TAMPER_SIG dan TAMPER_GAP → SEN-01 kategori integritas. BAND-01 tidak dipetakan ke skenario mana pun dan dilaporkan terpisah sebagai sinyal pendukung. Tes harus memastikan setiap skenario di ground_truth punya pemetaan.

METRIK
1. Deteksi per skenario (recall). Satu kejadian ground_truth dianggap tertangkap jika ada temuan dari aturan pasangannya pada RS dan tanggal yang sama (untuk aturan per tagihan: temuan yang memuat tagihan kejadian itu). Laporkan juga "tertangkap oleh aturan apa pun" sebagai informasi tambahan.
2. Presisi per aturan. Setiap temuan diklasifikasikan menjadi tiga:
   - benar: cocok dengan kejadian ground_truth;
   - kasus sah: cocok dengan kasus_sah (diharapkan tertandai; artinya perlu klarifikasi, bukan kecurangan);
   - keliru: tidak cocok dengan keduanya.
3. Prioritas, di level RS-periode (keputusan yang benar-benar dilihat petugas). RS-periode disebut "bermasalah" jika memuat minimal satu kejadian kecurangan (tanpa TAMPER, yang dilaporkan terpisah).
   - Presisi dan recall untuk prioritas tinggi, serta untuk tinggi+sedang.
   - Presisi top-5 dan top-10.
   - Sebaran prioritas untuk RS-periode yang hanya berisi kasus sah, dan untuk RS jujur, jujur-tapi-sibuk, dan volume tinggi.
   - Alasan prioritas (ambang skor atau lantai bukti fisik) untuk setiap RS-periode tinggi.
4. Integritas sensor: deteksi TAMPER_SIG dan TAMPER_GAP, serta jumlah anomali tanpa kejadian.
5. Akurasi Edge AI dari fase 3 dikutip di laporan (jangan dihitung ulang dengan cara berbeda).
6. Untuk setiap proporsi, tampilkan pembilang/penyebut (misalnya 13/14) dan interval kepercayaan 95% Wilson. Jangan pernah menampilkan persentase tanpa jumlahnya.

ANGKA UNTUK PROPOSAL (bagian khusus di laporan, dari dataset HIDDEN)
Tulis dengan definisi bahasa awam tepat di bawah angkanya:
- "Kecurangan yang tertangkap": recall gabungan semua kejadian kecurangan (tanpa TAMPER), level kejadian.
- "Tuduhan yang keliru": proporsi RS-periode prioritas tinggi+sedang yang tidak memuat kecurangan dan bukan sekadar kasus sah.
- "Kasus sah yang perlu klarifikasi": proporsi RS-periode prioritas tinggi+sedang yang hanya memuat kasus sah.
- "Rumah sakit jujur yang ikut ditandai": proporsi RS-periode jujur (termasuk sibuk dan volume tinggi) yang mendapat prioritas tinggi atau sedang.
- Akurasi Edge AI.
Tambahkan satu kalimat siap tempel yang merangkum angka-angka ini untuk slide.

KELUARAN
- reports/evaluasi.md (bahasa Indonesia, tabel siap tempel): ringkasan, angka untuk proposal, rincian utama dan hidden berdampingan, keterbatasan.
- reports/evaluasi.json: semua angka, termasuk pembilang, penyebut, dan interval.
- reports/recall_per_skenario.png: grafik batang recall per skenario dengan interval Wilson, hidden dan utama berdampingan, label bahasa Indonesia, ukuran pas untuk slide.
- reports/prioritas_hidden.png: matriks prioritas (tinggi/sedang/rendah) vs kondisi RS-periode (bermasalah/hanya kasus sah/bersih) pada hidden.

BAGIAN KETERBATASAN (wajib, jujur)
- Data tiruan; parameter dan nilai ampere ilustratif; belum diuji pada data asli.
- Margin aman pada data non-sah dari fase 1, sehingga ketepatan di titik batas tidak teruji (kecuali kasus sah).
- Jumlah kejadian per skenario kecil, sehingga interval kepercayaan lebar.
- Keterbatasan pembanding BAND-01 (catatan fase 2).
- Pengungkapan bahwa label hidden pernah dilihat sekali di fase 1 saat validasi generator, tanpa parameter yang berasal darinya.
- Pemeriksaan kalibrasi sensor fase 3 memakai label dataset utama.
- Aturan deterministik dengan ambang tegas diharapkan menangkap kasus yang jelas melewati batas; angka tinggi pada aturan seperti WJR-01 mencerminkan desain aturan, bukan kecerdasan model.

CLI
`make eval` menjalankan evaluasi utama lalu hidden dan membuat semua keluaran. Tambahkan dependensi grafik seperlunya (misalnya matplotlib) dan catat alasannya.

TES (pytest)
- Fungsi metrik pada data kecil buatan tangan (recall, presisi tiga kelas, metrik prioritas, top-k).
- Interval Wilson dibandingkan dengan nilai acuan yang diketahui.
- Setiap skenario punya pemetaan aturan.
- Modul evaluasi tidak menulis ke tabel mana pun (jumlah baris sebelum dan sesudah sama).

SELESAI JIKA
- `make eval` dan `make test` lulus.
- Laporkan isi bagian "Angka untuk proposal", tabel recall per skenario (utama dan hidden), metrik prioritas hidden, dan keputusan atau penyimpangan.
- Setelah melapor, lanjutkan langsung ke dokumentasi KECUALI ada tes gagal, keputusan yang menyimpang dari prompt ini, atau temuan bug. Dalam kasus itu, berhenti dan tunggu persetujuan saya.

LANGKAH DOKUMENTASI WAJIB (berurutan)
1. Commit kode dan keluaran reports/: "feat(fase-4): evaluasi akurasi". Catat hash-nya.
2. Simpan prompt ini VERBATIM (dari "Baca ROADMAP.md" sampai baris terakhir) ke docs/prompts/FASE-04_evaluasi.md dengan format arsip di ROADMAP.md, termasuk semua pesan lanjutan saya selama fase ini secara verbatim di "Catatan hasil". Perbarui docs/prompts/README.md.
3. ROADMAP.md: status Fase 4 menjadi ✅, tambah baris di Log progres.
4. Tambahkan entri di docs/DEVLOG.md, termasuk waktu jalan pertama evaluasi hidden dan angka utamanya.
5. Tambahkan entri versi 0.5.0 di CHANGELOG.md.
6. Catat penyimpangan baru di Catatan penyimpangan ROADMAP.md.
7. Commit dokumentasi: "docs(fase-4): arsip prompt, roadmap, devlog, changelog", lalu push ke origin main.
```

## Catatan hasil

### Yang dihasilkan

- **Modul `backend/sentinel/evaluation/`:**
  - `data.py`: hanya membaca; transaksi PostgreSQL READ ONLY dan selalu di-rollback.
  - `metrik.py`: Wilson, recall, presisi tiga kelas, kondisi RS-periode, metrik prioritas, top-k, integritas sensor, BAND-01.
  - `evaluasi.py`: menyusun metrik dan mengutip akurasi edge dari metadata model fase 3.
  - `laporan.py`: Markdown.
  - `grafik.py`: PNG; palet referensi tervalidasi, hidden biru dan utama oranye.
  - `__main__.py`: CLI, `--hanya-laporan`, log jalan hidden.
- **`make eval`** menulis `reports/evaluasi.md`, `evaluasi.json`, `recall_per_skenario.png`, `prioritas_hidden.png`, dan `log_evaluasi_hidden.json`.
- **`reports/catatan_pasca_hidden.md`** ditulis manual dan dimuat ke laporan sebagai bagian "Analisis pasca-jalan hidden".
- **Tes: 189 lulus.**
  - Wilson terhadap nilai acuan (13/14 → 68,5–98,7%, 0/10, 10/10, 5/10, 1/1).
  - Pemetaan skenario.
  - Recall, presisi tiga kelas, kondisi, metrik prioritas, top-k, integritas sensor pada data buatan tangan.
  - Evaluasi tidak mengubah jumlah baris satu tabel pun.
  - Pemeriksaan statis: kode evaluasi tanpa operasi tulis.
  - Log hidden menyimpan jalan pertama.
  - Tidak ada persentase tanpa jumlah.
  - Kalimat slide konsisten dengan angka.
- **Proses pengembangan.** Kode evaluasi dikembangkan dan diperiksa hanya pada dataset utama (keluaran sementara di scratchpad). Uji tampilan grafik dua seri memakai salinan data utama sebagai seri "hidden" palsu.
- **Perbandingan pertama keluaran hidden terhadap label: 2026-10-03T06:02:34+00:00** (UTC, container; 13:02 WIB). Jumlah jalan evaluasi hidden: 1. Perubahan laporan sesudahnya hanya dirender ulang dari `evaluasi.json` (`--hanya-laporan`); log hidden terbukti tidak berubah.
- **Angka untuk proposal (hidden):**

| Angka | Nilai |
|---|---|
| Kecurangan yang tertangkap | 83/86 (96,5%; IK95% 90,2–98,8%) |
| Periode bermasalah masuk daftar periksa (tinggi/sedang) | 23/28 (82,1%; IK95% 64,4–92,1%) |
| Periode bermasalah terdeteksi tetapi berprioritas rendah | 5/28 (17,9%; IK95% 7,9–35,6%) |
| Tuduhan yang keliru | 0/26 (0,0%; IK95% 0,0–12,9%); definisi harfiah 1/26 |
| Kasus sah yang perlu klarifikasi | 2/26 (7,7%; IK95% 2,1–24,1%) |
| Rumah sakit jujur yang ikut ditandai | 3/60 (5,0%; IK95% 1,7–13,7%) |
| Akurasi Edge AI (dikutip fase 3) | 16.892/17.280 (97,8%; IK95% 97,5–98,0%) |

- **Recall per skenario (utama / hidden):**
  - KAP_FISIO 13/13 / 14/14; KAP_HD 14/14 / 14/14.
  - ULANG_IDENTIK 8/8 / 7/7; ULANG_HARI 9/9 / 17/17.
  - HARGA_LEBIH 7/7 / 13/13; ABD_DINI 7/7 / 7/7.
  - SENSOR_PALSU 12/14 / 11/14.
  - TAMPER_SIG 1/1 / 1/1; TAMPER_GAP 1/1 / 1/1.
  - Gabungan 70/72 / 83/86.
- **Prioritas hidden:**
  - Presisi tinggi 12/12, recall tinggi 12/28.
  - Presisi tinggi+sedang 23/26, recall tinggi+sedang 23/28.
  - Top-5 5/5, top-10 10/10.

### Masalah yang muncul

- **Label grafik bertumpuk** dan legenda menutupi batang; diperbaiki sebelum jalan hidden.
- **Pemeriksaan statis "tanpa operasi tulis"** salah tangkap `set.update(` Python; polanya dipersempit ke konstruktor tulis SQLAlchemy dan SQL mentah.
- **Patch berkas lewat heredoc bash** beberapa kali gagal karena pelolosan karakter; diganti skrip berkas di scratchpad.
- **Tidak ada bug mesin aturan atau sensor yang ditemukan.**
  - Dua SENSOR_PALSU utama yang lolos dan tiga di hidden semuanya di bawah toleransi 10% atau tertutup kecenderungan edge mencatat sedikit lebih banyak.
  - Satu temuan SEN-01 keliru di hidden (RS-502) disebabkan derau klasifikasi pada RS kecil, sesuai definisi aturan.
  - Pemeriksaan hidden dilakukan setelah jalan pertama, hanya membaca (lihat "Analisis pasca-jalan hidden" di laporan).

### Penyimpangan dari prompt atau roadmap

Dicatat juga di `ROADMAP.md`.

1. **Kondisi keempat "hanya gangguan sensor"** (disetujui pengguna). Prompt menetapkan tiga kondisi RS-periode (bermasalah / hanya kasus sah / bersih). RS-periode yang hanya berisi TAMPER dipisahkan menjadi kondisi keempat, agar sensor yang dicabut atau pesannya dipalsukan tidak dihitung sebagai tuduhan keliru. Matriks prioritas (PNG) menjadi 4 kolom. Definisi harfiah tetap dihitung di jalan yang sama dan dicantumkan sebagai catatan kaki (tuduhan keliru hidden 1/26).
2. **Keputusan interpretasi:**
   - Temuan "benar" bila memuat tagihan kecurangan mana pun, atau integritas pada RS-tanggal gangguan sensor.
   - Urutan top-k = urutan petugas (prioritas, lalu skor).
   - Pembilang/penyebut akurasi edge diambil dari confusion matrix fase 3 (cara hitung sama).
3. **Infrastruktur dan dependensi:**
   - `matplotlib` untuk grafik.
   - `./reports` di-mount ke container.
   - Log jalan hidden permanen.
   - Catatan pasca-hidden ditulis manual di `reports/catatan_pasca_hidden.md`.

### Prompt lanjutan 1 (verbatim, 2026-10-03)

```text
Kondisi keempat "hanya gangguan sensor" disetujui. Definisi harfiah tetap dicantumkan sebagai catatan kaki.

Sebelum dokumentasi, perbarui HANYA laporan (render ulang dari evaluasi.json dengan --hanya-laporan, tanpa menghitung ulang hidden dan tanpa mengubah parameter apa pun):

1. Di bagian "Angka untuk proposal", tambahkan dua baris dengan definisi bahasa awam:
   - "Periode bermasalah yang masuk daftar periksa petugas (prioritas tinggi atau sedang)": 23/28 dengan IK95% Wilson.
   - "Periode bermasalah yang terdeteksi tetapi berprioritas rendah": 5/28 dengan IK95% Wilson.
   Jelaskan dalam satu kalimat perbedaan antara "kejadian terdeteksi" (ada temuan) dan "masuk daftar periksa" (prioritas tinggi atau sedang).

2. Ganti kalimat siap tempel menjadi versi yang konsisten dan tidak melebih-lebihkan:
   "Pada data uji tersembunyi (data tiruan), JKN-Sentinel mendeteksi 83 dari 86 kejadian kecurangan (96,5%) dan memasukkan 23 dari 28 periode rumah sakit bermasalah ke daftar periksa petugas (82%). Dari 26 periode yang diprioritaskan, tidak ada tuduhan keliru; 2 merupakan kasus sah yang perlu klarifikasi dan 1 merupakan gangguan sensor. Klasifikasi Edge AI pada sensor akurat 97,8%."

3. Tambahkan bagian "Analisis pasca-jalan hidden" yang menjelaskan bahwa pemeriksaan temuan keliru SEN-01 di RS-502 dan tiga SENSOR_PALSU yang lolos dilakukan SETELAH jalan pertama, hanya dengan membaca, tanpa perubahan apa pun.

4. Di bagian keterbatasan, tambahkan:
   - recall prioritas tinggi hanya 12/28, karena ambang dan lantai prioritas ditetapkan tanpa kalibrasi. Kalibrasi ambang bersama BPJS adalah rencana tahap hackathon, dan harus diuji dengan dataset hidden baru (seed baru), bukan dataset hidden ini;
   - pemalsuan sensor di bawah toleransi 10% sengaja tidak ditandai untuk mencegah derau sensor menjadi tuduhan; ini pertukaran yang disadari.

Setelah itu lanjutkan 7 langkah dokumentasi fase 4. Catat pesan ini verbatim di arsip prompt, dan catat kondisi keempat sebagai penyimpangan.
```

Hasil:
- **Renderer laporan diperbarui:**
  - dua baris baru di "Angka untuk proposal" beserta kalimat pembeda "terdeteksi" vs "masuk daftar periksa";
  - kalimat slide disusun dari angka dan tes memastikan hasilnya sama persis dengan kalimat di atas;
  - definisi harfiah sebagai catatan kaki;
  - bagian "Analisis pasca-jalan hidden" dimuat dari `reports/catatan_pasca_hidden.md`;
  - keterbatasan nomor 8 dan 9.
- **Laporan dirender ulang** dengan `--hanya-laporan` di container; `reports/log_evaluasi_hidden.json` tidak berubah (tetap 1 jalan).
- **Verifikasi label "terdeteksi".** Sebelum memakai label itu, dicek dengan membaca basis data bahwa kelima periode bermasalah berprioritas rendah di hidden semuanya punya 1–2 temuan.
