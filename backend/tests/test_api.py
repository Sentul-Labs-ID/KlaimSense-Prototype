"""Tes API dashboard (fase 5) pada SQLite: daftar/detail RS, keputusan, audit, sisipan demo,
verifikasi sensor, batas akses respons, dan dataset utama/hidden/reports tidak berubah."""

import hashlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.pool import StaticPool

from sentinel.api.deps import ambil_engine, ambil_pengaturan
from sentinel.config import Settings
from sentinel.db import Base
from sentinel.generator.bangkit import bangkitkan
from sentinel.generator.simpan import simpan
from sentinel.main import app
from sentinel.models.evaluasi import JENIS_KASUS_SAH, PROFIL, SKENARIO
from sentinel.models.sensor import Perangkat, StatusSensor
from sentinel.rules.__main__ import main as main_rules
from sentinel.sensor.pipeline import jalankan_dataset

REPORTS = Path(__file__).resolve().parents[2] / "reports"
NILAI_TERLARANG = (set(SKENARIO) | set(JENIS_KASUS_SAH) | set(PROFIL)) - {"TAMPER_SIG", "TAMPER_GAP"}
KUNCI_TERLARANG = {"skenario", "profil", "ground_truth", "sesi_aktual", "kasus_sah", "profil_rs"}


@pytest.fixture(scope="module")
def engine():
    e = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    for ds in ("utama", "hidden", "demo"):
        simpan(e, bangkitkan(ds, hari=35, jumlah_rs=20))
    with e.connect() as conn:
        rs_sensor = conn.execute(text(
            "SELECT id FROM rumah_sakit WHERE dataset_id='demo' AND punya_sensor ORDER BY id LIMIT 1")).scalar()
    jalankan_dataset(e, "demo", jumlah_proses=1, rs_ids=[rs_sensor])
    for ds in ("utama", "hidden", "demo"):
        assert main_rules(["--dataset", ds], engine=e) == 0
    Base.metadata.create_all(e)
    yield e
    e.dispose()


@pytest.fixture
def klien(engine):
    app.dependency_overrides[ambil_engine] = lambda: engine
    app.dependency_overrides[ambil_pengaturan] = lambda: Settings(demo_mode=True, _env_file=None)
    yield TestClient(app)
    app.dependency_overrides.clear()


def periksa_respons_bersih(data, jalur="") -> None:
    """Tidak ada kolom atau nilai dari tabel evaluasi di respons API."""
    if isinstance(data, dict):
        for k, v in data.items():
            assert k not in KUNCI_TERLARANG, f"{jalur}.{k}"
            periksa_respons_bersih(v, f"{jalur}.{k}")
    elif isinstance(data, list):
        for i, v in enumerate(data):
            periksa_respons_bersih(v, f"{jalur}[{i}]")
    elif isinstance(data, str):
        assert data not in NILAI_TERLARANG, f"{jalur} = {data}"


def rs_rendah_tanpa_kap01(klien) -> tuple[str, str]:
    data = klien.get("/rs", params={"dataset": "demo"}).json()["data"]
    for b in data:
        if b["prioritas"] == "rendah" and "KAP-01" not in b["temuan_per_aturan"]:
            return b["rs_id"], b["periode"]
    raise AssertionError("tidak ada RS-periode rendah tanpa KAP-01")


# ------------------------------------------------------------- daftar/detail


def test_meta_dan_dataset_hidden_tidak_tersedia(klien):
    m = klien.get("/meta", params={"dataset": "demo"}).json()
    assert m["dataset_tersedia"] == ["demo", "utama"] and m["mode_demo"] is True and m["periode"]
    r = klien.get("/rs", params={"dataset": "hidden"})
    assert r.status_code == 404 and "tidak tersedia" in r.json()["detail"]


def test_daftar_rs_urut_prioritas_lalu_skor_dan_filter(klien):
    r = klien.get("/rs", params={"dataset": "demo"}).json()
    urutan = {"tinggi": 0, "sedang": 1, "rendah": 2}
    kunci = [(urutan[b["prioritas"]], -b["skor"]) for b in r["data"]]
    assert kunci == sorted(kunci)
    assert r["ringkasan"]["jumlah_rs_periode"] == len(r["data"]) == 40  # 20 RS x 2 bulan
    assert r["ringkasan"]["jumlah_tagihan_diperiksa"] > 0
    b = r["data"][0]
    assert {"nama_samaran", "kelas", "provinsi", "periode", "skor", "prioritas", "alasan_prioritas", "jumlah_temuan"} <= b.keys()
    per = klien.get("/rs", params={"dataset": "demo", "periode": "2026-07", "prioritas": "rendah"}).json()
    assert per["data"] and all(x["periode"] == "2026-07" and x["prioritas"] == "rendah" for x in per["data"])
    assert klien.get("/rs", params={"prioritas": "darurat"}).status_code == 422


