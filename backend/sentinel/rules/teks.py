"""Format teks bahasa Indonesia untuk penjelasan temuan (template, bukan LLM)."""

from datetime import date

BULAN = (
    "Januari", "Februari", "Maret", "April", "Mei", "Juni",
    "Juli", "Agustus", "September", "Oktober", "November", "Desember",
)
HARI = ("Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu")
NAMA_LAYANAN = {
    "fisioterapi": "Fisioterapi",
    "hemodialisa": "Hemodialisa",
    "obat_kronis": "Obat kronis",
    "alat_bantu_dengar": "Alat bantu dengar",
}


def tanggal(d: date) -> str:
    return f"{d.day} {BULAN[d.month - 1]} {d.year}"


def hari_tanggal(d: date) -> str:
    return f"{HARI[d.weekday()]}, {tanggal(d)}"


def periode(p: str) -> str:
    tahun, bulan = p.split("-")
    return f"{BULAN[int(bulan) - 1]} {tahun}"


def angka(n: float, desimal: int = 0) -> str:
    teks = f"{n:,.{desimal}f}"
    return teks.replace(",", "_").replace(".", ",").replace("_", ".")


def rupiah(n: float) -> str:
    return f"Rp{angka(n)}"


def persen(rasio: float, desimal: int = 1) -> str:
    return f"{angka(rasio * 100, desimal)}%"


def bilangan(n: float) -> str:
    """5.0 -> '5', 4.5 -> '4,5'."""
    return f"{n:g}".replace(".", ",")


def tambah_bulan(d: date, bulan: int) -> date:
    """Tambah bulan kalender; tanggal dipotong ke akhir bulan bila perlu (29 Feb + 12 bulan = 28 Feb)."""
    total = d.year * 12 + (d.month - 1) + bulan
    tahun, bulan_baru = divmod(total, 12)
    bulan_baru += 1
    akhir = [31, 29 if tahun % 4 == 0 and (tahun % 100 != 0 or tahun % 400 == 0) else 28,
             31, 30, 31, 30, 31, 31, 30, 31, 30, 31][bulan_baru - 1]
    return date(tahun, bulan_baru, min(d.day, akhir))


def selang(awal: date, akhir: date) -> str:
    """Selang waktu dalam tahun dan bulan penuh, misalnya '2 tahun 1 bulan'."""
    bulan = (akhir.year - awal.year) * 12 + (akhir.month - awal.month)
    if akhir.day < awal.day:
        bulan -= 1
    if bulan <= 0:
        return f"{(akhir - awal).days} hari"
    tahun, sisa = divmod(bulan, 12)
    bagian = []
    if tahun:
        bagian.append(f"{tahun} tahun")
    if sisa:
        bagian.append(f"{sisa} bulan")
    return " ".join(bagian)
