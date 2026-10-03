"""Tes evaluasi akurasi (fase 4): metrik pada data buatan tangan, Wilson, pemetaan, read-only."""

import json
import re
from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.pool import StaticPool

from sentinel.db import Base
from sentinel.evaluation import metrik as m
from sentinel.evaluation.__main__ import catat_jalan_hidden, main
from sentinel.evaluation.laporan import p, render
from sentinel.generator.bangkit import bangkitkan
from sentinel.generator.simpan import simpan
from sentinel.models.evaluasi import SKENARIO
from sentinel.rules.__main__ import main as main_rules
from sentinel.sensor.gangguan import SKENARIO_SENSOR

T1, T2 = date(2026, 8, 5), date(2026, 8, 6)


# ------------------------------------------------------------------ Wilson


@pytest.mark.parametrize(
    "k, n, lo, hi",
    [
        (13, 14, 0.6853, 0.9873),  # nilai acuan Wilson yang umum dikutip
        (5, 10, 0.2366, 0.7634),
        (0, 10, 0.0, 0.2775),
        (10, 10, 0.7225, 1.0),
        (1, 1, 0.2065, 1.0),
    ],
)
def test_wilson_cocok_nilai_acuan(k, n, lo, hi):
    a, b = m.wilson(k, n)
    assert a == pytest.approx(lo, abs=1e-4) and b == pytest.approx(hi, abs=1e-4)


def test_proporsi_menyimpan_pembilang_penyebut():
    assert m.proporsi(13, 14) == {"pembilang": 13, "penyebut": 14, "nilai": 0.9286, "ci95": [0.6853, 0.9873]}
    assert m.proporsi(0, 0) == {"pembilang": 0, "penyebut": 0, "nilai": None, "ci95": None}
    assert p(m.proporsi(13, 14)) == "13/14 (92,9%; IK95% 68,5%–98,7%)"


# --------------------------------------------------------------- pemetaan


def test_setiap_skenario_punya_pemetaan_aturan():
    assert set(SKENARIO) | set(SKENARIO_SENSOR) == set(m.PEMETAAN)
    assert "BAND-01" not in {a for a, _ in m.PEMETAAN.values()}


# ------------------------------------------------------------------ recall


def gt(skenario, rs="RS-001", tgl=T1, ids=()):
    return {"skenario": skenario, "rs_id": rs, "tanggal": tgl, "tagihan_ids": list(ids)}


def tm(aturan, rs="RS-001", tgl=T1, ids=(), kategori=None):
    return {"aturan_id": aturan, "rs_id": rs, "tanggal": tgl, "periode": "2026-08", "tagihan_ids": list(ids), "kategori": kategori}


def test_recall_aturan_harian_dan_per_tagihan():
    kejadian = [
        gt("KAP_HD", ids=[1, 2]),                 # tertangkap: KAP-02 RS & tanggal sama
        gt("KAP_HD", tgl=T2, ids=[3]),            # tidak: tanggal berbeda
        gt("HARGA_LEBIH", ids=[10]),              # tertangkap: WJR-01 memuat tagihan 10
        gt("HARGA_LEBIH", ids=[11]),              # tidak: WJR-01 untuk tagihan lain
        gt("SENSOR_PALSU", ids=[20]),             # tidak: hanya SEN-01 integritas di hari itu
        gt("TAMPER_GAP", rs="RS-002"),            # tertangkap: SEN-01 integritas RS-002
    ]
    temuan = [
        tm("KAP-02", ids=[1, 2, 99]),
        tm("WJR-01", ids=[10]), tm("WJR-01", ids=[12]),
        tm("SEN-01", ids=[], kategori="integritas"),
        tm("SEN-01", rs="RS-002", ids=[], kategori="integritas"),
        tm("KAP-01", tgl=T2, ids=[3]),  # aturan lain di tanggal kejadian KAP_HD kedua
    ]
    r = m.recall_per_skenario(kejadian, temuan)
    assert r["KAP_HD"]["recall"]["pembilang"] == 1 and r["KAP_HD"]["recall"]["penyebut"] == 2
    assert r["KAP_HD"]["tertangkap_aturan_apa_pun"]["pembilang"] == 2  # tagihan 3 ada di temuan KAP-01
    assert r["HARGA_LEBIH"]["recall"]["pembilang"] == 1
    assert r["SENSOR_PALSU"]["recall"]["pembilang"] == 0  # kategori harus 'selisih'
    assert r["TAMPER_GAP"]["recall"]["pembilang"] == 1
    assert m.recall_gabungan(kejadian, temuan, m.SKENARIO_KECURANGAN) == m.proporsi(2, 5)


