"""Fungsi metrik evaluasi (murni, tanpa basis data).

Definisi pencocokan:
- Aturan per hari (KAP-01, KAP-02, SEN-01): kejadian tertangkap bila ada temuan aturan
  pasangannya (dan kategori, untuk SEN-01) pada RS dan tanggal yang sama.
- Aturan per tagihan (ULG-01, ULG-02, WJR-01, WJR-02): kejadian tertangkap bila ada temuan
  aturan pasangannya yang memuat salah satu tagihan kejadian itu.
- Klasifikasi temuan untuk presisi: "benar" bila memuat tagihan kejadian kecurangan mana pun
  (atau, untuk temuan integritas tanpa tagihan, jatuh pada RS-tanggal kejadian gangguan sensor);
  "kasus_sah" bila tidak benar tetapi memuat tagihan kasus sah; selain itu "keliru".
"""

import math
from collections import Counter, defaultdict
from datetime import date

Z95 = 1.959963984540054

# Skenario -> (aturan pasangan, kategori temuan). BAND-01 sengaja tidak dipetakan.
PEMETAAN: dict[str, tuple[str, str | None]] = {
    "KAP_FISIO": ("KAP-01", None),
    "KAP_HD": ("KAP-02", None),
    "ULANG_IDENTIK": ("ULG-01", None),
    "ULANG_HARI": ("ULG-02", None),
    "HARGA_LEBIH": ("WJR-01", None),
    "ABD_DINI": ("WJR-02", None),
    "SENSOR_PALSU": ("SEN-01", "selisih"),
    "TAMPER_SIG": ("SEN-01", "integritas"),
    "TAMPER_GAP": ("SEN-01", "integritas"),
}
SKENARIO_TAMPER = ("TAMPER_SIG", "TAMPER_GAP")
SKENARIO_KECURANGAN = tuple(s for s in PEMETAAN if s not in SKENARIO_TAMPER)
ATURAN_PER_TAGIHAN = {"ULG-01", "ULG-02", "WJR-01", "WJR-02"}
ATURAN = ("KAP-01", "KAP-02", "ULG-01", "ULG-02", "WJR-01", "WJR-02", "SEN-01")
PRIORITAS = ("tinggi", "sedang", "rendah")
KONDISI = ("bermasalah", "gangguan_sensor", "hanya_kasus_sah", "bersih")
PROFIL_JUJUR = ("jujur", "jujur_sibuk", "jujur_volume_tinggi")


# --------------------------------------------------------------- proporsi


def wilson(k: int, n: int, z: float = Z95) -> tuple[float, float] | tuple[None, None]:
    """Interval kepercayaan Wilson untuk proporsi k/n."""
    if n == 0:
        return None, None
    p = k / n
    penyebut = 1 + z * z / n
    tengah = (p + z * z / (2 * n)) / penyebut
    lebar = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / penyebut
    return max(0.0, tengah - lebar), min(1.0, tengah + lebar)


def proporsi(k: int, n: int) -> dict:
    lo, hi = wilson(k, n)
    return {
        "pembilang": k,
        "penyebut": n,
        "nilai": None if n == 0 else round(k / n, 4),
        "ci95": None if n == 0 else [round(lo, 4), round(hi, 4)],
    }


def periode_dari(d: date) -> str:
    return f"{d.year:04d}-{d.month:02d}"


# ------------------------------------------------------------- pencocokan


class Indeks:
    def __init__(self, temuan: list[dict]):
        self.per_hari: set[tuple] = set()
        self.per_tagihan: dict[tuple, set[int]] = defaultdict(set)
        self.semua_tagihan: set[int] = set()
        self.sen_hari: set[tuple] = set()
        for t in temuan:
            if t["aturan_id"] == "BAND-01":
                continue
            kunci = (t["aturan_id"], t.get("kategori"))
            if t["tanggal"] is not None:
                self.per_hari.add((*kunci, t["rs_id"], t["tanggal"]))
                if t["aturan_id"] == "SEN-01":
                    self.sen_hari.add((t["rs_id"], t["tanggal"]))
            self.per_tagihan[kunci].update(t["tagihan_ids"])
            self.semua_tagihan.update(t["tagihan_ids"])


def tertangkap(kejadian: dict, indeks: Indeks) -> bool:
    aturan, kategori = PEMETAAN[kejadian["skenario"]]
    if aturan in ATURAN_PER_TAGIHAN:
        return bool(set(kejadian["tagihan_ids"]) & indeks.per_tagihan.get((aturan, kategori), set()))
    return (aturan, kategori, kejadian["rs_id"], kejadian["tanggal"]) in indeks.per_hari


def tertangkap_apa_pun(kejadian: dict, indeks: Indeks) -> bool:
    if kejadian["tagihan_ids"]:
        return bool(set(kejadian["tagihan_ids"]) & indeks.semua_tagihan)
    return (kejadian["rs_id"], kejadian["tanggal"]) in indeks.sen_hari


