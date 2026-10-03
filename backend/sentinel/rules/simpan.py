"""Menyimpan temuan dan skor ke database."""

from sqlalchemy import Engine, delete, insert

from sentinel.models.hasil import Skor, Temuan
from sentinel.rules.mesin import HasilAturan

UKURAN_BATCH = 2_000


def simpan_hasil(engine: Engine, hasil: HasilAturan) -> None:
    """Hapus hasil lama dataset yang sama, lalu tulis ulang dalam satu transaksi."""
    tabel = [Temuan.__table__, Skor.__table__]
    Temuan.metadata.create_all(engine, tables=tabel)
    with engine.begin() as conn:
        for t in tabel:
            conn.execute(delete(t).where(t.c.dataset_id == hasil.dataset_id))
        for t, baris in ((Temuan.__table__, hasil.temuan), (Skor.__table__, hasil.skor)):
            for i in range(0, len(baris), UKURAN_BATCH):
                conn.execute(insert(t), baris[i : i + UKURAN_BATCH])
