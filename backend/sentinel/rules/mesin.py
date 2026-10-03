"""Mesin aturan: menjalankan semua aturan dan menghitung skor, deterministik."""

from dataclasses import dataclass
from datetime import date

from sentinel.parameter import Parameter
from sentinel.rules.aturan import ATURAN_HARIAN
from sentinel.rules.aturan_sensor import sen_01
from sentinel.rules.banding import Penilaian, nilai_banding
from sentinel.rules.masukan import Masukan
from sentinel.rules.skor import hitung_skor

VERSI_ATURAN = "1.1.0"


@dataclass
class HasilAturan:
    dataset_id: str
    temuan: list[dict]
    skor: list[dict]
    penilaian_banding: list[Penilaian]
    hash_parameter: str


def jalankan(m: Masukan, p: Parameter, hash_parameter: str) -> HasilAturan:
    temuan: list[dict] = []
    for aturan in (*ATURAN_HARIAN, sen_01):
        temuan += aturan(m, p)
    penilaian, temuan_banding = nilai_banding(m, p)
    temuan += temuan_banding

    temuan.sort(key=lambda t: (t["rs_id"], t["periode"], t["tanggal"] or date.min, t["aturan_id"], t["kategori"] or "", t["penjelasan"]))
    for t in temuan:
        t["dataset_id"] = m.dataset_id
        t["versi_aturan"] = VERSI_ATURAN

    skor = hitung_skor(m, p, temuan, penilaian)
    for s in skor:
        s["dataset_id"] = m.dataset_id
        s["versi_aturan"] = VERSI_ATURAN
        s["hash_parameter"] = hash_parameter

    return HasilAturan(m.dataset_id, temuan, skor, penilaian, hash_parameter)
