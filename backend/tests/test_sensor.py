"""Tes sensor IoT dan edge AI (fase 3): simulator, model edge, integritas pesan, ringkasan."""

import hashlib
import json
import shutil
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, insert, select
from sqlalchemy.pool import StaticPool

from sentinel.api.sensor import ambil_engine
from sentinel.db import Base
from sentinel.main import app
from sentinel.models.sensor import Perangkat as TabelPerangkat
from sentinel.models.sensor import SensorAnomali, StatusSensor
from sentinel.parameter import muat_parameter
from sentinel.sensor import konfigurasi as k
from sentinel.sensor.edge import Perangkat, fitur, klasifikasi, kunci_simulasi, label_jendela, muat_model, path_model
from sentinel.sensor.ingest import ingest
from sentinel.sensor.latih import latih, lingkungan
from sentinel.sensor.protokol import kanonik
from sentinel.sensor.ringkasan import ringkas_perangkat, slot_shift
from sentinel.sensor.simulator import MATI, STANDBY, TERAPI, Mesin, rng_untuk, sinyal_hari, sinyal_mesin

PARAM = muat_parameter()
MODEL = muat_model()
DURASI = round(PARAM.kapasitas.hemodialisa_durasi_sesi_jam * 60)
HARI = date(2026, 8, 5)
SEED = 99
DEVICE = "DEV-RS-001-HD01"


# ------------------------------------------------------------ simulator


def test_simulator_terapi_hanya_pada_shift_bersesi():
    arus, label = sinyal_hari(rng_untuk(1, "a"), {1}, True, DURASI)
    mulai, selesai = k.JADWAL_SHIFT[1]
    assert set(np.flatnonzero(label == TERAPI)) <= set(range(mulai, selesai))
    assert abs((label == TERAPI).sum() - DURASI) <= 30
    assert arus[label == TERAPI].mean() > arus[label == STANDBY].mean() > arus[label == MATI].mean()


def test_simulator_tanpa_sesi_tidak_ada_terapi():
    _, label = sinyal_hari(rng_untuk(1, "b"), set(), True, DURASI)
    assert (label == TERAPI).sum() == 0
    _, label = sinyal_hari(rng_untuk(1, "c"), {1, 2}, False, DURASI)  # unit tutup
    assert (label == TERAPI).sum() == 0


def test_simulator_deterministik():
    m = Mesin("RS-001", "RS-001-HD01", 6)
    a1, l1 = sinyal_mesin(m, [(HARI, 2)], [HARI], DURASI, SEED)
    a2, l2 = sinyal_mesin(m, [(HARI, 2)], [HARI], DURASI, SEED)
    assert np.array_equal(a1, a2) and np.array_equal(l1, l2)


# ----------------------------------------------------------- model edge


def jendela(nilai) -> np.ndarray:
    return np.asarray(nilai, dtype=float)


@pytest.mark.parametrize(
    "arus, status",
    [
        (jendela([0.02, 0.03, 0.04, 0.03, 0.02, 0.03, 0.05, 0.03, 0.02, 0.03]), "mati"),
        (jendela([1.0, 1.05, 0.98, 1.02, 1.0, 0.97, 1.03, 1.01, 0.99, 1.0]), "standby"),
        (jendela(2.0 + 0.3 * np.sin(2 * np.pi * np.arange(10) / 4)), "terapi"),
    ],
)
def test_klasifikasi_contoh_khas(arus, status):
    kode, keyakinan = klasifikasi(MODEL, arus)
    assert k.STATUS[kode[0]] == status
    assert 0 < keyakinan[0] <= 1


def test_model_dan_hash_konsisten(tmp_path):
    isi = path_model().read_bytes()
    assert MODEL.sha256 == hashlib.sha256(isi).hexdigest()
    meta = json.loads(path_model().with_suffix(".json").read_text(encoding="utf-8"))
    assert meta["sha256"] == MODEL.sha256 and MODEL.versi == MODEL.sha256[:12]
    # File model yang diubah satu byte ditolak.
    for akhiran in (".pkl", ".sha256"):
        shutil.copy(path_model().with_suffix(akhiran), tmp_path / f"{k.NAMA_MODEL.split('.')[0]}{akhiran}")
    rusak = tmp_path / k.NAMA_MODEL
    data = bytearray(rusak.read_bytes())
    data[-5] ^= 0xFF
    rusak.write_bytes(bytes(data))
    with pytest.raises(ValueError, match="hash model"):
        muat_model(rusak)


