"""Menyimpan dataset tiruan ke database."""

from sqlalchemy import Engine, delete, insert

from sentinel.generator.bangkit import URUTAN_TABEL, DataTiruan
from sentinel.models import Base

UKURAN_BATCH = 5_000


def buat_tabel(engine: Engine) -> None:
    Base.metadata.create_all(engine)


def simpan(engine: Engine, data: DataTiruan) -> None:
    """Hapus data lama dataset yang sama, lalu tulis ulang dalam satu transaksi.
    Dataset lain (misalnya hidden saat menulis utama) tidak disentuh."""
    buat_tabel(engine)
    tabel = Base.metadata.tables
    with engine.begin() as conn:
        for nama in reversed(URUTAN_TABEL):
            t = tabel[nama]
            conn.execute(delete(t).where(t.c.dataset_id == data.dataset_id))
        for nama in URUTAN_TABEL:
            baris = data.tabel[nama]
            for i in range(0, len(baris), UKURAN_BATCH):
                conn.execute(insert(tabel[nama]), baris[i : i + UKURAN_BATCH])
