"""Tes generator data tiruan (fase 1)."""

import os
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

import pytest

from sentinel.generator.__main__ import main
from sentinel.generator.bangkit import DataTiruan, bangkitkan
from sentinel.generator.ringkasan import sidik
from sentinel.models.evaluasi import JENIS_KASUS_SAH, SKENARIO
from sentinel.parameter import muat_parameter

PARAM = muat_parameter()
FIKTIF_HD = ("KAP_HD", "SENSOR_PALSU")
KASUS_KAPASITAS = {"FISIO_LEMBUR": "fisioterapi", "HD_SHIFT_TAMBAHAN": "hemodialisa"}
KAP = {"KAP_FISIO": "fisioterapi", "KAP_HD": "hemodialisa"}


# ---------------------------------------------------------------- utilitas


def kapasitas(data: DataTiruan) -> dict[str, dict[str, int]]:
    hasil = {}
    for k in data.tabel["kapasitas"]:
        hasil[k["rs_id"]] = {
            "fisioterapi": k["jumlah_fisioterapis"] * PARAM.kapasitas.fisioterapi_sesi_per_terapis_per_hari,
            "hemodialisa": k["jumlah_mesin_hd"] * k["shift_hd_per_hari"],
            "hari_hd": k["hari_operasional_hd"],
        }
    return hasil


def hitung_per_hari(baris: list[dict]) -> Counter:
    return Counter((x["rs_id"], x["layanan"], x["tanggal"]) for x in baris)


def skenario_per_rs(data: DataTiruan) -> dict[str, set[str]]:
    hasil = defaultdict(set)
    for g in data.tabel["ground_truth"]:
        hasil[g["rs_id"]].add(g["skenario"])
    return hasil


def tagihan_skenario(data: DataTiruan, *skenario: str) -> set[int]:
    return {i for g in data.tabel["ground_truth"] if g["skenario"] in skenario for i in g["tagihan_ids"]}


def profil(data: DataTiruan) -> dict[str, str]:
    return {p["rs_id"]: p["profil"] for p in data.tabel["profil_rs"]}


def tagihan_kasus_sah(data: DataTiruan, *jenis: str) -> set[int]:
    return {i for k in data.tabel["kasus_sah"] if k["jenis"] in jenis for i in k["tagihan_ids"]}


def hari_lewat_sah(data: DataTiruan) -> set[tuple[str, str, object]]:
    """(rs, layanan, tanggal) kasus sah yang memang melewati kapasitas."""
    return {
        (k["rs_id"], KASUS_KAPASITAS[k["jenis"]], k["tanggal"])
        for k in data.tabel["kasus_sah"]
        if k["jenis"] in KASUS_KAPASITAS
    }


def hari_kap(data: DataTiruan) -> set[tuple[str, str, object]]:
    return {(g["rs_id"], KAP[g["skenario"]], g["tanggal"]) for g in data.tabel["ground_truth"] if g["skenario"] in KAP}


# ----------------------------------------------------------- reproduksibel


def test_seed_sama_menghasilkan_data_identik(utama):
    ulang = bangkitkan("utama", seed=42)
    assert sidik(ulang) == sidik(utama)
    assert ulang.tabel == utama.tabel


def test_seed_berbeda_menghasilkan_data_berbeda(utama):
    lain = bangkitkan("utama", seed=43)
    assert sidik(lain) != sidik(utama)


def test_identik_lintas_proses_dengan_hash_seed_berbeda():
    """Menangkap ketergantungan tak sengaja pada urutan iterasi set/str hash."""
    kode = (
        "from sentinel.generator.bangkit import bangkitkan;"
        "from sentinel.generator.ringkasan import sidik;"
        "print(sidik(bangkitkan('utama', seed=7, hari=35, jumlah_rs=20)))"
    )
    hasil = []
    for hash_seed in ("1", "2"):
        env = {**os.environ, "PYTHONHASHSEED": hash_seed}
        keluaran = subprocess.run(
            [sys.executable, "-c", kode], env=env, capture_output=True, text=True, check=True,
            cwd=Path(__file__).resolve().parents[1],
        )
        hasil.append(keluaran.stdout.strip())
    assert hasil[0] == hasil[1]


