"""Format pesan perangkat -> server (dipakai bersama oleh perangkat dan server).

Pesan berisi ringkasan status per jendela, BUKAN sinyal mentah. Bentuk kanonik
(JSON, kunci terurut, tanpa spasi) adalah yang ditandatangani dan di-hash.
"""

import hashlib
import json

FIELD_PESAN = (
    "device_id", "rs_id", "mesin_id", "window_start", "status", "confidence", "seq", "prev_hash", "versi_model",
)
HASH_AWAL = "0" * 64  # prev_hash pesan pertama setiap perangkat


def kanonik(pesan: dict) -> bytes:
    return json.dumps({f: pesan[f] for f in FIELD_PESAN}, sort_keys=True, separators=(",", ":")).encode("utf-8")


def hash_pesan(pesan: dict) -> str:
    return hashlib.sha256(kanonik(pesan)).hexdigest()
