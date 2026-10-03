"""Tes mesin aturan (fase 2) dengan data kecil buatan tangan.

Setiap aturan diuji untuk kasus melanggar, tidak melanggar, dan tepat di batas
(tepat di batas TIDAK melanggar).
"""

import shutil
import time
from datetime import date

import pytest

from sentinel.parameter import hash_parameter, muat_parameter
from sentinel.rules.aturan import kap_01, kap_02, ulg_01, ulg_02, wjr_01, wjr_02
from sentinel.rules.banding import KONSTANTA_MAD, Penilaian, nilai_banding, robust_z
from sentinel.rules.masukan import Masukan
from sentinel.rules.mesin import jalankan
from sentinel.rules.skor import hitung_skor, prioritas

PARAM = muat_parameter()
SENIN = date(2026, 8, 3)
RABU = date(2026, 8, 5)
SABTU = date(2026, 8, 8)
MINGGU = date(2026, 8, 9)


# -------------------------------------------------------------- pembuat data


def rs(rs_id="RS-001", kelas="C", provinsi="Jawa Barat") -> dict:
    return {"id": rs_id, "kelas": kelas, "provinsi": provinsi}


def kap(rs_id="RS-001", terapis=4, mesin=2, shift=3, hari=6) -> dict:
    return {
        "rs_id": rs_id, "jumlah_fisioterapis": terapis, "jumlah_mesin_hd": mesin,
        "shift_hd_per_hari": shift, "hari_operasional_hd": hari,
    }


ACUAN = [
    {"kode_item": "OBK-X", "nama_item": "Tablet uji", "jenis": "obat_kronis", "harga": 1000},
    {"kode_item": "OBK-Y", "nama_item": "Tablet uji kecil", "jenis": "obat_kronis", "harga": 420},
    {"kode_item": "ABD-X", "nama_item": "Alat bantu dengar uji", "jenis": "alat_bantu_dengar", "harga": 2_000_000},
]


class Tagihan:
    def __init__(self):
        self.daftar: list[dict] = []

    def tambah(self, layanan, tanggal, pasien="P-000001", rs_id="RS-001", n=1, kode=None, sisi=None,
               jumlah=1, harga=150_000) -> list[dict]:
        baru = []
        for _ in range(n):
            t = {
                "id": len(self.daftar) + 1, "rs_id": rs_id, "pasien_id": pasien, "tanggal": tanggal,
                "layanan": layanan, "kode_item": kode, "sisi_telinga": sisi, "jumlah": jumlah,
                "harga_satuan": harga, "total": jumlah * harga,
            }
            self.daftar.append(t)
            baru.append(t)
        return baru

    def banyak_pasien(self, layanan, tanggal, n, rs_id="RS-001"):
        for i in range(n):
            self.tambah(layanan, tanggal, pasien=f"P-{i + 1:06d}", rs_id=rs_id)


def masukan(tagihan: Tagihan, daftar_rs=None, daftar_kap=None, riwayat=None) -> Masukan:
    return Masukan(
        dataset_id="uji",
        rumah_sakit=daftar_rs or [rs()],
        kapasitas=daftar_kap or [kap()],
        harga_acuan=ACUAN,
        tagihan=tagihan.daftar,
        riwayat_abd=riwayat or [],
    )


# -------------------------------------------------------------------- KAP-01


@pytest.mark.parametrize("n, melanggar", [(33, True), (31, False), (32, False)])
def test_kap_01(n, melanggar):
    t = Tagihan()
    t.banyak_pasien("fisioterapi", RABU, n)
    hasil = kap_01(masukan(t), PARAM)  # kapasitas 4 terapis x 8 = 32
    assert bool(hasil) == melanggar
    if melanggar:
        assert (hasil[0]["nilai_teramati"], hasil[0]["batas"], hasil[0]["selisih"]) == (33, 32, 1)
        assert len(hasil[0]["tagihan_ids"]) == 33


def test_kap_01_penjelasan_sesuai_template():
    t = Tagihan()
    t.banyak_pasien("fisioterapi", RABU, 75)
    (hasil,) = kap_01(masukan(t), PARAM)
    assert hasil["penjelasan"] == (
        "Fisioterapi 5 Agustus 2026: 75 sesi ditagih, kapasitas 32 (4 terapis × 8 sesi). Selisih 43 sesi."
    )
    assert hasil["periode"] == "2026-08"


def test_kap_01_dihitung_per_rumah_sakit():
    t = Tagihan()
    t.banyak_pasien("fisioterapi", RABU, 20, rs_id="RS-001")
    t.banyak_pasien("fisioterapi", RABU, 20, rs_id="RS-002")
    m = masukan(t, [rs("RS-001"), rs("RS-002")], [kap("RS-001"), kap("RS-002")])
    assert kap_01(m, PARAM) == []