# --------------------------------------------------------------- presisi


def test_presisi_tiga_kelas():
    kejadian = [gt("KAP_HD", ids=[1]), gt("TAMPER_SIG", rs="RS-002")]
    kasus_sah = [{"jenis": "HD_SHIFT_TAMBAHAN", "rs_id": "RS-003", "tanggal": T1, "tagihan_ids": [50]}]
    temuan = [
        tm("KAP-02", ids=[1, 2]),                                   # benar
        tm("KAP-02", rs="RS-003", ids=[50, 51]),                    # kasus sah
        tm("KAP-02", rs="RS-004", ids=[60]),                        # keliru
        tm("SEN-01", rs="RS-002", ids=[], kategori="integritas"),   # benar (hari gangguan)
        tm("SEN-01", rs="RS-005", ids=[], kategori="integritas"),   # keliru
        tm("BAND-01", tgl=None, ids=[]),                            # tidak ikut presisi
    ]
    assert m.klasifikasi_temuan(temuan[:5], kejadian, kasus_sah) == ["benar", "kasus_sah", "keliru", "benar", "keliru"]
    pr = m.presisi_per_aturan(temuan, kejadian, kasus_sah)
    assert pr["KAP-02"]["jumlah_temuan"] == 3
    assert (pr["KAP-02"]["benar"]["pembilang"], pr["KAP-02"]["kasus_sah"]["pembilang"], pr["KAP-02"]["keliru"]["pembilang"]) == (1, 1, 1)
    assert pr["SEN-01 (integritas)"]["benar"] == m.proporsi(1, 2)
    assert "BAND-01" not in pr


# -------------------------------------------------------------- prioritas


def skor(rs, prioritas, nilai, periode="2026-08", alasan="ambang skor ≥ 20"):
    return {"rs_id": rs, "periode": periode, "skor": nilai, "prioritas": prioritas, "alasan_prioritas": alasan}


@pytest.fixture
def kasus_prioritas():
    daftar = [
        skor("RS-001", "tinggi", 40), skor("RS-002", "tinggi", 15, alasan="lantai: KAP-02 jenuh"),
        skor("RS-003", "sedang", 12), skor("RS-004", "sedang", 10), skor("RS-005", "sedang", 10),
        skor("RS-006", "rendah", 3), skor("RS-007", "rendah", 0), skor("RS-008", "rendah", 5),
    ]
    kejadian = [gt("KAP_HD", rs="RS-001", ids=[1]), gt("ULANG_HARI", rs="RS-003", ids=[2]),
                gt("HARGA_LEBIH", rs="RS-006", ids=[3]), gt("TAMPER_GAP", rs="RS-004")]
    kasus_sah = [{"jenis": "FISIO_LEMBUR", "rs_id": "RS-005", "tanggal": T1, "tagihan_ids": [9]},
                 {"jenis": "FISIO_LEMBUR", "rs_id": "RS-008", "tanggal": T1, "tagihan_ids": [8]}]
    profil = {"RS-001": "disisipi", "RS-002": "jujur", "RS-003": "disisipi", "RS-004": "jujur",
              "RS-005": "jujur_sibuk", "RS-006": "disisipi", "RS-007": "jujur", "RS-008": "jujur_volume_tinggi"}
    return daftar, kejadian, kasus_sah, profil


