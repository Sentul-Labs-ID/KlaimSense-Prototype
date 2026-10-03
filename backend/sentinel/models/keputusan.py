"""Keputusan petugas (Langkah 4: Putuskan), dirantai hash per dataset.

Setiap entri menyimpan `prev_hash` (hash entri sebelumnya di dataset yang sama) dan
`hash` = SHA-256 isi entri. Mengubah satu entri lama memutus rantai dan terdeteksi
di halaman audit. Hanya dataset "demo" yang boleh ditulisi dashboard.
"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from sentinel.db import Base

_ID = BigInteger().with_variant(Integer, "sqlite")
PILIHAN_KEPUTUSAN = ("setujui", "minta_klarifikasi", "rujuk_audit")


class Keputusan(Base):
    __tablename__ = "keputusan"

    id: Mapped[int] = mapped_column(_ID, primary_key=True, autoincrement=True)
    dataset_id: Mapped[str] = mapped_column(String(16), index=True)
    rs_id: Mapped[str] = mapped_column(ForeignKey("rumah_sakit.id"), index=True)
    periode: Mapped[str] = mapped_column(String(7))
    keputusan: Mapped[str] = mapped_column(String(24))
    alasan: Mapped[str] = mapped_column(Text)
    petugas: Mapped[str] = mapped_column(String(80))
    waktu: Mapped[datetime] = mapped_column(DateTime)
    prev_hash: Mapped[str] = mapped_column(String(64))
    hash: Mapped[str] = mapped_column(String(64))
