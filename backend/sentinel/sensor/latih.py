"""Pelatihan model edge ("pabrik firmware"), terpisah dari perangkat dan server.

Data latih dibangkitkan simulator dengan SEED_LATIH (bukan seed dataset utama/hidden).
Pembagian latih/uji dilakukan per mesin-hari, sehingga jendela uji tidak pernah dipakai melatih.
"""

import hashlib
import json
import pickle
import platform
from pathlib import Path

import numpy as np
import sklearn
from sklearn.metrics import accuracy_score, confusion_matrix
from sklearn.tree import DecisionTreeClassifier

from sentinel.parameter import Parameter, muat_parameter
from sentinel.sensor import konfigurasi as k
from sentinel.sensor.edge import NAMA_FITUR, fitur, label_jendela, path_model
from sentinel.sensor.simulator import data_latih


def latih(
    parameter: Parameter | None = None,
    panjang_jendela: int = k.PANJANG_JENDELA_DEFAULT,
    seed: int = k.SEED_LATIH,
    jumlah_hari: int = k.HARI_LATIH,
) -> tuple[DecisionTreeClassifier, dict]:
    p = parameter or muat_parameter()
    durasi = round(p.kapasitas.hemodialisa_durasi_sesi_jam * 60)
    arus, label, _ = data_latih(seed, jumlah_hari, durasi)
    rng = np.random.default_rng(seed)
    hari_uji = set(rng.choice(jumlah_hari, size=round(jumlah_hari * k.PORSI_UJI), replace=False).tolist())

    def kumpulkan(hari):
        x = np.concatenate([fitur(arus[h], panjang_jendela) for h in hari])
        y = np.concatenate([label_jendela(label[h], panjang_jendela) for h in hari])
        return x, y

    hari_latih = [h for h in range(jumlah_hari) if h not in hari_uji]
    x_latih, y_latih = kumpulkan(hari_latih)
    x_uji, y_uji = kumpulkan(sorted(hari_uji))
    pohon = DecisionTreeClassifier(max_depth=k.KEDALAMAN_POHON, random_state=0).fit(x_latih, y_latih)
    prediksi = pohon.predict(x_uji)
    metrik = {
        "seed_latih": seed,
        "panjang_jendela_menit": panjang_jendela,
        "jumlah_mesin_hari": {"latih": len(hari_latih), "uji": len(hari_uji)},
        "jumlah_jendela": {"latih": int(len(y_latih)), "uji": int(len(y_uji))},
        "fitur": list(NAMA_FITUR),
        "kedalaman_pohon": k.KEDALAMAN_POHON,
        "akurasi_uji": round(float(accuracy_score(y_uji, prediksi)), 4),
        "label": list(k.STATUS),
        "confusion_matrix_uji": confusion_matrix(y_uji, prediksi, labels=[0, 1, 2]).tolist(),
    }
    return pohon, metrik


def lingkungan() -> dict[str, str]:
    """Versi yang memengaruhi byte pickle (dan hash file) model."""
    return {"python": platform.python_version(), "numpy": np.__version__, "scikit-learn": sklearn.__version__}


def simpan_model(pohon: DecisionTreeClassifier, metrik: dict, direktori: Path | None = None) -> str:
    """Simpan model, hash SHA-256, dan metadata. Kembalikan hash."""
    path = path_model(direktori)
    path.parent.mkdir(parents=True, exist_ok=True)
    isi = pickle.dumps({"pohon": pohon, "panjang_jendela": metrik["panjang_jendela_menit"]}, protocol=5)
    sha = hashlib.sha256(isi).hexdigest()
    path.write_bytes(isi)
    path.with_suffix(".sha256").write_text(f"{sha}  {path.name}\n", encoding="utf-8")
    path.with_suffix(".json").write_text(
        json.dumps({**metrik, "sha256": sha, "lingkungan": lingkungan()}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return sha