def test_model_tersimpan_bisa_direproduksi_dari_seed_latih():
    pohon, metrik = latih()
    # Struktur pohon hasil latih ulang identik dengan model tersimpan.
    for atribut in ("children_left", "children_right", "feature", "threshold", "value"):
        assert np.array_equal(getattr(pohon.tree_, atribut), getattr(MODEL.pohon.tree_, atribut)), atribut
    # Hash file juga identik bila dilatih ulang di proses baru dengan lingkungan yang sama
    # (byte pickle bergantung pada versi Python/numpy dan keadaan proses).
    meta = json.loads(path_model().with_suffix(".json").read_text(encoding="utf-8"))
    if meta["lingkungan"] != lingkungan():
        return
    kode = (
        "import hashlib, pickle; from sentinel.sensor.latih import latih; p, _ = latih(); "
        "print(hashlib.sha256(pickle.dumps({'pohon': p, 'panjang_jendela': 10}, protocol=5)).hexdigest())"
    )
    keluaran = subprocess.run([sys.executable, "-c", kode], capture_output=True, text=True, check=True,
                              cwd=Path(__file__).resolve().parents[1])
    assert keluaran.stdout.strip() == MODEL.sha256
    # Akurasi realistis: tinggi, tetapi tidak sempurna.
    assert 0.9 <= metrik["akurasi_uji"] < 0.995
    assert metrik["seed_latih"] not in (42, 2026, *k.SEED_SENSOR.values())


def test_label_jendela_mayoritas():
    label = np.array([TERAPI] * 6 + [STANDBY] * 4)
    assert label_jendela(label, 10).tolist() == [TERAPI]
    assert fitur(np.ones(25), 10).shape == (2, 4)


# ------------------------------------------------------- integritas pesan


@pytest.fixture
def engine():
    e = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(e)
    publik = kunci_simulasi(DEVICE, SEED).public_key().public_bytes_raw().hex()
    with e.begin() as conn:
        conn.execute(insert(TabelPerangkat.__table__), [{
            "device_id": DEVICE, "dataset_id": "uji", "rs_id": "RS-001", "mesin_id": "RS-001-HD01",
            "public_key": publik, "aktif": True,
        }])
    yield e
    e.dispose()


def pesan_satu_hari(aktif=None) -> list[dict]:
    m = Mesin("RS-001", "RS-001-HD01", 6)
    arus, _ = sinyal_mesin(m, [(HARI, 1), (HARI, 3)], [HARI], DURASI, SEED)
    perangkat = Perangkat(DEVICE, "RS-001", "RS-001-HD01", kunci_simulasi(DEVICE, SEED), MODEL)
    return perangkat.proses(arus, datetime(2026, 8, 5), aktif)


def jumlah(engine, model) -> int:
    with engine.connect() as conn:
        return conn.execute(select(func.count()).select_from(model)).scalar()


def test_pesan_sah_diterima(engine):
    pesan = pesan_satu_hari()
    hasil = ingest(engine, pesan, PARAM)
    assert len(hasil.diterima) == 144 and hasil.anomali == [] and hasil.ditolak == 0
    assert jumlah(engine, StatusSensor) == 144
    assert "arus" not in pesan[0]["pesan"]  # hanya ringkasan status, bukan sinyal mentah


def test_tanda_tangan_palsu_ditolak(engine):
    pesan = pesan_satu_hari()
    palsu = {**pesan[40], "pesan": {**pesan[40]["pesan"], "status": "terapi", "confidence": 0.99}}
    pesan.insert(41, palsu)  # disisipkan di samping pesan asli
    hasil = ingest(engine, pesan, PARAM)
    assert [a["jenis"] for a in hasil.anomali] == ["TAMPER_SIG"]
    assert hasil.ditolak == 1 and len(hasil.diterima) == 144  # semua pesan asli tetap diterima
    assert jumlah(engine, SensorAnomali) == 1


def test_kunci_salah_dan_perangkat_tak_dikenal_ditolak(engine):
    asli = pesan_satu_hari()[:3]
    salah_kunci = {**asli[1], "tanda_tangan": kunci_simulasi(DEVICE, SEED + 1).sign(kanonik(asli[1]["pesan"])).hex()}
    asing = {**asli[2], "pesan": {**asli[2]["pesan"], "device_id": "DEV-ASING"}}
    hasil = ingest(engine, [asli[0], salah_kunci, asing], PARAM)
    assert [a["jenis"] for a in hasil.anomali] == ["TAMPER_SIG", "TAMPER_SIG"]
    assert "tidak terdaftar" in hasil.anomali[1]["keterangan"]


