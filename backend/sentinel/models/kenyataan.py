"""Kenyataan fisik: sesi yang BENAR-BENAR terjadi.

HANYA boleh dibaca simulator sensor (fase 3) dan evaluasi (fase 4).
Mesin aturan (`sentinel/rules/`) DILARANG membaca tabel ini, karena BPJS di dunia
nyata tidak tahu sesi mana yang benar-benar terjadi. Tagihan fiktif tidak punya
pasangan di tabel ini.
"""

from datetime import date

from sqlalchemy import BigInteger, Date, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from sentinel.db import Base


class SesiAktual(Base):
    __tablename__ = "sesi_aktual"
    __table_args__ = (Index("ix_sesi_dataset_rs_tanggal", "dataset_id", "rs_id", "tanggal"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    dataset_id: Mapped[str] = mapped_column(String(16), index=True)
    rs_id: Mapped[str] = mapped_column(ForeignKey("rumah_sakit.id"), index=True)
    pasien_id: Mapped[str] = mapped_column(ForeignKey("pasien.id_pseudonim"), index=True)
    tanggal: Mapped[date] = mapped_column(Date)
    layanan: Mapped[str] = mapped_column(String(32))
    mesin_id: Mapped[str | None] = mapped_column(String(24))  # hanya hemodialisa
    shift: Mapped[int | None] = mapped_column(Integer)  # hanya hemodialisa, mulai 1