def test_kondisi_rs_periode(kasus_prioritas):
    daftar, kejadian, kasus_sah, _ = kasus_prioritas
    k = m.kondisi_rs_periode(daftar, kejadian, kasus_sah)
    assert [k[(s["rs_id"], "2026-08")] for s in daftar] == [
        "bermasalah", "bersih", "bermasalah", "gangguan_sensor", "hanya_kasus_sah", "bermasalah", "bersih", "hanya_kasus_sah",
    ]
    harfiah = m.kondisi_rs_periode(daftar, kejadian, kasus_sah, pisahkan_tamper=False)
    assert harfiah[("RS-004", "2026-08")] == "bersih"


def test_metrik_prioritas_dan_top_k(kasus_prioritas):
    daftar, kejadian, kasus_sah, profil = kasus_prioritas
    r = m.metrik_prioritas(daftar, m.kondisi_rs_periode(daftar, kejadian, kasus_sah), profil)
    assert r["tinggi"]["presisi"] == m.proporsi(1, 2) and r["tinggi"]["recall"] == m.proporsi(1, 3)
    assert r["tinggi_sedang"]["presisi"] == m.proporsi(2, 5) and r["tinggi_sedang"]["recall"] == m.proporsi(2, 3)
    assert r["top_5"] == m.proporsi(2, 5)  # urutan: RS-001, RS-002, RS-003, RS-004, RS-005
    assert r["top_10"] == m.proporsi(3, 8)  # hanya 8 RS-periode
    assert r["ditandai"]["tuduhan_keliru"] == m.proporsi(1, 5)  # RS-002
    assert r["ditandai"]["kasus_sah_perlu_klarifikasi"] == m.proporsi(1, 5)  # RS-005
    assert r["ditandai"]["gangguan_sensor"] == m.proporsi(1, 5)  # RS-004
    assert r["rs_jujur_ikut_ditandai"] == m.proporsi(3, 5)  # RS-002, RS-004, RS-005 dari 5 RS jujur
    assert r["matriks_prioritas_kondisi"]["rendah"]["bermasalah"] == 1
    assert [x["alasan_prioritas"] for x in r["daftar_tinggi"]] == ["ambang skor ≥ 20", "lantai: KAP-02 jenuh"]


def test_integritas_sensor_menghitung_anomali_tanpa_kejadian():
    from datetime import datetime

    kejadian = [gt("TAMPER_SIG", rs="RS-001"), gt("TAMPER_GAP", rs="RS-002")]
    temuan = [tm("SEN-01", rs="RS-001", ids=[], kategori="integritas")]
    anomali = [
        {"jenis": "TAMPER_SIG", "device_id": "D1", "waktu": datetime(2026, 8, 5, 9)},
        {"jenis": "TAMPER_SIG", "device_id": "D1", "waktu": datetime(2026, 8, 7, 9)},  # tanpa kejadian
        {"jenis": "TAMPER_CHAIN", "device_id": "D2", "waktu": datetime(2026, 8, 5, 9)},  # tanpa kejadian
    ]
    r = m.integritas_sensor(kejadian, temuan, anomali, {"D1": "RS-001", "D2": "RS-002"})
    assert r["TAMPER_SIG"] == m.proporsi(1, 1) and r["TAMPER_GAP"] == m.proporsi(0, 1)
    assert r["anomali_tanpa_kejadian"] == 2
    assert r["anomali_tanpa_kejadian_per_jenis"] == {"TAMPER_SIG": 1, "TAMPER_CHAIN": 1}


# ------------------------------------------------------ hanya membaca, CLI


def jumlah_baris(engine) -> dict[str, int]:
    with engine.connect() as conn:
        return {n: conn.execute(select(func.count()).select_from(t)).scalar() for n, t in Base.metadata.tables.items()}