# -------------------------------------------------------------------- KAP-02


@pytest.mark.parametrize("n, melanggar", [(7, True), (5, False), (6, False)])
def test_kap_02_kapasitas(n, melanggar):
    t = Tagihan()
    t.banyak_pasien("hemodialisa", RABU, n)
    hasil = kap_02(masukan(t), PARAM)  # 2 mesin x 3 shift = 6
    assert bool(hasil) == melanggar
    if melanggar:
        assert (hasil[0]["batas"], hasil[0]["selisih"]) == (6, 1)


def test_kap_02_sesi_pada_hari_unit_tutup():
    t = Tagihan()
    t.banyak_pasien("hemodialisa", MINGGU, 1)
    t.banyak_pasien("hemodialisa", SABTU, 6)
    (hasil,) = kap_02(masukan(t), PARAM)  # unit 6 hari: Senin-Sabtu
    assert hasil["tanggal"] == MINGGU and hasil["batas"] == 0 and hasil["selisih"] == 1
    assert "tidak beroperasi" in hasil["penjelasan"] and "Senin–Sabtu" in hasil["penjelasan"]


def test_kap_02_unit_tujuh_hari_boleh_hari_minggu():
    t = Tagihan()
    t.banyak_pasien("hemodialisa", MINGGU, 6)
    assert kap_02(masukan(t, daftar_kap=[kap(hari=7)]), PARAM) == []


# -------------------------------------------------------------------- ULG-01


def test_ulg_01_salinan_identik():
    t = Tagihan()
    (a,) = t.tambah("obat_kronis", RABU, kode="OBK-X", jumlah=30, harga=1000)
    (b,) = t.tambah("obat_kronis", RABU, kode="OBK-X", jumlah=30, harga=1000)
    (hasil,) = ulg_01(masukan(t), PARAM)
    assert hasil["tagihan_ids"] == [a["id"], b["id"]]
    assert f"#{b['id']} identik dengan tagihan #{a['id']}" in hasil["penjelasan"]


def test_ulg_01_tiga_salinan_menjadi_dua_temuan():
    t = Tagihan()
    t.tambah("fisioterapi", RABU, n=3)
    hasil = ulg_01(masukan(t), PARAM)
    assert len(hasil) == 2
    assert [h["tagihan_ids"] for h in hasil] == [[1, 2], [1, 3]]


@pytest.mark.parametrize("beda", [{"harga": 1001}, {"jumlah": 60}, {"tanggal": SENIN}, {"pasien": "P-000002"}])
def test_ulg_01_tidak_identik(beda):
    t = Tagihan()
    t.tambah("obat_kronis", RABU, kode="OBK-X", jumlah=30, harga=1000)
    argumen = {"tanggal": RABU, "kode": "OBK-X", "jumlah": 30, "harga": 1000} | beda
    t.tambah("obat_kronis", **argumen)
    assert ulg_01(masukan(t), PARAM) == []


def test_ulg_01_satu_tagihan_tepat_di_batas():
    t = Tagihan()
    t.tambah("obat_kronis", RABU, kode="OBK-X", jumlah=30, harga=1000)
    assert ulg_01(masukan(t), PARAM) == []


# -------------------------------------------------------------------- ULG-02


def test_ulg_02_dua_sesi_hd_sehari():
    t = Tagihan()
    t.tambah("hemodialisa", RABU, n=2)
    (hasil,) = ulg_02(masukan(t), PARAM)
    assert (hasil["nilai_teramati"], hasil["batas"], hasil["selisih"]) == (2, 1, 1)
    assert hasil["tagihan_ids"] == [1, 2]


def test_ulg_02_tidak_melanggar_dan_batas():
    t = Tagihan()
    t.tambah("hemodialisa", RABU)  # tepat 1 sesi: batas
    t.tambah("hemodialisa", SENIN)  # hari lain
    t.tambah("hemodialisa", RABU, rs_id="RS-002")  # RS lain
    t.tambah("fisioterapi", RABU, n=2)  # bukan hemodialisa
    m = masukan(t, [rs("RS-001"), rs("RS-002")], [kap("RS-001"), kap("RS-002")])
    assert ulg_02(m, PARAM) == []


# -------------------------------------------------------------------- WJR-01


