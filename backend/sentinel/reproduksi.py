"""Verifikasi reproduksi: bangkitkan ulang SEMUA data di basis data terpisah, jalankan sensor,
aturan, dan perhitungan evaluasi, lalu bandingkan dengan reports/evaluasi.json.

Ini verifikasi reproduksi dengan kode dan parameter yang sudah dibekukan, BUKAN penyetelan.
- Data aktif tidak disentuh: semua langkah berjalan di basis data `sentinel_verifikasi`
  yang dibuat untuk keperluan ini lalu dihapus.
- reports/evaluasi.json dan log jalan evaluasi hidden TIDAK diubah. Satu-satunya keluaran
  adalah reports/verifikasi_reproduksi.json.
"""

import json
import os
import time
from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from sentinel.config import get_settings
from sentinel.evaluation.data import muat
from sentinel.evaluation.evaluasi import angka_proposal, edge_ai, evaluasi
from sentinel.generator.bangkit import bangkitkan
from sentinel.generator.simpan import simpan
from sentinel.parameter import hash_parameter, muat_parameter
from sentinel.rules.masukan import muat_dari_db
from sentinel.rules.mesin import jalankan
from sentinel.rules.simpan import simpan_hasil
from sentinel.sensor.pipeline import jalankan_dataset, jumlah_proses_default

NAMA_DB = "sentinel_verifikasi"
DATASET = ("utama", "hidden")
PERNYATAAN = (
    "Verifikasi reproduksi dengan kode dan parameter yang sudah dibekukan, bukan penyetelan. "
    "Semua data dibangkitkan ulang di basis data terpisah; reports/evaluasi.json dan log jalan "
    "evaluasi hidden tidak diubah."
)


def bandingkan(a, b, jalur: str = "") -> list[str]:
    """Daftar perbedaan antara dua struktur JSON (kosong = identik)."""
    if isinstance(a, dict) and isinstance(b, dict):
        hasil = []
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                hasil.append(f"{jalur}.{k}: hanya ada di {'hasil ulang' if k in a else 'evaluasi.json'}")
            else:
                hasil += bandingkan(a[k], b[k], f"{jalur}.{k}")
        return hasil
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return [f"{jalur}: panjang {len(a)} vs {len(b)}"]
        return [x for i, (p, q) in enumerate(zip(a, b)) for x in bandingkan(p, q, f"{jalur}[{i}]")]
    return [] if a == b else [f"{jalur}: {a!r} vs {b!r}"]


def jalankan_verifikasi(direktori_laporan: Path, komit: str) -> dict:
    t0 = time.perf_counter()
    acuan = json.loads((direktori_laporan / "evaluasi.json").read_text(encoding="utf-8"))
    url_aktif = make_url(get_settings().database_url)
    url_verifikasi = url_aktif.set(database=NAMA_DB)
    admin = create_engine(url_aktif, isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text(f"DROP DATABASE IF EXISTS {NAMA_DB}"))
        conn.execute(text(f"CREATE DATABASE {NAMA_DB}"))
    engine = create_engine(url_verifikasi)
    p = muat_parameter()
    try:
        hasil_ulang = {}
        for ds in DATASET:
            simpan(engine, bangkitkan(ds))
            jalankan_dataset(engine, ds, jumlah_proses=jumlah_proses_default())
            simpan_hasil(engine, jalankan(muat_dari_db(engine, ds), p, hash_parameter()))
            hasil_ulang[ds] = evaluasi(muat(engine, ds))
        hasil_ulang["edge_ai"] = edge_ai()
        hasil_ulang["proposal"] = angka_proposal(hasil_ulang["hidden"], hasil_ulang["edge_ai"])
    finally:
        engine.dispose()
        with admin.connect() as conn:
            conn.execute(text(f"DROP DATABASE IF EXISTS {NAMA_DB}"))
        admin.dispose()

    acuan_json = json.loads(json.dumps({k: acuan[k] for k in hasil_ulang}, default=str))
    ulang_json = json.loads(json.dumps(hasil_ulang, default=str))
    per_bagian = {k: bandingkan(ulang_json[k], acuan_json[k], k) for k in hasil_ulang}
    perbedaan = [x for v in per_bagian.values() for x in v]
    return {
        "jenis": "verifikasi_reproduksi",
        "pernyataan": PERNYATAAN,
        "waktu": datetime.now().astimezone().isoformat(timespec="seconds"),
        "komit": komit,
        "hash_parameter": hash_parameter(),
        "dibandingkan_dengan": {
            "berkas": "reports/evaluasi.json",
            "dibuat_pada": acuan.get("dibuat_pada"),
            "perbandingan_pertama_hidden": (acuan.get("log_hidden") or {}).get("pertama"),
        },
        "identik": not perbedaan,
        "per_bagian": {k: {"identik": not v, "jumlah_perbedaan": len(v)} for k, v in per_bagian.items()},
        "perbedaan": perbedaan[:200],
        "durasi_detik": round(time.perf_counter() - t0, 1),
    }


def main() -> int:
    direktori = get_settings().parameter_path.parent.parent / "reports"
    hasil = jalankan_verifikasi(direktori, os.environ.get("KOMIT", "tidak diketahui"))
    (direktori / "verifikasi_reproduksi.json").write_text(
        json.dumps(hasil, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print("=== Verifikasi reproduksi ===")
    print(PERNYATAAN)
    print(f"Komit           : {hasil['komit']}")
    print(f"Hash parameter  : {hasil['hash_parameter'][:12]}")
    for k, v in hasil["per_bagian"].items():
        status = "IDENTIK" if v["identik"] else f"BERBEDA ({v['jumlah_perbedaan']} perbedaan)"
        print(f"  {k:<9}: {status}")
    print(f"Hasil           : {'IDENTIK dengan reports/evaluasi.json' if hasil['identik'] else 'TIDAK IDENTIK'}")
    print(f"Durasi          : {hasil['durasi_detik']} detik")
    for x in hasil["perbedaan"][:20]:
        print(f"  - {x}")
    return 0 if hasil["identik"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
