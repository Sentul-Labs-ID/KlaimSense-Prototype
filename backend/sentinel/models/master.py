"""Data master yang dilihat BPJS: rumah sakit, kapasitas, pasien, harga acuan."""

from sqlalchemy import BigInteger, Boolean, CheckConstraint, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from sentinel.db import Base


class RumahSakit(Base):
    __tablename__ = "rumah_sakit"
    __table_args__ = (CheckConstraint("kelas IN ('A','B','C','D')", name="ck_rs_kelas"),)

    id: Mapped[str] = mapped_column(String(16), primary_key=True)
    dataset_id: Mapped[str] = mapped_column(String(16), index=True)
    nama_samaran: Mapped[str] = mapped_column(String(100))
    kelas: Mapped[str] = mapped_column(String(1))
    provinsi: Mapped[str] = mapped_column(String(64))
    kab_kota: Mapped[str] = mapped_column(String(64))
    punya_sensor: Mapped[bool] = mapped_column(Boolean)


class Kapasitas(Base):
    __tablename__ = "kapasitas"

    rs_id: Mapped[str] = mapped_column(ForeignKey("rumah_sakit.id"), primary_key=True)
    dataset_id: Mapped[str] = mapped_column(String(16), index=True)
    jumlah_fisioterapis: Mapped[int] = mapped_column(Integer)
    jumlah_mesin_hd: Mapped[int] = mapped_column(Integer)
    shift_hd_per_hari: Mapped[int] = mapped_column(Integer)
    # Jumlah hari unit hemodialisa buka per minggu (6 = Senin-Sabtu, 7 = setiap hari).
    hari_operasional_hd: Mapped[int] = mapped_column(Integer)


class Pasien(Base):
    __tablename__ = "pasien"
    __table_args__ = (CheckConstraint("jenis_kelamin IN ('L','P')", name="ck_pasien_jk"),)

    # Pseudonim berbentuk "P-000123"; tidak menyerupai NIK atau nomor kartu.
    id_pseudonim: Mapped[str] = mapped_column(String(16), primary_key=True)
    dataset_id: Mapped[str] = mapped_column(String(16), index=True)
    umur: Mapped[int] = mapped_column(Integer)
    jenis_kelamin: Mapped[str] = mapped_column(String(1))
    provinsi: Mapped[str] = mapped_column(String(64))


class HargaAcuan(Base):
    __tablename__ = "harga_acuan"
    __table_args__ = (
        CheckConstraint("jenis IN ('obat_kronis','alat_bantu_dengar')", name="ck_harga_jenis"),
    )

    dataset_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    kode_item: Mapped[str] = mapped_column(String(16), primary_key=True)
    nama_item: Mapped[str] = mapped_column(String(120))
    jenis: Mapped[str] = mapped_column(String(32))
    harga: Mapped[int] = mapped_column(BigInteger)  # rupiah per satuan
