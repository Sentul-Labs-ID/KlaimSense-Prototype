"""Konfigurasi simulasi sensor (BUKAN batas aturan; batas aturan ada di parameter.yaml).

Semua nilai ampere ILUSTRATIF dan WAJIB dikalibrasi dengan perangkat dan mesin
hemodialisa nyata sebelum dipakai di luar prototipe.
"""

from pathlib import Path

# Jadwal shift unit hemodialisa: nomor shift -> (menit mulai, menit selesai) sejak 00:00.
# Shift 4 adalah shift darurat (kasus sah HD_SHIFT_TAMBAHAN). Di luar slot ini = shift 0.
JADWAL_SHIFT: dict[int, tuple[int, int]] = {
    1: (5 * 60, 9 * 60 + 50),  # 05:00-09:50
    2: (9 * 60 + 50, 14 * 60 + 40),  # 09:50-14:40
    3: (14 * 60 + 40, 19 * 60 + 30),  # 14:40-19:30
    4: (19 * 60 + 30, 24 * 60),  # 19:30-24:00 (darurat)
}
SHIFT_DI_LUAR = 0
MENIT_SEHARI = 24 * 60

# Terapi dimulai 5-20 menit setelah slot shift dibuka (persiapan mesin), durasi dari
# parameter.yaml (hemodialisa_durasi_sesi_jam) dengan variasi kecil.
PERSIAPAN_MENIT = (5, 20)
VARIASI_DURASI_MENIT = 6.0  # simpangan baku

# Peluang mesin yang tidak dipakai pada sebuah shift tetap menyala (standby); sisanya mati.
PELUANG_STANDBY_SAAT_KOSONG = 0.5
# Peluang mesin standby di luar jam shift (malam hari).
PELUANG_STANDBY_MALAM = 0.05

# ---- Pola arus (ampere, ILUSTRATIF, kalibrasi dengan perangkat nyata) ----
# Standby dan terapi sengaja tumpang tindih (lonjakan pemanas saat standby, jeda pompa
# saat terapi) agar klasifikasi tidak trivial; akurasi edge pada data uji ±97-98%.
ARUS_MATI = (0.03, 0.02)  # rata-rata, simpangan baku
ARUS_STANDBY_DASAR = (0.80, 1.25)  # rentang rata-rata per segmen
ARUS_STANDBY_NOISE = 0.12
ARUS_STANDBY_PEMANAS = (0.15, 0.50, 1.10)  # peluang lonjakan pemanas per menit, rentang tambahan
ARUS_TERAPI_DASAR = (1.50, 2.30)  # rentang rata-rata per sesi
ARUS_TERAPI_POMPA = (0.12, 0.38)  # amplitudo fluktuasi pompa
ARUS_TERAPI_PERIODE = (3.0, 5.5)  # periode pompa (menit)
ARUS_TERAPI_NOISE = 0.28
ARUS_TERAPI_JEDA = (0.10, 0.50, 1.00)  # peluang menit jeda (alarm/bypass), rentang penurunan

# Gangguan alami (bukan kecurangan): peluang satu jendela tidak terkirim (kedip listrik).
PELUANG_JENDELA_HILANG = 0.002

# ---- Perangkat edge ----
PANJANG_JENDELA_DEFAULT = 10  # menit
SEED_LATIH = 7_001  # KHUSUS pelatihan model; berbeda dari seed dataset utama (42) dan hidden (2026)
HARI_LATIH = 400  # jumlah mesin-hari simulasi untuk melatih dan menguji model
PORSI_UJI = 0.3
KEDALAMAN_POHON = 6
SEED_SENSOR = {"utama": 4_242, "hidden": 2_626}  # seed simulasi sinyal per dataset

DIREKTORI_MODEL = Path(__file__).resolve().parent / "model"
NAMA_MODEL = "edge_pohon_keputusan.pkl"

STATUS = ("mati", "standby", "terapi")  # indeks = kode label