def test_detail_rs(klien, engine):
    with engine.connect() as conn:
        rs_sensor = conn.execute(select(Perangkat.rs_id).limit(1)).scalar()
    d = klien.get(f"/rs/{rs_sensor}", params={"dataset": "demo"}).json()
    assert d["rumah_sakit"]["id"] == rs_sensor and d["periode"] in [x["periode"] for x in d["periode_tersedia"]]
    assert d["skor"]["rincian_per_aturan"]["KAP-01"]["bobot"] == 15
    assert d["harian"] and {"fisioterapi", "kapasitas_fisioterapi", "hemodialisa", "kapasitas_hemodialisa"} <= d["harian"][0].keys()
    assert d["sensor"]["bersensor"] and d["sensor"]["status_harian"]
    assert all("penjelasan" in t for t in d["temuan"])
    assert klien.get("/rs/RS-999", params={"dataset": "demo"}).status_code == 404


# --------------------------------------------------------- keputusan & audit


def test_keputusan_validasi_dan_hanya_dataset_demo(klien):
    rs_id, periode = rs_rendah_tanpa_kap01(klien)
    dasar = {"dataset": "demo", "rs_id": rs_id, "periode": periode, "keputusan": "setujui", "petugas": "Uji"}
    r = klien.post("/keputusan", json={**dasar, "alasan": "pendek"})
    assert r.status_code == 422 and "minimal 10 karakter" in r.json()["detail"]
    r = klien.post("/keputusan", json={**dasar, "alasan": "Alasan yang cukup panjang", "dataset": "utama"})
    assert r.status_code == 403 and "dataset demo" in r.json()["detail"]
    r = klien.post("/keputusan", json={**dasar, "alasan": "Alasan yang cukup panjang", "keputusan": "hapus"})
    assert r.status_code == 422 and "pilihan" in r.json()["detail"]


def test_keputusan_berantai_dan_audit_mendeteksi_perusakan(klien, engine):
    from sentinel.api.keputusan import HASH_AWAL, hash_entri

    rs_id, periode = rs_rendah_tanpa_kap01(klien)
    dasar = {"dataset": "demo", "rs_id": rs_id, "periode": periode, "petugas": "Petugas Uji"}
    awal = klien.get("/audit", params={"dataset": "demo"}).json()
    a = klien.post("/keputusan", json={**dasar, "keputusan": "minta_klarifikasi", "alasan": "Mohon penjelasan lonjakan sesi."})
    b = klien.post("/keputusan", json={**dasar, "keputusan": "rujuk_audit", "alasan": "Klarifikasi tidak memadai, rujuk."})
    assert a.status_code == b.status_code == 201
    a, b = a.json(), b.json()
    assert b["prev_hash"] == a["hash"]
    if not awal["entri"]:
        assert a["prev_hash"] == HASH_AWAL
    from datetime import datetime

    assert hash_entri({**b, "waktu": datetime.fromisoformat(b["waktu"]), "dataset_id": "demo"}) == b["hash"]
    audit = klien.get("/audit", params={"dataset": "demo"}).json()
    assert audit["rantai"]["status"] == "utuh"

    with engine.begin() as conn:
        conn.execute(text("UPDATE keputusan SET alasan = 'diubah diam-diam oleh orang dalam' WHERE id = :i"), {"i": a["id"]})
    rusak = klien.get("/audit", params={"dataset": "demo"}).json()["rantai"]
    assert rusak["status"] == "rusak" and rusak["entri_rusak"] == a["id"] and "diubah" in rusak["keterangan"]
    with engine.begin() as conn:  # kembalikan, lalu putus rantainya
        conn.execute(text("UPDATE keputusan SET alasan = 'Mohon penjelasan lonjakan sesi.' WHERE id = :i"), {"i": a["id"]})
        conn.execute(text("UPDATE keputusan SET prev_hash = :h WHERE id = :i"), {"h": "f" * 64, "i": b["id"]})
    putus = klien.get("/audit", params={"dataset": "demo"}).json()["rantai"]
    assert putus["status"] == "rusak" and putus["entri_rusak"] == b["id"] and "terputus" in putus["keterangan"]
    with engine.begin() as conn:
        conn.execute(text("UPDATE keputusan SET prev_hash = :h WHERE id = :i"), {"h": a["hash"], "i": b["id"]})


# ------------------------------------------------------------- sisipan demo


