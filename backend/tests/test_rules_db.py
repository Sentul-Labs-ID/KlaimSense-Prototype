"""Mesin aturan dari database (SQLite) dan CLI."""

import pytest
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.pool import StaticPool

from sentinel.generator.bangkit import bangkitkan
from sentinel.generator.simpan import simpan
from sentinel.models import Skor, Temuan
from sentinel.rules.__main__ import main

TABEL_TERLARANG = ("sesi_aktual", "ground_truth", "profil_rs", "kasus_sah")


@pytest.fixture
def engine():
    e = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    simpan(e, bangkitkan("utama", hari=35, jumlah_rs=20))
    yield e
    e.dispose()


def jumlah(engine, model, dataset="utama") -> int:
    with engine.connect() as conn:
        return conn.execute(select(func.count()).select_from(model).where(model.dataset_id == dataset)).scalar()


def test_mesin_aturan_tidak_membutuhkan_tabel_terlarang(engine, capsys):
    """Tabel kenyataan dan evaluasi dihapus dari database; mesin aturan tetap jalan."""
    with engine.begin() as conn:
        for nama in TABEL_TERLARANG:
            conn.execute(text(f"DROP TABLE {nama}"))
    assert main(["--dataset", "utama"], engine=engine) == 0
    assert jumlah(engine, Temuan) > 0
    assert jumlah(engine, Skor) == 20 * 2  # 20 RS x 2 bulan (Juli-Agustus)
    keluaran = capsys.readouterr().out
    assert "10 RS teratas" in keluaran
    for kata in TABEL_TERLARANG:
        assert kata not in keluaran


def test_jalan_ulang_mengganti_hasil_lama(engine):
    main(["--dataset", "utama"], engine=engine)
    pertama = (jumlah(engine, Temuan), jumlah(engine, Skor))
    main(["--dataset", "utama"], engine=engine)
    assert (jumlah(engine, Temuan), jumlah(engine, Skor)) == pertama


def test_dataset_kosong(engine, capsys):
    assert main(["--dataset", "hidden"], engine=engine) == 1
    assert "make generate" in capsys.readouterr().out


def test_generate_ulang_menghapus_hasil_aturan_yang_basi(engine):
    main(["--dataset", "utama"], engine=engine)
    assert jumlah(engine, Temuan) > 0
    simpan(engine, bangkitkan("utama", seed=7, hari=35, jumlah_rs=20))
    assert jumlah(engine, Temuan) == 0 and jumlah(engine, Skor) == 0
