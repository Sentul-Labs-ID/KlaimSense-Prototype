"""Tes aturan SEN-01 dengan data kecil buatan tangan, dan uji integrasi pipeline sensor."""

from datetime import date, datetime

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.pool import StaticPool

from sentinel.generator.bangkit import bangkitkan
from sentinel.generator.simpan import simpan
from sentinel.models import GroundTruth, KasusSah, SensorAnomali, Temuan
from sentinel.parameter import muat_parameter
from sentinel.rules.__main__ import main as main_rules
from sentinel.rules.aturan_sensor import sen_01
from sentinel.rules.masukan import Masukan
from sentinel.rules.skor import hitung_skor
from sentinel.sensor.pipeline import jalankan_dataset

PARAM = muat_parameter()
TGL = date(2026, 8, 12)


def masukan(n_tagihan: int, menit_terapi: list[int], tanpa_data: list[int] | None = None, anomali=None, tgl=TGL) -> Masukan:
    """RS-001 dengan satu perangkat per elemen `menit_terapi`; satu hari data."""
    tanpa_data = tanpa_data or [0] * len(menit_terapi)
    perangkat = [
        {"device_id": f"DEV-RS-001-HD{i + 1:02d}", "rs_id": "RS-001", "mesin_id": f"RS-001-HD{i + 1:02d}", "aktif": True}
        for i in range(len(menit_terapi))
    ]
    harian = [
        {"mesin_id": p["mesin_id"], "tanggal": tgl, "shift": 1, "menit_terapi": t, "menit_tanpa_data": h}
        for p, t, h in zip(perangkat, menit_terapi, tanpa_data)
    ]
    tagihan = [
        {"id": i + 1, "rs_id": "RS-001", "pasien_id": f"P-{i + 1:06d}", "tanggal": tgl, "layanan": "hemodialisa",
         "kode_item": None, "sisi_telinga": None, "jumlah": 1, "harga_satuan": 1, "total": 1}
        for i in range(n_tagihan)
    ]
    return Masukan(
        "uji", [{"id": "RS-001", "kelas": "C", "provinsi": "Bali"}], [], [], tagihan, [],
        perangkat=perangkat, status_harian=harian, anomali_sensor=anomali or [],
    )


def kategori(hasil: list[dict]) -> list[str]:
    return [t["kategori"] for t in hasil]


def test_sen_01_selisih_dengan_penjelasan_template():
    # 30 sesi x 4 jam = 120 jam dibutuhkan; tercatat 84 jam (dibagi ke 7 mesin).
    hasil = sen_01(masukan(30, [720] * 7), PARAM)
    assert kategori(hasil) == ["selisih"]
    assert hasil[0]["penjelasan"] == (
        "Hemodialisa 12 Agustus 2026: 30 sesi ditagih (butuh 120 jam-mesin terapi), "
        "sensor mencatat 84 jam terapi. Selisih 36 jam."
    )
    assert len(hasil[0]["tagihan_ids"]) == 30


@pytest.mark.parametrize("menit, selisih", [(300, True), (450, False), (432, False)])
def test_sen_01_selisih_tidak_dan_tepat_di_batas(menit, selisih):
    # 2 sesi x 240 menit = 480; batas 480 x 0,9 = 432 menit (tepat di batas tidak melanggar).
    assert kategori(sen_01(masukan(2, [menit]), PARAM)) == (["selisih"] if selisih else [])


def test_sen_01_data_bolong_bukan_temuan_selisih():
    # Data hilang 10% (> batas 5%) dan terapi tercatat 0: jangan menuduh selisih.
    hasil = sen_01(masukan(10, [0, 0], tanpa_data=[288, 0]), PARAM)
    assert kategori(hasil) == ["integritas"]
    assert "hilang 10,0%" in hasil[0]["penjelasan"] and "tidak dihitung" in hasil[0]["penjelasan"]


def test_sen_01_perangkat_tanpa_ringkasan_dianggap_bolong():
    m = masukan(4, [960, 0])
    m = Masukan(**{**m.__dict__, "status_harian": m.status_harian[:1]})  # perangkat kedua diam seharian
    assert kategori(sen_01(m, PARAM)) == ["integritas"]


def test_sen_01_anomali_menjadi_temuan_integritas():
    anomali = [
        {"device_id": "DEV-RS-001-HD03", "jenis": "TAMPER_GAP", "waktu": datetime(2026, 8, 20, 10, 0), "durasi_menit": 130},
        {"device_id": "DEV-RS-001-HD01", "jenis": "TAMPER_SIG", "waktu": datetime(2026, 8, 20, 11, 0), "durasi_menit": None},
        {"device_id": "DEV-RS-001-HD01", "jenis": "TAMPER_SIG", "waktu": datetime(2026, 8, 20, 12, 0), "durasi_menit": None},
        {"device_id": "DEV-RS-001-HD02", "jenis": "TAMPER_CHAIN", "waktu": datetime(2026, 8, 20, 9, 0), "durasi_menit": None},
    ]
    hasil = sen_01(masukan(1, [240, 0, 0], anomali=anomali), PARAM)
    integritas = [t["penjelasan"] for t in hasil if t["kategori"] == "integritas"]
    assert "Sensor mesin HD-03 tidak mengirim data selama 2 jam 10 menit pada 20 Agustus 2026." in integritas
    assert "Sensor mesin HD-01: 2 pesan dengan tanda tangan tidak sah ditolak pada 20 Agustus 2026." in integritas
    assert any("Rantai pesan sensor mesin HD-02 terputus" in x for x in integritas)


