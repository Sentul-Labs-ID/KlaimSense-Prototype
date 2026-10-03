"""CLI sensor.

    python -m sentinel.sensor --dataset utama        # simulasi -> edge -> ingest -> ringkasan
    python -m sentinel.sensor latih                  # latih ulang model edge (seed khusus pelatihan)
"""

import argparse
import json

from sentinel.sensor import konfigurasi as k


def main(argv: list[str] | None = None, engine=None) -> int:
    parser = argparse.ArgumentParser(prog="python -m sentinel.sensor", description="Simulasi sensor IoT dan edge AI.")
    parser.add_argument("perintah", nargs="?", choices=["jalankan", "latih"], default="jalankan")
    parser.add_argument("--dataset", choices=["utama", "hidden", "demo"], default="utama")
    parser.add_argument("--proses", type=int, default=None, help="jumlah proses paralel (default: jumlah CPU, maks 16)")
    parser.add_argument("--jendela", type=int, default=k.PANJANG_JENDELA_DEFAULT, help="panjang jendela (menit)")
    args = parser.parse_args(argv)

    if args.perintah == "latih":
        from sentinel.sensor.latih import latih, simpan_model

        pohon, metrik = latih(panjang_jendela=args.jendela)
        sha = simpan_model(pohon, metrik)
        print(json.dumps({**metrik, "sha256": sha}, indent=2, ensure_ascii=False))
        return 0

    from sentinel.sensor.pipeline import jalankan_dataset, jumlah_proses_default

    if engine is None:
        from sentinel.db import get_engine

        engine = get_engine()
    proses = args.proses or jumlah_proses_default()
    h = jalankan_dataset(engine, args.dataset, jumlah_proses=proses, panjang_jendela=args.jendela)
    print(f"=== Sensor: dataset {args.dataset} ===")
    print(f"Perangkat   : {h.perangkat}")
    angka = lambda n: f"{n:,}".replace(",", ".")  # noqa: E731
    print(f"Pesan       : {angka(h.pesan)} (diterima {angka(h.diterima)}, ditolak {angka(h.ditolak)})")
    print("Anomali     : " + (", ".join(f"{j} {n}" for j, n in sorted(h.anomali.items())) or "tidak ada"))
    print(f"Waktu       : {h.detik:.1f} detik ({proses} proses)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
