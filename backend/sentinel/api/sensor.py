"""SERVER: endpoint penerimaan pesan perangkat sensor dan verifikasi ulang pesan tersimpan."""

from datetime import date, datetime, timedelta
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import Engine, func, select

from sentinel.api.deps import ambil_engine, periksa_dataset
from sentinel.models.sensor import Perangkat, StatusSensor
from sentinel.sensor.ingest import ingest
from sentinel.sensor.protokol import HASH_AWAL, hash_pesan, kanonik

router = APIRouter(prefix="/sensor", tags=["sensor"])

__all__ = ["ambil_engine", "router"]


class PesanMasuk(BaseModel):
    pesan: dict[str, Any]
    tanda_tangan: str


class HasilIngestApi(BaseModel):
    diterima: int
    ditolak: int
    anomali: list[dict[str, Any]]


class PermintaanVerifikasi(BaseModel):
    dataset: str = "demo"
    device_id: str
    tanggal: date


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


@router.post("/verifikasi")
def verifikasi(body: PermintaanVerifikasi, engine: Engine = Depends(ambil_engine)) -> dict[str, Any]:
    """Verifikasi ulang tanda tangan dan rantai hash pesan tersimpan satu perangkat pada satu tanggal."""
    periksa_dataset(body.dataset)
    p, s = Perangkat.__table__, StatusSensor.__table__
    awal = datetime.combine(body.tanggal, datetime.min.time())
    akhir = awal + timedelta(days=1)
    with engine.connect() as conn:
        reg = conn.execute(select(p).where(p.c.device_id == body.device_id, p.c.dataset_id == body.dataset)).mappings().first()
        if reg is None:
            raise HTTPException(status_code=404, detail=f"Perangkat {body.device_id} tidak terdaftar di dataset {body.dataset}.")
        pesan = [dict(x) for x in conn.execute(
            select(s).where(s.c.device_id == body.device_id, s.c.window_start >= awal, s.c.window_start < akhir)
            .order_by(s.c.seq)).mappings()]
        sebelumnya = None
        if pesan:
            seq_lalu = conn.execute(select(func.max(s.c.seq)).where(
                s.c.device_id == body.device_id, s.c.seq < pesan[0]["seq"])).scalar()
            if seq_lalu is not None:
                sebelumnya = conn.execute(select(s.c.seq, s.c.hash).where(
                    s.c.device_id == body.device_id, s.c.seq == seq_lalu)).mappings().first()

    kunci = Ed25519PublicKey.from_public_bytes(bytes.fromhex(reg["public_key"]))
    seq_lalu, hash_lalu = (sebelumnya["seq"], bytes(sebelumnya["hash"]).hex()) if sebelumnya else (0, HASH_AWAL)
    valid = gagal = putus = 0
    masalah: list[str] = []
    for x in pesan:
        isi = {
            "device_id": x["device_id"], "rs_id": reg["rs_id"], "mesin_id": reg["mesin_id"],
            "window_start": x["window_start"].isoformat(timespec="minutes"), "status": x["status"],
            "confidence": x["confidence"], "seq": x["seq"], "prev_hash": bytes(x["prev_hash"]).hex(),
            "versi_model": x["versi_model"],
        }
        ok_ttd = True
        try:
            kunci.verify(bytes(x["tanda_tangan"]), kanonik(isi))
        except InvalidSignature:
            ok_ttd = False
        ok_hash = hash_pesan(isi) == bytes(x["hash"]).hex()
        ok_rantai = isi["prev_hash"] == hash_lalu and (sebelumnya is None and x is pesan[0] or x["seq"] == seq_lalu + 1)
        if not ok_ttd or not ok_hash:
            gagal += 1
            if len(masalah) < 5:
                masalah.append(f"Pesan seq {x['seq']} ({x['window_start']:%H:%M}): tanda tangan atau isi tidak cocok.")
        elif not ok_rantai:
            putus += 1
            if len(masalah) < 5:
                masalah.append(f"Pesan seq {x['seq']} ({x['window_start']:%H:%M}): tidak tersambung ke pesan sebelumnya.")
        else:
            valid += 1
        seq_lalu, hash_lalu = x["seq"], bytes(x["hash"]).hex()

    utuh = gagal == 0 and putus == 0 and bool(pesan)
    return {
        "device_id": body.device_id,
        "mesin_id": reg["mesin_id"],
        "tanggal": body.tanggal,
        "jumlah_pesan": len(pesan),
        "valid": valid,
        "rantai_putus": putus,
        "tanda_tangan_gagal": gagal,
        "status": "utuh" if utuh else ("tidak ada data" if not pesan else "bermasalah"),
        "keterangan": (
            f"Semua {len(pesan)} pesan bertanda tangan sah dan tersambung dalam rantai hash." if utuh
            else "Tidak ada pesan tersimpan untuk tanggal ini." if not pesan
            else f"{gagal} pesan gagal verifikasi tanda tangan/isi, {putus} pesan tidak tersambung."
        ),
        "rincian": masalah,
    }
