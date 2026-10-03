"""Loader dan validasi config/parameter.yaml.

Semua batas aturan dibaca dari file tersebut, bukan di-hardcode (prinsip 4).
Nilai default di file itu ilustratif sampai divalidasi.
"""

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator

from sentinel.config import get_settings

KODE_ATURAN = ("KAP-01", "KAP-02", "ULG-01", "ULG-02", "WJR-01", "WJR-02", "BAND-01", "SEN-01")
TOTAL_BOBOT = 100


class _Ketat(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Kapasitas(_Ketat):
    fisioterapi_sesi_per_terapis_per_hari: int = Field(gt=0)
    hemodialisa_durasi_sesi_jam: float = Field(gt=0, le=24)
    hemodialisa_shift_per_hari: int = Field(gt=0)


class Kewajaran(_Ketat):
    toleransi_harga_di_atas_acuan_persen: float = Field(ge=0)
    alat_bantu_dengar_masa_penggantian_tahun: float = Field(gt=0)
    alat_bantu_dengar_per_telinga: bool


class Perbandingan(_Ketat):
    ambang_robust_z: float = Field(gt=0)


class Sensor(_Ketat):
    toleransi_selisih_jam_mesin_persen: float = Field(ge=0, le=100)


class Parameter(_Ketat):
    versi_skema: int
    kapasitas: Kapasitas
    kewajaran: Kewajaran
    perbandingan: Perbandingan
    sensor: Sensor
    bobot_aturan: dict[str, float]

    @field_validator("bobot_aturan")
    @classmethod
    def _cek_bobot(cls, bobot: dict[str, float]) -> dict[str, float]:
        kurang = set(KODE_ATURAN) - bobot.keys()
        asing = bobot.keys() - set(KODE_ATURAN)
        if kurang:
            raise ValueError(f"bobot aturan belum lengkap: {sorted(kurang)}")
        if asing:
            raise ValueError(f"kode aturan tidak dikenal: {sorted(asing)}")
        negatif = [kode for kode, nilai in bobot.items() if nilai < 0]
        if negatif:
            raise ValueError(f"bobot tidak boleh negatif: {sorted(negatif)}")
        total = sum(bobot.values())
        if abs(total - TOTAL_BOBOT) > 1e-9:
            raise ValueError(f"jumlah bobot harus {TOTAL_BOBOT}, sekarang {total}")
        return bobot


def muat_parameter(path: Path | str | None = None) -> Parameter:
    """Baca dan validasi file parameter. Default: PARAMETER_PATH dari environment."""
    path = Path(path) if path is not None else get_settings().parameter_path
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return Parameter.model_validate(data)
