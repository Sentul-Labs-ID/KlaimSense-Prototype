"""Katalog statis data tiruan: wilayah, item harga acuan, dan tarif paket.

Nama item generik dan fiktif (bukan merek dagang). Harga dan tarif fiktif.
Nama provinsi dan kabupaten/kota adalah geografi publik; nama rumah sakit samaran.
"""

KAB_KOTA: dict[str, list[str]] = {
    "Jawa Barat": ["Kota Bandung", "Kab. Bogor", "Kota Bekasi", "Kab. Cirebon"],
    "Jawa Timur": ["Kota Surabaya", "Kota Malang", "Kab. Sidoarjo", "Kab. Jember"],
    "Sumatera Utara": ["Kota Medan", "Kab. Deli Serdang", "Kota Pematangsiantar", "Kab. Asahan"],
    "Sulawesi Selatan": ["Kota Makassar", "Kab. Gowa", "Kota Parepare", "Kab. Bone"],
    "Kalimantan Timur": ["Kota Samarinda", "Kota Balikpapan", "Kab. Kutai Kartanegara", "Kota Bontang"],
    "Bali": ["Kota Denpasar", "Kab. Badung", "Kab. Gianyar", "Kab. Tabanan"],
}
PROVINSI = list(KAB_KOTA)

# Urutan prioritas kombinasi (indeks provinsi, kelas). Kelas A hanya di sedikit provinsi,
# kelas C dan D ada di hampir semua provinsi. Setiap kombinasi yang dipakai diisi
# minimal 3 rumah sakit (kebutuhan perbandingan antar-rumah sakit di fase 2).
PRIORITAS_KOMBINASI: list[tuple[int, str]] = [
    (0, "A"), (0, "B"), (0, "C"), (0, "D"),
    (1, "B"), (1, "C"), (1, "D"),
    (2, "C"), (2, "D"),
    (1, "A"), (2, "B"),
    (3, "C"), (3, "D"), (3, "B"),
    (4, "C"), (4, "D"), (4, "B"),
    (2, "A"),
    (5, "C"), (5, "D"), (5, "B"),
]
BOBOT_SISA_KELAS = {"A": 1, "B": 2, "C": 3, "D": 3}

# (kode_item, nama_item, jenis, harga acuan rupiah per satuan)
HARGA_ACUAN: list[tuple[str, str, str, int]] = [
    ("OBK-001", "Tablet antidiabetes oral generik 500 mg", "obat_kronis", 420),
    ("OBK-002", "Tablet antidiabetes oral generik 80 mg", "obat_kronis", 650),
    ("OBK-003", "Tablet antihipertensi generik 5 mg", "obat_kronis", 380),
    ("OBK-004", "Tablet antihipertensi generik 50 mg", "obat_kronis", 900),
    ("OBK-005", "Tablet penurun kolesterol generik 20 mg", "obat_kronis", 1_150),
    ("OBK-006", "Tablet antiplatelet generik 75 mg", "obat_kronis", 2_400),
    ("OBK-007", "Inhaler bronkodilator generik 100 mcg", "obat_kronis", 48_000),
    ("OBK-008", "Tablet antiepilepsi generik 200 mg", "obat_kronis", 1_800),
    ("ABD-001", "Alat bantu dengar analog belakang telinga", "alat_bantu_dengar", 1_100_000),
    ("ABD-002", "Alat bantu dengar digital belakang telinga", "alat_bantu_dengar", 2_350_000),
    ("ABD-003", "Alat bantu dengar digital dalam telinga", "alat_bantu_dengar", 3_200_000),
]
JUMLAH_OBAT_PER_RESEP = (30, 60, 90)
JUMLAH_OBAT_KHUSUS = {"OBK-007": (1, 2)}  # inhaler dihitung per unit, bukan per tablet

# Tarif paket fiktif per sesi, per kelas rumah sakit (rupiah).
TARIF_FISIOTERAPI = {"A": 215_000, "B": 190_000, "C": 165_000, "D": 150_000}
TARIF_HEMODIALISA = {"A": 1_120_000, "B": 1_040_000, "C": 980_000, "D": 930_000}