# ----------------------------------------------------------------- kapasitas


def test_rs_jujur_hanya_melewati_kapasitas_pada_hari_kasus_sah(dataset):
    kap = kapasitas(dataset)
    prof = profil(dataset)
    sah = hari_lewat_sah(dataset)
    for (rs, layanan, tgl), n in hitung_per_hari(dataset.tabel["tagihan"]).items():
        if prof[rs] != "disisipi" and layanan in ("fisioterapi", "hemodialisa"):
            assert (n > kap[rs][layanan]) == ((rs, layanan, tgl) in sah), (rs, layanan, tgl, n)


def test_tagihan_melewati_kapasitas_hanya_pada_hari_kap_atau_kasus_sah(dataset):
    kap = kapasitas(dataset)
    boleh_lewat = hari_kap(dataset) | hari_lewat_sah(dataset)
    for (rs, layanan, tgl), n in hitung_per_hari(dataset.tabel["tagihan"]).items():
        if layanan in ("fisioterapi", "hemodialisa"):
            assert (n > kap[rs][layanan]) == ((rs, layanan, tgl) in boleh_lewat), (rs, layanan, tgl, n)


def test_sesi_aktual_hanya_melewati_kapasitas_pada_hari_kasus_sah(dataset):
    kap = kapasitas(dataset)
    sah = hari_lewat_sah(dataset)
    for (rs, layanan, tgl), n in hitung_per_hari(dataset.tabel["sesi_aktual"]).items():
        assert (n > kap[rs][layanan]) == ((rs, layanan, tgl) in sah), (rs, layanan, tgl, n)


def test_hemodialisa_satu_sesi_per_pasien_per_hari_dan_satu_pasien_per_slot(dataset):
    sesi_hd = [s for s in dataset.tabel["sesi_aktual"] if s["layanan"] == "hemodialisa"]
    kap = {k["rs_id"]: k for k in dataset.tabel["kapasitas"]}
    assert all(s["mesin_id"] and s["shift"] for s in sesi_hd)
    assert max(Counter((s["pasien_id"], s["tanggal"]) for s in sesi_hd).values()) == 1
    assert max(Counter((s["mesin_id"], s["shift"], s["tanggal"]) for s in sesi_hd).values()) == 1
    shift_darurat = {(rs, tgl) for rs, layanan, tgl in hari_lewat_sah(dataset) if layanan == "hemodialisa"}
    for s in sesi_hd:
        batas = kap[s["rs_id"]]["shift_hd_per_hari"]
        if (s["rs_id"], s["tanggal"]) in shift_darurat:
            batas += 1  # shift darurat
        assert 1 <= s["shift"] <= batas, s
        assert s["tanggal"].weekday() < kap[s["rs_id"]]["hari_operasional_hd"]


def test_pasien_hemodialisa_dua_sampai_tiga_kali_per_minggu(dataset):
    per_minggu = Counter(
        (s["pasien_id"], s["tanggal"].isocalendar()[:2])
        for s in dataset.tabel["sesi_aktual"]
        if s["layanan"] == "hemodialisa"
    )
    assert max(per_minggu.values()) <= 3


def test_utilisasi_normal_dan_kontrol_sibuk(dataset):
    kap = kapasitas(dataset)
    prof = profil(dataset)
    sesi = hitung_per_hari(dataset.tabel["sesi_aktual"])
    sah = hari_lewat_sah(dataset)
    rasio = defaultdict(list)
    for (rs, layanan, tgl), n in sesi.items():
        if tgl.weekday() < 5 and (rs, layanan, tgl) not in sah:  # Senin-Jumat, di luar kasus sah
            rasio[(rs, layanan)].append(n / kap[rs][layanan])
    for (rs, layanan), nilai in rasio.items():
        rata = sum(nilai) / len(nilai)
        if prof[rs] == "jujur_sibuk":
            assert rata >= 0.95 and max(nilai) <= 1.0, (rs, layanan, rata)
        else:
            assert 0.50 <= rata <= 0.95 and max(nilai) <= 0.95, (rs, layanan, rata, max(nilai))