def recall_per_skenario(ground_truth: list[dict], temuan: list[dict]) -> dict[str, dict]:
    indeks = Indeks(temuan)
    hasil = {}
    for skenario, (aturan, kategori) in PEMETAAN.items():
        kejadian = [g for g in ground_truth if g["skenario"] == skenario]
        hasil[skenario] = {
            "aturan": aturan + (f" ({kategori})" if kategori else ""),
            "recall": proporsi(sum(tertangkap(g, indeks) for g in kejadian), len(kejadian)),
            "tertangkap_aturan_apa_pun": proporsi(sum(tertangkap_apa_pun(g, indeks) for g in kejadian), len(kejadian)),
        }
    return hasil


def recall_gabungan(ground_truth: list[dict], temuan: list[dict], skenario: tuple[str, ...]) -> dict:
    indeks = Indeks(temuan)
    kejadian = [g for g in ground_truth if g["skenario"] in skenario]
    return proporsi(sum(tertangkap(g, indeks) for g in kejadian), len(kejadian))


def klasifikasi_temuan(temuan: list[dict], ground_truth: list[dict], kasus_sah: list[dict]) -> list[str]:
    tagihan_curang = {i for g in ground_truth if g["skenario"] not in SKENARIO_TAMPER for i in g["tagihan_ids"]}
    hari_tamper = {(g["rs_id"], g["tanggal"]) for g in ground_truth if g["skenario"] in SKENARIO_TAMPER}
    tagihan_sah = {i for k in kasus_sah for i in k["tagihan_ids"]}
    kelas = []
    for t in temuan:
        ids = set(t["tagihan_ids"])
        if ids & tagihan_curang or (not ids and (t["rs_id"], t["tanggal"]) in hari_tamper):
            kelas.append("benar")
        elif ids & tagihan_sah:
            kelas.append("kasus_sah")
        else:
            kelas.append("keliru")
    return kelas


def presisi_per_aturan(temuan: list[dict], ground_truth: list[dict], kasus_sah: list[dict]) -> dict[str, dict]:
    """Tiga kelas per aturan (BAND-01 dilaporkan terpisah). SEN-01 dipecah per kategori."""
    harian = [t for t in temuan if t["aturan_id"] != "BAND-01"]
    kelas = klasifikasi_temuan(harian, ground_truth, kasus_sah)
    hitung: dict[str, Counter] = defaultdict(Counter)
    for t, k in zip(harian, kelas):
        nama = t["aturan_id"] if t["aturan_id"] != "SEN-01" else f"SEN-01 ({t.get('kategori')})"
        hitung[nama][k] += 1
    urutan = [a for a in ATURAN if a != "SEN-01"] + ["SEN-01 (selisih)", "SEN-01 (integritas)"]
    hasil = {}
    for nama in urutan:
        c = hitung.get(nama, Counter())
        total = sum(c.values())
        hasil[nama] = {
            "jumlah_temuan": total,
            "benar": proporsi(c["benar"], total),
            "kasus_sah": proporsi(c["kasus_sah"], total),
            "keliru": proporsi(c["keliru"], total),
        }
    return hasil


# ----------------------------------------------------------- RS-periode


def kondisi_rs_periode(
    skor: list[dict], ground_truth: list[dict], kasus_sah: list[dict], pisahkan_tamper: bool = True
) -> dict[tuple[str, str], str]:
    """bermasalah > gangguan_sensor > hanya_kasus_sah > bersih. Bila `pisahkan_tamper` False,
    RS-periode yang hanya berisi gangguan sensor dihitung sebagai 'bersih' (definisi harfiah)."""
    curang = {(g["rs_id"], periode_dari(g["tanggal"])) for g in ground_truth if g["skenario"] not in SKENARIO_TAMPER}
    tamper = {(g["rs_id"], periode_dari(g["tanggal"])) for g in ground_truth if g["skenario"] in SKENARIO_TAMPER}
    sah = {(k["rs_id"], periode_dari(k["tanggal"])) for k in kasus_sah}
    hasil = {}
    for s in skor:
        kunci = (s["rs_id"], s["periode"])
        if kunci in curang:
            hasil[kunci] = "bermasalah"
        elif pisahkan_tamper and kunci in tamper:
            hasil[kunci] = "gangguan_sensor"
        elif kunci in sah:
            hasil[kunci] = "hanya_kasus_sah"
        else:
            hasil[kunci] = "bersih"
    return hasil


def urutan_petugas(skor: list[dict]) -> list[dict]:
    """Urutan yang dilihat petugas: prioritas tertinggi dulu, lalu skor, lalu ID."""
    peringkat = {p: i for i, p in enumerate(PRIORITAS)}
    return sorted(skor, key=lambda s: (peringkat[s["prioritas"]], -s["skor"], s["rs_id"], s["periode"]))


