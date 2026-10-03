"""SEN-01: jam-mesin terapi tercatat sensor vs sesi hemodialisa yang ditagih (level hari).

Hanya membaca data yang diterima server dari perangkat (registri perangkat, ringkasan
harian status mesin, dan anomali ingest), serta tagihan. Dua kategori temuan:

- selisih    : jam_tercatat < jam_dibutuhkan x (1 - toleransi), dengan
               jam_dibutuhkan = jumlah tagihan HD hari itu x durasi sesi HD, dan
               jam_tercatat = menit terapi semua mesin RS itu ÷ 60. Tepat di batas tidak melanggar.
               TIDAK dihitung bila data sensor hari itu hilang melebihi batas (data bolong).
- integritas : hari dengan data bolong, serta setiap anomali TAMPER_SIG, TAMPER_CHAIN,
               dan TAMPER_GAP (dikelompokkan per perangkat, jenis, dan tanggal).
"""

from collections import defaultdict
from datetime import date, timedelta
from fractions import Fraction

from sentinel.parameter import Parameter
from sentinel.rules import teks
from sentinel.rules.aturan import periode_dari, temuan
from sentinel.rules.masukan import Masukan

MENIT_SEHARI = 24 * 60


def label_mesin(mesin_id: str) -> str:
    """'RS-001-HD03' -> 'HD-03'."""
    akhir = mesin_id.rsplit("-", 1)[-1]
    return f"{akhir[:2]}-{akhir[2:]}" if akhir[:2].isalpha() and akhir[2:].isdigit() else akhir


def jam(menit: Fraction | int) -> str:
    nilai = Fraction(menit) / 60
    return teks.angka(float(nilai), 0 if nilai.denominator == 1 else 1)


def _rentang(m: Masukan) -> list[date]:
    if not m.tagihan:
        return []
    awal = min(t["tanggal"] for t in m.tagihan)
    akhir = max(t["tanggal"] for t in m.tagihan)
    return [awal + timedelta(days=i) for i in range((akhir - awal).days + 1)]


def sen_01(m: Masukan, p: Parameter) -> list[dict]:
    perangkat = [x for x in m.perangkat if x["aktif"]]
    if not perangkat:
        return []
    durasi_menit = Fraction(str(p.kapasitas.hemodialisa_durasi_sesi_jam)) * 60
    toleransi = Fraction(str(p.sensor.toleransi_selisih_jam_mesin_persen)) / 100
    batas_hilang = Fraction(str(p.sensor.batas_data_hilang_persen)) / 100

    perangkat_rs: dict[str, list[dict]] = defaultdict(list)
    for x in perangkat:
        perangkat_rs[x["rs_id"]].append(x)
    mesin_rs = {x["mesin_id"]: x["rs_id"] for x in perangkat}
    device = {x["device_id"]: x for x in m.perangkat}

    terapi: dict[tuple[str, date], int] = defaultdict(int)
    tanpa_data: dict[tuple[str, date], int] = defaultdict(int)
    mesin_berdata: dict[tuple[str, date], set[str]] = defaultdict(set)
    for r in m.status_harian:
        rs_id = mesin_rs.get(r["mesin_id"])
        if rs_id is None:
            continue
        kunci = (rs_id, r["tanggal"])
        terapi[kunci] += r["menit_terapi"]
        tanpa_data[kunci] += r["menit_tanpa_data"]
        mesin_berdata[kunci].add(r["mesin_id"])

    tagihan_hd: dict[tuple[str, date], list[int]] = defaultdict(list)
    for t in m.tagihan:
        if t["layanan"] == "hemodialisa" and t["rs_id"] in perangkat_rs:
            tagihan_hd[(t["rs_id"], t["tanggal"])].append(t["id"])

    hasil = []
    for rs_id in sorted(perangkat_rs):
        n_perangkat = len(perangkat_rs[rs_id])
        for tgl in _rentang(m):
            kunci = (rs_id, tgl)
            hilang = tanpa_data[kunci] + MENIT_SEHARI * (n_perangkat - len(mesin_berdata[kunci]))
            porsi_hilang = Fraction(hilang, n_perangkat * MENIT_SEHARI)
            ids = tagihan_hd.get(kunci, [])
            if porsi_hilang > batas_hilang:
                hasil.append(temuan(
                    "SEN-01", rs_id, tgl, periode_dari(tgl), "hemodialisa", [], float(porsi_hilang),
                    float(batas_hilang), float(porsi_hilang - batas_hilang),
                    f"Data sensor hemodialisa {teks.tanggal(tgl)} hilang {teks.persen(float(porsi_hilang))} "
                    f"dari seharusnya (batas {teks.persen(float(batas_hilang), 0)}); "
                    f"selisih jam terapi tidak dihitung.",
                    kategori="integritas",
                ))
                continue
            if not ids:
                continue
            dibutuhkan = len(ids) * durasi_menit
            tercatat = Fraction(terapi[kunci])
            batas = dibutuhkan * (1 - toleransi)
            if tercatat < batas:
                hasil.append(temuan(
                    "SEN-01", rs_id, tgl, periode_dari(tgl), "hemodialisa", ids, float(tercatat / 60),
                    float(batas / 60), float((dibutuhkan - tercatat) / 60),
                    f"Hemodialisa {teks.tanggal(tgl)}: {len(ids)} sesi ditagih (butuh {jam(dibutuhkan)} jam-mesin "
                    f"terapi), sensor mencatat {jam(tercatat)} jam terapi. Selisih {jam(dibutuhkan - tercatat)} jam.",
                    kategori="selisih",
                ))

    # Anomali integritas pesan, dikelompokkan per (perangkat, jenis, tanggal).
    kelompok: dict[tuple[str, str, date], list[dict]] = defaultdict(list)
    for a in sorted(m.anomali_sensor, key=lambda a: (a["device_id"], a["waktu"], a["jenis"])):
        if a["device_id"] in device:
            kelompok[(a["device_id"], a["jenis"], a["waktu"].date())].append(a)
    for (device_id, jenis, tgl), daftar in sorted(kelompok.items()):
        d = device[device_id]
        mesin = label_mesin(d["mesin_id"])
        if jenis == "TAMPER_GAP":
            for a in daftar:
                menit = a["durasi_menit"] or 0
                hasil.append(temuan(
                    "SEN-01", d["rs_id"], tgl, periode_dari(tgl), "hemodialisa", [], menit, p.sensor.gap_maks_jendela,
                    menit, f"Sensor mesin {mesin} tidak mengirim data selama {_durasi(menit)} pada {teks.tanggal(tgl)}.",
                    kategori="integritas",
                ))
            continue
        if jenis == "TAMPER_SIG":
            kalimat = (
                f"Sensor mesin {mesin}: {len(daftar)} pesan dengan tanda tangan tidak sah ditolak "
                f"pada {teks.tanggal(tgl)}."
            )
        else:
            kalimat = f"Rantai pesan sensor mesin {mesin} terputus {len(daftar)} kali pada {teks.tanggal(tgl)}."
        hasil.append(temuan(
            "SEN-01", d["rs_id"], tgl, periode_dari(tgl), "hemodialisa", [], len(daftar), 0, len(daftar), kalimat,
            kategori="integritas",
        ))
    return hasil


def _durasi(menit: int) -> str:
    j, sisa = divmod(int(menit), 60)
    bagian = ([f"{j} jam"] if j else []) + ([f"{sisa} menit"] if sisa else [])
    return " ".join(bagian) or "0 menit"