@pytest.mark.parametrize(
    "kode, harga, melanggar",
    [("OBK-X", 1101, True), ("OBK-X", 900, False), ("OBK-X", 1100, False), ("OBK-Y", 462, False), ("OBK-Y", 463, True)],
)
def test_wjr_01(kode, harga, melanggar):
    t = Tagihan()
    t.tambah("obat_kronis", RABU, kode=kode, jumlah=30, harga=harga)
    hasil = wjr_01(masukan(t), PARAM)
    assert bool(hasil) == melanggar
    if melanggar and kode == "OBK-X":
        assert (hasil[0]["batas"], hasil[0]["selisih"]) == (1100, 1)
        assert "batas toleransi 10% = Rp1.100" in hasil[0]["penjelasan"]


def test_wjr_01_mengabaikan_tagihan_tanpa_kode_item():
    t = Tagihan()
    t.tambah("hemodialisa", RABU, harga=99_999_999)
    assert wjr_01(masukan(t), PARAM) == []


# -------------------------------------------------------------------- WJR-02


def riwayat(tanggal, sisi="kiri", pasien="P-000123") -> dict:
    return {"pasien_id": pasien, "sisi_telinga": sisi, "tanggal_diberikan": tanggal}


@pytest.mark.parametrize("tgl, melanggar", [(date(2026, 8, 4), True), (date(2026, 8, 5), False), (date(2026, 9, 1), False)])
def test_wjr_02_terhadap_riwayat(tgl, melanggar):
    t = Tagihan()
    t.tambah("alat_bantu_dengar", tgl, pasien="P-000123", kode="ABD-X", sisi="kiri", harga=2_000_000)
    hasil = wjr_02(masukan(t, riwayat=[riwayat(date(2021, 8, 5))]), PARAM)  # tepat 5 tahun = 5 Agustus 2026
    assert bool(hasil) == melanggar
    if melanggar:
        assert hasil[0]["selisih"] == 1  # kurang 1 hari


def test_wjr_02_penjelasan_sesuai_template():
    t = Tagihan()
    t.tambah("alat_bantu_dengar", RABU, pasien="P-000123", kode="ABD-X", sisi="kiri", harga=2_000_000)
    (hasil,) = wjr_02(masukan(t, riwayat=[riwayat(date(2024, 7, 1))]), PARAM)
    assert hasil["penjelasan"] == (
        "Alat bantu dengar telinga kiri pasien P-000123 ditagih 2 tahun 1 bulan setelah pemberian "
        "sebelumnya; masa penggantian 5 tahun."
    )


def test_wjr_02_telinga_lain_tidak_melanggar():
    t = Tagihan()
    t.tambah("alat_bantu_dengar", RABU, pasien="P-000123", kode="ABD-X", sisi="kanan", harga=2_000_000)
    assert wjr_02(masukan(t, riwayat=[riwayat(date(2025, 1, 1), sisi="kiri")]), PARAM) == []


def test_wjr_02_memakai_tagihan_abd_sebelumnya():
    t = Tagihan()
    (a,) = t.tambah("alat_bantu_dengar", date(2026, 7, 1), pasien="P-000123", kode="ABD-X", sisi="kiri", harga=2_000_000)
    (b,) = t.tambah("alat_bantu_dengar", RABU, pasien="P-000123", kode="ABD-X", sisi="kiri", harga=2_000_000)
    # Riwayat lama (> 5 tahun) tidak melanggar; yang melanggar adalah tagihan kedua terhadap yang pertama.
    (hasil,) = wjr_02(masukan(t, riwayat=[riwayat(date(2020, 1, 1))]), PARAM)
    assert hasil["tagihan_ids"] == [a["id"], b["id"]]
    assert "1 bulan setelah pemberian sebelumnya" in hasil["penjelasan"]


def test_wjr_02_riwayat_setelah_tanggal_tagihan_diabaikan():
    t = Tagihan()
    t.tambah("alat_bantu_dengar", RABU, pasien="P-000123", kode="ABD-X", sisi="kiri", harga=2_000_000)
    assert wjr_02(masukan(t, riwayat=[riwayat(date(2026, 8, 20))]), PARAM) == []


# ------------------------------------------------------------------- BAND-01


def masukan_banding(nilai_per_rs: dict[str, tuple[str, str, int]]) -> Masukan:
    """nilai_per_rs: rs_id -> (kelas, provinsi, sesi HD pada satu hari Senin; kapasitas 100)."""
    t = Tagihan()
    daftar_rs, daftar_kap = [], []
    for rs_id, (kelas, provinsi, sesi) in nilai_per_rs.items():
        daftar_rs.append(rs(rs_id, kelas, provinsi))
        daftar_kap.append(kap(rs_id, mesin=50, shift=2))
        t.banyak_pasien("hemodialisa", SENIN, sesi, rs_id=rs_id)
    return masukan(t, daftar_rs, daftar_kap)


