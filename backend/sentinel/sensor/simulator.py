"""DUNIA FISIK: simulator arus listrik mesin hemodialisa.

Satu-satunya modul aplikasi yang boleh membaca `sesi_aktual` (kenyataan: kapan mesin
benar-benar dipakai). Keluarannya hanya larik arus per menit (yang "terbaca" sensor)
dan label kebenaran per menit (untuk melatih model dan memilih skenario gangguan).
Tagihan fiktif tidak punya sesi_aktual, sehingga mesinnya tidak menunjukkan pola terapi.
"""

import hashlib
from collections import defaultdict
from dataclasses import dataclass
from datetime import date

import numpy as np
from sqlalchemy import Engine, select

from sentinel.models.kenyataan import SesiAktual
from sentinel.models.master import Kapasitas, RumahSakit
from sentinel.sensor import konfigurasi as k

MATI, STANDBY, TERAPI = 0, 1, 2


@dataclass(frozen=True)
class Mesin:
    rs_id: str
    mesin_id: str
    hari_operasional_hd: int


def rng_untuk(seed: int, *kunci: str) -> np.random.Generator:
    """Generator acak yang hanya bergantung pada seed dan kunci (aman untuk proses paralel)."""
    bahan = ":".join([str(seed), *kunci]).encode()
    return np.random.default_rng(int.from_bytes(hashlib.sha256(bahan).digest()[:8], "big"))


# --------------------------------------------------------------- baca dunia


def daftar_mesin_bersensor(engine: Engine, dataset_id: str) -> list[Mesin]:
    rs, kap = RumahSakit.__table__, Kapasitas.__table__
    query = (
        select(rs.c.id, kap.c.jumlah_mesin_hd, kap.c.hari_operasional_hd)
        .join(kap, kap.c.rs_id == rs.c.id)
        .where(rs.c.dataset_id == dataset_id, rs.c.punya_sensor.is_(True))
        .order_by(rs.c.id)
    )
    with engine.connect() as conn:
        return [
            Mesin(rs_id, f"{rs_id}-HD{i + 1:02d}", hari)
            for rs_id, jumlah, hari in conn.execute(query)
            for i in range(jumlah)
        ]


def muat_sesi(engine: Engine, dataset_id: str, mesin: list[Mesin]) -> dict[str, list[tuple[date, int]]]:
    """mesin_id -> daftar (tanggal, shift) sesi hemodialisa yang benar-benar terjadi."""
    t = SesiAktual.__table__
    rs_ids = sorted({m.rs_id for m in mesin})
    query = (
        select(t.c.mesin_id, t.c.tanggal, t.c.shift)
        .where(t.c.dataset_id == dataset_id, t.c.layanan == "hemodialisa", t.c.rs_id.in_(rs_ids))
        .order_by(t.c.mesin_id, t.c.tanggal, t.c.shift)
    )
    hasil: dict[str, list[tuple[date, int]]] = defaultdict(list)
    with engine.connect() as conn:
        for mesin_id, tanggal, shift in conn.execute(query):
            hasil[mesin_id].append((tanggal, shift))
    return dict(hasil)


# ----------------------------------------------------------------- sinyal


def _segmen(rng, arus, label, awal, akhir, status):
    n = akhir - awal
    if n <= 0:
        return
    if status == MATI:
        arus[awal:akhir] = np.clip(rng.normal(*k.ARUS_MATI, n), 0, None)
    elif status == STANDBY:
        dasar = rng.uniform(*k.ARUS_STANDBY_DASAR)
        nilai = dasar + rng.normal(0, k.ARUS_STANDBY_NOISE, n)
        peluang, lo, hi = k.ARUS_STANDBY_PEMANAS
        lonjak = rng.random(n) < peluang
        nilai[lonjak] += rng.uniform(lo, hi, lonjak.sum())
        arus[awal:akhir] = np.clip(nilai, 0, None)
    else:
        dasar = rng.uniform(*k.ARUS_TERAPI_DASAR)
        amplitudo = rng.uniform(*k.ARUS_TERAPI_POMPA)
        periode = rng.uniform(*k.ARUS_TERAPI_PERIODE)
        fase = rng.uniform(0, 2 * np.pi)
        t = np.arange(n)
        nilai = dasar + amplitudo * np.sin(2 * np.pi * t / periode + fase) + rng.normal(0, k.ARUS_TERAPI_NOISE, n)
        peluang, lo, hi = k.ARUS_TERAPI_JEDA
        jeda = rng.random(n) < peluang
        nilai[jeda] -= rng.uniform(lo, hi, jeda.sum())
        arus[awal:akhir] = np.clip(nilai, 0, None)
    label[awal:akhir] = status


