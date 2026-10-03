"""Harness simulasi: dunia fisik -> perangkat -> server, untuk satu dataset.

Setiap perangkat diproses mandiri (rantai pesannya independen), sehingga bisa paralel:
  simulator.sinyal_mesin (DUNIA) -> edge.Perangkat.proses (PERANGKAT)
  -> ingest + ringkas_perangkat (SERVER).
Ketiga sisi hanya bertukar data lewat larik arus (dunia -> perangkat) dan pesan
bertanda tangan (perangkat -> server).
"""

import os
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from multiprocessing import get_context

import numpy as np
from sqlalchemy import Engine, create_engine, delete, func, insert, select

from sentinel.db import Base
from sentinel.models.sensor import Perangkat as TabelPerangkat
from sentinel.models.sensor import SensorAnomali, StatusMesinHarian, StatusSensor
from sentinel.models.transaksi import Tagihan
from sentinel.parameter import muat_parameter
from sentinel.sensor import gangguan
from sentinel.sensor import konfigurasi as k
from sentinel.sensor import simulator
from sentinel.sensor.edge import Perangkat, kunci_simulasi, muat_model
from sentinel.sensor.ingest import durasi, ingest
from sentinel.sensor.ringkasan import ringkas_perangkat, simpan_ringkasan

TABEL_SENSOR = (StatusMesinHarian, SensorAnomali, StatusSensor, TabelPerangkat)


@dataclass(frozen=True)
class Tugas:
    dataset_id: str
    mesin: simulator.Mesin
    sesi: tuple[tuple[date, int], ...]
    daftar_tanggal: tuple[date, ...]
    durasi_menit: int
    seed: int
    panjang_jendela: int
    rencana_sig: gangguan.RencanaSig | None = None
    rencana_gap: gangguan.RencanaGap | None = None
    kunci_acak: str | None = None  # untuk dataset kembar

    @property
    def device_id(self) -> str:
        return f"DEV-{self.mesin.mesin_id}"


@dataclass
class HasilDataset:
    dataset_id: str
    perangkat: int = 0
    pesan: int = 0
    diterima: int = 0
    ditolak: int = 0
    anomali: Counter = field(default_factory=Counter)
    kejadian: list[dict] = field(default_factory=list)
    detik: float = 0.0


# --------------------------------------------------------------- pekerja

_ENGINE: Engine | None = None


def _siapkan_pekerja(url: str) -> None:
    global _ENGINE
    _ENGINE = create_engine(url, pool_size=1, max_overflow=0)