def metrik_prioritas(skor: list[dict], kondisi: dict[tuple[str, str], str], profil: dict[str, str]) -> dict:
    def k(s):
        return kondisi[(s["rs_id"], s["periode"])]

    bermasalah = [s for s in skor if k(s) == "bermasalah"]
    tinggi = [s for s in skor if s["prioritas"] == "tinggi"]
    ditandai = [s for s in skor if s["prioritas"] in ("tinggi", "sedang")]
    urut = urutan_petugas(skor)
    matriks = {p: {c: 0 for c in KONDISI} for p in PRIORITAS}
    for s in skor:
        matriks[s["prioritas"]][k(s)] += 1
    per_profil: dict[str, dict[str, int]] = {}
    for s in skor:
        per_profil.setdefault(profil[s["rs_id"]], {p: 0 for p in PRIORITAS})[s["prioritas"]] += 1
    jujur = [s for s in skor if profil[s["rs_id"]] in PROFIL_JUJUR]
    return {
        "jumlah_rs_periode": len(skor),
        "jumlah_per_kondisi": {c: sum(k(s) == c for s in skor) for c in KONDISI},
        "tinggi": {
            "presisi": proporsi(sum(k(s) == "bermasalah" for s in tinggi), len(tinggi)),
            "recall": proporsi(sum(s["prioritas"] == "tinggi" for s in bermasalah), len(bermasalah)),
        },
        "tinggi_sedang": {
            "presisi": proporsi(sum(k(s) == "bermasalah" for s in ditandai), len(ditandai)),
            "recall": proporsi(sum(s["prioritas"] in ("tinggi", "sedang") for s in bermasalah), len(bermasalah)),
        },
        "top_5": proporsi(sum(k(s) == "bermasalah" for s in urut[:5]), min(5, len(urut))),
        "top_10": proporsi(sum(k(s) == "bermasalah" for s in urut[:10]), min(10, len(urut))),
        "matriks_prioritas_kondisi": matriks,
        "sebaran_per_profil": per_profil,
        "ditandai": {
            "tuduhan_keliru": proporsi(sum(k(s) == "bersih" for s in ditandai), len(ditandai)),
            "kasus_sah_perlu_klarifikasi": proporsi(sum(k(s) == "hanya_kasus_sah" for s in ditandai), len(ditandai)),
            "gangguan_sensor": proporsi(sum(k(s) == "gangguan_sensor" for s in ditandai), len(ditandai)),
        },
        "rs_jujur_ikut_ditandai": proporsi(sum(s["prioritas"] in ("tinggi", "sedang") for s in jujur), len(jujur)),
        "daftar_tinggi": [
            {"rs_id": s["rs_id"], "periode": s["periode"], "skor": s["skor"],
             "alasan_prioritas": s.get("alasan_prioritas"), "kondisi": k(s), "profil": profil[s["rs_id"]]}
            for s in urut if s["prioritas"] == "tinggi"
        ],
    }


# ------------------------------------------------------ integritas & BAND


def integritas_sensor(ground_truth: list[dict], temuan: list[dict], anomali: list[dict], rs_perangkat: dict[str, str]) -> dict:
    indeks = Indeks(temuan)
    hasil = {}
    for skenario in SKENARIO_TAMPER:
        kejadian = [g for g in ground_truth if g["skenario"] == skenario]
        hasil[skenario] = proporsi(sum(tertangkap(g, indeks) for g in kejadian), len(kejadian))
    kejadian = {(g["skenario"], g["rs_id"], g["tanggal"]) for g in ground_truth if g["skenario"] in SKENARIO_TAMPER}
    tanpa = [
        a for a in anomali
        if (a["jenis"], rs_perangkat.get(a["device_id"]), a["waktu"].date()) not in kejadian
    ]
    hasil["jumlah_anomali"] = len(anomali)
    hasil["anomali_tanpa_kejadian"] = len(tanpa)
    hasil["anomali_tanpa_kejadian_per_jenis"] = dict(Counter(a["jenis"] for a in tanpa))
    return hasil


def ringkasan_band(temuan: list[dict], kondisi: dict[tuple[str, str], str], profil: dict[str, str]) -> dict:
    band = [t for t in temuan if t["aturan_id"] == "BAND-01"]
    return {
        "jumlah_temuan": len(band),
        "per_kondisi_rs_periode": dict(Counter(kondisi.get((t["rs_id"], t["periode"]), "bersih") for t in band)),
        "per_profil_rs": dict(Counter(profil[t["rs_id"]] for t in band)),
        "pada_rs_periode_bermasalah": proporsi(
            sum(kondisi.get((t["rs_id"], t["periode"])) == "bermasalah" for t in band), len(band)
        ),
    }
