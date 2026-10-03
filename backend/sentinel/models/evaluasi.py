"""Label kebenaran untuk evaluasi: ground truth, profil rumah sakit, dan kasus sah.

HANYA boleh dibaca modul evaluasi (`sentinel/evaluation/`, fase 4). Mesin aturan,
sensor, agen, dan API dashboard DILARANG membaca atau mengekspos tabel ini (prinsip 6).
"""

from datetime import date

from sqlalchemy import JSON, BigInteger, Date, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from sentinel.db import Base

SKENARIO = (
    "KAP_FISIO",
    "KAP_HD",
    "ULANG_IDENTIK",
    "ULANG_HARI",
    "HARGA_LEBIH",
    "ABD_DINI",
    "SENSOR_PALSU",
)
PROFIL = ("jujur", "jujur_sibuk", "jujur_volume_tinggi", "disisipi")
JENIS_KASUS_SAH = ("HD_SHIFT_TAMBAHAN", "FISIO_LEMBUR", "HARGA_ACUAN_LAMA")


class GroundTruth(Base):
    """Satu baris = satu kejadian: satu skenario di satu rumah sakit pada satu tanggal."""

    __tablename__ = "ground_truth"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    dataset_id: Mapped[str] = mapped_column(String(16), index=True)
    skenario: Mapped[str] = mapped_column(String(32), index=True)
    rs_id: Mapped[str] = mapped_column(ForeignKey("rumah_sakit.id"), index=True)
    tanggal: Mapped[date] = mapped_column(Date)
    tagihan_ids: Mapped[list[int]] = mapped_column(JSON)
    keterangan: Mapped[str] = mapped_column(Text)


class KasusSah(Base):
    """Kejadian sah di area batas aturan pada rumah sakit jujur.

    Mesin aturan memang diharapkan menandainya. Di evaluasi, kasus ini dihitung
    sebagai tuduhan keliru dan dilaporkan terpisah sebagai "kasus sah yang perlu
    klarifikasi". Satu baris = satu jenis kasus di satu rumah sakit pada satu tanggal.
    """

    __tablename__ = "kasus_sah"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    dataset_id: Mapped[str] = mapped_column(String(16), index=True)
    jenis: Mapped[str] = mapped_column(String(32), index=True)
    rs_id: Mapped[str] = mapped_column(ForeignKey("rumah_sakit.id"), index=True)
    tanggal: Mapped[date] = mapped_column(Date)
    tagihan_ids: Mapped[list[int]] = mapped_column(JSON)
    keterangan: Mapped[str] = mapped_column(Text)


class ProfilRS(Base):
    """Profil tiap rumah sakit tiruan, untuk menghitung false positive pada kontrol."""

    __tablename__ = "profil_rs"

    rs_id: Mapped[str] = mapped_column(ForeignKey("rumah_sakit.id"), primary_key=True)
    dataset_id: Mapped[str] = mapped_column(String(16), index=True)
    profil: Mapped[str] = mapped_column(String(32))