def test_sisipan_ditolak_bila_mode_demo_mati_atau_bukan_demo(klien):
    rs_id, periode = rs_rendah_tanpa_kap01(klien)
    body = {"rs_id": rs_id, "skenario": "KAP_FISIO", "jumlah_hari": 3, "periode": periode}
    app.dependency_overrides[ambil_pengaturan] = lambda: Settings(demo_mode=False, _env_file=None)
    r = klien.post("/demo/sisipkan", json=body)
    assert r.status_code == 403 and "Mode demo tidak aktif" in r.json()["detail"]
    app.dependency_overrides[ambil_pengaturan] = lambda: Settings(demo_mode=True, _env_file=None)
    r = klien.post("/demo/sisipkan", json={**body, "dataset": "utama"})
    assert r.status_code == 403
    assert klien.post("/demo/sisipkan", json={**body, "jumlah_hari": 9}).status_code == 422


def test_sisipan_kap_menaikkan_skor_dan_prioritas(klien):
    rs_id, periode = rs_rendah_tanpa_kap01(klien)
    r = klien.post("/demo/sisipkan", json={"rs_id": rs_id, "skenario": "KAP_FISIO", "jumlah_hari": 3, "periode": periode})
    assert r.status_code == 200, r.text
    hasil = r.json()
    (ubah,) = hasil["perubahan"]
    assert ubah["sesudah"]["skor"] > ubah["sebelum"]["skor"]
    assert ubah["sebelum"]["prioritas"] == "rendah" and ubah["sesudah"]["prioritas"] == "tinggi"
    assert "lantai: KAP-01 jenuh" in ubah["sesudah"]["alasan_prioritas"]
    assert hasil["tagihan_baru"] > 0 and len(hasil["tanggal"]) == 3
    periksa_respons_bersih(hasil)


# ------------------------------------------------------------ verifikasi sensor


def test_verifikasi_sensor_valid_lalu_rusak(klien, engine):
    with engine.connect() as conn:
        device_id = conn.execute(select(Perangkat.device_id).order_by(Perangkat.device_id).limit(1)).scalar()
    body = {"dataset": "demo", "device_id": device_id, "tanggal": "2026-07-15"}
    v = klien.post("/sensor/verifikasi", json=body).json()
    assert v["status"] == "utuh" and v["valid"] == v["jumlah_pesan"] > 100 and v["tanda_tangan_gagal"] == 0
    with engine.begin() as conn:
        sid = conn.execute(select(StatusSensor.id).where(
            StatusSensor.device_id == device_id, func.date(StatusSensor.window_start) == "2026-07-15",
            StatusSensor.status != "terapi").limit(1)).scalar()
        conn.execute(text("UPDATE status_sensor SET status = 'terapi' WHERE id = :i"), {"i": sid})
    r = klien.post("/sensor/verifikasi", json=body).json()
    assert r["status"] == "bermasalah" and r["tanda_tangan_gagal"] == 1 and r["rincian"]


# ------------------------------------------------ batas akses dan dataset aman


def test_respons_api_tanpa_kolom_tabel_evaluasi(klien, engine):
    with engine.connect() as conn:
        rs_sensor = conn.execute(select(Perangkat.rs_id).limit(1)).scalar()
    for url, params in [
        ("/meta", {"dataset": "demo"}), ("/rs", {"dataset": "demo"}), ("/rs", {"dataset": "utama"}),
        (f"/rs/{rs_sensor}", {"dataset": "demo"}), ("/audit", {"dataset": "demo"}),
    ]:
        r = klien.get(url, params=params)
        assert r.status_code == 200, url
        periksa_respons_bersih(r.json(), url)


def _jejak(engine) -> dict:
    hasil = {}
    with engine.connect() as conn:
        for nama, t in Base.metadata.tables.items():
            if "dataset_id" in t.c:
                for ds, n in conn.execute(select(t.c.dataset_id, func.count()).group_by(t.c.dataset_id)):
                    if ds in ("utama", "hidden"):
                        hasil[(nama, ds)] = n
        hasil["tagihan_utama_total"] = conn.execute(text("SELECT SUM(total) FROM tagihan WHERE dataset_id='utama'")).scalar()
    for f in sorted(REPORTS.glob("*")):
        if f.is_file():
            hasil[f.name] = hashlib.sha256(f.read_bytes()).hexdigest()
    return hasil


def test_alur_demo_tidak_mengubah_utama_hidden_dan_reports(klien, engine):
    sebelum = _jejak(engine)
    rs_id, periode = rs_rendah_tanpa_kap01(klien)
    klien.post("/demo/sisipkan", json={"rs_id": rs_id, "skenario": "HARGA_LEBIH", "jumlah_hari": 2, "periode": periode})
    klien.post("/demo/sisipkan", json={"rs_id": rs_id, "skenario": "KAP_HD", "jumlah_hari": 2, "periode": periode})
    klien.post("/keputusan", json={"dataset": "demo", "rs_id": rs_id, "periode": periode, "keputusan": "minta_klarifikasi",
                                   "alasan": "Mohon klarifikasi temuan ini.", "petugas": "Uji"})
    klien.get("/audit", params={"dataset": "demo"})
    assert _jejak(engine) == sebelum
