"""Loader dan validasi config/parameter.yaml.

Semua batas aturan dibaca dari file tersebut, bukan di-hardcode (prinsip 4).
Nilai default di file itu ilustratif sampai divalidasi.
"""

import hashlib
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from sentinel.config import get_settings

KODE_ATURAN = ("KAP-01", "KAP-02", "ULG-01", "ULG-02", "WJR-01", "WJR-02", "BAND-01", "SEN-01")
TOTAL_BOBOT = 100
# Aturan yang keparahannya dihitung dari jumlah temuan per periode (BAND-01 memakai z-score).
ATURAN_HITUNGAN = ("KAP-01", "KAP-02", "ULG-01", "ULG-02", "WJR-01", "WJR-02", "SEN-01")


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


class Prioritas(_Ketat):
    tinggi: float = Field(gt=0, le=100)
    sedang: float = Field(gt=0, le=100)

    @model_validator(mode="after")
    def _urut(self) -> "Prioritas":
        if self.sedang >= self.tinggi:
            raise ValueError("ambang prioritas sedang harus lebih kecil dari tinggi")
        return self


class Skor(_Ketat):
    titik_jenuh: dict[str, float]
    prioritas: Prioritas

    @field_validator("titik_jenuh")
    @classmethod
    def _cek_titik_jenuh(cls, nilai: dict[str, float]) -> dict[str, float]:
        if set(nilai) != set(ATURAN_HITUNGAN):
            raise ValueError(f"titik_jenuh harus berisi tepat: {list(ATURAN_HITUNGAN)}")
        if any(v <= 0 for v in nilai.values()):
            raise ValueError("titik_jenuh harus positif")
        return nilai


class Parameter(_Ketat):
    versi_skema: int
    kapasitas: Kapasitas
    kewajaran: Kewajaran
    perbandingan: Perbandingan
    sensor: Sensor
    bobot_aturan: dict[str, float]
    skor: Skor

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


def _path(path: Path | str | None) -> Path:
    return Path(path) if path is not None else get_settings().parameter_path


def muat_parameter(path: Path | str | None = None) -> Parameter:
    """Baca dan validasi file parameter. Default: PARAMETER_PATH dari environment."""
    with _path(path).open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return Parameter.model_validate(data)


def hash_parameter(path: Path | str | None = None) -> str:
    """SHA-256 isi file parameter (byte apa adanya), untuk melacak skor ke parameternya."""
    return hashlib.sha256(_path(path).read_bytes()).hexdigest()
