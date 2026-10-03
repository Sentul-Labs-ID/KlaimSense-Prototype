"""SERVER: ringkasan harian status mesin dari pesan perangkat yang valid.

Satu baris per (mesin, tanggal, shift). Shift mengikuti jadwal unit yang dideklarasikan
(`konfigurasi.JADWAL_SHIFT`); shift 0 = di luar jam shift. Menit tanpa data = panjang
slot dikurangi menit yang tercakup pesan valid.
"""

from collections import defaultdict
from datetime import date

from sqlalchemy import Engine, delete, insert, select

from sentinel.models.sensor import Perangkat, StatusMesinHarian, StatusSensor
from sentinel.sensor import konfigurasi as k


def slot_shift() -> dict[int, int]:
    """Panjang (menit) tiap slot shift dalam sehari, termasuk shift 0."""
    panjang = {s: b - a for s, (a, b) in k.JADWAL_SHIFT.items()}
    panjang[k.SHIFT_DI_LUAR] = k.MENIT_SEHARI - sum(panjang.values())
    return dict(sorted(panjang.items()))


def shift_untuk(menit: int) -> int:
    for shift, (a, b) in k.JADWAL_SHIFT.items():
        if a <= menit < b:
            return shift
    return k.SHIFT_DI_LUAR


def ringkas_perangkat(
    baris_status: list[dict],
    dataset_id: str,
    rs_id: str,
    mesin_id: str,
    daftar_tanggal: list[date],
    panjang_jendela: int,
) -> list[dict]:
    slot = slot_shift()
    hitung: dict[tuple[date, int], dict[str, int]] = defaultdict(lambda: {"terapi": 0, "standby": 0, "mati": 0})
    rentang = set(daftar_tanggal)
    for b in baris_status:
        ws = b["window_start"]
        if ws.date() in rentang:
            hitung[(ws.date(), shift_untuk(ws.hour * 60 + ws.minute))][b["status"]] += panjang_jendela
    hasil = []
    for tgl in daftar_tanggal:
        for shift, panjang in slot.items():
            h = hitung.get((tgl, shift), {"terapi": 0, "standby": 0, "mati": 0})
            terisi = min(panjang, h["terapi"] + h["standby"] + h["mati"])
            hasil.append({
                "dataset_id": dataset_id, "mesin_id": mesin_id, "tanggal": tgl, "shift": shift, "rs_id": rs_id,
                "menit_terapi": h["terapi"], "menit_standby": h["standby"], "menit_mati": h["mati"],
                "menit_tanpa_data": panjang - terisi,
            })
    return hasil


def simpan_ringkasan(engine: Engine, baris: list[dict]) -> None:
    with engine.begin() as conn:
        for i in range(0, len(baris), 5_000):
            conn.execute(insert(StatusMesinHarian.__table__), baris[i : i + 5_000])


def perbarui_ringkasan(engine: Engine, dataset_id: str, daftar_tanggal: list[date], panjang_jendela: int) -> int:
    """Hitung ulang ringkasan seluruh perangkat sebuah dataset dari tabel status_sensor."""
    p, s, h = Perangkat.__table__, StatusSensor.__table__, StatusMesinHarian.__table__
    total = 0
    with engine.connect() as conn:
        perangkat = conn.execute(select(p.c.device_id, p.c.rs_id, p.c.mesin_id).where(p.c.dataset_id == dataset_id)).all()
    with engine.begin() as conn:
        conn.execute(delete(h).where(h.c.dataset_id == dataset_id))
    for device_id, rs_id, mesin_id in perangkat:
        with engine.connect() as conn:
            baris = [dict(x) for x in conn.execute(
                select(s.c.window_start, s.c.status).where(s.c.device_id == device_id)
            ).mappings()]
        ringkas = ringkas_perangkat(baris, dataset_id, rs_id, mesin_id, daftar_tanggal, panjang_jendela)
        simpan_ringkasan(engine, ringkas)
        total += len(ringkas)
    return total