def test_kontrol_ada_dan_tidak_pernah_disisipi(dataset):
    prof = profil(dataset)
    sk = skenario_per_rs(dataset)
    rs = {x["id"]: x for x in dataset.tabel["rumah_sakit"]}
    sibuk = [r for r, p in prof.items() if p == "jujur_sibuk"]
    volume = [r for r, p in prof.items() if p == "jujur_volume_tinggi"]
    assert len(sibuk) >= 2
    assert len(volume) == 1 and rs[volume[0]]["kelas"] == "A"
    for r, p in prof.items():
        assert (p == "disisipi") == bool(sk[r]), r
    # Rumah sakit volume tinggi punya tagihan terbanyak di antara kelas A.
    jumlah = Counter(t["rs_id"] for t in dataset.tabel["tagihan"])
    kelas_a = [r for r, x in rs.items() if x["kelas"] == "A"]
    assert max(kelas_a, key=lambda r: jumlah[r]) == volume[0]


def test_sensor_dan_sebaran_skenario(dataset):
    prof = profil(dataset)
    sk = skenario_per_rs(dataset)
    rs = {x["id"]: x for x in dataset.tabel["rumah_sakit"]}
    sensor = [r for r, x in rs.items() if x["punya_sensor"]]
    assert len(sensor) == 10
    assert sum(prof[r] != "disisipi" for r in sensor) >= 4
    assert all(rs[r]["punya_sensor"] for r in sk if "SENSOR_PALSU" in sk[r])
    disisipi = [r for r, p in prof.items() if p == "disisipi"]
    assert 7 <= len(disisipi) <= 10


# ----------------------------------------------------- sesi aktual vs tagihan


def test_tagihan_hd_nyata_berpasangan_dan_fiktif_tidak(dataset):
    fiktif_tanpa_sesi = tagihan_skenario(dataset, *FIKTIF_HD)
    ganda = tagihan_skenario(dataset, "ULANG_HARI")
    kunci = lambda x: (x["rs_id"], x["pasien_id"], x["tanggal"])  # noqa: E731
    sesi = Counter(kunci(s) for s in dataset.tabel["sesi_aktual"] if s["layanan"] == "hemodialisa")
    hd = [t for t in dataset.tabel["tagihan"] if t["layanan"] == "hemodialisa"]
    nyata = Counter(kunci(t) for t in hd if t["id"] not in fiktif_tanpa_sesi | ganda)

    # Setiap tagihan HD nyata punya tepat satu sesi aktual, dan sebaliknya.
    assert nyata == sesi
    for t in hd:
        if t["id"] in fiktif_tanpa_sesi:
            assert sesi[kunci(t)] == 0, t  # fiktif: tidak ada sesi sama sekali
        if t["id"] in ganda:
            assert sesi[kunci(t)] == 1, t  # sesi kedua di hari yang sama tidak terjadi


def test_sensor_palsu_tidak_melebihi_kapasitas(dataset):
    kap = kapasitas(dataset)
    per_hari = hitung_per_hari(dataset.tabel["tagihan"])
    for g in dataset.tabel["ground_truth"]:
        if g["skenario"] == "SENSOR_PALSU":
            assert per_hari[(g["rs_id"], "hemodialisa", g["tanggal"])] <= kap[g["rs_id"]]["hemodialisa"]


# -------------------------------------------------------------- ground truth


def test_ground_truth_merujuk_tagihan_yang_ada(dataset):
    tagihan = {t["id"]: t for t in dataset.tabel["tagihan"]}
    for g in dataset.tabel["ground_truth"]:
        assert g["tagihan_ids"], g
        for i in g["tagihan_ids"]:
            t = tagihan[i]
            assert (t["rs_id"], t["tanggal"], t["dataset_id"]) == (g["rs_id"], g["tanggal"], g["dataset_id"])


