"""BAND-01: perbandingan utilisasi dengan rumah sakit sejenis (sinyal pendukung).

Utilisasi = rata-rata rasio harian (sesi ditagih ÷ kapasitas harian) per rumah sakit,
per layanan, per periode (bulan), dihitung atas hari yang punya tagihan layanan itu.
Hemodialisa hanya dihitung pada hari unit beroperasi; sesi pada hari tutup sudah
ditangani KAP-02.

Robust z = (x − median pembanding) ÷ (1,4826 × MAD pembanding), dengan leave-one-out:
rumah sakit yang dinilai tidak ikut menghitung pembandingnya. Pembanding utama adalah
kelas dan provinsi yang sama; jika kurang dari 3 RS atau MAD = 0, turun ke kelas yang
sama (semua provinsi); jika tetap tidak memadai, penilaian dilewati dan alasannya dicatat.
Hanya utilisasi yang lebih TINGGI dari pembanding yang ditandai.
"""

from collections import defaultdict
from dataclasses import dataclass
from statistics import median

from sentinel.parameter import Parameter
from sentinel.rules import teks
from sentinel.rules.aturan import hd_beroperasi, per_hari, periode_dari, temuan
from sentinel.rules.masukan import Masukan

LAYANAN_BANDING = ("fisioterapi", "hemodialisa")
KONSTANTA_MAD = 1.4826  # membuat MAD setara simpangan baku untuk data normal
PEMBANDING_MINIMUM = 3


@dataclass(frozen=True)
class Penilaian:
    rs_id: str
    layanan: str
    periode: str
    utilisasi: float
    z: float | None
    kelompok: str | None  # "kelas_provinsi", "kelas", atau None bila dilewati
    jumlah_pembanding: int
    median_pembanding: float | None
    alasan_dilewati: str | None


def robust_z(nilai: float, pembanding: list[float]) -> tuple[float | None, float, float]:
    """Kembalikan (z, median, MAD). z = None bila MAD = 0."""
    med = median(pembanding)
    mad = median(abs(v - med) for v in pembanding)
    if mad == 0:
        return None, med, mad
    return (nilai - med) / (KONSTANTA_MAD * mad), med, mad


def utilisasi(m: Masukan, p: Parameter) -> dict[tuple[str, str, str], float]:
    """(rs, layanan, periode) -> rata-rata rasio harian sesi ÷ kapasitas."""
    kap = {k["rs_id"]: k for k in m.kapasitas}
    sesi_per_terapis = p.kapasitas.fisioterapi_sesi_per_terapis_per_hari
    rasio: dict[tuple[str, str, str], list[float]] = defaultdict(list)
    for layanan in LAYANAN_BANDING:
        for (rs_id, tgl), daftar in sorted(per_hari(m, layanan).items()):
            k = kap[rs_id]
            if layanan == "fisioterapi":
                kapasitas = k["jumlah_fisioterapis"] * sesi_per_terapis
            else:
                if not hd_beroperasi(tgl, k["hari_operasional_hd"]):
                    continue
                kapasitas = k["jumlah_mesin_hd"] * k["shift_hd_per_hari"]
            if kapasitas > 0:
                rasio[(rs_id, layanan, periode_dari(tgl))].append(sum(t["jumlah"] for t in daftar) / kapasitas)
    return {kunci: sum(v) / len(v) for kunci, v in sorted(rasio.items())}


def nilai_banding(m: Masukan, p: Parameter) -> tuple[list[Penilaian], list[dict]]:
    ambang = p.perbandingan.ambang_robust_z
    rs = {x["id"]: x for x in m.rumah_sakit}
    util = utilisasi(m, p)
    per_kelompok: dict[tuple[str, str], list[tuple[str, float]]] = defaultdict(list)
    for (rs_id, layanan, periode), nilai in util.items():
        per_kelompok[(layanan, periode)].append((rs_id, nilai))

    penilaian: list[Penilaian] = []
    hasil: list[dict] = []
    for (layanan, periode), daftar in sorted(per_kelompok.items()):
        for rs_id, nilai in daftar:
            kelas, provinsi = rs[rs_id]["kelas"], rs[rs_id]["provinsi"]
            tingkat = [
                ("kelas_provinsi", f"kelas {kelas} {provinsi}",
                 [v for r, v in daftar if r != rs_id and rs[r]["kelas"] == kelas and rs[r]["provinsi"] == provinsi]),
                ("kelas", f"kelas {kelas} semua provinsi",
                 [v for r, v in daftar if r != rs_id and rs[r]["kelas"] == kelas]),
            ]
            alasan = []
            dinilai = None
            for nama, label, pembanding in tingkat:
                if len(pembanding) < PEMBANDING_MINIMUM:
                    alasan.append(f"{label}: pembanding {len(pembanding)} RS (< {PEMBANDING_MINIMUM})")
                    continue
                z, med, _ = robust_z(nilai, pembanding)
                if z is None:
                    alasan.append(f"{label}: MAD = 0")
                    continue
                dinilai = (nama, label, pembanding, z, med)
                break

            if dinilai is None:
                penilaian.append(Penilaian(rs_id, layanan, periode, nilai, None, None, 0, None, "; ".join(alasan)))
                continue
            nama, label, pembanding, z, med = dinilai
            penilaian.append(Penilaian(rs_id, layanan, periode, nilai, z, nama, len(pembanding), med, None))
            if z > ambang:
                turun = " (turun dari kelas-provinsi karena " + "; ".join(alasan) + ")" if alasan else ""
                hasil.append(temuan(
                    "BAND-01", rs_id, None, periode, layanan, [], z, ambang, z - ambang,
                    f"Utilisasi {layanan} {teks.periode(periode)} rata-rata {teks.persen(nilai)} kapasitas; "
                    f"pembanding {label} ({len(pembanding)} RS){turun} median {teks.persen(med)}. "
                    f"Robust z = {teks.angka(z, 2)}, di atas ambang {teks.bilangan(ambang)}. "
                    f"Sinyal pendukung, bukan bukti utama.",
                ))
    return penilaian, hasil
