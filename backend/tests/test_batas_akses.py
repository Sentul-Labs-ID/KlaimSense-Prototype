"""Penjaga prinsip 6 dan batas tiga sisi sensor (fase 3).

- DUNIA FISIK  : hanya `sensor/simulator.py` (dan generator yang menciptakannya, serta
                 evaluasi) yang boleh menyebut kenyataan fisik (`sesi_aktual`).
- PERANGKAT    : `sensor/edge.py` dan `sensor/protokol.py` tidak boleh menyentuh basis data.
- SERVER       : ingest, ringkasan, API, dan mesin aturan tidak boleh menyentuh kenyataan
                 fisik maupun tabel evaluasi.
- Tabel evaluasi (`ground_truth`, `profil_rs`, `kasus_sah`) hanya boleh disebut oleh
  generator, evaluasi, skema, dan harness gangguan sensor yang mencatat ground truth.
"""

import subprocess
import sys
from pathlib import Path

import pytest

PAKET = Path(__file__).resolve().parents[1] / "sentinel"
KENYATAAN = ("sentinel.models.kenyataan", "SesiAktual", "sesi_aktual")
EVALUASI = (
    "sentinel.models.evaluasi", "GroundTruth", "ProfilRS", "KasusSah", "ground_truth", "profil_rs", "kasus_sah",
)
BASIS_DATA = ("sqlalchemy", "sentinel.db", "sentinel.models", "Engine", "engine")

TERLARANG = {
    "rules": KENYATAAN + EVALUASI,
    "api": KENYATAAN + EVALUASI,
    "sensor/ingest.py": KENYATAAN + EVALUASI,
    "sensor/ringkasan.py": KENYATAAN + EVALUASI,
    "sensor/edge.py": KENYATAAN + EVALUASI + BASIS_DATA,
    "sensor/protokol.py": KENYATAAN + EVALUASI + BASIS_DATA,
    "sensor/simulator.py": EVALUASI,
    "sensor/pipeline.py": KENYATAAN + EVALUASI,
    "sensor/latih.py": KENYATAAN + EVALUASI,
    "generator/sisipan.py": KENYATAAN + EVALUASI,
}
BOLEH_KENYATAAN = {
    "generator/bangkit.py", "generator/simpan.py", "generator/ringkasan.py", "generator/__main__.py",
    "evaluation", "models", "sensor/simulator.py",
}
BOLEH_EVALUASI = {
    "generator/bangkit.py", "generator/simpan.py", "generator/ringkasan.py", "generator/__main__.py",
    "evaluation", "models", "sensor/gangguan.py",
}


def berkas(target: str) -> list[Path]:
    path = PAKET / target
    return sorted(path.rglob("*.py")) if path.is_dir() else [path]


def relatif(path: Path) -> str:
    return path.relative_to(PAKET).as_posix()


def diizinkan(path: Path, boleh: set[str]) -> bool:
    r = relatif(path)
    return any(r == b or r.startswith(b + "/") for b in boleh)


@pytest.mark.parametrize("target", sorted(TERLARANG))
def test_modul_tidak_menyentuh_yang_terlarang(target):
    for path in berkas(target):
        isi = path.read_text(encoding="utf-8")
        for kata in TERLARANG[target]:
            assert kata not in isi, f"{relatif(path)} menyebut {kata!r}"


@pytest.mark.parametrize("kata, boleh", [(KENYATAAN, BOLEH_KENYATAAN), (EVALUASI, BOLEH_EVALUASI)])
def test_hanya_modul_tertentu_yang_menyebut_tabel_sensitif(kata, boleh):
    for path in sorted(PAKET.rglob("*.py")):
        if diizinkan(path, boleh):
            continue
        isi = path.read_text(encoding="utf-8")
        assert not any(x in isi for x in kata), f"{relatif(path)} tidak boleh menyebut {kata}"


def test_perangkat_edge_tidak_memuat_pustaka_basis_data():
    kode = "import sys, sentinel.sensor.edge; print(sorted(m for m in sys.modules if m.startswith(('sqlalchemy', 'psycopg', 'sentinel.db', 'sentinel.models'))))"
    keluaran = subprocess.run([sys.executable, "-c", kode], capture_output=True, text=True, check=True, cwd=PAKET.parent)
    assert keluaran.stdout.strip() == "[]"


FRONTEND = PAKET.parents[1] / "frontend"
# Label dan tabel yang tidak boleh muncul di dashboard (termasuk label profil rumah sakit).
TERLARANG_FRONTEND = EVALUASI + KENYATAAN + ("jujur", "disisipi", "volume_tinggi", "HD_SHIFT_TAMBAHAN", "FISIO_LEMBUR",
                                             "HARGA_ACUAN_LAMA", "SENSOR_PALSU", "ULANG_IDENTIK", "ABD_DINI")


def test_frontend_tidak_menyebut_tabel_atau_label_evaluasi():
    berkas_fe = [
        p for pola in ("app/**/*.tsx", "app/**/*.ts", "components/**/*.tsx", "lib/**/*.ts")
        for p in FRONTEND.glob(pola)
    ]
    assert berkas_fe, "berkas frontend tidak ditemukan"
    for path in berkas_fe:
        isi = path.read_text(encoding="utf-8")
        for kata in TERLARANG_FRONTEND:
            assert kata not in isi, f"{path.relative_to(FRONTEND)} menyebut {kata!r}"
