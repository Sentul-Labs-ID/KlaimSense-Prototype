"""Aturan harian dan per tagihan: KAP-01, KAP-02, ULG-01, ULG-02, WJR-01, WJR-02.

Semua batas dibaca dari parameter.yaml. Nilai yang tepat sama dengan batas TIDAK
dianggap melanggar. Setiap fungsi mengembalikan daftar temuan (dict) dengan
penjelasan dari template teks.
"""

from bisect import bisect_left
from collections import defaultdict
from datetime import date
from fractions import Fraction

from sentinel.parameter import Parameter
from sentinel.rules import teks
from sentinel.rules.masukan import Masukan


def temuan(
    aturan_id: str,
    rs_id: str,
    tanggal: date | None,
    periode: str,
    layanan: str,
    tagihan_ids: list[int],
    nilai_teramati: float,
    batas: float,
    selisih: float,
    penjelasan: str,
) -> dict:
    return {
        "aturan_id": aturan_id,
        "rs_id": rs_id,
        "tanggal": tanggal,
        "periode": periode,
        "layanan": layanan,
        "tagihan_ids": tagihan_ids,
        "nilai_teramati": float(nilai_teramati),
        "batas": float(batas),
        "selisih": float(selisih),
        "penjelasan": penjelasan,
    }


def periode_dari(d: date) -> str:
    return f"{d.year:04d}-{d.month:02d}"


def hd_beroperasi(tgl: date, hari_operasional_hd: int) -> bool:
    """Definisi yang sama dengan generator: unit buka pada `hari_operasional_hd` hari
    pertama dalam minggu, dihitung dari Senin. 6 = Senin-Sabtu, 7 = setiap hari."""
    return tgl.weekday() < hari_operasional_hd


def per_hari(m: Masukan, layanan: str) -> dict[tuple[str, date], list[dict]]:
    """Tagihan satu layanan dikelompokkan per (rumah sakit, tanggal), urut ID."""
    hasil: dict[tuple[str, date], list[dict]] = defaultdict(list)
    for t in m.tagihan:
        if t["layanan"] == layanan:
            hasil[(t["rs_id"], t["tanggal"])].append(t)
    return hasil


def _kapasitas(m: Masukan) -> dict[str, dict]:
    return {k["rs_id"]: k for k in m.kapasitas}


# ------------------------------------------------------------------ kapasitas


def kap_01(m: Masukan, p: Parameter) -> list[dict]:
    """Fisioterapi: sesi ditagih per hari > jumlah terapis x sesi wajar per terapis."""
    sesi_per_terapis = p.kapasitas.fisioterapi_sesi_per_terapis_per_hari
    kap = _kapasitas(m)
    hasil = []
    for (rs_id, tgl), daftar in sorted(per_hari(m, "fisioterapi").items()):
        terapis = kap[rs_id]["jumlah_fisioterapis"]
        batas = terapis * sesi_per_terapis
        n = sum(t["jumlah"] for t in daftar)
        if n > batas:
            hasil.append(temuan(
                "KAP-01", rs_id, tgl, periode_dari(tgl), "fisioterapi", [t["id"] for t in daftar],
                n, batas, n - batas,
                f"Fisioterapi {teks.tanggal(tgl)}: {n} sesi ditagih, kapasitas {batas} "
                f"({terapis} terapis × {sesi_per_terapis} sesi). Selisih {n - batas} sesi.",
            ))
    return hasil


