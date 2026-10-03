"""SERVER: endpoint penerimaan pesan perangkat sensor."""

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import Engine

from sentinel.sensor.ingest import ingest

router = APIRouter(prefix="/sensor", tags=["sensor"])


class PesanMasuk(BaseModel):
    pesan: dict[str, Any]
    tanda_tangan: str


class HasilIngestApi(BaseModel):
    diterima: int
    ditolak: int
    anomali: list[dict[str, Any]]


def ambil_engine() -> Engine:
    from sentinel.db import get_engine

    return get_engine()


@router.post("/ingest", response_model=HasilIngestApi)
def terima(body: PesanMasuk | list[PesanMasuk], engine: Engine = Depends(ambil_engine)) -> HasilIngestApi:
    """Terima satu pesan atau sekumpulan pesan (urut kirim) dari perangkat."""
    daftar = [x.model_dump() for x in (body if isinstance(body, list) else [body])]
    hasil = ingest(engine, daftar)
    return HasilIngestApi(
        diterima=len(hasil.diterima),
        ditolak=hasil.ditolak,
        anomali=[
            {"jenis": a["jenis"], "device_id": a["device_id"], "waktu": a["waktu"].isoformat(), "keterangan": a["keterangan"]}
            for a in hasil.anomali
        ],
    )