def penilaian_untuk(penilaian: list[Penilaian], rs_id: str) -> Penilaian:
    return next(x for x in penilaian if x.rs_id == rs_id and x.layanan == "hemodialisa")


def test_robust_z():
    z, med, mad = robust_z(0.95, [0.60, 0.62, 0.64, 0.66])
    assert med == pytest.approx(0.63) and mad == pytest.approx(0.02)
    assert z == pytest.approx((0.95 - 0.63) / (KONSTANTA_MAD * 0.02))
    assert robust_z(0.9, [0.6, 0.6, 0.6])[0] is None  # MAD = 0


def test_band_01_leave_one_out():
    m = masukan_banding({
        "RS-001": ("C", "Jawa Barat", 60), "RS-002": ("C", "Jawa Barat", 62), "RS-003": ("C", "Jawa Barat", 64),
        "RS-004": ("C", "Jawa Barat", 66), "RS-005": ("C", "Jawa Barat", 95),
    })
    penilaian, hasil = nilai_banding(m, PARAM)
    target = penilaian_untuk(penilaian, "RS-005")
    # Pembanding RS-005 hanya 4 RS lain (tanpa dirinya): median 0,63, MAD 0,02.
    assert target.kelompok == "kelas_provinsi" and target.jumlah_pembanding == 4
    assert target.median_pembanding == pytest.approx(0.63)
    assert target.z == pytest.approx((0.95 - 0.63) / (KONSTANTA_MAD * 0.02))
    # Jika dirinya ikut dihitung, z akan berbeda.
    assert target.z != pytest.approx(robust_z(0.95, [0.60, 0.62, 0.64, 0.66, 0.95])[0])
    # RS-001 dibandingkan dengan RS-002..RS-005, bukan dengan dirinya.
    assert penilaian_untuk(penilaian, "RS-001").median_pembanding == pytest.approx(0.65)
    assert [h["rs_id"] for h in hasil] == ["RS-005"]
    assert hasil[0]["tanggal"] is None and hasil[0]["periode"] == "2026-08"
    assert "Sinyal pendukung, bukan bukti utama." in hasil[0]["penjelasan"]


def test_band_01_turun_ke_kelas_bila_pembanding_kurang():
    m = masukan_banding({
        "RS-001": ("C", "Bali", 90), "RS-002": ("C", "Bali", 60), "RS-003": ("C", "Bali", 61),  # hanya 2 pembanding
        "RS-004": ("C", "Jawa Barat", 62), "RS-005": ("C", "Jawa Barat", 64), "RS-006": ("D", "Bali", 99),
    })
    penilaian, hasil = nilai_banding(m, PARAM)
    target = penilaian_untuk(penilaian, "RS-001")
    assert target.kelompok == "kelas" and target.jumlah_pembanding == 4
    assert "RS-001" in [h["rs_id"] for h in hasil]
    assert "turun dari kelas-provinsi" in next(h for h in hasil if h["rs_id"] == "RS-001")["penjelasan"]


def test_band_01_turun_ke_kelas_bila_mad_nol():
    m = masukan_banding({
        "RS-001": ("B", "Bali", 90), "RS-002": ("B", "Bali", 60), "RS-003": ("B", "Bali", 60),
        "RS-004": ("B", "Bali", 60), "RS-005": ("B", "Jawa Timur", 66), "RS-006": ("B", "Jawa Timur", 70),
        "RS-007": ("B", "Jawa Timur", 72),
    })
    penilaian, _ = nilai_banding(m, PARAM)
    target = penilaian_untuk(penilaian, "RS-001")
    # Kelas-provinsi (Bali) MAD = 0; kelas B semua provinsi: [60, 60, 60, 66, 70, 72], MAD 3.
    assert target.kelompok == "kelas" and target.jumlah_pembanding == 6


def test_band_01_dilewati_bila_tetap_tidak_memadai():
    m = masukan_banding({"RS-001": ("A", "Bali", 95), "RS-002": ("A", "Bali", 60), "RS-003": ("A", "Bali", 61)})
    penilaian, hasil = nilai_banding(m, PARAM)
    target = penilaian_untuk(penilaian, "RS-001")
    assert target.z is None and target.kelompok is None
    assert "pembanding 2 RS" in target.alasan_dilewati
    assert hasil == []


# ---------------------------------------------------------------------- skor


def temuan_palsu(aturan: str, n: int, rs_id="RS-001", periode="2026-08") -> list[dict]:
    return [{"aturan_id": aturan, "rs_id": rs_id, "periode": periode} for _ in range(n)]