def kap_02(m: Masukan, p: Parameter) -> list[dict]:
    """Hemodialisa: sesi ditagih per hari > mesin x shift, atau ada sesi saat unit tutup."""
    kap = _kapasitas(m)
    hasil = []
    for (rs_id, tgl), daftar in sorted(per_hari(m, "hemodialisa").items()):
        k = kap[rs_id]
        n = sum(t["jumlah"] for t in daftar)
        ids = [t["id"] for t in daftar]
        if not hd_beroperasi(tgl, k["hari_operasional_hd"]):
            hari_buka = f"{teks.HARI[0]}–{teks.HARI[k['hari_operasional_hd'] - 1]}"
            hasil.append(temuan(
                "KAP-02", rs_id, tgl, periode_dari(tgl), "hemodialisa", ids, n, 0, n,
                f"Hemodialisa {teks.hari_tanggal(tgl)}: {n} sesi ditagih pada hari unit tidak "
                f"beroperasi (unit buka {k['hari_operasional_hd']} hari, {hari_buka}). Selisih {n} sesi.",
            ))
            continue
        batas = k["jumlah_mesin_hd"] * k["shift_hd_per_hari"]
        if n > batas:
            hasil.append(temuan(
                "KAP-02", rs_id, tgl, periode_dari(tgl), "hemodialisa", ids, n, batas, n - batas,
                f"Hemodialisa {teks.tanggal(tgl)}: {n} sesi ditagih, kapasitas {batas} "
                f"({k['jumlah_mesin_hd']} mesin × {k['shift_hd_per_hari']} shift). Selisih {n - batas} sesi.",
            ))
    return hasil


# --------------------------------------------------------------- pengulangan


def ulg_01(m: Masukan, p: Parameter) -> list[dict]:
    """Tagihan identik: kombinasi (rs, pasien, tanggal, layanan, kode_item, jumlah,
    harga_satuan) muncul lebih dari sekali. Setiap salinan setelah yang pertama
    (urut ID) menjadi satu temuan."""
    kelompok: dict[tuple, list[dict]] = defaultdict(list)
    for t in m.tagihan:
        kunci = (t["rs_id"], t["pasien_id"], t["tanggal"], t["layanan"], t["kode_item"], t["jumlah"], t["harga_satuan"])
        kelompok[kunci].append(t)
    hasil = []
    for daftar in kelompok.values():
        if len(daftar) < 2:
            continue
        pertama = daftar[0]
        for ke, salinan in enumerate(daftar[1:], start=2):
            tgl = salinan["tanggal"]
            item = f" {salinan['kode_item']}" if salinan["kode_item"] else ""
            hasil.append(temuan(
                "ULG-01", salinan["rs_id"], tgl, periode_dari(tgl), salinan["layanan"],
                [pertama["id"], salinan["id"]], len(daftar), 1, 1,
                f"{teks.NAMA_LAYANAN[salinan['layanan']]}{item} {teks.tanggal(tgl)} pasien "
                f"{salinan['pasien_id']}: tagihan #{salinan['id']} identik dengan tagihan #{pertama['id']} "
                f"(jumlah {salinan['jumlah']}, harga satuan {teks.rupiah(salinan['harga_satuan'])}). "
                f"Salinan ke-{ke} dari {len(daftar)}.",
            ))
    return hasil


def ulg_02(m: Masukan, p: Parameter) -> list[dict]:
    """Sesi ganda: pasien yang sama punya > 1 tagihan hemodialisa di RS yang sama pada hari yang sama."""
    kelompok: dict[tuple, list[dict]] = defaultdict(list)
    for t in m.tagihan:
        if t["layanan"] == "hemodialisa":
            kelompok[(t["rs_id"], t["pasien_id"], t["tanggal"])].append(t)
    hasil = []
    for (rs_id, pasien_id, tgl), daftar in kelompok.items():
        n = len(daftar)
        if n > 1:
            hasil.append(temuan(
                "ULG-02", rs_id, tgl, periode_dari(tgl), "hemodialisa", [t["id"] for t in daftar],
                n, 1, n - 1,
                f"Hemodialisa {teks.tanggal(tgl)}: pasien {pasien_id} ditagih {n} sesi pada hari "
                f"yang sama; batas 1 sesi per hari. Selisih {n - 1} sesi.",
            ))
    return hasil


# ---------------------------------------------------------------- kewajaran


