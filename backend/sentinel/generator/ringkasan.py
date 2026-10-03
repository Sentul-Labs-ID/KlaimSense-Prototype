"""Ringkasan dan sidik (hash) dataset tiruan."""

import hashlib
import json
from collections import Counter

from sentinel.generator.bangkit import DataTiruan
from sentinel.models.evaluasi import JENIS_KASUS_SAH, PROFIL, SKENARIO
from sentinel.models.transaksi import LAYANAN


def ringkasan(data: DataTiruan) -> dict:
    t = data.tabel
    per_layanan = Counter(x["layanan"] for x in t["tagihan"])
    sesi_per_layanan = Counter(x["layanan"] for x in t["sesi_aktual"])
    per_skenario = Counter(x["skenario"] for x in t["ground_truth"])
    rs_per_skenario = {
        sk: len({x["rs_id"] for x in t["ground_truth"] if x["skenario"] == sk}) for sk in SKENARIO
    }
    profil = Counter(x["profil"] for x in t["profil_rs"])
    return {
        "dataset_id": data.dataset_id,
        "seed": data.seed,
        "periode": f"{data.mulai.isoformat()} s.d. {data.tabel['tagihan'][-1]['tanggal'].isoformat()}"
        if t["tagihan"]
        else data.mulai.isoformat(),
        "hari": data.hari,
        "rumah_sakit": len(t["rumah_sakit"]),
        "rs_punya_sensor": sum(x["punya_sensor"] for x in t["rumah_sakit"]),
        "profil_rs": {p: profil.get(p, 0) for p in PROFIL},
        "pasien": len(t["pasien"]),
        "tagihan": len(t["tagihan"]),
        "tagihan_per_layanan": {k: per_layanan.get(k, 0) for k in LAYANAN},
        "sesi_aktual": len(t["sesi_aktual"]),
        "sesi_aktual_per_layanan": {k: sesi_per_layanan.get(k, 0) for k in ("fisioterapi", "hemodialisa")},
        "riwayat_alat_bantu_dengar": len(t["riwayat_alat_bantu_dengar"]),
        "kejadian_per_skenario": {sk: per_skenario.get(sk, 0) for sk in SKENARIO},
        "rs_per_skenario": rs_per_skenario,
        "tagihan_disisipi": sum(len(x["tagihan_ids"]) for x in t["ground_truth"]),
        "kasus_sah_per_jenis": {
            j: {
                "kejadian": sum(x["jenis"] == j for x in t["kasus_sah"]),
                "tagihan": sum(len(x["tagihan_ids"]) for x in t["kasus_sah"] if x["jenis"] == j),
                "rs": len({x["rs_id"] for x in t["kasus_sah"] if x["jenis"] == j}),
            }
            for j in JENIS_KASUS_SAH
        },
    }


def format_ringkasan(r: dict) -> str:
    angka = lambda n: f"{n:,}".replace(",", ".")  # noqa: E731
    baris = [
        f"=== Dataset {r['dataset_id']} (seed {r['seed']}, {r['hari']} hari, {r['periode']}) ===",
        f"Rumah sakit        : {r['rumah_sakit']} (punya sensor: {r['rs_punya_sensor']})",
        "  profil           : " + ", ".join(f"{k} {v}" for k, v in r["profil_rs"].items()),
        f"Pasien             : {angka(r['pasien'])}",
        f"Tagihan            : {angka(r['tagihan'])}",
    ]
    baris += [f"  {k:<17}: {angka(v)}" for k, v in r["tagihan_per_layanan"].items()]
    baris.append(f"Sesi aktual        : {angka(r['sesi_aktual'])}")
    baris += [f"  {k:<17}: {angka(v)}" for k, v in r["sesi_aktual_per_layanan"].items()]
    baris.append(f"Riwayat ABD        : {angka(r['riwayat_alat_bantu_dengar'])}")
    baris.append(f"Kejadian per skenario (tagihan disisipi/diubah: {angka(r['tagihan_disisipi'])}):")
    baris += [
        f"  {sk:<17}: {n:>3} kejadian di {r['rs_per_skenario'][sk]} RS"
        for sk, n in r["kejadian_per_skenario"].items()
    ]
    baris.append("Kasus sah di area batas (perlu klarifikasi, bukan kecurangan):")
    baris += [
        f"  {j:<17}: {v['kejadian']:>3} hari/kejadian, {v['tagihan']:>3} tagihan di {v['rs']} RS"
        for j, v in r["kasus_sah_per_jenis"].items()
    ]
    return "\n".join(baris)


def sidik(data: DataTiruan) -> str:
    """SHA-256 seluruh isi tabel; sama persis berarti datanya identik."""
    isi = json.dumps(data.tabel, sort_keys=True, default=str, ensure_ascii=False)
    return hashlib.sha256(isi.encode("utf-8")).hexdigest()
