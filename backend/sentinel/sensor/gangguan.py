"""Skenario gangguan sensor (sisi "penyerang" dalam simulasi) dan pencatatan ground truth.

- TAMPER_SIG : satu perangkat "mengirim" beberapa pesan palsu berstatus terapi yang
               ditandatangani kunci yang salah (meniru upaya menutupi tagihan fiktif).
- TAMPER_GAP : satu perangkat dicabut ±2 jam di tengah sesi terapi pada satu shift.

Modul ini bagian dari harness simulasi: ia menulis kejadian ke tabel ground_truth
(hanya dibaca evaluasi). Ia tidak membaca kenyataan fisik secara langsung; posisi sesi
terapi diambil dari label yang dikeluarkan simulator.
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta

import numpy as np
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from sqlalchemy import Engine, delete, func, insert, select

from sentinel.models.evaluasi import GroundTruth
from sentinel.sensor import konfigurasi as k
from sentinel.sensor.protokol import kanonik
from sentinel.sensor.simulator import TERAPI

SKENARIO_SENSOR = ("TAMPER_SIG", "TAMPER_GAP")
JUMLAH_PESAN_PALSU = (3, 6)
MENIT_CABUT = (110, 130)  # ±2 jam


@dataclass(frozen=True)
class RencanaSig:
    device_id: str
    tanggal: date
    jumlah: int
    seed: int


@dataclass(frozen=True)
class RencanaGap:
    device_id: str
    tanggal: date
    shift: int
    seed: int


def topeng_cabut(label: np.ndarray, daftar_tanggal: list[date], rencana: RencanaGap, panjang_jendela: int):
    """Tentukan jendela yang hilang karena sensor dicabut ±2 jam di tengah sesi terapi.
    Kembalikan (topeng_aktif per jendela, mulai, selesai) atau None bila tidak ada terapi."""
    rng = np.random.default_rng(rencana.seed)
    hari = daftar_tanggal.index(rencana.tanggal)
    mulai_slot, selesai_slot = k.JADWAL_SHIFT[rencana.shift]
    potong = label[hari * k.MENIT_SEHARI + mulai_slot : hari * k.MENIT_SEHARI + selesai_slot]
    terapi = np.flatnonzero(potong == TERAPI)
    if len(terapi) < 180:
        return None
    awal_menit = mulai_slot + int(terapi[0]) + int(rng.integers(50, 70))
    lama = int(rng.integers(*MENIT_CABUT, endpoint=True))
    jendela_awal = (hari * k.MENIT_SEHARI + awal_menit) // panjang_jendela
    jendela_akhir = -(-(hari * k.MENIT_SEHARI + awal_menit + lama) // panjang_jendela)
    aktif = np.ones(len(label) // panjang_jendela, dtype=bool)
    aktif[jendela_awal:jendela_akhir] = False
    t0 = datetime.combine(daftar_tanggal[0], datetime.min.time())
    return aktif, t0 + timedelta(minutes=jendela_awal * panjang_jendela), t0 + timedelta(minutes=jendela_akhir * panjang_jendela)


def sisipkan_pesan_palsu(pesan: list[dict], rencana: RencanaSig) -> tuple[list[dict], list[str]]:
    """Sisipkan pesan palsu (status terapi, tanda tangan kunci penyerang) setelah beberapa
    pesan asli pada tanggal rencana. Kembalikan (aliran pesan baru, waktu jendela palsu)."""
    rng = np.random.default_rng(rencana.seed)
    kunci_penyerang = Ed25519PrivateKey.from_private_bytes(rng.bytes(32))
    indeks = [i for i, x in enumerate(pesan) if x["pesan"]["window_start"].startswith(rencana.tanggal.isoformat())]
    if not indeks:
        return pesan, []
    pilih = set(rng.choice(indeks, size=min(rencana.jumlah, len(indeks)), replace=False).tolist())
    keluar, waktu = [], []
    for i, x in enumerate(pesan):
        keluar.append(x)
        if i in pilih:
            palsu = {**x["pesan"], "status": "terapi", "confidence": 0.99}
            keluar.append({"pesan": palsu, "tanda_tangan": kunci_penyerang.sign(kanonik(palsu)).hex()})
            waktu.append(palsu["window_start"])
    return keluar, sorted(waktu)


def hapus_kejadian_lama(engine: Engine, dataset_id: str) -> None:
    t = GroundTruth.__table__
    with engine.begin() as conn:
        conn.execute(delete(t).where(t.c.dataset_id == dataset_id, t.c.skenario.in_(SKENARIO_SENSOR)))


def catat_kejadian(engine: Engine, dataset_id: str, kejadian: list[dict]) -> None:
    """kejadian: dict(skenario, rs_id, tanggal, keterangan). Tidak merujuk tagihan."""
    if not kejadian:
        return
    t = GroundTruth.__table__
    with engine.begin() as conn:
        id_terakhir = conn.execute(select(func.max(t.c.id)).where(t.c.dataset_id == dataset_id)).scalar() or 0
        conn.execute(insert(t), [
            {"id": id_terakhir + i + 1, "dataset_id": dataset_id, "tagihan_ids": [], **x}
            for i, x in enumerate(sorted(kejadian, key=lambda x: (x["tanggal"], x["skenario"])))
        ])
