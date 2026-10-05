# Naskah video demo KlaimSense

Video: [`assets/demo.webm`](../assets/demo.webm), 1920×1080, ±90 detik (alur ±84 detik, lalu bingkai penutup ditahan). Direkam otomatis dengan `make rekam-demo` dari dataset demo yang baru di-reset. Keterangan bahasa Indonesia tampil di layar pada setiap langkah, sehingga video tetap bisa dipahami tanpa suara. Waktu per langkah tercatat di [`assets/demo_waktu.json`](../assets/demo_waktu.json).

**Seluruh data dalam video adalah data tiruan.**

| Detik | Yang tampil di layar | Narasi |
|---|---|---|
| 0–10 | **Daftar periksa.** Ringkasan jumlah rumah sakit per prioritas dan ±121 ribu tagihan yang diperiksa; tabel rumah sakit per bulan, diurutkan dari prioritas tertinggi. Halaman bergulir pelan. | "Setiap tagihan rumah sakit ke BPJS diperiksa otomatis dengan dua pertanyaan: mungkinkah layanan ini terjadi, dan wajarkah tagihannya. Hasilnya adalah daftar periksa: rumah sakit mana yang paling perlu diperiksa lebih dulu." |
| 11–17 | **Detail RS Tiruan 012, Agustus 2026.** Skor rendah, belum ada temuan kapasitas fisioterapi. | "Ambil contoh rumah sakit ini. Bulan Agustus prioritasnya rendah; belum ada yang mencurigakan." |
| 18–26 | **Panel demo.** Dipilih: Agustus 2026, RS Tiruan 012, "Fisioterapi melebihi kapasitas terapis", 3 hari. Tombol "Sisipkan kecurangan" ditekan. | "Sekarang kita simulasikan kecurangan: tagihan fisioterapi fiktif selama tiga hari, sampai jumlah sesinya melebihi kemampuan terapis yang ada." |
| 27–34 | **Hasil sebelum → sesudah.** Skor 3,3 (rendah) menjadi 18,3 (tinggi), dengan alasan "Bukti fisik berulang". | "Sistem langsung menghitung ulang. Prioritasnya naik dari rendah menjadi tinggi. Bukan karena skornya besar, tetapi karena bukti fisiknya berulang: sesi yang ditagih melebihi kapasitas terapis pada tiga hari berbeda." |
| 35–41 | **Detail rumah sakit.** Rincian skor per aturan dan daftar temuan. Contoh: "Fisioterapi 11 Agustus 2026: 61 sesi ditagih, kapasitas 56 (7 terapis × 8 sesi). Selisih 5 sesi." | "Setiap temuan dijelaskan dengan kalimat yang bisa dibaca siapa pun: berapa yang ditagih, berapa kapasitasnya, dan selisihnya." |
| 42–48 | **Grafik harian.** Garis sesi ditagih dibanding garis putus-putus kapasitas; hari dengan temuan ditandai lingkaran oranye. | "Grafik ini memperlihatkan hari-hari ketika tagihan menembus batas kapasitas. Petugas tidak perlu membaca ribuan baris tagihan." |
| 49–55 | **Sensor mesin cuci darah RS Tiruan 026.** Kotak per mesin dan shift: hijau = terapi, abu-abu = siaga atau mati. | "Untuk mesin cuci darah, kami memasang sensor listrik. Sensor membedakan mesin yang benar-benar menjalankan terapi dari mesin yang sekadar menyala. Jika sesi ditagih tetapi mesinnya tidak bekerja, sistem akan tahu." |
| 55–62 | **Tombol "Verifikasi tanda tangan" ditekan.** Hasil: semua pesan bertanda tangan sah dan tersambung. | "Setiap pesan sensor diberi tanda tangan digital dan dirangkai seperti rantai. Pesan yang dipalsukan, dihapus, atau sensor yang dicabut akan langsung terdeteksi." |
| 62–70 | **Panel keputusan RS Tiruan 012.** Petugas mengetik alasan, mengisi nama, lalu menekan "Minta klarifikasi". Keputusan tercatat. | "Keputusan tetap di tangan petugas. Di sini petugas meminta klarifikasi kepada rumah sakit, dengan alasan tertulis. Rumah sakit diberi kesempatan menjelaskan sebelum ada audit." |
| 70–77 | **Halaman audit.** "Rantai keputusan utuh"; keputusan tercatat dengan waktu WIB. | "Setiap keputusan juga dirangkai seperti rantai. Bila ada catatan lama yang diubah diam-diam, rantainya akan terlihat rusak." |
| 77–90 | **Keterangan penutup** di atas halaman audit. | "Pada uji dengan data tersembunyi, sistem mendeteksi 83 dari 86 kejadian kecurangan tiruan, tanpa tuduhan keliru pada periode yang diprioritaskan. Skor adalah prioritas pemeriksaan, bukan penetapan kecurangan. Keputusan selalu di tangan petugas." |

## Catatan untuk perekam narasi

- Bacakan narasi dengan tempo sedang; setiap baris dirancang ±6–9 detik.
- Bila menambah suara, waktu di tabel mengikuti `assets/demo_waktu.json` (selisih ±1 detik dari video).
- Istilah yang muncul: **kapasitas** = jumlah sesi yang mungkin dilayani dengan tenaga atau mesin yang ada; **sensor** = alat pengukur arus listrik mesin; **tanda tangan digital** = segel elektronik yang membuktikan pesan berasal dari sensor yang sah dan tidak diubah; **audit** = pemeriksaan lanjutan.
- Angka "83 dari 86" berasal dari [`reports/evaluasi.md`](../reports/evaluasi.md) (dataset hidden, data tiruan).

Skor adalah prioritas pemeriksaan, bukan penetapan kecurangan. Keputusan selalu di tangan petugas.