def test_evaluasi_tidak_menulis_ke_tabel_mana_pun(tmp_path):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    simpan(engine, bangkitkan("utama", hari=35, jumlah_rs=20))
    assert main_rules(["--dataset", "utama"], engine=engine) == 0
    Base.metadata.create_all(engine)
    sebelum = jumlah_baris(engine)
    assert main(["--dataset", "utama"], engine=engine, direktori=tmp_path) == 0
    assert jumlah_baris(engine) == sebelum
    for nama in ("evaluasi.md", "evaluasi.json", "recall_per_skenario.png"):
        assert (tmp_path / nama).exists()
    hasil = json.loads((tmp_path / "evaluasi.json").read_text(encoding="utf-8"))
    assert hasil["utama"]["skenario_tanpa_pemetaan"] == []
    assert "hidden" not in hasil and not (tmp_path / "log_evaluasi_hidden.json").exists()


def test_kode_evaluasi_tidak_berisi_operasi_tulis():
    paket = Path(__file__).resolve().parents[1] / "sentinel" / "evaluation"
    for berkas in paket.glob("*.py"):
        isi = berkas.read_text(encoding="utf-8")
        pola_tulis = (
            r"from sqlalchemy import[^\n]*\b(insert|delete|update)\b",  # konstruktor tulis SQLAlchemy
            r"\b(INSERT|UPDATE|DELETE|DROP|ALTER)\s",  # SQL mentah
            r"\.begin\(", r"\.commit\(", r"create_all",
        )
        for pola in pola_tulis:
            assert not re.search(pola, isi), f"{berkas.name} memuat {pola}"


def test_log_hidden_menyimpan_jalan_pertama(tmp_path):
    a = catat_jalan_hidden(tmp_path, "2026-10-03T10:00:00+07:00")
    b = catat_jalan_hidden(tmp_path, "2026-10-03T11:00:00+07:00")
    assert a["pertama"] == b["pertama"] == "2026-10-03T10:00:00+07:00"
    assert len(b["jalan"]) == 2


def test_laporan_tanpa_hidden_dan_tidak_ada_persen_tanpa_jumlah(tmp_path):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    simpan(engine, bangkitkan("utama", hari=35, jumlah_rs=20))
    main_rules(["--dataset", "utama"], engine=engine)
    main(["--dataset", "utama"], engine=engine, direktori=tmp_path)
    md = (tmp_path / "evaluasi.md").read_text(encoding="utf-8")
    assert "belum dijalankan" in md and "## Keterbatasan" in md
    # Setiap persentase di tabel metrik didahului jumlah k/n.
    for baris in md.splitlines():
        if baris.startswith("|") and "%" in baris:
            assert re.search(r"\d+/\d+ \(", baris), baris
    assert render(json.loads((tmp_path / "evaluasi.json").read_text(encoding="utf-8"))) == md


def test_kalimat_slide_konsisten_dengan_angka():
    from sentinel.evaluation.laporan import kalimat_slide

    hidden = {"prioritas": {"tinggi_sedang": {"recall": m.proporsi(23, 28)}}}
    proposal = {
        "kecurangan_tertangkap": m.proporsi(83, 86),
        "tuduhan_keliru": m.proporsi(0, 26),
        "kasus_sah_perlu_klarifikasi": m.proporsi(2, 26),
        "gangguan_sensor_ditandai": m.proporsi(1, 26),
        "akurasi_edge_ai": m.proporsi(16892, 17280),
    }
    assert kalimat_slide(hidden, proposal) == (
        "Pada data uji tersembunyi (data tiruan), JKN-Sentinel mendeteksi 83 dari 86 kejadian kecurangan (96,5%) dan "
        "memasukkan 23 dari 28 periode rumah sakit bermasalah ke daftar periksa petugas (82%). Dari 26 periode yang "
        "diprioritaskan, tidak ada tuduhan keliru; 2 merupakan kasus sah yang perlu klarifikasi dan 1 merupakan gangguan "
        "sensor. Klasifikasi Edge AI pada sensor akurat 97,8%."
    )