def sinyal_hari(rng, shift_terapi: set[int], beroperasi: bool, durasi_menit: int) -> tuple[np.ndarray, np.ndarray]:
    """Arus per menit (1440) dan label kebenaran untuk satu mesin satu hari."""
    arus = np.zeros(k.MENIT_SEHARI)
    label = np.zeros(k.MENIT_SEHARI, dtype=np.int8)
    # Malam / di luar slot shift.
    malam = STANDBY if rng.random() < k.PELUANG_STANDBY_MALAM else MATI
    _segmen(rng, arus, label, 0, k.MENIT_SEHARI, malam)
    if not beroperasi:
        return arus, label
    for shift, (mulai, selesai) in sorted(k.JADWAL_SHIFT.items()):
        if shift in shift_terapi:
            awal = mulai + int(rng.integers(*k.PERSIAPAN_MENIT, endpoint=True))
            durasi = int(round(durasi_menit + rng.normal(0, k.VARIASI_DURASI_MENIT)))
            akhir = min(selesai, awal + durasi)
            _segmen(rng, arus, label, mulai, awal, STANDBY)  # persiapan
            _segmen(rng, arus, label, awal, akhir, TERAPI)
            pasca = min(selesai, akhir + int(rng.integers(5, 15, endpoint=True)))
            _segmen(rng, arus, label, akhir, pasca, STANDBY)  # pembilasan
            _segmen(rng, arus, label, pasca, selesai, STANDBY if rng.random() < 0.5 else MATI)
        elif shift <= 3:
            kosong = STANDBY if rng.random() < k.PELUANG_STANDBY_SAAT_KOSONG else MATI
            _segmen(rng, arus, label, mulai, selesai, kosong)
    return arus, label


def sinyal_mesin(
    mesin: Mesin,
    sesi: list[tuple[date, int]],
    daftar_tanggal: list[date],
    durasi_menit: int,
    seed: int,
    kunci_acak: str | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Arus dan label per menit untuk seluruh periode (len(daftar_tanggal) x 1440).
    `kunci_acak` (default mesin_id) menentukan aliran acak; dataset kembar memakai kunci
    mesin kembarannya agar sinyalnya identik."""
    rng = rng_untuk(seed, kunci_acak or mesin.mesin_id)
    per_hari: dict[date, set[int]] = defaultdict(set)
    for tgl, shift in sesi:
        per_hari[tgl].add(shift)
    arus, label = [], []
    for tgl in daftar_tanggal:
        a, lbl = sinyal_hari(rng, per_hari.get(tgl, set()), tgl.weekday() < mesin.hari_operasional_hd, durasi_menit)
        arus.append(a)
        label.append(lbl)
    return np.concatenate(arus), np.concatenate(label)


def data_latih(seed: int, jumlah_hari: int, durasi_menit: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Mesin-hari simulasi dengan jadwal acak untuk melatih model edge.
    Kembalikan (arus [hari x 1440], label [hari x 1440], id_hari)."""
    rng = rng_untuk(seed, "latih")
    arus, label = [], []
    for _ in range(jumlah_hari):
        beroperasi = rng.random() < 0.9
        shift_terapi = {s for s in (1, 2, 3, 4) if rng.random() < (0.65 if s <= 3 else 0.1)}
        a, lbl = sinyal_hari(rng, shift_terapi, beroperasi, durasi_menit)
        arus.append(a)
        label.append(lbl)
    return np.stack(arus), np.stack(label), np.arange(jumlah_hari)
