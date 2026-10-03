"""Penyimpanan dataset ke database (SQLite di memori agar tes tidak butuh PostgreSQL)."""

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.pool import StaticPool

from sentinel.generator.bangkit import bangkitkan
from sentinel.generator.simpan import simpan
from sentinel.models import Base


@pytest.fixture
def engine():
    e = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    yield e
    e.dispose()


def jumlah_per_dataset(engine) -> dict[tuple[str, str], int]:
    hasil = {}
    with engine.connect() as conn:
        for nama, tabel in Base.metadata.tables.items():
            for dataset_id, n in conn.execute(
                select(tabel.c.dataset_id, func.count()).group_by(tabel.c.dataset_id)
            ):
                hasil[(nama, dataset_id)] = n
    return hasil


def test_simpan_mengganti_hanya_dataset_yang_sama(engine):
    utama = bangkitkan("utama", hari=35, jumlah_rs=20)
    hidden = bangkitkan("hidden", hari=35, jumlah_rs=20)
    simpan(engine, utama)
    simpan(engine, hidden)
    awal = jumlah_per_dataset(engine)
    for data in (utama, hidden):
        for nama, baris in data.tabel.items():
            assert awal.get((nama, data.dataset_id), 0) == len(baris), (nama, data.dataset_id)

    # Bangkitkan ulang utama dengan seed lain: data lama utama terganti, hidden utuh.
    utama_baru = bangkitkan("utama", seed=99, hari=35, jumlah_rs=20)
    simpan(engine, utama_baru)
    akhir = jumlah_per_dataset(engine)
    for nama, baris in utama_baru.tabel.items():
        assert akhir.get((nama, "utama"), 0) == len(baris), nama
    for nama in hidden.tabel:
        assert akhir.get((nama, "hidden"), 0) == awal.get((nama, "hidden"), 0), nama


def test_simpan_dua_kali_tidak_menggandakan(engine):
    data = bangkitkan("utama", hari=35, jumlah_rs=20)
    simpan(engine, data)
    simpan(engine, data)
    jumlah = jumlah_per_dataset(engine)
    assert jumlah[("tagihan", "utama")] == len(data.tabel["tagihan"])
