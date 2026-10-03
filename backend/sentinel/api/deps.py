"""Dependensi bersama API dashboard."""

from fastapi import HTTPException
from sqlalchemy import Engine

from sentinel.config import Settings, get_settings

# Dataset yang boleh ditampilkan dashboard. Dataset uji akhir sengaja tidak tersedia.
DATASET_TAMPIL = ("demo", "utama")
DATASET_TULIS = "demo"


def ambil_engine() -> Engine:
    from sentinel.db import get_engine

    return get_engine()


def ambil_pengaturan() -> Settings:
    return get_settings()


def periksa_dataset(dataset: str) -> str:
    if dataset not in DATASET_TAMPIL:
        raise HTTPException(status_code=404, detail=f"Dataset '{dataset}' tidak tersedia di dashboard.")
    return dataset


def periksa_dataset_tulis(dataset: str) -> str:
    if dataset != DATASET_TULIS:
        raise HTTPException(
            status_code=403,
            detail="Perubahan hanya boleh dilakukan pada dataset demo. Dataset lain bersifat baca-saja.",
        )
    return dataset
