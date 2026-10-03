"""SERVER: menerima pesan perangkat, memverifikasi, menyimpan.

Server hanya mengenal pesan dan registri kunci publik. Pemeriksaan per pesan, berurutan:
1. Perangkat terdaftar dan aktif, identitas (rs_id, mesin_id) cocok dengan registri,
   tanda tangan Ed25519 sah                         -> bila gagal: TAMPER_SIG, pesan ditolak.
2. seq = seq terakhir + 1 dan prev_hash = hash pesan terakhir
                                                  -> bila gagal: TAMPER_CHAIN. Pesan ulangan
   (seq tidak maju atau waktu mundur) ditolak; pesan yang melompat maju tetap disimpan
   (tanda tangannya sah) dan rantai dilanjutkan dari pesan itu.
3. Jendela yang hilang di antara dua pesan > gap_maks_jendela
                                                  -> TAMPER_GAP (sensor dicabut/dimatikan).
Fungsi `ingest` yang sama dipakai endpoint POST /sensor/ingest dan simulasi massal.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from sqlalchemy import Engine, func, insert, select

from sentinel.models.sensor import Perangkat, SensorAnomali, StatusSensor
from sentinel.parameter import Parameter, muat_parameter
from sentinel.sensor import konfigurasi as k
from sentinel.sensor.protokol import FIELD_PESAN, HASH_AWAL, hash_pesan, kanonik

UKURAN_BATCH = 5_000


@dataclass
class Registri:
    dataset_id: str
    rs_id: str
    mesin_id: str
    kunci: Ed25519PublicKey
    aktif: bool


@dataclass
class Keadaan:
    seq: int
    hash: str
    window_start: datetime


@dataclass
class HasilIngest:
    diterima: list[dict] = field(default_factory=list)
    anomali: list[dict] = field(default_factory=list)
    ditolak: int = 0


def durasi(menit: int) -> str:
    jam, sisa = divmod(menit, 60)
    bagian = ([f"{jam} jam"] if jam else []) + ([f"{sisa} menit"] if sisa else [])
    return " ".join(bagian) or "0 menit"


def _anomali(jenis: str, device_id: str, waktu: datetime, keterangan: str, reg: Registri | None, durasi_menit=None):
    return {
        "dataset_id": reg.dataset_id if reg else None,
        "jenis": jenis,
        "device_id": device_id,
        "waktu": waktu,
        "durasi_menit": durasi_menit,
        "keterangan": keterangan,
    }


def periksa(
    daftar: list[dict],
    registri: dict[str, Registri],
    keadaan: dict[str, Keadaan],
    gap_maks_jendela: int,
    panjang_jendela: int,
) -> HasilIngest:
    """Verifikasi murni (tanpa basis data). `keadaan` diperbarui di tempat."""
    hasil = HasilIngest()
    langkah = timedelta(minutes=panjang_jendela)
    for item in daftar:
        pesan = item.get("pesan") or {}
        device_id = str(pesan.get("device_id", "?"))
        reg = registri.get(device_id)
        try:
            waktu = datetime.fromisoformat(pesan["window_start"])
            if any(f not in pesan for f in FIELD_PESAN):
                raise KeyError
        except (KeyError, TypeError, ValueError):
            hasil.anomali.append(_anomali("TAMPER_SIG", device_id, datetime.min, "Pesan tidak lengkap atau rusak.", reg))
            hasil.ditolak += 1
            continue

        alasan = None
        if reg is None or not reg.aktif:
            alasan = "perangkat tidak terdaftar atau tidak aktif"
        elif (pesan["rs_id"], pesan["mesin_id"]) != (reg.rs_id, reg.mesin_id):
            alasan = "identitas rumah sakit/mesin tidak cocok dengan registri"
        else:
            try:
                reg.kunci.verify(bytes.fromhex(item.get("tanda_tangan", "")), kanonik(pesan))
            except (InvalidSignature, ValueError):
                alasan = "tanda tangan tidak sah"
        if alasan:
            hasil.anomali.append(_anomali(
                "TAMPER_SIG", device_id, waktu, f"Pesan seq {pesan['seq']} ditolak: {alasan}.", reg,
            ))
            hasil.ditolak += 1
            continue

        st = keadaan.get(device_id)
        seq_lalu, hash_lalu = (st.seq, st.hash) if st else (0, HASH_AWAL)
        if pesan["seq"] <= seq_lalu or (st and waktu <= st.window_start):
            hasil.anomali.append(_anomali(
                "TAMPER_CHAIN", device_id, waktu,
                f"Pesan ulangan/tidak berurutan ditolak: seq {pesan['seq']} setelah seq {seq_lalu}.", reg,
            ))
            hasil.ditolak += 1
            continue
        if pesan["seq"] != seq_lalu + 1 or pesan["prev_hash"] != hash_lalu:
            masalah = (
                f"seq melompat dari {seq_lalu} ke {pesan['seq']}" if pesan["seq"] != seq_lalu + 1
                else "prev_hash tidak cocok dengan hash pesan sebelumnya"
            )
            hasil.anomali.append(_anomali("TAMPER_CHAIN", device_id, waktu, f"Rantai pesan putus: {masalah}.", reg))
        if st:
            hilang = round((waktu - st.window_start) / langkah) - 1
            if hilang > gap_maks_jendela:
                mulai = st.window_start + langkah
                menit = hilang * panjang_jendela
                hasil.anomali.append(_anomali(
                    "TAMPER_GAP", device_id, mulai,
                    f"Tidak ada data {durasi(menit)} ({hilang} jendela) dari "
                    f"{mulai:%Y-%m-%d %H:%M} sampai {waktu:%Y-%m-%d %H:%M}.", reg, durasi_menit=menit,
                ))

        h = hash_pesan(pesan)
        keadaan[device_id] = Keadaan(pesan["seq"], h, waktu)
        hasil.diterima.append({
            "dataset_id": reg.dataset_id,
            "device_id": device_id,
            "window_start": waktu,
            "status": pesan["status"],
            "confidence": float(pesan["confidence"]),
            "seq": pesan["seq"],
            "prev_hash": bytes.fromhex(pesan["prev_hash"]),
            "hash": bytes.fromhex(h),
            "tanda_tangan": bytes.fromhex(item["tanda_tangan"]),
            "versi_model": pesan["versi_model"],
        })
    return hasil


def muat_registri(engine: Engine, device_ids: list[str]) -> tuple[dict[str, Registri], dict[str, Keadaan]]:
    p, s = Perangkat.__table__, StatusSensor.__table__
    registri, keadaan = {}, {}
    with engine.connect() as conn:
        for baris in conn.execute(select(p).where(p.c.device_id.in_(device_ids))).mappings():
            registri[baris["device_id"]] = Registri(
                baris["dataset_id"], baris["rs_id"], baris["mesin_id"],
                Ed25519PublicKey.from_public_bytes(bytes.fromhex(baris["public_key"])), baris["aktif"],
            )
        terakhir = (
            select(s.c.device_id, func.max(s.c.seq).label("seq"))
            .where(s.c.device_id.in_(device_ids))
            .group_by(s.c.device_id)
            .subquery()
        )
        query = select(s.c.device_id, s.c.seq, s.c.hash, s.c.window_start).join(
            terakhir, (s.c.device_id == terakhir.c.device_id) & (s.c.seq == terakhir.c.seq)
        )
        for device_id, seq, h, ws in conn.execute(query):
            keadaan[device_id] = Keadaan(seq, bytes(h).hex(), ws)
    return registri, keadaan


def ingest(
    engine: Engine,
    daftar: list[dict],
    parameter: Parameter | None = None,
    panjang_jendela: int = k.PANJANG_JENDELA_DEFAULT,
) -> HasilIngest:
    """Verifikasi dan simpan satu pesan atau sekumpulan pesan (urut kirim)."""
    p = parameter or muat_parameter()
    device_ids = sorted({str((x.get("pesan") or {}).get("device_id", "?")) for x in daftar})
    registri, keadaan = muat_registri(engine, device_ids)
    hasil = periksa(daftar, registri, keadaan, p.sensor.gap_maks_jendela, panjang_jendela)
    with engine.begin() as conn:
        for i in range(0, len(hasil.diterima), UKURAN_BATCH):
            conn.execute(insert(StatusSensor.__table__), hasil.diterima[i : i + UKURAN_BATCH])
        if hasil.anomali:
            conn.execute(insert(SensorAnomali.__table__), hasil.anomali)
    return hasil
