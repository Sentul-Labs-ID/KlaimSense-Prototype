"""Menyimpan dataset tiruan ke database."""

from sqlalchemy import Engine, delete, insert

from sentinel.generator.bangkit import URUTAN_TABEL, DataTiruan
from sentinel.models import Base

UKURAN_BATCH = 5_000
# Tabel turunan (hasil aturan dan data sensor) yang menjadi basi bila data dibangkitkan ulang.
TABEL_TURUNAN = ("skor", "temuan", "status_mesin_harian", "sensor_anomali", "status_sensor", "perangkat")


def buat_tabel(engine: Engine) -> None:
    Base.metadata.create_all(engine)


def simpan(engine: Engine, data: DataTiruan) -> None:
    """Hapus data lama dataset yang sama (termasuk temuan dan skor turunannya), lalu
    tulis ulang dalam satu transaksi. Dataset lain tidak disentuh."""
    buat_tabel(engine)
    tabel = Base.metadata.tables
    with engine.begin() as conn:
        for nama in TABEL_TURUNAN + tuple(reversed(URUTAN_TABEL)):
            t = tabel[nama]
            conn.execute(delete(t).where(t.c.dataset_id == data.dataset_id))
        for nama in URUTAN_TABEL:
            baris = data.tabel[nama]
            for i in range(0, len(baris), UKURAN_BATCH):
                conn.execute(insert(tabel[nama]), baris[i : i + UKURAN_BATCH])