def test_seq_lompat_terdeteksi(engine):
    pesan = pesan_satu_hari()
    del pesan[50]  # pesan hilang di tengah rantai
    hasil = ingest(engine, pesan, PARAM)
    assert [a["jenis"] for a in hasil.anomali] == ["TAMPER_CHAIN"]
    assert "seq melompat dari 50 ke 52" in hasil.anomali[0]["keterangan"]


def test_rantai_putus_prev_hash_terdeteksi(engine):
    pesan = pesan_satu_hari()
    kunci = kunci_simulasi(DEVICE, SEED)
    ubah = {**pesan[60]["pesan"], "prev_hash": "f" * 64}
    pesan[60] = {"pesan": ubah, "tanda_tangan": kunci.sign(kanonik(ubah)).hex()}  # tanda tangan sah, rantai salah
    hasil = ingest(engine, pesan, PARAM)
    jenis = [a["jenis"] for a in hasil.anomali]
    assert "TAMPER_CHAIN" in jenis and "TAMPER_SIG" not in jenis
    assert any("prev_hash" in a["keterangan"] for a in hasil.anomali)


def test_pesan_ulangan_ditolak(engine):
    pesan = pesan_satu_hari()
    hasil = ingest(engine, pesan + [pesan[10]], PARAM)
    assert [a["jenis"] for a in hasil.anomali] == ["TAMPER_CHAIN"] and hasil.ditolak == 1


@pytest.mark.parametrize("hilang, gap", [(5, True), (3, False)])
def test_gap_heartbeat(engine, hilang, gap):
    aktif = np.ones(144, dtype=bool)
    aktif[60 : 60 + hilang] = False  # perangkat tidak mengirim (seq tidak bertambah)
    hasil = ingest(engine, pesan_satu_hari(aktif), PARAM)
    jenis = [a["jenis"] for a in hasil.anomali]
    assert jenis == (["TAMPER_GAP"] if gap else [])
    if gap:
        assert hasil.anomali[0]["durasi_menit"] == hilang * 10
        assert hasil.anomali[0]["waktu"] == datetime(2026, 8, 5, 10, 0)


def test_ingest_bertahap_melanjutkan_rantai_dari_database(engine):
    pesan = pesan_satu_hari()
    assert ingest(engine, pesan[:70], PARAM).anomali == []
    hasil = ingest(engine, pesan[70:], PARAM)
    assert hasil.anomali == [] and jumlah(engine, StatusSensor) == 144


def test_endpoint_ingest_satu_dan_batch(engine):
    app.dependency_overrides[ambil_engine] = lambda: engine
    try:
        klien = TestClient(app)
        pesan = pesan_satu_hari()
        r = klien.post("/sensor/ingest", json=pesan[0])
        assert r.status_code == 200 and r.json() == {"diterima": 1, "ditolak": 0, "anomali": []}
        palsu = {**pesan[2], "pesan": {**pesan[2]["pesan"], "status": "terapi"}}
        r = klien.post("/sensor/ingest", json=[pesan[1], palsu])
        assert r.json()["diterima"] == 1 and r.json()["anomali"][0]["jenis"] == "TAMPER_SIG"
    finally:
        app.dependency_overrides.clear()


# --------------------------------------------------------------- ringkasan


def test_ringkasan_harian_menit_lengkap_dan_tanpa_data():
    aktif = np.ones(144, dtype=bool)
    aktif[60:66] = False  # 60 menit tanpa data
    pesan = pesan_satu_hari(aktif)
    baris = [{"window_start": datetime.fromisoformat(x["pesan"]["window_start"]), "status": x["pesan"]["status"]} for x in pesan]
    ringkas = ringkas_perangkat(baris, "uji", "RS-001", "RS-001-HD01", [HARI], 10)
    assert [r["shift"] for r in ringkas] == list(slot_shift())
    total = sum(r["menit_terapi"] + r["menit_standby"] + r["menit_mati"] + r["menit_tanpa_data"] for r in ringkas)
    assert total == 24 * 60
    assert sum(r["menit_tanpa_data"] for r in ringkas) == 60
    assert sum(r["menit_terapi"] for r in ringkas) > 0
