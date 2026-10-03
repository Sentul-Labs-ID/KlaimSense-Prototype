"""API dashboard petugas: daftar periksa dan detail rumah sakit (baca-saja)."""

from collections import Counter, defaultdict
from datetime import date, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import Engine, func, inspect, select

from sentinel.api.deps import DATASET_TAMPIL, ambil_engine, ambil_pengaturan, periksa_dataset
from sentinel.config import Settings
from sentinel.models.hasil import Skor, Temuan
from sentinel.models.keputusan import Keputusan
from sentinel.models.master import Kapasitas, RumahSakit
from sentinel.models.sensor import Perangkat, SensorAnomali, StatusMesinHarian
from sentinel.models.transaksi import Tagihan
from sentinel.parameter import muat_parameter

router = APIRouter(tags=["dashboard"])
URUTAN_PRIORITAS = {"tinggi": 0, "sedang": 1, "rendah": 2}


def _baris(conn, query) -> list[dict]:
    return [dict(x) for x in conn.execute(query).mappings()]


@router.get("/meta")
def meta(
    dataset: str = Query("demo"),
    engine: Engine = Depends(ambil_engine),
    pengaturan: Settings = Depends(ambil_pengaturan),
) -> dict[str, Any]:
    """Informasi untuk navigasi: dataset yang tersedia, periode, daftar RS, dan mode demo."""
    periksa_dataset(dataset)
    s, r = Skor.__table__, RumahSakit.__table__
    with engine.connect() as conn:
        periode = [x for (x,) in conn.execute(select(s.c.periode).where(s.c.dataset_id == dataset).distinct().order_by(s.c.periode))]
        rs = _baris(conn, select(r.c.id, r.c.nama_samaran, r.c.kelas, r.c.provinsi).where(r.c.dataset_id == dataset).order_by(r.c.id))
    return {
        "dataset": dataset,
        "dataset_tersedia": list(DATASET_TAMPIL),
        "dataset_dapat_diubah": dataset == "demo",
        "periode": periode,
        "rumah_sakit": rs,
        "mode_demo": bool(pengaturan.demo_mode),
    }


@router.get("/rs")
def daftar_rs(
    dataset: str = Query("demo"),
    periode: str | None = Query(None),
    prioritas: str | None = Query(None),
    engine: Engine = Depends(ambil_engine),
) -> dict[str, Any]:
    """Daftar periksa: RS-periode urut prioritas lalu skor."""
    periksa_dataset(dataset)
    if prioritas and prioritas not in URUTAN_PRIORITAS:
        raise HTTPException(status_code=422, detail="Prioritas harus tinggi, sedang, atau rendah.")
    s, r, t, tg = Skor.__table__, RumahSakit.__table__, Temuan.__table__, Tagihan.__table__
    with engine.connect() as conn:
        q = (
            select(s.c.rs_id, s.c.periode, s.c.skor, s.c.prioritas, s.c.alasan_prioritas,
                   r.c.nama_samaran, r.c.kelas, r.c.provinsi, r.c.punya_sensor)
            .join(r, r.c.id == s.c.rs_id)
            .where(s.c.dataset_id == dataset)
        )
        if periode:
            q = q.where(s.c.periode == periode)
        baris = _baris(conn, q)
        qt = select(t.c.rs_id, t.c.periode, t.c.aturan_id, func.count()).where(t.c.dataset_id == dataset)
        if periode:
            qt = qt.where(t.c.periode == periode)
        jumlah: dict[tuple, dict[str, int]] = defaultdict(dict)
        for rs_id, per, aturan, n in conn.execute(qt.group_by(t.c.rs_id, t.c.periode, t.c.aturan_id)):
            jumlah[(rs_id, per)][aturan] = n
        qn = select(func.count()).select_from(tg).where(tg.c.dataset_id == dataset)
        if periode:
            awal = date.fromisoformat(periode + "-01")
            akhir = (awal + timedelta(days=32)).replace(day=1)
            qn = qn.where(tg.c.tanggal >= awal, tg.c.tanggal < akhir)
        jumlah_tagihan = conn.execute(qn).scalar()

    for b in baris:
        b["temuan_per_aturan"] = dict(sorted(jumlah.get((b["rs_id"], b["periode"]), {}).items()))
        b["jumlah_temuan"] = sum(b["temuan_per_aturan"].values())
    ringkasan_prioritas = Counter(b["prioritas"] for b in baris)
    if prioritas:
        baris = [b for b in baris if b["prioritas"] == prioritas]
    baris.sort(key=lambda b: (URUTAN_PRIORITAS[b["prioritas"]], -b["skor"], b["nama_samaran"], b["periode"]))
    return {
        "dataset": dataset,
        "periode": periode,
        "ringkasan": {
            "jumlah_rs_periode": sum(ringkasan_prioritas.values()),
            "per_prioritas": {p: ringkasan_prioritas.get(p, 0) for p in URUTAN_PRIORITAS},
            "jumlah_tagihan_diperiksa": jumlah_tagihan,
        },
        "data": baris,
    }


