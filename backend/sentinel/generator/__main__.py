"""CLI generator data tiruan.

Contoh:
    python -m sentinel.generator --dataset utama --seed 42 --days 90 --rs 30
    python -m sentinel.generator --hidden
    python -m sentinel.generator --hidden --dry-run   # tanpa menulis ke database
"""

import argparse
import sys
import time
from datetime import date

from sentinel.generator.bangkit import HARI_DEFAULT, MULAI_DEFAULT, RS_DEFAULT, bangkitkan
from sentinel.generator.profil import PROFIL
from sentinel.generator.ringkasan import format_ringkasan, ringkasan, sidik


def buat_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m sentinel.generator",
        description="Bangkitkan data tiruan JKN-Sentinel (seluruhnya fiktif) beserta ground truth.",
    )
    p.add_argument("--dataset", choices=list(PROFIL), default=None, help="dataset_id (default: utama)")
    p.add_argument("--hidden", action="store_true", help="singkatan untuk --dataset hidden (seed default 2026)")
    p.add_argument("--seed", type=int, default=None, help="seed acak (default: 42 utama, 2026 hidden)")
    p.add_argument("--days", type=int, default=HARI_DEFAULT, help=f"jumlah hari (default {HARI_DEFAULT})")
    p.add_argument("--rs", type=int, default=RS_DEFAULT, help=f"jumlah rumah sakit (default {RS_DEFAULT})")
    p.add_argument("--mulai", type=date.fromisoformat, default=MULAI_DEFAULT, help="tanggal mulai YYYY-MM-DD")
    p.add_argument("--dry-run", action="store_true", help="hanya bangkitkan dan cetak ringkasan")
    return p


def main(argv: list[str] | None = None) -> int:
    args = buat_parser().parse_args(argv)
    if args.hidden and args.dataset == "utama":
        print("--hidden tidak bisa digabung dengan --dataset utama", file=sys.stderr)
        return 2
    dataset_id = "hidden" if args.hidden else (args.dataset or "utama")

    t0 = time.perf_counter()
    data = bangkitkan(dataset_id, seed=args.seed, hari=args.days, jumlah_rs=args.rs, mulai=args.mulai)
    t1 = time.perf_counter()
    print(format_ringkasan(ringkasan(data)))
    print(f"Sidik data         : {sidik(data)[:16]}")
    print(f"Waktu bangkit      : {t1 - t0:.1f} detik")

    if args.dry_run:
        print("Dry run: tidak ada yang ditulis ke database.")
        return 0

    from sentinel.db import get_engine
    from sentinel.generator.simpan import simpan

    simpan(get_engine(), data)
    print(f"Tersimpan ke database (data lama dataset '{dataset_id}' diganti) dalam {time.perf_counter() - t1:.1f} detik.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