def test_setiap_skenario_muncul_di_kedua_dataset(utama, hidden):
    for data in (utama, hidden):
        muncul = Counter(g["skenario"] for g in data.tabel["ground_truth"])
        assert all(muncul[sk] >= 1 for sk in SKENARIO), (data.dataset_id, muncul)


def test_besaran_kap_acak_termasuk_yang_halus(dataset):
    kap = kapasitas(dataset)
    per_hari = hitung_per_hari(dataset.tabel["tagihan"])
    lebih = []
    for g in dataset.tabel["ground_truth"]:
        if g["skenario"] in ("KAP_FISIO", "KAP_HD"):
            layanan = "fisioterapi" if g["skenario"] == "KAP_FISIO" else "hemodialisa"
            n, c = per_hari[(g["rs_id"], layanan, g["tanggal"])], kap[g["rs_id"]][layanan]
            lebih.append((n - c, (n - c) / c))
    assert any(sesi <= 2 for sesi, _ in lebih), "harus ada kejadian KAP yang sangat halus"
    assert all(sesi >= 1 and persen <= 0.85 for sesi, persen in lebih)
    assert len({round(p, 2) for _, p in lebih}) > len(lebih) / 3, "besaran tidak boleh seragam"


def test_harga_normal_dalam_toleransi_dan_harga_lebih_di_atasnya(dataset):
    acuan = {h["kode_item"]: h["harga"] for h in dataset.tabel["harga_acuan"]}
    toleransi = PARAM.kewajaran.toleransi_harga_di_atas_acuan_persen / 100
    lebih = tagihan_skenario(dataset, "HARGA_LEBIH")
    acuan_lama = tagihan_kasus_sah(dataset, "HARGA_ACUAN_LAMA")
    for t in dataset.tabel["tagihan"]:
        if t["kode_item"] is None:
            continue
        rasio = t["harga_satuan"] / acuan[t["kode_item"]] - 1
        if t["id"] in lebih:
            assert rasio > toleransi + 0.01, t
        elif t["id"] in acuan_lama:
            assert toleransi < rasio <= toleransi + 0.05, t  # sah, tapi di atas toleransi
        else:
            assert rasio <= toleransi, t
        assert t["total"] == t["jumlah"] * t["harga_satuan"]


def test_alat_bantu_dengar_normal_lewat_masa_penggantian_dan_abd_dini_belum(dataset):
    masa_hari = PARAM.kewajaran.alat_bantu_dengar_masa_penggantian_tahun * 365.25
    dini = tagihan_skenario(dataset, "ABD_DINI")
    riwayat = defaultdict(list)
    for r in dataset.tabel["riwayat_alat_bantu_dengar"]:
        riwayat[(r["pasien_id"], r["sisi_telinga"])].append(r["tanggal_diberikan"])
    abd = [t for t in dataset.tabel["tagihan"] if t["layanan"] == "alat_bantu_dengar"]
    assert all(t["sisi_telinga"] in ("kiri", "kanan") for t in abd)
    assert max(Counter((t["pasien_id"], t["sisi_telinga"]) for t in abd).values()) == 1
    for t in abd:
        sebelumnya = [d for d in riwayat[(t["pasien_id"], t["sisi_telinga"])] if d < t["tanggal"]]
        jarak = (t["tanggal"] - max(sebelumnya)).days if sebelumnya else None
        if t["id"] in dini:
            assert jarak is not None and jarak < masa_hari, t
        else:
            assert jarak is None or jarak >= masa_hari, t


def test_riwayat_abd_mencakup_enam_tahun_ke_belakang(dataset):
    tanggal = [r["tanggal_diberikan"] for r in dataset.tabel["riwayat_alat_bantu_dengar"]]
    awal = dataset.mulai
    assert min(tanggal) >= awal.replace(year=awal.year - 6)
    assert (awal - min(tanggal)).days > 5.5 * 365


