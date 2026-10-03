"""Data transaksi yang dilihat BPJS: tagihan dan riwayat alat bantu dengar."""

from datetime import date

from sqlalchemy import BigInteger, CheckConstraint, Date, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from sentinel.db import Base

LAYANAN = ("fisioterapi", "hemodialisa", "alat_bantu_dengar", "obat_kronis")
SISI_TELINGA = ("kiri", "kanan")


class Tagihan(Base):
    __tablename__ = "tagihan"
    __table_args__ = (
        CheckConstraint(
            "layanan IN ('fisioterapi','hemodialisa','alat_bantu_dengar','obat_kronis')",
            name="ck_tagihan_layanan",
        ),
        Index("ix_tagihan_dataset_rs_tanggal", "dataset_id", "rs_id", "tanggal"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    dataset_id: Mapped[str] = mapped_column(String(16), index=True)
    rs_id: Mapped[str] = mapped_column(ForeignKey("rumah_sakit.id"), index=True)
    pasien_id: Mapped[str] = mapped_column(ForeignKey("pasien.id_pseudonim"), index=True)
    tanggal: Mapped[date] = mapped_column(Date)
    layanan: Mapped[str] = mapped_column(String(32))
    # Terisi untuk obat_kronis dan alat_bantu_dengar (kode di harga_acuan);
    # kosong untuk fisioterapi dan hemodialisa yang memakai tarif paket.
    kode_item: Mapped[str | None] = mapped_column(String(16))
    sisi_telinga: Mapped[str | None] = mapped_column(String(8))
    jumlah: Mapped[int] = mapped_column(Integer)
    harga_satuan: Mapped[int] = mapped_column(BigInteger)
    total: Mapped[int] = mapped_column(BigInteger)


class RiwayatAlatBantuDengar(Base):
    __tablename__ = "riwayat_alat_bantu_dengar"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    dataset_id: Mapped[str] = mapped_column(String(16), index=True)
    pasien_id: Mapped[str] = mapped_column(ForeignKey("pasien.id_pseudonim"), index=True)
    sisi_telinga: Mapped[str] = mapped_column(String(8))
    tanggal_diberikan: Mapped[date] = mapped_column(Date)
