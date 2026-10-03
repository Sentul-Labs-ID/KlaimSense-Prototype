"""PERANGKAT (edge): berjalan "di perangkat" yang terpasang di mesin hemodialisa.

Perangkat hanya menerima larik arus dari sensornya, menghitung fitur per jendela,
mengklasifikasikan status (mati/standby/terapi) dengan pohon keputusan, lalu
mengirim ringkasan status per jendela yang ditandatangani Ed25519 dan dirantai
dengan hash. Perangkat TIDAK membaca basis data dan tidak mengirim sinyal mentah.
"""

import hashlib
import pickle
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from sentinel.sensor import konfigurasi as k
from sentinel.sensor.protokol import HASH_AWAL, hash_pesan, kanonik

NAMA_FITUR = ("rata_rata", "simpangan_baku", "puncak", "fluktuasi")


def fitur(arus: np.ndarray, panjang_jendela: int) -> np.ndarray:
    """Fitur per jendela: rata-rata, simpangan baku, puncak, dan fluktuasi berkala
    (rata-rata selisih mutlak antar-menit berurutan; besar bila pompa berdenyut)."""
    jendela = arus[: len(arus) // panjang_jendela * panjang_jendela].reshape(-1, panjang_jendela)
    return np.column_stack([
        jendela.mean(axis=1),
        jendela.std(axis=1),
        jendela.max(axis=1),
        np.abs(np.diff(jendela, axis=1)).mean(axis=1),
    ])


def label_jendela(label_menit: np.ndarray, panjang_jendela: int) -> np.ndarray:
    """Label mayoritas per jendela (dipakai untuk melatih dan menguji model)."""
    jendela = label_menit[: len(label_menit) // panjang_jendela * panjang_jendela].reshape(-1, panjang_jendela)
    hitung = np.stack([(jendela == s).sum(axis=1) for s in range(len(k.STATUS))], axis=1)
    return hitung.argmax(axis=1)


# ------------------------------------------------------------------- model


@dataclass(frozen=True)
class ModelEdge:
    pohon: object  # sklearn DecisionTreeClassifier
    panjang_jendela: int
    sha256: str

    @property
    def versi(self) -> str:
        return self.sha256[:12]


def path_model(direktori: Path | None = None) -> Path:
    return (direktori or k.DIREKTORI_MODEL) / k.NAMA_MODEL


def muat_model(path: Path | None = None) -> ModelEdge:
    """Muat model dari file dan pastikan hash-nya cocok dengan file .sha256."""
    path = path or path_model()
    isi = path.read_bytes()
    sha = hashlib.sha256(isi).hexdigest()
    tercatat = path.with_suffix(".sha256").read_text(encoding="utf-8").split()[0]
    if sha != tercatat:
        raise ValueError(f"hash model tidak cocok: file {sha[:12]}, tercatat {tercatat[:12]}")
    data = pickle.loads(isi)
    return ModelEdge(data["pohon"], data["panjang_jendela"], sha)


def klasifikasi(model: ModelEdge, arus: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """(kode status per jendela, confidence per jendela)."""
    x = fitur(arus, model.panjang_jendela)
    proba = model.pohon.predict_proba(x)
    kelas = model.pohon.classes_[proba.argmax(axis=1)]
    return kelas.astype(int), proba.max(axis=1)


# --------------------------------------------------------------- perangkat


def kunci_simulasi(device_id: str, seed: int) -> Ed25519PrivateKey:
    """HANYA UNTUK SIMULASI: kunci privat diturunkan dari seed agar hasil bisa direproduksi.
    Perangkat sungguhan membangkitkan kunci di dalam secure element dan kunci privat
    tidak pernah keluar dari perangkat. Server hanya menyimpan kunci publik."""
    return Ed25519PrivateKey.from_private_bytes(hashlib.sha256(f"kunci:{seed}:{device_id}".encode()).digest())


class Perangkat:
    def __init__(self, device_id: str, rs_id: str, mesin_id: str, kunci: Ed25519PrivateKey, model: ModelEdge):
        self.device_id, self.rs_id, self.mesin_id = device_id, rs_id, mesin_id
        self._kunci = kunci
        self.model = model
        self.seq = 0
        self.hash_terakhir = HASH_AWAL

    def pesan(self, window_start: datetime, status: str, confidence: float) -> dict:
        """Bangun dan tandatangani satu pesan; memajukan seq dan rantai hash."""
        self.seq += 1
        isi = {
            "device_id": self.device_id,
            "rs_id": self.rs_id,
            "mesin_id": self.mesin_id,
            "window_start": window_start.isoformat(timespec="minutes"),
            "status": status,
            "confidence": round(float(confidence), 3),
            "seq": self.seq,
            "prev_hash": self.hash_terakhir,
            "versi_model": self.model.versi,
        }
        self.hash_terakhir = hash_pesan(isi)
        return {"pesan": isi, "tanda_tangan": self._kunci.sign(kanonik(isi)).hex()}

    def proses(self, arus: np.ndarray, mulai: datetime, aktif: np.ndarray | None = None) -> list[dict]:
        """Klasifikasikan seluruh larik arus dan kirim satu pesan per jendela.
        `aktif[i] = False` berarti perangkat tidak menyala/tidak terpasang pada jendela i
        (tidak ada pesan, seq tidak bertambah)."""
        kode, keyakinan = klasifikasi(self.model, arus)
        langkah = timedelta(minutes=self.model.panjang_jendela)
        keluar = []
        for i, (s, c) in enumerate(zip(kode, keyakinan)):
            if aktif is not None and not aktif[i]:
                continue
            keluar.append(self.pesan(mulai + i * langkah, k.STATUS[s], c))
        return keluar