def wjr_01(m: Masukan, p: Parameter) -> list[dict]:
    """Harga satuan > harga acuan x (1 + toleransi). Dibandingkan secara eksak (pecahan)
    agar harga yang tepat di batas tidak tertandai karena galat pembulatan."""
    toleransi = Fraction(str(p.kewajaran.toleransi_harga_di_atas_acuan_persen))
    acuan = {h["kode_item"]: h for h in m.harga_acuan}
    hasil = []
    for t in m.tagihan:
        h = acuan.get(t["kode_item"]) if t["kode_item"] else None
        if h is None:
            continue
        batas = Fraction(h["harga"]) * (100 + toleransi) / 100
        harga = Fraction(t["harga_satuan"])
        if harga > batas:
            tgl = t["tanggal"]
            selisih = harga - batas
            hasil.append(temuan(
                "WJR-01", t["rs_id"], tgl, periode_dari(tgl), t["layanan"], [t["id"]],
                t["harga_satuan"], float(batas), float(selisih),
                f"{teks.NAMA_LAYANAN[t['layanan']]} {t['kode_item']} ({h['nama_item']}) {teks.tanggal(tgl)}: "
                f"harga satuan {teks.rupiah(t['harga_satuan'])}, harga acuan {teks.rupiah(h['harga'])}, "
                f"batas toleransi {teks.bilangan(float(toleransi))}% = {teks.rupiah(float(batas))}. "
                f"Lebih {teks.rupiah(float(selisih))} "
                f"({teks.persen(float(harga / h['harga'] - 1))} di atas harga acuan).",
            ))
    return hasil


def wjr_02(m: Masukan, p: Parameter) -> list[dict]:
    """Alat bantu dengar ditagih sebelum masa penggantian sejak pemberian sebelumnya
    untuk pasien dan telinga yang sama. Pemberian sebelumnya diambil dari riwayat
    (tanggal sebelum tagihan) dan tagihan alat bantu dengar sebelumnya (urut tanggal, ID).
    Masa penggantian dihitung dalam bulan kalender; tepat di batas tidak melanggar."""
    masa_tahun = p.kewajaran.alat_bantu_dengar_masa_penggantian_tahun
    masa_bulan = round(masa_tahun * 12)
    per_telinga = p.kewajaran.alat_bantu_dengar_per_telinga

    def kunci(pasien_id: str, sisi: str | None) -> tuple:
        return (pasien_id, sisi) if per_telinga else (pasien_id,)

    riwayat: dict[tuple, list[date]] = defaultdict(list)
    for r in m.riwayat_abd:
        riwayat[kunci(r["pasien_id"], r["sisi_telinga"])].append(r["tanggal_diberikan"])
    for daftar in riwayat.values():
        daftar.sort()

    abd = sorted((t for t in m.tagihan if t["layanan"] == "alat_bantu_dengar"), key=lambda t: (t["tanggal"], t["id"]))
    tagihan_terakhir: dict[tuple, dict] = {}
    hasil = []
    for t in abd:
        k = kunci(t["pasien_id"], t["sisi_telinga"])
        tgl = t["tanggal"]
        sebelumnya: tuple[date, int | None] | None = None
        daftar = riwayat.get(k, [])
        i = bisect_left(daftar, tgl)  # riwayat yang tanggalnya sebelum tagihan
        if i > 0:
            sebelumnya = (daftar[i - 1], None)
        if k in tagihan_terakhir:
            lalu = tagihan_terakhir[k]
            if sebelumnya is None or lalu["tanggal"] >= sebelumnya[0]:
                sebelumnya = (lalu["tanggal"], lalu["id"])
        tagihan_terakhir[k] = t
        if sebelumnya is None:
            continue
        tgl_lalu, id_lalu = sebelumnya
        batas_tgl = teks.tambah_bulan(tgl_lalu, masa_bulan)
        if tgl < batas_tgl:
            jarak, batas = (tgl - tgl_lalu).days, (batas_tgl - tgl_lalu).days
            ids = [t["id"]] if id_lalu is None else [id_lalu, t["id"]]
            telinga = f"telinga {t['sisi_telinga']} " if per_telinga else ""
            hasil.append(temuan(
                "WJR-02", t["rs_id"], tgl, periode_dari(tgl), "alat_bantu_dengar", ids,
                jarak, batas, batas - jarak,
                f"Alat bantu dengar {telinga}pasien {t['pasien_id']} ditagih "
                f"{teks.selang(tgl_lalu, tgl)} setelah pemberian sebelumnya; "
                f"masa penggantian {teks.bilangan(masa_tahun)} tahun.",
            ))
    return hasil


ATURAN_HARIAN = (kap_01, kap_02, ulg_01, ulg_02, wjr_01, wjr_02)
