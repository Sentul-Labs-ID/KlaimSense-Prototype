"""Panel demo: sisipkan kecurangan ke dataset demo lalu hitung ulang skor."""

from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import Engine, select

from sentinel.api.deps import ambil_engine, ambil_pengaturan, periksa_dataset_tulis
from sentinel.config import Settings
from sentinel.generator.sisipan import SisipanDitolak, sisipkan
from sentinel.models.hasil import Skor
from sentinel.models.master import RumahSakit
from sentinel.parameter import hash_parameter, muat_parameter
from sentinel.rules.masukan import muat_dari_db
from sentinel.rules.mesin import jalankan
from sentinel.rules.simpan import simpan_hasil

router = APIRouter(prefix="/demo", tags=["demo"])
LABEL_SISIPAN = {
    "KAP_FISIO": "fisioterapi melebihi kapasitas terapis",
    "KAP_HD": "hemodialisa melebihi kapasitas mesin",
    "ULANG_HARI": "dua sesi hemodialisa sehari untuk pasien yang sama",
    "HARGA_LEBIH": "harga di atas harga acuan",
}


class SisipanMasuk(BaseModel):
    dataset: str = "demo"
    rs_id: str
    skenario: Literal["KAP_FISIO", "KAP_HD", "ULANG_HARI", "HARGA_LEBIH"]
    jumlah_hari: int = Field(ge=1, le=5)
    periode: str | None = None


def _skor(engine: Engine, rs_id: str) -> dict[str, dict]:
    s = Skor.__table__
    with engine.connect() as conn:
        return {x["periode"]: {"skor": x["skor"], "prioritas": x["prioritas"], "alasan_prioritas": x["alasan_prioritas"]}
                for x in conn.execute(select(s).where(s.c.dataset_id == "demo", s.c.rs_id == rs_id)).mappings()}


@router.post("/sisipkan")
def sisipkan_kecurangan(
    body: SisipanMasuk,
    engine: Engine = Depends(ambil_engine),
    pengaturan: Settings = Depends(ambil_pengaturan),
) -> dict[str, Any]:
    if not pengaturan.demo_mode:
        raise HTTPException(status_code=403, detail="Mode demo tidak aktif. Nyalakan DEMO_MODE=true untuk memakai panel ini.")
    periksa_dataset_tulis(body.dataset)
    p = muat_parameter()
    sebelum = _skor(engine, body.rs_id)
    try:
        hasil = sisipkan(engine, p, body.rs_id, body.skenario, body.jumlah_hari, body.periode, seed=len(sebelum))
    except SisipanDitolak as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    simpan_hasil(engine, jalankan(muat_dari_db(engine, "demo"), p, hash_parameter()))
    sesudah = _skor(engine, body.rs_id)
    periode = sorted({t.strftime("%Y-%m") for t in hasil.tanggal})
    with engine.connect() as conn:
        nama = conn.execute(select(RumahSakit.nama_samaran).where(RumahSakit.id == body.rs_id)).scalar()
    return {
        "rs_id": body.rs_id,
        "nama_samaran": nama,
        "sisipan": LABEL_SISIPAN[body.skenario],
        "tanggal": hasil.tanggal,
        "tagihan_baru": hasil.tagihan_baru,
        "tagihan_diubah": hasil.tagihan_diubah,
        "perubahan": [
            {"periode": per, "sebelum": sebelum.get(per), "sesudah": sesudah.get(per)} for per in periode
        ],
        "pesan": "Sisipan hanya berlaku di dataset demo. Skor seluruh dataset demo sudah dihitung ulang.",
    }
