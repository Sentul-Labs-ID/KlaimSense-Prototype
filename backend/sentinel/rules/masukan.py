"""Data masukan mesin aturan.

Mesin aturan HANYA membaca apa yang juga dilihat BPJS di dunia nyata: data master
rumah sakit, kapasitas, harga acuan, tagihan, riwayat alat bantu dengar, dan data yang
diterima server dari perangkat sensor (registri perangkat, ringkasan harian, anomali).
Daftar tabel di bawah adalah satu-satunya pintu masuk data ke mesin aturan.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field

from sqlalchemy import Engine, inspect, select

from sentinel.models.master import HargaAcuan, Kapasitas, RumahSakit
from sentinel.models.sensor import Perangkat, SensorAnomali, StatusMesinHarian
from sentinel.models.transaksi import RiwayatAlatBantuDengar, Tagihan

TABEL_MASUKAN = (
    "rumah_sakit", "kapasitas", "harga_acuan", "tagihan", "riwayat_alat_bantu_dengar",
    "perangkat", "status_mesin_harian", "sensor_anomali",
)


@dataclass(frozen=True)
class Masukan:
    dataset_id: str
    rumah_sakit: list[dict]
    kapasitas: list[dict]
    harga_acuan: list[dict]
    tagihan: list[dict]
    riwayat_abd: list[dict]
    perangkat: list[dict] = field(default_factory=list)
    status_harian: list[dict] = field(default_factory=list)
    anomali_sensor: list[dict] = field(default_factory=list)

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
            perangkat=list(tabel.get("perangkat", [])),
            status_harian=list(tabel.get("status_mesin_harian", [])),
            anomali_sensor=list(tabel.get("sensor_anomali", [])),
        )


def muat_dari_db(engine: Engine, dataset_id: str) -> Masukan:
    def ambil(model, urut):
        t = model.__table__
        query = select(t).where(t.c.dataset_id == dataset_id).order_by(*[t.c[k] for k in urut])
        return [dict(baris) for baris in conn.execute(query).mappings()]

    ada = set(inspect(engine).get_table_names())

    def ambil_jika_ada(model, urut):
        return ambil(model, urut) if model.__tablename__ in ada else []

    with engine.connect() as conn:
        return Masukan(
            dataset_id=dataset_id,
            rumah_sakit=ambil(RumahSakit, ["id"]),
            kapasitas=ambil(Kapasitas, ["rs_id"]),
            harga_acuan=ambil(HargaAcuan, ["kode_item"]),
            tagihan=ambil(Tagihan, ["id"]),
            riwayat_abd=ambil(RiwayatAlatBantuDengar, ["id"]),
            perangkat=ambil_jika_ada(Perangkat, ["device_id"]),
            status_harian=ambil_jika_ada(StatusMesinHarian, ["mesin_id", "tanggal", "shift"]),
            anomali_sensor=ambil_jika_ada(SensorAnomali, ["device_id", "waktu", "jenis"]),
        )
