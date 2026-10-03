"""Menyimpan temuan dan skor ke database."""

from sqlalchemy import Engine, delete, insert, inspect, text

from sentinel.models.hasil import Skor, Temuan
from sentinel.rules.mesin import HasilAturan

UKURAN_BATCH = 2_000


def simpan_hasil(engine: Engine, hasil: HasilAturan) -> None:
    """Hapus hasil lama dataset yang sama, lalu tulis ulang dalam satu transaksi."""
    tabel = [Temuan.__table__, Skor.__table__]
    Temuan.metadata.create_all(engine, tables=tabel)
    # Migrasi sederhana untuk kolom yang ditambahkan di fase 3.
    for tabel_nama, kolom, tipe in (("temuan", "kategori", "VARCHAR(16)"), ("skor", "alasan_prioritas", "VARCHAR(160)")):
        if kolom not in {c["name"] for c in inspect(engine).get_columns(tabel_nama)}:
            with engine.begin() as conn:
                conn.execute(text(f"ALTER TABLE {tabel_nama} ADD COLUMN {kolom} {tipe}"))
    with engine.begin() as conn:
        for t in tabel:
            conn.execute(delete(t).where(t.c.dataset_id == hasil.dataset_id))
        for t, baris in ((Temuan.__table__, hasil.temuan), (Skor.__table__, hasil.skor)):
            for i in range(0, len(baris), UKURAN_BATCH):
                conn.execute(insert(t), baris[i : i + UKURAN_BATCH])
