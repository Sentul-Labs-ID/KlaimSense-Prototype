"""CLI mesin aturan.

Contoh:
    python -m sentinel.rules --dataset utama
    python -m sentinel.rules --dataset hidden
"""

import argparse
import time
from collections import Counter
from statistics import median

from sqlalchemy import Engine

from sentinel.parameter import KODE_ATURAN, hash_parameter, muat_parameter
from sentinel.rules import teks
from sentinel.rules.masukan import Masukan, muat_dari_db
from sentinel.rules.mesin import HasilAturan, jalankan
from sentinel.rules.simpan import simpan_hasil

PRIORITAS = ("tinggi", "sedang", "rendah")


def ringkasan(m: Masukan, h: HasilAturan, teratas: int = 10) -> str:
    rs = {x["id"]: x for x in m.rumah_sakit}
    baris = [f"=== Mesin aturan: dataset {h.dataset_id} (hash parameter {h.hash_parameter[:12]}) ==="]

    per_aturan = Counter(t["aturan_id"] for t in h.temuan)
    baris.append(f"Temuan: {len(h.temuan)}")
    baris += [f"  {a:<8}: {per_aturan.get(a, 0)}" for a in KODE_ATURAN if a != "SEN-01"]
    dilewati = [x for x in h.penilaian_banding if x.z is None]
    turun = sum(x.kelompok == "kelas" for x in h.penilaian_banding)
    baris.append(
        f"  BAND-01 : {len(h.penilaian_banding)} penilaian, {turun} memakai pembanding kelas saja, "
        f"{len(dilewati)} dilewati"
    )
    for x in dilewati[:5]:
        baris.append(f"    dilewati {x.rs_id} {x.layanan} {x.periode}: {x.alasan_dilewati}")

    nilai = sorted(s["skor"] for s in h.skor)
    baris.append(
        f"Skor ({len(h.skor)} RS-periode): min {teks.angka(nilai[0], 2)}, median {teks.angka(median(nilai), 2)}, "
        f"maks {teks.angka(nilai[-1], 2)} (maksimum sementara 80; SEN-01 aktif di fase 3)"
    )
    per_prioritas = Counter(s["prioritas"] for s in h.skor)
    baris.append("  RS-periode per prioritas: " + ", ".join(f"{p} {per_prioritas.get(p, 0)}" for p in PRIORITAS))

    terbaik: dict[str, dict] = {}
    for s in h.skor:
        if s["rs_id"] not in terbaik or s["skor"] > terbaik[s["rs_id"]]["skor"]:
            terbaik[s["rs_id"]] = s
    per_rs = Counter(s["prioritas"] for s in terbaik.values())
    baris.append("  RS per prioritas (periode tertinggi): " + ", ".join(f"{p} {per_rs.get(p, 0)}" for p in PRIORITAS))

    baris.append(f"{teratas} RS dengan skor tertinggi (periode tertinggi masing-masing):")
    urut = sorted(terbaik.values(), key=lambda s: (-s["skor"], s["rs_id"]))[:teratas]
    for i, s in enumerate(urut, 1):
        r = rs[s["rs_id"]]
        pemicu = []
        for aturan, d in s["rincian_per_aturan"].items():
            if d["kontribusi"] <= 0:
                continue
            if "jumlah_temuan" in d:
                pemicu.append(f"{aturan}×{d['jumlah_temuan']}")
            else:
                z = max((v["z"] for v in d.get("per_layanan", {}).values() if v["z"] is not None), default=0)
                pemicu.append(f"{aturan} z={teks.angka(z, 1)}")
        baris.append(
            f"  {i:>2}. {s['rs_id']} (kelas {r['kelas']}, {r['provinsi']}) {s['periode']}: "
            f"skor {teks.angka(s['skor'], 2)} [{s['prioritas']}] — {', '.join(pemicu) or '-'}"
        )
    return "\n".join(baris)


def main(argv: list[str] | None = None, engine: Engine | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m sentinel.rules", description="Jalankan mesin aturan JKN-Sentinel.")
    parser.add_argument("--dataset", choices=["utama", "hidden"], default="utama")
    parser.add_argument("--parameter", default=None, help="path parameter.yaml (default: PARAMETER_PATH)")
    args = parser.parse_args(argv)

    if engine is None:
        from sentinel.db import get_engine

        engine = get_engine()
    t0 = time.perf_counter()
    p = muat_parameter(args.parameter)
    m = muat_dari_db(engine, args.dataset)
    if not m.tagihan:
        print(f"Dataset {args.dataset} kosong. Jalankan `make generate` dulu.")
        return 1
    t1 = time.perf_counter()
    h = jalankan(m, p, hash_parameter(args.parameter))
    t2 = time.perf_counter()
    simpan_hasil(engine, h)
    t3 = time.perf_counter()
    print(ringkasan(m, h))
    print(f"Waktu: baca {t1 - t0:.1f} dtk, hitung {t2 - t1:.1f} dtk, simpan {t3 - t2:.1f} dtk.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