def m_satu_bulan() -> Masukan:
    t = Tagihan()
    t.tambah("fisioterapi", RABU)
    return masukan(t)


def test_skor_rumus_keparahan_dan_sen_01_nol():
    temuan = temuan_palsu("KAP-01", 1) + temuan_palsu("WJR-02", 5)
    band = [Penilaian("RS-001", "hemodialisa", "2026-08", 0.9, 4.5, "kelas", 4, 0.6, None)]
    (s,) = hitung_skor(m_satu_bulan(), PARAM, temuan, band)
    r = s["rincian_per_aturan"]
    assert r["KAP-01"]["keparahan"] == pytest.approx(1 / 3, abs=1e-4) and r["KAP-01"]["kontribusi"] == pytest.approx(5)
    assert r["WJR-02"]["keparahan"] == 1  # jenuh
    assert r["BAND-01"]["keparahan"] == pytest.approx(0.5)  # (4,5 - 3) / 3
    assert r["SEN-01"]["kontribusi"] == 0
    assert s["skor"] == pytest.approx(5 + 10 + 2.5)


def test_skor_maksimum_sementara_80_dan_selalu_0_sampai_100():
    temuan = sum((temuan_palsu(a, 50) for a in ("KAP-01", "KAP-02", "ULG-01", "ULG-02", "WJR-01", "WJR-02")), [])
    band = [Penilaian("RS-001", "fisioterapi", "2026-08", 1.0, 99.0, "kelas", 4, 0.5, None)]
    (s,) = hitung_skor(m_satu_bulan(), PARAM, temuan, band)
    assert s["skor"] == 80 and s["prioritas"] == "tinggi"
    (kosong,) = hitung_skor(m_satu_bulan(), PARAM, [], [])
    assert kosong["skor"] == 0 and kosong["prioritas"] == "rendah"


def test_band_tepat_di_ambang_tidak_menambah_skor():
    band = [Penilaian("RS-001", "fisioterapi", "2026-08", 0.9, PARAM.perbandingan.ambang_robust_z, "kelas", 4, 0.6, None)]
    (s,) = hitung_skor(m_satu_bulan(), PARAM, [], band)
    assert s["skor"] == 0


def test_prioritas_tepat_di_ambang():
    tinggi, sedang = PARAM.skor.prioritas.tinggi, PARAM.skor.prioritas.sedang
    assert prioritas(tinggi, PARAM) == "tinggi"
    assert prioritas(tinggi - 0.01, PARAM) == "sedang"
    assert prioritas(sedang, PARAM) == "sedang"
    assert prioritas(sedang - 0.01, PARAM) == "rendah"


# ------------------------------------------------- data penuh, determinisme


@pytest.fixture(scope="module")
def hasil_utama(utama):
    m = Masukan.dari_tabel("utama", utama.tabel)
    t0 = time.perf_counter()
    h = jalankan(m, PARAM, hash_parameter())
    return m, h, time.perf_counter() - t0


def test_dataset_penuh_cepat_dan_skor_dalam_rentang(hasil_utama):
    m, h, durasi = hasil_utama
    assert durasi < 30
    assert all(0 <= s["skor"] <= 80 for s in h.skor)
    assert all(s["rincian_per_aturan"]["SEN-01"]["kontribusi"] == 0 for s in h.skor)
    assert len(h.skor) == len(m.rumah_sakit) * 3  # 3 bulan: Juli-September
    assert {t["aturan_id"] for t in h.temuan} <= {"KAP-01", "KAP-02", "ULG-01", "ULG-02", "WJR-01", "WJR-02", "BAND-01"}


def test_hasil_identik_bila_dijalankan_dua_kali(hasil_utama):
    m, h, _ = hasil_utama
    ulang = jalankan(m, PARAM, hash_parameter())
    assert ulang.temuan == h.temuan
    assert ulang.skor == h.skor


def test_hash_parameter_berubah_bila_parameter_berubah(tmp_path):
    salinan = tmp_path / "parameter.yaml"
    shutil.copy(PARAM_PATH := muat_parameter.__globals__["get_settings"]().parameter_path, salinan)
    assert hash_parameter(salinan) == hash_parameter(PARAM_PATH)
    salinan.write_text(salinan.read_text(encoding="utf-8").replace("tinggi: 20", "tinggi: 25"), encoding="utf-8")
    assert hash_parameter(salinan) != hash_parameter(PARAM_PATH)
    assert muat_parameter(salinan).skor.prioritas.tinggi == 25