def test_id_tagihan_tidak_membocorkan_penyisipan(dataset):
    """ID diberikan setelah penyisipan dan diacak di dalam (rumah sakit, tanggal)."""
    tagihan = dataset.tabel["tagihan"]
    assert [t["tanggal"] for t in tagihan] == sorted(t["tanggal"] for t in tagihan)
    blok = defaultdict(list)
    for t in tagihan:
        blok[(t["rs_id"], t["tanggal"])].append(t["id"])
    di_ujung = 0
    kejadian = [g for g in dataset.tabel["ground_truth"] if g["skenario"] in ("KAP_FISIO", "KAP_HD")]
    for g in kejadian:
        ids = sorted(blok[(g["rs_id"], g["tanggal"])])
        di_ujung += sorted(g["tagihan_ids"]) == ids[-len(g["tagihan_ids"]):]
    assert di_ujung < len(kejadian) / 2


# ---------------------------------------------------------------- kasus sah


def test_kasus_sah_ada_di_kedua_dataset_dengan_jumlah_sesuai(utama, hidden):
    for data in (utama, hidden):
        kasus = data.tabel["kasus_sah"]
        hari = Counter(k["jenis"] for k in kasus)
        assert 2 <= hari["HD_SHIFT_TAMBAHAN"] <= 4, data.dataset_id
        assert 2 <= hari["FISIO_LEMBUR"] <= 4, data.dataset_id
        assert 5 <= len(tagihan_kasus_sah(data, "HARGA_ACUAN_LAMA")) <= 10, data.dataset_id
        assert {k["jenis"] for k in kasus} == set(JENIS_KASUS_SAH)


def test_kasus_sah_hanya_di_rs_jujur_atau_sibuk(dataset):
    prof = profil(dataset)
    for k in dataset.tabel["kasus_sah"]:
        assert prof[k["rs_id"]] in ("jujur", "jujur_sibuk"), k


def test_kasus_sah_tidak_bertumpuk_dengan_kejadian_kecurangan(dataset):
    hari_kejadian = {(g["rs_id"], g["tanggal"]) for g in dataset.tabel["ground_truth"]}
    tagihan_gt = tagihan_skenario(dataset, *SKENARIO)
    for k in dataset.tabel["kasus_sah"]:
        assert (k["rs_id"], k["tanggal"]) not in hari_kejadian, k
        assert not set(k["tagihan_ids"]) & tagihan_gt, k


def test_kasus_sah_merujuk_tagihan_yang_ada(dataset):
    tagihan = {t["id"]: t for t in dataset.tabel["tagihan"]}
    for k in dataset.tabel["kasus_sah"]:
        assert k["tagihan_ids"], k
        for i in k["tagihan_ids"]:
            assert (tagihan[i]["rs_id"], tagihan[i]["tanggal"]) == (k["rs_id"], k["tanggal"])


def test_kasus_sah_kapasitas_benar_terjadi_dan_besarannya_sesuai(dataset):
    kap = kapasitas(dataset)
    kunci = lambda x: (x["rs_id"], x["pasien_id"], x["tanggal"], x["layanan"])  # noqa: E731
    sesi = Counter(kunci(s) for s in dataset.tabel["sesi_aktual"])
    tagihan = {t["id"]: t for t in dataset.tabel["tagihan"]}
    per_hari = hitung_per_hari(dataset.tabel["tagihan"])
    sesi_per_hari = hitung_per_hari(dataset.tabel["sesi_aktual"])
    batas_lebih = {"HD_SHIFT_TAMBAHAN": (1, 2), "FISIO_LEMBUR": (1, 3)}
    for k in dataset.tabel["kasus_sah"]:
        if k["jenis"] not in KASUS_KAPASITAS:
            continue
        layanan = KASUS_KAPASITAS[k["jenis"]]
        for i in k["tagihan_ids"]:
            assert sesi[kunci(tagihan[i])] == 1, tagihan[i]  # punya pasangan di sesi_aktual
        hari = (k["rs_id"], layanan, k["tanggal"])
        lebih = per_hari[hari] - kap[k["rs_id"]][layanan]
        lo, hi = batas_lebih[k["jenis"]]
        assert lo <= lebih <= hi, (k, lebih)
        assert sesi_per_hari[hari] == per_hari[hari]  # semua tagihan hari itu nyata


