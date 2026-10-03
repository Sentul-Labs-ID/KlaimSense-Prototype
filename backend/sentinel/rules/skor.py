"""Skor prioritas per rumah sakit per periode (bulan kalender).

skor = Σ bobot_aturan × keparahan_aturan, keparahan 0–1. Total bobot 100, jadi skor 0–100.
- KAP, ULG, WJR : keparahan = min(1, jumlah temuan dalam periode ÷ titik_jenuh).
- BAND-01       : keparahan = min(1, (z − ambang) ÷ ambang) bila z > ambang, selain itu 0;
                  diambil yang terbesar dari fisioterapi dan hemodialisa.
- SEN-01        : keparahan 0 sampai fase 3 (skor maksimum sementara 80).
"""

from collections import Counter

from sentinel.parameter import KODE_ATURAN, Parameter
from sentinel.rules.aturan import periode_dari
from sentinel.rules.banding import Penilaian
from sentinel.rules.masukan import Masukan

ATURAN_BELUM_AKTIF = {"SEN-01": "belum aktif; diisi sensor di fase 3"}


def prioritas(skor: float, p: Parameter) -> str:
    if skor >= p.skor.prioritas.tinggi:
        return "tinggi"
    if skor >= p.skor.prioritas.sedang:
        return "sedang"
    return "rendah"


def _keparahan_band(z: float | None, ambang: float) -> float:
    if z is None or z <= ambang:
        return 0.0
    return min(1.0, (z - ambang) / ambang)


def hitung_skor(m: Masukan, p: Parameter, temuan: list[dict], penilaian: list[Penilaian]) -> list[dict]:
    daftar_periode = sorted({periode_dari(t["tanggal"]) for t in m.tagihan})
    jumlah = Counter((t["rs_id"], t["periode"], t["aturan_id"]) for t in temuan)
    band: dict[tuple[str, str], list[Penilaian]] = {}
    for x in penilaian:
        band.setdefault((x.rs_id, x.periode), []).append(x)
    ambang = p.perbandingan.ambang_robust_z

    hasil = []
    for rs_id in sorted(r["id"] for r in m.rumah_sakit):
        for periode in daftar_periode:
            rincian: dict[str, dict] = {}
            total = 0.0
            for aturan in KODE_ATURAN:
                bobot = p.bobot_aturan[aturan]
                if aturan in ATURAN_BELUM_AKTIF:
                    keparahan = 0.0
                    detail = {"catatan": ATURAN_BELUM_AKTIF[aturan]}
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
            hasil.append({
                "rs_id": rs_id,
                "periode": periode,
                "skor": skor,
                "prioritas": prioritas(skor, p),
                "rincian_per_aturan": rincian,
            })
    return hasil
