"""Keputusan petugas dan audit rantai hash."""

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, field_validator
from sqlalchemy import Engine, insert, select

from sentinel.api.deps import ambil_engine, periksa_dataset, periksa_dataset_tulis
from sentinel.models.hasil import Skor
from sentinel.models.keputusan import Keputusan
from sentinel.models.master import RumahSakit

router = APIRouter(tags=["keputusan"])
HASH_AWAL = "0" * 64
LABEL_KEPUTUSAN = {
    "setujui": "Setujui",
    "minta_klarifikasi": "Minta klarifikasi",
    "rujuk_audit": "Rujuk ke audit",
}


class KeputusanMasuk(BaseModel):
    dataset: str
    rs_id: str
    periode: str
    keputusan: Literal["setujui", "minta_klarifikasi", "rujuk_audit"]
    alasan: str
    petugas: str

    @field_validator("alasan")
    @classmethod
    def _alasan(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 10:
            raise ValueError("Alasan wajib diisi, minimal 10 karakter.")
        return v

    @field_validator("petugas")
    @classmethod
    def _petugas(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Nama petugas wajib diisi.")
        return v


def hash_entri(e: dict) -> str:
    isi = {k: e[k] for k in ("dataset_id", "rs_id", "periode", "keputusan", "alasan", "petugas", "prev_hash")}
    isi["waktu"] = e["waktu"].isoformat(timespec="seconds")
    return hashlib.sha256(json.dumps(isi, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def periksa_rantai(entri: list[dict]) -> dict[str, Any]:
    sebelumnya = HASH_AWAL
    for e in entri:
        if e["prev_hash"] != sebelumnya:
            return {"status": "rusak", "entri_rusak": e["id"],
                    "keterangan": f"Entri #{e['id']} tidak menunjuk ke hash entri sebelumnya (rantai terputus)."}
        if hash_entri(e) != e["hash"]:
            return {"status": "rusak", "entri_rusak": e["id"],
                    "keterangan": f"Isi entri #{e['id']} tidak cocok dengan hash-nya (entri telah diubah)."}
        sebelumnya = e["hash"]
    return {"status": "utuh", "entri_rusak": None,
            "keterangan": f"Semua {len(entri)} entri tersambung dan isinya cocok dengan hash."}


def _entri(engine: Engine, dataset: str) -> list[dict]:
    k = Keputusan.__table__
    Keputusan.metadata.create_all(engine, tables=[k])
    with engine.connect() as conn:
        return [dict(x) for x in conn.execute(select(k).where(k.c.dataset_id == dataset).order_by(k.c.id)).mappings()]


@router.post("/keputusan", status_code=201)
def catat_keputusan(body: KeputusanMasuk, engine: Engine = Depends(ambil_engine)) -> dict[str, Any]:
    periksa_dataset(body.dataset)
    periksa_dataset_tulis(body.dataset)
    s = Skor.__table__
    with engine.connect() as conn:
        ada = conn.execute(select(s.c.rs_id).where(
            s.c.dataset_id == body.dataset, s.c.rs_id == body.rs_id, s.c.periode == body.periode)).first()
    if ada is None:
        raise HTTPException(status_code=404, detail=f"RS {body.rs_id} periode {body.periode} tidak ada di daftar periksa.")
    entri = _entri(engine, body.dataset)
    e = {
        "dataset_id": body.dataset, "rs_id": body.rs_id, "periode": body.periode, "keputusan": body.keputusan,
        "alasan": body.alasan, "petugas": body.petugas,
        "waktu": datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0),
        "prev_hash": entri[-1]["hash"] if entri else HASH_AWAL,
    }
    e["hash"] = hash_entri(e)
    with engine.begin() as conn:
        e["id"] = conn.execute(insert(Keputusan.__table__).values(**e)).inserted_primary_key[0]
    return {**e, "label_keputusan": LABEL_KEPUTUSAN[e["keputusan"]],
            "pesan": "Keputusan tercatat dan dirantai ke entri sebelumnya."}


@router.get("/audit")
def audit(dataset: str = Query("demo"), engine: Engine = Depends(ambil_engine)) -> dict[str, Any]:
    periksa_dataset(dataset)
    entri = _entri(engine, dataset)
    r = RumahSakit.__table__
    with engine.connect() as conn:
        nama = dict(conn.execute(select(r.c.id, r.c.nama_samaran).where(r.c.dataset_id == dataset)).all())
    for e in entri:
        e["label_keputusan"] = LABEL_KEPUTUSAN.get(e["keputusan"], e["keputusan"])
        e["nama_samaran"] = nama.get(e["rs_id"])
    return {"dataset": dataset, "rantai": periksa_rantai(entri), "entri": list(reversed(entri))}
