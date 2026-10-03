"""Skema database JKN-Sentinel (SQLAlchemy 2.x).

Tabel dikelompokkan menurut siapa yang boleh membacanya:

- `master`, `transaksi`  : data yang dilihat BPJS (rumah sakit, kapasitas, pasien,
                           harga acuan, tagihan, riwayat alat bantu dengar).
                           Boleh dibaca semua modul, termasuk mesin aturan.
- `kenyataan`            : sesi yang benar-benar terjadi. Hanya untuk simulator
                           sensor (fase 3) dan evaluasi (fase 4). DILARANG dibaca
                           mesin aturan.
- `hasil`                : temuan dan skor hasil mesin aturan. Boleh dibaca semua modul.
- `evaluasi`             : ground truth, profil rumah sakit tiruan, dan kasus sah di
                           area batas. Hanya untuk evaluasi (fase 4); tidak boleh
                           dibaca mesin aturan atau diekspos API dashboard.

Semua tabel punya kolom `dataset_id` ("utama" atau "hidden"). Seluruh isinya data tiruan.
"""

from sentinel.db import Base
from sentinel.models.evaluasi import GroundTruth, KasusSah, ProfilRS
from sentinel.models.hasil import Skor, Temuan
from sentinel.models.kenyataan import SesiAktual
from sentinel.models.master import HargaAcuan, Kapasitas, Pasien, RumahSakit
from sentinel.models.transaksi import RiwayatAlatBantuDengar, Tagihan

DATASET = ("utama", "hidden")

__all__ = [
    "DATASET",
    "Base",
    "GroundTruth",
    "HargaAcuan",
    "KasusSah",
    "Kapasitas",
    "Pasien",
    "ProfilRS",
    "RiwayatAlatBantuDengar",
    "RumahSakit",
    "SesiAktual",
    "Skor",
    "Tagihan",
    "Temuan",
]
