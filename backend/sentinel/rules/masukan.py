"""Data masukan mesin aturan.

Mesin aturan HANYA membaca apa yang juga dilihat BPJS di dunia nyata: data master
rumah sakit, kapasitas, harga acuan, tagihan, dan riwayat alat bantu dengar.
Daftar tabel di bawah adalah satu-satunya pintu masuk data ke mesin aturan.
"""

from collections.abc import Mapping
from dataclasses import dataclass

from sqlalchemy import Engine, select

from sentinel.models.master import HargaAcuan, Kapasitas, RumahSakit
from sentinel.models.transaksi import RiwayatAlatBantuDengar, Tagihan

TABEL_MASUKAN = ("rumah_sakit", "kapasitas", "harga_acuan", "tagihan", "riwayat_alat_bantu_dengar")


@dataclass(frozen=True)
class Masukan:
    dataset_id: str
    rumah_sakit: list[dict]
    kapasitas: list[dict]
    harga_acuan: list[dict]
    tagihan: list[dict]
    riwayat_abd: list[dict]

    @classmethod
    def dari_tabel(cls, dataset_id: str, tabel: Mapping[str, list[dict]]) -> "Masukan":
        """Ambil hanya tabel yang diizinkan dari kumpulan tabel apa pun (dipakai tes)."""
        return cls(
            dataset_id=dataset_id,
            rumah_sakit=list(tabel["rumah_sakit"]),
            kapasitas=list(tabel["kapasitas"]),
            harga_acuan=list(tabel["harga_acuan"]),
            tagihan=sorted(tabel["tagihan"], key=lambda t: t["id"]),
            riwayat_abd=list(tabel.get("riwayat_alat_bantu_dengar", [])),
        )


def muat_dari_db(engine: Engine, dataset_id: str) -> Masukan:
    def ambil(model, urut):
        t = model.__table__
        query = select(t).where(t.c.dataset_id == dataset_id).order_by(*[t.c[k] for k in urut])
        return [dict(baris) for baris in conn.execute(query).mappings()]

    with engine.connect() as conn:
        return Masukan(
            dataset_id=dataset_id,
            rumah_sakit=ambil(RumahSakit, ["id"]),
            kapasitas=ambil(Kapasitas, ["rs_id"]),
            harga_acuan=ambil(HargaAcuan, ["kode_item"]),
            tagihan=ambil(Tagihan, ["id"]),
            riwayat_abd=ambil(RiwayatAlatBantuDengar, ["id"]),
        )
