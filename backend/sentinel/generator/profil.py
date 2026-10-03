"""Profil distribusi data tiruan per dataset.

Batas aturan (kapasitas per terapis, shift, toleransi harga, masa penggantian alat)
TIDAK ada di sini; semuanya dibaca dari `config/parameter.yaml`. File ini hanya berisi
pengaturan simulasi: seberapa sibuk rumah sakit, seberapa sering kecurangan disisipkan,
dan seberapa besar. Dataset "hidden" sengaja memakai distribusi yang sedikit berbeda
agar evaluasi akhir tidak sirkular.
"""

from dataclasses import dataclass, field

Rentang = tuple[float, float]
RentangInt = tuple[int, int]


@dataclass(frozen=True)
class ProfilDataset:
    dataset_id: str
    seed_default: int
    # Penomoran ID dipisah per dataset agar utama dan hidden tidak pernah bertabrakan.
    offset_rs: int
    offset_pasien: int
    offset_baris: int
    jumlah_rs_disisipi: int
    rs_per_skenario: RentangInt
    kejadian_per_rs: dict[str, RentangInt]
    kap_lebih_persen: Rentang  # besaran tagihan di atas kapasitas
    kap_porsi_halus: float  # porsi kejadian KAP yang hanya lewat 1-2 sesi
    harga_lebih_persen: Rentang  # besaran harga di atas harga acuan
    sensor_palsu_porsi: Rentang  # sesi fiktif sebagai porsi sesi nyata hari itu
    abd_dini_tahun: Rentang  # jarak dari pemberian terakhir, dalam tahun
    abd_dini_porsi_halus: float  # porsi kejadian ABD_DINI yang nyaris lewat masa penggantian
    jumlah_rs_sensor: int = 10
    jumlah_kontrol_sensor_min: int = 4


PROFIL: dict[str, ProfilDataset] = {
    "utama": ProfilDataset(
        dataset_id="utama",
        seed_default=42,
        offset_rs=0,
        offset_pasien=0,
        offset_baris=0,
        jumlah_rs_disisipi=8,
        rs_per_skenario=(2, 2),
        kejadian_per_rs={
            "KAP_FISIO": (3, 8),
            "KAP_HD": (3, 8),
            "ULANG_IDENTIK": (3, 6),
            "ULANG_HARI": (3, 6),
            "HARGA_LEBIH": (3, 6),
            "ABD_DINI": (2, 4),
            "SENSOR_PALSU": (6, 12),
        },
        kap_lebih_persen=(1, 60),
        kap_porsi_halus=0.3,
        harga_lebih_persen=(15, 200),
        sensor_palsu_porsi=(0.10, 0.40),
        abd_dini_tahun=(0.5, 4.9),
        abd_dini_porsi_halus=0.25,
    ),
    "hidden": ProfilDataset(
        dataset_id="hidden",
        seed_default=2026,
        offset_rs=500,
        offset_pasien=500_000,
        offset_baris=50_000_000,
        jumlah_rs_disisipi=10,
        rs_per_skenario=(2, 3),
        kejadian_per_rs={
            "KAP_FISIO": (2, 10),
            "KAP_HD": (2, 10),
            "ULANG_IDENTIK": (2, 8),
            "ULANG_HARI": (2, 8),
            "HARGA_LEBIH": (2, 8),
            "ABD_DINI": (1, 5),
            "SENSOR_PALSU": (4, 14),
        },
        kap_lebih_persen=(1, 80),
        kap_porsi_halus=0.4,
        harga_lebih_persen=(12, 150),
        sensor_palsu_porsi=(0.05, 0.30),
        abd_dini_tahun=(0.3, 4.95),
        abd_dini_porsi_halus=0.35,
    ),
}


@dataclass(frozen=True)
class ProfilUmum:
    """Pengaturan simulasi yang sama untuk kedua dataset."""

    # Utilisasi dasar per rumah sakit dan batas utilisasi harian.
    utilisasi_normal: Rentang = (0.60, 0.92)
    utilisasi_normal_harian: Rentang = (0.50, 0.95)
    utilisasi_sibuk: Rentang = (0.97, 1.00)
    utilisasi_sibuk_harian: Rentang = (0.95, 1.00)
    utilisasi_volume_tinggi: Rentang = (0.85, 0.93)
    sebaran_harian: float = 0.05
    faktor_sabtu_fisioterapi: float = 0.55
    # Hemodialisa: porsi jadwal 2x/minggu (sisanya 3x), ketidakhadiran, pergantian pasien.
    porsi_hd_dua_kali: float = 0.7
    absen_hd: float = 0.03
    absen_hd_sibuk: float = 0.01
    porsi_hd_mulai_tengah: float = 0.10
    porsi_hd_berhenti_tengah: float = 0.05
    porsi_hd_tidak_aktif: float = 0.15
    peluang_hd_tujuh_hari: float = 0.25
    # Variasi harga normal: bawah sampai porsi toleransi dari parameter.yaml.
    harga_normal_bawah: float = -0.08
    harga_normal_porsi_toleransi: float = 0.6
    # Jarak aman (hari) antara ABD normal/ABD_DINI dan batas masa penggantian.
    margin_abd_hari: int = 60
    kontrol_sibuk: int = 2
    # Kasus sah di area batas (per dataset), hanya di rumah sakit jujur dan jujur-sibuk.
    kasus_hd_shift_tambahan: RentangInt = (2, 4)  # hari; lewat kapasitas 1-2 sesi
    kasus_hd_lebih_sesi: RentangInt = (1, 2)
    kasus_fisio_lembur: RentangInt = (2, 4)  # hari; lewat kapasitas 1-3 sesi
    kasus_fisio_lebih_sesi: RentangInt = (1, 3)
    kasus_fisio_lembur_per_terapis: int = 2  # sesi lembur maksimal per terapis
    kasus_harga_acuan_lama: RentangInt = (5, 10)  # tagihan
    harga_acuan_lama_di_atas_toleransi_pp: Rentang = (0.5, 4.5)  # poin persen, dibulatkan ke atas
    kapasitas_kelas: dict[str, dict[str, RentangInt]] = field(
        default_factory=lambda: {
            "A": {"fisioterapis": (6, 10), "mesin_hd": (15, 25)},
            "B": {"fisioterapis": (4, 7), "mesin_hd": (8, 15)},
            "C": {"fisioterapis": (2, 4), "mesin_hd": (4, 8)},
            "D": {"fisioterapis": (1, 2), "mesin_hd": (2, 4)},
            "A_volume_tinggi": {"fisioterapis": (12, 16), "mesin_hd": (30, 40)},
        }
    )
    pasien_obat_kelas: dict[str, RentangInt] = field(
        default_factory=lambda: {"A": (300, 500), "B": (150, 300), "C": (60, 150), "D": (30, 60)}
    )
    abd_baru_kelas: dict[str, RentangInt] = field(
        default_factory=lambda: {"A": (8, 15), "B": (5, 10), "C": (2, 6), "D": (1, 3)}
    )
    riwayat_abd_kelas: dict[str, int] = field(
        default_factory=lambda: {"A": 40, "B": 25, "C": 12, "D": 6}
    )
    faktor_volume_tinggi: float = 1.5


UMUM = ProfilUmum()