# ------------------------------------------------------------ struktur data


def test_setiap_kombinasi_kelas_provinsi_minimal_tiga_rs(dataset):
    kombinasi = Counter((x["kelas"], x["provinsi"]) for x in dataset.tabel["rumah_sakit"])
    assert min(kombinasi.values()) >= 3, kombinasi
    assert {k for k, _ in kombinasi} == {"A", "B", "C", "D"}


POLA_MIRIP_NIK = re.compile(r"\d{16}")
POLA_MIRIP_KARTU = re.compile(r"\d{13}")


def test_tidak_ada_id_menyerupai_nik_atau_nomor_kartu(dataset):
    for nama, baris in dataset.tabel.items():
        for x in baris:
            for kolom, nilai in x.items():
                teks = str(nilai)
                assert not POLA_MIRIP_NIK.search(teks), (nama, kolom, teks)
                assert not POLA_MIRIP_KARTU.search(teks), (nama, kolom, teks)
    assert all(re.fullmatch(r"P-\d{6}", p["id_pseudonim"]) for p in dataset.tabel["pasien"])


def test_data_utama_dan_hidden_tidak_tercampur(utama, hidden):
    for data in (utama, hidden):
        for nama, baris in data.tabel.items():
            assert all(x["dataset_id"] == data.dataset_id for x in baris), nama
        rs = {x["id"] for x in data.tabel["rumah_sakit"]}
        pasien = {x["id_pseudonim"] for x in data.tabel["pasien"]}
        for nama in ("tagihan", "sesi_aktual"):
            assert all(x["rs_id"] in rs and x["pasien_id"] in pasien for x in data.tabel[nama])
        assert all(x["pasien_id"] in pasien for x in data.tabel["riwayat_alat_bantu_dengar"])

    kunci_id = {
        "rumah_sakit": "id", "pasien": "id_pseudonim", "tagihan": "id", "sesi_aktual": "id",
        "ground_truth": "id", "riwayat_alat_bantu_dengar": "id", "kasus_sah": "id",
    }
    for nama, kolom in kunci_id.items():
        a = {x[kolom] for x in utama.tabel[nama]}
        b = {x[kolom] for x in hidden.tabel[nama]}
        assert len(a) == len(utama.tabel[nama]) and len(b) == len(hidden.tabel[nama]), nama
        assert not a & b, nama


def test_hidden_memakai_seed_dan_distribusi_berbeda(utama, hidden):
    assert (utama.seed, hidden.seed) == (42, 2026)
    jumlah_disisipi = lambda d: sum(p["profil"] == "disisipi" for p in d.tabel["profil_rs"])  # noqa: E731
    assert jumlah_disisipi(utama) != jumlah_disisipi(hidden)


def test_validasi_argumen():
    with pytest.raises(ValueError, match="minimal"):
        bangkitkan("utama", jumlah_rs=10)
    with pytest.raises(ValueError, match="minimal"):
        bangkitkan("utama", hari=7)
    with pytest.raises(ValueError, match="tidak dikenal"):
        bangkitkan("lain")


# ----------------------------------------------------------------------- CLI


def test_cli_dry_run_mencetak_ringkasan(capsys):
    assert main(["--hidden", "--rs", "20", "--days", "35", "--dry-run"]) == 0
    keluaran = capsys.readouterr().out
    assert "Dataset hidden" in keluaran
    for sk in SKENARIO:
        assert sk in keluaran
    assert "tidak ada yang ditulis" in keluaran


def test_cli_menolak_hidden_bersama_dataset_utama(capsys):
    assert main(["--hidden", "--dataset", "utama", "--dry-run"]) == 2
