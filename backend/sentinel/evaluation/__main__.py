"""CLI evaluasi akurasi.

    python -m sentinel.evaluation                     # utama lalu hidden (dipakai `make eval`)
    python -m sentinel.evaluation --dataset utama     # hanya utama (pengembangan)
    python -m sentinel.evaluation --hanya-laporan     # tulis ulang laporan dari reports/evaluasi.json

Setiap jalan evaluasi hidden dicatat di reports/log_evaluasi_hidden.json. Jalan pertama
adalah "perbandingan pertama keluaran hidden terhadap label" dan tidak pernah ditimpa.
"""

import argparse
import json
from datetime import datetime
from pathlib import Path

from sentinel.config import get_settings
from sentinel.evaluation import grafik, laporan
from sentinel.evaluation.data import muat
from sentinel.evaluation.evaluasi import angka_proposal, edge_ai, evaluasi

DIREKTORI = get_settings().parameter_path.parent.parent / "reports"


def sekarang() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def catat_jalan_hidden(direktori: Path, waktu: str) -> dict:
    path = direktori / "log_evaluasi_hidden.json"
    log = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"pertama": waktu, "jalan": []}
    log["jalan"].append(waktu)
    path.write_text(json.dumps(log, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return log


def tulis_keluaran(hasil: dict, direktori: Path) -> None:
    direktori.mkdir(parents=True, exist_ok=True)
    (direktori / "evaluasi.json").write_text(
        json.dumps(hasil, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8"
    )
    catatan = direktori / "catatan_pasca_hidden.md"
    teks_catatan = catatan.read_text(encoding="utf-8") if catatan.exists() else None
    (direktori / "evaluasi.md").write_text(laporan.render(hasil, teks_catatan), encoding="utf-8")
    grafik.recall_per_skenario(hasil, direktori / "recall_per_skenario.png")
    if hasil.get("hidden"):
        grafik.matriks_prioritas(
            hasil["hidden"], direktori / "prioritas_hidden.png", "Prioritas vs kondisi RS-periode, dataset hidden"
        )


def main(argv: list[str] | None = None, engine=None, direktori: Path | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m sentinel.evaluation", description="Evaluasi akurasi KlaimSense.")
    parser.add_argument("--dataset", action="append", choices=["utama", "hidden"],
                        help="boleh diulang; default: utama lalu hidden")
    parser.add_argument("--hanya-laporan", action="store_true", help="render ulang dari evaluasi.json tanpa menghitung")
    args = parser.parse_args(argv)
    direktori = direktori or DIREKTORI

    if args.hanya_laporan:
        hasil = json.loads((direktori / "evaluasi.json").read_text(encoding="utf-8"))
        tulis_keluaran(hasil, direktori)
        print(f"Laporan ditulis ulang di {direktori} dari evaluasi.json (tidak ada evaluasi baru).")
        return 0

    if engine is None:
        from sentinel.db import get_engine

        engine = get_engine()
    dataset = args.dataset or ["utama", "hidden"]
    lama = direktori / "evaluasi.json"
    hasil = json.loads(lama.read_text(encoding="utf-8")) if lama.exists() else {}
    hasil["dibuat_pada"] = sekarang()
    hasil["edge_ai"] = edge_ai()
    for ds in dataset:
        if ds == "hidden":
            hasil["log_hidden"] = catat_jalan_hidden(direktori, sekarang())
        data = muat(engine, ds)
        if not data.skor:
            print(f"Dataset {ds} belum punya skor. Jalankan `make generate`, `make sensor` dulu.")
            return 1
        hasil[ds] = evaluasi(data)
        r = hasil[ds]
        print(f"=== Evaluasi {ds} ===")
        print(f"  Kecurangan tertangkap : {laporan.p(r['recall_gabungan_kecurangan'])}")
        print(f"  Presisi tinggi+sedang : {laporan.p(r['prioritas']['tinggi_sedang']['presisi'])}")
        print(f"  Tuduhan keliru        : {laporan.p(r['prioritas']['ditandai']['tuduhan_keliru'])}")
    if hasil.get("hidden"):
        hasil["proposal"] = angka_proposal(hasil["hidden"], hasil["edge_ai"])
    tulis_keluaran(hasil, direktori)
    print(f"Keluaran ditulis di {direktori}: evaluasi.md, evaluasi.json, recall_per_skenario.png"
          + (", prioritas_hidden.png" if hasil.get("hidden") else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
