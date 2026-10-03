"""Tes fungsi pembanding verifikasi reproduksi (fase 7)."""

from sentinel.reproduksi import PERNYATAAN, bandingkan


def test_identik_tidak_ada_perbedaan():
    a = {"recall": {"pembilang": 83, "penyebut": 86, "ci95": [0.902, 0.988]}, "daftar": [1, 2]}
    assert bandingkan(a, {"recall": {"pembilang": 83, "penyebut": 86, "ci95": [0.902, 0.988]}, "daftar": [1, 2]}) == []


def test_perbedaan_dilaporkan_dengan_jalur():
    a = {"hidden": {"recall": {"pembilang": 82, "penyebut": 86}, "baru": 1}, "daftar": [1, 2]}
    b = {"hidden": {"recall": {"pembilang": 83, "penyebut": 86}}, "daftar": [1, 2, 3]}
    hasil = bandingkan(a, b)
    assert "hidden.recall.pembilang: 82 vs 83" in [x.lstrip(".") for x in hasil]
    assert any("baru" in x and "hanya ada di hasil ulang" in x for x in hasil)
    assert any("daftar" in x and "panjang 2 vs 3" in x for x in hasil)


def test_pernyataan_menegaskan_bukan_penyetelan():
    assert "bukan penyetelan" in PERNYATAAN
