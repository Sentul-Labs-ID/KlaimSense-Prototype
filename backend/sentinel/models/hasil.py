"""Hasil mesin aturan (Langkah 1: Hitung): temuan dan skor prioritas.

Boleh dibaca semua modul, termasuk dashboard. Isinya hanya turunan dari tabel
`master`, `transaksi`, dan `config/parameter.yaml`.
"""

from datetime import date

from sqlalchemy import JSON, BigInteger, Date, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from sentinel.db import Base

# BIGINT autoincrement di PostgreSQL; SQLite (tes) butuh INTEGER untuk autoincrement.
_ID = BigInteger().with_variant(Integer, "sqlite")


class Temuan(Base):
    __tablename__ = "temuan"
    __table_args__ = (Index("ix_temuan_dataset_rs_periode", "dataset_id", "rs_id", "periode"),)

    id: Mapped[int] = mapped_column(_ID, primary_key=True, autoincrement=True)
    dataset_id: Mapped[str] = mapped_column(String(16), index=True)
    aturan_id: Mapped[str] = mapped_column(String(16), index=True)
    rs_id: Mapped[str] = mapped_column(ForeignKey("rumah_sakit.id"), index=True)
    tanggal: Mapped[date | None] = mapped_column(Date)  # kosong untuk aturan per periode (BAND-01)
    periode: Mapped[str] = mapped_column(String(7))  # YYYY-MM
    layanan: Mapped[str] = mapped_column(String(32))
    tagihan_ids: Mapped[list[int]] = mapped_column(JSON)
    nilai_teramati: Mapped[float] = mapped_column(Float)
    batas: Mapped[float] = mapped_column(Float)
    selisih: Mapped[float] = mapped_column(Float)
    penjelasan: Mapped[str] = mapped_column(Text)
    versi_aturan: Mapped[str] = mapped_column(String(16))
    # Khusus SEN-01: "selisih" atau "integritas"; kosong untuk aturan lain.
    kategori: Mapped[str | None] = mapped_column(String(16))


class Skor(Base):
    __tablename__ = "skor"

    dataset_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    rs_id: Mapped[str] = mapped_column(ForeignKey("rumah_sakit.id"), primary_key=True)
    periode: Mapped[str] = mapped_column(String(7), primary_key=True)
    skor: Mapped[float] = mapped_column(Float)
    prioritas: Mapped[str] = mapped_column(String(8))
    # Mengapa label prioritas itu: "ambang skor ≥ 20" atau "lantai: KAP-02 jenuh" (fase 3).
    alasan_prioritas: Mapped[str | None] = mapped_column(String(160))
    rincian_per_aturan: Mapped[dict] = mapped_column(JSON)
    versi_aturan: Mapped[str] = mapped_column(String(16))
    hash_parameter: Mapped[str] = mapped_column(String(64))
