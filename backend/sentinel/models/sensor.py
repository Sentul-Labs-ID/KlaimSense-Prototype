"""Data sensor di sisi SERVER: registri perangkat, pesan valid, anomali, ringkasan harian.

Server hanya tahu apa yang dikirim perangkat. Kunci privat perangkat TIDAK pernah
disimpan di sini; registri hanya berisi kunci publik. Boleh dibaca semua modul
server, termasuk mesin aturan (SEN-01) dan dashboard.
"""

from datetime import date, datetime

from sqlalchemy import (
    BigInteger, Boolean, Date, DateTime, Float, ForeignKey, Index, Integer, LargeBinary, String, Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from sentinel.db import Base

_ID = BigInteger().with_variant(Integer, "sqlite")


class Perangkat(Base):
    __tablename__ = "perangkat"

    device_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    dataset_id: Mapped[str] = mapped_column(String(16), index=True)
    rs_id: Mapped[str] = mapped_column(ForeignKey("rumah_sakit.id"), index=True)
    mesin_id: Mapped[str] = mapped_column(String(24))
    public_key: Mapped[str] = mapped_column(String(64))  # Ed25519, heksadesimal
    aktif: Mapped[bool] = mapped_column(Boolean)


class StatusSensor(Base):
    """Pesan perangkat yang lolos verifikasi tanda tangan (satu baris per jendela)."""

    __tablename__ = "status_sensor"
    __table_args__ = (Index("ix_status_sensor_device_seq", "device_id", "seq"),)

    id: Mapped[int] = mapped_column(_ID, primary_key=True, autoincrement=True)
    dataset_id: Mapped[str] = mapped_column(String(16), index=True)
    device_id: Mapped[str] = mapped_column(ForeignKey("perangkat.device_id"))
    window_start: Mapped[datetime] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(8))
    confidence: Mapped[float] = mapped_column(Float)
    seq: Mapped[int] = mapped_column(Integer)
    prev_hash: Mapped[bytes] = mapped_column(LargeBinary(32))
    hash: Mapped[bytes] = mapped_column(LargeBinary(32))
    tanda_tangan: Mapped[bytes] = mapped_column(LargeBinary(64))
    versi_model: Mapped[str] = mapped_column(String(16))


class SensorAnomali(Base):
    __tablename__ = "sensor_anomali"

    id: Mapped[int] = mapped_column(_ID, primary_key=True, autoincrement=True)
    dataset_id: Mapped[str | None] = mapped_column(String(16), index=True)  # kosong bila perangkat tak dikenal
    jenis: Mapped[str] = mapped_column(String(16), index=True)  # TAMPER_SIG / TAMPER_CHAIN / TAMPER_GAP
    device_id: Mapped[str] = mapped_column(String(40), index=True)
    waktu: Mapped[datetime] = mapped_column(DateTime)
    durasi_menit: Mapped[int | None] = mapped_column(Integer)  # khusus TAMPER_GAP
    keterangan: Mapped[str] = mapped_column(Text)


class StatusMesinHarian(Base):
    """Ringkasan menit per status per mesin per shift per hari (untuk SEN-01 dan dashboard)."""

    __tablename__ = "status_mesin_harian"

    dataset_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    mesin_id: Mapped[str] = mapped_column(String(24), primary_key=True)
    tanggal: Mapped[date] = mapped_column(Date, primary_key=True)
    shift: Mapped[int] = mapped_column(Integer, primary_key=True)  # 0 = di luar jam shift
    rs_id: Mapped[str] = mapped_column(ForeignKey("rumah_sakit.id"), index=True)
    menit_terapi: Mapped[int] = mapped_column(Integer)
    menit_standby: Mapped[int] = mapped_column(Integer)
    menit_mati: Mapped[int] = mapped_column(Integer)
    menit_tanpa_data: Mapped[int] = mapped_column(Integer)