@router.get("/rs/{rs_id}")
def detail_rs(
    rs_id: str,
    dataset: str = Query("demo"),
    periode: str | None = Query(None),
    engine: Engine = Depends(ambil_engine),
) -> dict[str, Any]:
    periksa_dataset(dataset)
    p = muat_parameter()
    s, r, k, t, tg = Skor.__table__, RumahSakit.__table__, Kapasitas.__table__, Temuan.__table__, Tagihan.__table__
    with engine.connect() as conn:
        rs = conn.execute(select(r).where(r.c.id == rs_id, r.c.dataset_id == dataset)).mappings().first()
        if rs is None:
            raise HTTPException(status_code=404, detail=f"Rumah sakit {rs_id} tidak ditemukan di dataset {dataset}.")
        kap = conn.execute(select(k).where(k.c.rs_id == rs_id)).mappings().one()
        skor_semua = _baris(conn, select(s).where(s.c.dataset_id == dataset, s.c.rs_id == rs_id).order_by(s.c.periode))
        if not skor_semua:
            raise HTTPException(status_code=404, detail="Skor rumah sakit ini belum dihitung.")
        if periode is None:
            periode = min(skor_semua, key=lambda x: (URUTAN_PRIORITAS[x["prioritas"]], -x["skor"], x["periode"]))["periode"]
        skor = next((x for x in skor_semua if x["periode"] == periode), None)
        if skor is None:
            raise HTTPException(status_code=404, detail=f"Tidak ada skor untuk periode {periode}.")
        awal = date.fromisoformat(periode + "-01")
        akhir = (awal + timedelta(days=32)).replace(day=1)
        temuan = _baris(conn, select(
            t.c.id, t.c.aturan_id, t.c.kategori, t.c.tanggal, t.c.layanan, t.c.nilai_teramati, t.c.batas, t.c.selisih,
            t.c.penjelasan, t.c.tagihan_ids,
        ).where(t.c.dataset_id == dataset, t.c.rs_id == rs_id, t.c.periode == periode).order_by(t.c.aturan_id, t.c.tanggal, t.c.id))
        harian_q = (
            select(tg.c.tanggal, tg.c.layanan, func.count())
            .where(tg.c.dataset_id == dataset, tg.c.rs_id == rs_id, tg.c.tanggal >= awal, tg.c.tanggal < akhir,
                   tg.c.layanan.in_(["fisioterapi", "hemodialisa"]))
            .group_by(tg.c.tanggal, tg.c.layanan)
        )
        hitung = {(tgl, lay): n for tgl, lay, n in conn.execute(harian_q)}
        ada = set(inspect(engine).get_table_names())
        perangkat, status, anomali, keputusan = [], [], [], []
        if "perangkat" in ada:
            perangkat = _baris(conn, select(Perangkat.device_id, Perangkat.mesin_id).where(
                Perangkat.rs_id == rs_id, Perangkat.dataset_id == dataset).order_by(Perangkat.mesin_id))
        if perangkat:
            h = StatusMesinHarian.__table__
            status = _baris(conn, select(h.c.mesin_id, h.c.tanggal, h.c.shift, h.c.menit_terapi, h.c.menit_standby,
                                         h.c.menit_mati, h.c.menit_tanpa_data)
                            .where(h.c.dataset_id == dataset, h.c.rs_id == rs_id, h.c.tanggal >= awal, h.c.tanggal < akhir)
                            .order_by(h.c.tanggal, h.c.mesin_id, h.c.shift))
            a = SensorAnomali.__table__
            anomali = _baris(conn, select(a.c.jenis, a.c.device_id, a.c.waktu, a.c.durasi_menit, a.c.keterangan)
                             .where(a.c.device_id.in_([x["device_id"] for x in perangkat]),
                                    a.c.waktu >= awal, a.c.waktu < akhir).order_by(a.c.waktu))
        if "keputusan" in ada:
            kp = Keputusan.__table__
            keputusan = _baris(conn, select(kp.c.id, kp.c.keputusan, kp.c.alasan, kp.c.petugas, kp.c.waktu, kp.c.hash)
                               .where(kp.c.dataset_id == dataset, kp.c.rs_id == rs_id, kp.c.periode == periode)
                               .order_by(kp.c.id))

    for x in temuan:
        x["jumlah_tagihan"] = len(x.pop("tagihan_ids") or [])
    kap_fisio = kap["jumlah_fisioterapis"] * p.kapasitas.fisioterapi_sesi_per_terapis_per_hari
    kap_hd = kap["jumlah_mesin_hd"] * kap["shift_hd_per_hari"]
    hari_temuan = defaultdict(set)
    for x in temuan:
        if x["tanggal"]:
            hari_temuan[x["tanggal"]].add(x["aturan_id"])
    harian = []
    tgl = awal
    while tgl < akhir:
        if any(d[0] == tgl for d in hitung) or tgl in hari_temuan:
            harian.append({
                "tanggal": tgl,
                "fisioterapi": hitung.get((tgl, "fisioterapi"), 0),
                "kapasitas_fisioterapi": kap_fisio,
                "hemodialisa": hitung.get((tgl, "hemodialisa"), 0),
                "kapasitas_hemodialisa": kap_hd if tgl.weekday() < kap["hari_operasional_hd"] else 0,
                "aturan_temuan": sorted(hari_temuan.get(tgl, [])),
            })
        tgl += timedelta(days=1)

    return {
        "dataset": dataset,
        "rumah_sakit": {k_: rs[k_] for k_ in ("id", "nama_samaran", "kelas", "provinsi", "kab_kota", "punya_sensor")},
        "kapasitas": {
            "jumlah_fisioterapis": kap["jumlah_fisioterapis"],
            "sesi_per_terapis": p.kapasitas.fisioterapi_sesi_per_terapis_per_hari,
            "kapasitas_fisioterapi_harian": kap_fisio,
            "jumlah_mesin_hd": kap["jumlah_mesin_hd"],
            "shift_hd_per_hari": kap["shift_hd_per_hari"],
            "kapasitas_hemodialisa_harian": kap_hd,
            "hari_operasional_hd": kap["hari_operasional_hd"],
            "durasi_sesi_hd_jam": p.kapasitas.hemodialisa_durasi_sesi_jam,
        },
        "periode": periode,
        "periode_tersedia": [
            {"periode": x["periode"], "skor": x["skor"], "prioritas": x["prioritas"]} for x in skor_semua
        ],
        "skor": {k_: skor[k_] for k_ in ("skor", "prioritas", "alasan_prioritas", "rincian_per_aturan",
                                           "versi_aturan", "hash_parameter")},
        "temuan": temuan,
        "harian": harian,
        "sensor": {
            "bersensor": bool(perangkat),
            "perangkat": perangkat,
            "status_harian": status,
            "anomali": anomali,
        },
        "keputusan": keputusan,
    }
