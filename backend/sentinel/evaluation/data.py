"""Memuat data untuk evaluasi, HANYA MEMBACA.

Modul evaluasi satu-satunya yang boleh membaca label (`ground_truth`, `profil_rs`,
`kasus_sah`) dan kenyataan fisik. Di PostgreSQL transaksi dibuka sebagai READ ONLY,
sehingga upaya menulis akan ditolak basis data; transaksi selalu di-rollback.
"""

from dataclasses import dataclass

from sqlalchemy import Engine, select

from sentinel.models.evaluasi import GroundTruth, KasusSah, ProfilRS
from sentinel.models.hasil import Skor, Temuan
from sentinel.models.sensor import Perangkat, SensorAnomali


@dataclass
class DataEvaluasi:
    dataset_id: str
    ground_truth: list[dict]
    kasus_sah: list[dict]
    profil: dict[str, str]
    temuan: list[dict]
    skor: list[dict]
    anomali: list[dict]
    rs_perangkat: dict[str, str]


def muat(engine: Engine, dataset_id: str) -> DataEvaluasi:
    def ambil(model, *kolom, urut=None):
        t = model.__table__
        query = select(*[t.c[k] for k in kolom]).where(t.c.dataset_id == dataset_id)
        if urut:
            query = query.order_by(*[t.c[k] for k in urut])
        return [dict(x) for x in conn.execute(query).mappings()]

    with engine.connect() as conn:
        if conn.dialect.name == "postgresql":
            conn.exec_driver_sql("SET TRANSACTION READ ONLY")
        try:
            data = DataEvaluasi(
                dataset_id=dataset_id,
                ground_truth=ambil(GroundTruth, "id", "skenario", "rs_id", "tanggal", "tagihan_ids", urut=["id"]),
                kasus_sah=ambil(KasusSah, "id", "jenis", "rs_id", "tanggal", "tagihan_ids", urut=["id"]),
                profil={x["rs_id"]: x["profil"] for x in ambil(ProfilRS, "rs_id", "profil")},
                temuan=ambil(
                    Temuan, "id", "aturan_id", "rs_id", "tanggal", "periode", "layanan", "tagihan_ids", "kategori",
                    urut=["id"],
                ),
                skor=ambil(Skor, "rs_id", "periode", "skor", "prioritas", "alasan_prioritas", "hash_parameter",
                           "versi_aturan", urut=["rs_id", "periode"]),
                anomali=ambil(SensorAnomali, "jenis", "device_id", "waktu", urut=["id"]),
                rs_perangkat={x["device_id"]: x["rs_id"] for x in ambil(Perangkat, "device_id", "rs_id")},
            )
        finally:
            conn.rollback()
    return data
