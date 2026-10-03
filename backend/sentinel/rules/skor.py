"""Skor prioritas per rumah sakit per periode (bulan kalender).

skor = Σ bobot_aturan × keparahan_aturan, keparahan 0–1. Total bobot 100, jadi skor 0–100.
- KAP, ULG, WJR : keparahan = min(1, jumlah temuan dalam periode ÷ titik_jenuh).
- BAND-01       : keparahan = min(1, (z − ambang) ÷ ambang) bila z > ambang, selain itu 0;
                  diambil yang terbesar dari fisioterapi dan hemodialisa.
- SEN-01        : keparahan = maksimum dari keparahan selisih dan keparahan integritas,
                  masing-masing min(1, jumlah temuan kategori itu ÷ titik_jenuh kategorinya).

Prioritas: dari ambang skor, lalu LANTAI PRIORITAS: bila aturan bukti fisik
(`skor.aturan_bukti_fisik`, default KAP-01, KAP-02, SEN-01 selisih) jenuh dalam periode itu,
prioritas minimal "tinggi". Skor tidak berubah.
"""

from collections import Counter

from sentinel.parameter import KODE_ATURAN, Parameter
from sentinel.rules.aturan import periode_dari
from sentinel.rules.banding import Penilaian
from sentinel.rules.masukan import Masukan


def prioritas(skor: float, p: Parameter) -> str:
    if skor >= p.skor.prioritas.tinggi:
        return "tinggi"
    if skor >= p.skor.prioritas.sedang:
        return "sedang"
    return "rendah"


def _ambang(n: float) -> str:
    return f"{n:g}".replace(".", ",")


def prioritas_dengan_lantai(skor: float, keparahan: dict[str, float], p: Parameter) -> tuple[str, str]:
    """(prioritas, alasan). `keparahan` berkunci seperti titik_jenuh (mis. "KAP-02", "SEN-01-selisih")."""
    label = prioritas(skor, p)
    if label == "tinggi":
        alasan = f"ambang skor ≥ {_ambang(p.skor.prioritas.tinggi)}"
    elif label == "sedang":
        alasan = f"ambang skor ≥ {_ambang(p.skor.prioritas.sedang)}"
    else:
        alasan = f"skor di bawah ambang sedang ({_ambang(p.skor.prioritas.sedang)})"
    jenuh = [a for a in p.skor.aturan_bukti_fisik if keparahan.get(a, 0.0) >= 1.0]
    if jenuh:
        lantai = "lantai: " + ", ".join(f"{a} jenuh" for a in jenuh)
        alasan = lantai if label != "tinggi" else f"{alasan}; {lantai}"
        label = "tinggi"
    return label, alasan


def _keparahan_band(z: float | None, ambang: float) -> float:
    if z is None or z <= ambang:
        return 0.0
    return min(1.0, (z - ambang) / ambang)


def hitung_skor(m: Masukan, p: Parameter, temuan: list[dict], penilaian: list[Penilaian]) -> list[dict]:
    daftar_periode = sorted({periode_dari(t["tanggal"]) for t in m.tagihan})
    jumlah = Counter((t["rs_id"], t["periode"], t["aturan_id"]) for t in temuan)
    jumlah_sen = Counter((t["rs_id"], t["periode"], t["kategori"]) for t in temuan if t["aturan_id"] == "SEN-01")
    band: dict[tuple[str, str], list[Penilaian]] = {}
    for x in penilaian:
        band.setdefault((x.rs_id, x.periode), []).append(x)
    ambang = p.perbandingan.ambang_robust_z

    hasil = []
    for rs_id in sorted(r["id"] for r in m.rumah_sakit):
        for periode in daftar_periode:
            rincian: dict[str, dict] = {}
            per_kunci: dict[str, float] = {}
            total = 0.0
            for aturan in KODE_ATURAN:
                bobot = p.bobot_aturan[aturan]
                if aturan == "SEN-01":
                    detail, keparahan = {}, 0.0
                    for kategori in ("selisih", "integritas"):
                        n = jumlah_sen[(rs_id, periode, kategori)]
                        jenuh = p.skor.titik_jenuh[f"SEN-01-{kategori}"]
                        k = min(1.0, n / jenuh)
                        keparahan = max(keparahan, k)
                        per_kunci[f"SEN-01-{kategori}"] = k
                        detail[kategori] = {"jumlah_temuan": n, "titik_jenuh": jenuh, "keparahan": round(k, 4)}
                elif aturan == "BAND-01":
                    per_layanan = {
                        x.layanan: {
                            "utilisasi": round(x.utilisasi, 4),
                            "z": None if x.z is None else round(x.z, 4),
                            "kelompok": x.kelompok,
                            "jumlah_pembanding": x.jumlah_pembanding,
                            **({"dilewati": x.alasan_dilewati} if x.alasan_dilewati else {}),
                        }
                        for x in band.get((rs_id, periode), [])
                    }
                    keparahan = max(
                        (_keparahan_band(x.z, ambang) for x in band.get((rs_id, periode), [])), default=0.0
                    )
                    detail = {"per_layanan": per_layanan}
                else:
                    n = jumlah[(rs_id, periode, aturan)]
                    jenuh = p.skor.titik_jenuh[aturan]
                    keparahan = min(1.0, n / jenuh)
                    per_kunci[aturan] = keparahan
                    detail = {"jumlah_temuan": n, "titik_jenuh": jenuh}
                kontribusi = bobot * keparahan
                total += kontribusi
                rincian[aturan] = {
                    "bobot": bobot,
                    "keparahan": round(keparahan, 4),
                    "kontribusi": round(kontribusi, 4),
                    **detail,
                }
            skor = round(total, 2)
            label, alasan = prioritas_dengan_lantai(skor, per_kunci, p)
            hasil.append({
                "rs_id": rs_id,
                "periode": periode,
                "skor": skor,
                "prioritas": label,
                "alasan_prioritas": alasan,
                "rincian_per_aturan": rincian,
            })
    return hasil