def test_sen_01_rs_tanpa_perangkat_dilewati():
    m = masukan(30, [0])
    m = Masukan(**{**m.__dict__, "perangkat": []})
    assert sen_01(m, PARAM) == []


def test_skor_sen_01_maksimum_dari_selisih_dan_integritas():
    temuan = [{"aturan_id": "SEN-01", "rs_id": "RS-001", "periode": "2026-08", "kategori": "selisih"}] + [
        {"aturan_id": "SEN-01", "rs_id": "RS-001", "periode": "2026-08", "kategori": "integritas"}
    ] * 2
    (s,) = hitung_skor(masukan(1, [240]), PARAM, temuan, [])
    r = s["rincian_per_aturan"]["SEN-01"]
    assert r["selisih"]["keparahan"] == pytest.approx(1 / 3, abs=1e-4)
    assert r["integritas"]["keparahan"] == 1
    assert r["keparahan"] == 1 and s["skor"] == 20


# ----------------------------------------------------------- uji integrasi


@pytest.fixture(scope="module")
def dunia():
    """Dataset kecil di SQLite, sensor disimulasikan untuk RS bersensor yang punya kasus sah shift darurat.
    Tes boleh membaca tabel evaluasi; kode aplikasi tidak."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    simpan(engine, bangkitkan("utama", seed=42, hari=35, jumlah_rs=20))
    with engine.connect() as conn:
        kasus = conn.execute(select(KasusSah.rs_id, KasusSah.tanggal).where(KasusSah.jenis == "HD_SHIFT_TAMBAHAN")).all()
    rs_sensor = {"RS-012"}  # RS bersensor dengan dua hari shift darurat pada seed ini
    kasus = [(r, t) for r, t in kasus if r in rs_sensor]
    hasil = jalankan_dataset(engine, "utama", jumlah_proses=1, rs_ids=sorted(rs_sensor))
    assert main_rules(["--dataset", "utama"], engine=engine) == 0
    yield engine, kasus, hasil
    engine.dispose()


def test_integrasi_shift_darurat_tidak_memicu_selisih(dunia):
    engine, kasus, _ = dunia
    assert kasus, "dataset uji harus berisi kasus sah HD_SHIFT_TAMBAHAN di RS bersensor"
    with engine.connect() as conn:
        selisih = set(conn.execute(
            select(Temuan.rs_id, Temuan.tanggal).where(Temuan.aturan_id == "SEN-01", Temuan.kategori == "selisih")
        ).all())
        kap = set(conn.execute(select(Temuan.rs_id, Temuan.tanggal).where(Temuan.aturan_id == "KAP-02")).all())
    for hari in kasus:
        assert hari not in selisih, hari
        assert hari in kap, hari  # KAP-02 tetap menandai: perlu klarifikasi, bukan kecurangan


def test_integrasi_gangguan_terdeteksi_dan_tercatat(dunia):
    engine, _, hasil = dunia
    assert hasil.anomali["TAMPER_SIG"] >= 3 and hasil.anomali["TAMPER_GAP"] == 1
    assert hasil.ditolak == hasil.anomali["TAMPER_SIG"]
    with engine.connect() as conn:
        gt = {r for (r,) in conn.execute(select(GroundTruth.skenario).where(GroundTruth.skenario.like("TAMPER%")))}
        jenis = {r for (r,) in conn.execute(select(SensorAnomali.jenis))}
        integritas = conn.execute(
            select(Temuan.penjelasan).where(Temuan.aturan_id == "SEN-01", Temuan.kategori == "integritas")
        ).all()
    assert gt == {"TAMPER_SIG", "TAMPER_GAP"} and jenis == {"TAMPER_SIG", "TAMPER_GAP"}
    assert len(integritas) >= 2


def test_integrasi_jalan_ulang_mengganti_data_sensor(dunia):
    engine, _, pertama = dunia
    kedua = jalankan_dataset(engine, "utama", jumlah_proses=1, rs_ids=["RS-012"])
    assert (kedua.pesan, kedua.diterima, kedua.anomali) == (pertama.pesan, pertama.diterima, pertama.anomali)
    with engine.connect() as conn:
        assert len(conn.execute(select(GroundTruth.id).where(GroundTruth.skenario.like("TAMPER%"))).all()) == 2