def kerjakan(tugas: Tugas, engine: Engine | None = None) -> dict:
    engine = engine or _ENGINE
    p = muat_parameter()
    model = muat_model()
    m = tugas.mesin
    daftar_tanggal = list(tugas.daftar_tanggal)

    # DUNIA: arus per menit dari sesi yang benar-benar terjadi.
    arus, label = simulator.sinyal_mesin(
        m, list(tugas.sesi), daftar_tanggal, tugas.durasi_menit, tugas.seed, tugas.kunci_acak
    )
    n_jendela = len(arus) // tugas.panjang_jendela
    rng = simulator.rng_untuk(tugas.seed, tugas.kunci_acak or m.mesin_id, "kedip")
    aktif = rng.random(n_jendela) >= k.PELUANG_JENDELA_HILANG  # kedip listrik alami
    kejadian = []
    if tugas.rencana_gap:
        cabut = gangguan.topeng_cabut(label, daftar_tanggal, tugas.rencana_gap, tugas.panjang_jendela)
        if cabut:
            topeng, mulai, selesai = cabut
            aktif &= topeng
            menit = int((selesai - mulai).total_seconds() // 60)
            kejadian.append({
                "skenario": "TAMPER_GAP", "rs_id": m.rs_id, "tanggal": tugas.rencana_gap.tanggal,
                "keterangan": f"Perangkat {tugas.device_id} dicabut {mulai:%H:%M}-{selesai:%H:%M} "
                              f"({durasi(menit)}) di tengah sesi terapi shift {tugas.rencana_gap.shift}.",
            })

    # PERANGKAT: klasifikasi, tanda tangan, rantai hash.
    perangkat = Perangkat(tugas.device_id, m.rs_id, m.mesin_id, kunci_simulasi(tugas.device_id, tugas.seed), model)
    t0 = datetime.combine(daftar_tanggal[0], datetime.min.time())
    pesan = perangkat.proses(arus, t0, aktif)
    if tugas.rencana_sig:
        pesan, waktu_palsu = gangguan.sisipkan_pesan_palsu(pesan, tugas.rencana_sig)
        if waktu_palsu:
            kejadian.append({
                "skenario": "TAMPER_SIG", "rs_id": m.rs_id, "tanggal": tugas.rencana_sig.tanggal,
                "keterangan": f"Perangkat {tugas.device_id}: {len(waktu_palsu)} pesan palsu berstatus terapi "
                              f"dengan tanda tangan tidak sah pada jendela "
                              f"{', '.join(w[11:16] for w in waktu_palsu)}.",
            })

    # SERVER: verifikasi, simpan, ringkas.
    hasil = ingest(engine, pesan, p, tugas.panjang_jendela)
    ringkas = ringkas_perangkat(hasil.diterima, tugas.dataset_id, m.rs_id, m.mesin_id, daftar_tanggal, tugas.panjang_jendela)
    simpan_ringkasan(engine, ringkas)
    return {
        "pesan": len(pesan),
        "diterima": len(hasil.diterima),
        "ditolak": hasil.ditolak,
        "anomali": Counter(a["jenis"] for a in hasil.anomali),
        "kejadian": kejadian,
    }


# ------------------------------------------------------------ orkestrasi


def hapus_data_sensor(engine: Engine, dataset_id: str) -> None:
    Base.metadata.create_all(engine, tables=[t.__table__ for t in TABEL_SENSOR])
    with engine.begin() as conn:
        for t in TABEL_SENSOR:
            conn.execute(delete(t.__table__).where(t.__table__.c.dataset_id == dataset_id))
    gangguan.hapus_kejadian_lama(engine, dataset_id)


def rentang_tanggal(engine: Engine, dataset_id: str) -> list[date]:
    t = Tagihan.__table__
    with engine.connect() as conn:
        awal, akhir = conn.execute(select(func.min(t.c.tanggal), func.max(t.c.tanggal)).where(t.c.dataset_id == dataset_id)).one()
    if awal is None:
        return []
    return [awal + timedelta(days=i) for i in range((akhir - awal).days + 1)]


def daftarkan_perangkat(engine: Engine, dataset_id: str, mesin: list[simulator.Mesin], seed: int) -> None:
    from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

    baris = []
    for m in mesin:
        device_id = f"DEV-{m.mesin_id}"
        publik = kunci_simulasi(device_id, seed).public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
        baris.append({
            "device_id": device_id, "dataset_id": dataset_id, "rs_id": m.rs_id,
            "mesin_id": m.mesin_id, "public_key": publik.hex(), "aktif": True,
        })
    with engine.begin() as conn:
        conn.execute(insert(TabelPerangkat.__table__), baris)


def rencanakan_gangguan(
    mesin: list[simulator.Mesin], sesi: dict, daftar_tanggal: list[date], seed: int
) -> tuple[gangguan.RencanaSig, gangguan.RencanaGap | None]:
    rng = np.random.default_rng(seed)
    m_sig = mesin[int(rng.integers(len(mesin)))]
    sig = gangguan.RencanaSig(
        f"DEV-{m_sig.mesin_id}", daftar_tanggal[int(rng.integers(len(daftar_tanggal)))],
        int(rng.integers(*gangguan.JUMLAH_PESAN_PALSU, endpoint=True)), seed + 1,
    )
    calon = [
        (m, tgl, shift) for m in mesin for tgl, shift in sesi.get(m.mesin_id, ())
        if shift in (1, 2, 3) and f"DEV-{m.mesin_id}" != sig.device_id and tgl in set(daftar_tanggal)
    ]
    if not calon:
        return sig, None
    m_gap, tgl, shift = calon[int(rng.integers(len(calon)))]
    return sig, gangguan.RencanaGap(f"DEV-{m_gap.mesin_id}", tgl, shift, seed + 2)


def jalankan_dataset(
    engine: Engine,
    dataset_id: str,
    jumlah_proses: int = 1,
    panjang_jendela: int = k.PANJANG_JENDELA_DEFAULT,
    seed: int | None = None,
    rs_ids: list[str] | None = None,
) -> HasilDataset:
    import time

    t_mulai = time.perf_counter()
    seed = k.SEED_SENSOR.get(dataset_id, 1) if seed is None else seed
    p = muat_parameter()
    model = muat_model()
    if model.panjang_jendela != panjang_jendela:
        raise ValueError(
            f"model dilatih untuk jendela {model.panjang_jendela} menit, diminta {panjang_jendela}; latih ulang dulu"
        )
    hapus_data_sensor(engine, dataset_id)
    daftar_tanggal = rentang_tanggal(engine, dataset_id)
    mesin = simulator.daftar_mesin_bersensor(engine, dataset_id)
    if rs_ids is not None:
        mesin = [m for m in mesin if m.rs_id in rs_ids]
    hasil = HasilDataset(dataset_id, perangkat=len(mesin))
    if not mesin or not daftar_tanggal:
        return hasil
    sesi = simulator.muat_sesi(engine, dataset_id, mesin)
    daftarkan_perangkat(engine, dataset_id, mesin, seed)
    sig, gap = rencanakan_gangguan(mesin, sesi, daftar_tanggal, seed)
    durasi_menit = round(p.kapasitas.hemodialisa_durasi_sesi_jam * 60)
    tugas = [
        Tugas(
            dataset_id, m, tuple(sesi.get(m.mesin_id, ())), tuple(daftar_tanggal), durasi_menit, seed, panjang_jendela,
            sig if sig.device_id == f"DEV-{m.mesin_id}" else None,
            gap if gap and gap.device_id == f"DEV-{m.mesin_id}" else None,
            kunci_kembar(m.mesin_id, dataset_id),
        )
        for m in mesin
    ]

    if jumlah_proses <= 1:
        keluaran = [kerjakan(t, engine) for t in tugas]
    else:
        with ProcessPoolExecutor(
            max_workers=jumlah_proses, mp_context=get_context("spawn"),
            initializer=_siapkan_pekerja, initargs=(engine.url.render_as_string(hide_password=False),),
        ) as pool:
            keluaran = list(pool.map(kerjakan, tugas, chunksize=1))

    for x in keluaran:
        hasil.pesan += x["pesan"]
        hasil.diterima += x["diterima"]
        hasil.ditolak += x["ditolak"]
        hasil.anomali.update(x["anomali"])
        hasil.kejadian += x["kejadian"]
    gangguan.catat_kejadian(engine, dataset_id, hasil.kejadian)
    hasil.detik = time.perf_counter() - t_mulai
    return hasil


def kunci_kembar(mesin_id: str, dataset_id: str) -> str | None:
    """Untuk dataset kembar (demo): ID mesin padanannya di dataset asal, mis. RS-903-HD02 -> RS-003-HD02."""
    from sentinel.generator.profil import PROFIL

    profil = PROFIL.get(dataset_id)
    if profil is None or profil.kembar_dari is None:
        return None
    asal = PROFIL[profil.kembar_dari]
    _, nomor, mesin = mesin_id.split("-")
    return f"RS-{int(nomor) - profil.offset_rs + asal.offset_rs:03d}-{mesin}"


def jumlah_proses_default() -> int:
    return max(1, min(16, os.cpu_count() or 1))

