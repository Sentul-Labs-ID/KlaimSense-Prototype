"""Grafik laporan evaluasi (PNG untuk slide). Warna: palet referensi tervalidasi.

- Hidden = slot kategorikal 1 (biru), utama = slot 2 (oranye); lulus validator (CVD ΔE 24,7).
- Matriks memakai satu hue berurutan (biru, terang -> gelap) dengan angka tertulis di sel.
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402

from sentinel.evaluation import metrik as m  # noqa: E402
from sentinel.evaluation.laporan import LABEL_KONDISI  # noqa: E402

PERMUKAAN = "#fcfcfb"
TEKS = "#0b0b0b"
TEKS_2 = "#52514e"
GRID = "#e4e3df"
HIDDEN = "#2a78d6"
UTAMA = "#eb6834"
LABEL_GRAFIK = {
    "KAP_FISIO": "Fisioterapi\nmelebihi kapasitas",
    "KAP_HD": "Hemodialisa\nmelebihi kapasitas",
    "ULANG_IDENTIK": "Tagihan\nduplikat persis",
    "ULANG_HARI": "Dua sesi HD\nsehari",
    "HARGA_LEBIH": "Harga di atas\nharga acuan",
    "ABD_DINI": "Alat bantu dengar\nsebelum waktunya",
    "SENSOR_PALSU": "HD ditagih tanpa\nkerja mesin",
    "TAMPER_SIG": "Pesan sensor\npalsu",
    "TAMPER_GAP": "Sensor\ndicabut",
}
RAMPA_BIRU = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]


def _gaya(ax):
    ax.set_facecolor(PERMUKAAN)
    for sisi in ("top", "right"):
        ax.spines[sisi].set_visible(False)
    for sisi in ("left", "bottom"):
        ax.spines[sisi].set_color(GRID)
    ax.tick_params(colors=TEKS_2, labelsize=9)


def recall_per_skenario(hasil: dict, path: Path) -> None:
    seri = [(nama, warna, hasil.get(kunci)) for nama, warna, kunci in (
        ("Hidden (uji akhir)", HIDDEN, "hidden"), ("Utama (pengembangan)", UTAMA, "utama"))]
    seri = [s for s in seri if s[2]]
    skenario = list(m.PEMETAAN)
    fig, ax = plt.subplots(figsize=(13.33, 5.6), dpi=150)
    fig.patch.set_facecolor(PERMUKAAN)
    _gaya(ax)
    lebar = 0.38
    for j, (nama, warna, data) in enumerate(seri):
        offset = (j - (len(seri) - 1) / 2) * (lebar + 0.02)
        for i, s in enumerate(skenario):
            r = data["recall_per_skenario"][s]["recall"]
            if r["penyebut"] == 0:
                continue
            x = i + offset
            ax.bar(x, r["nilai"] * 100, width=lebar, color=warna, label=nama if i == 0 else None, zorder=2)
            lo, hi = r["ci95"]
            ax.errorbar(x, r["nilai"] * 100, yerr=[[(r["nilai"] - lo) * 100], [(hi - r["nilai"]) * 100]],
                        fmt="none", ecolor=TEKS_2, elinewidth=1.2, capsize=3, zorder=3)
            ax.text(x, hi * 100 + 2, f"{r['pembilang']}/{r['penyebut']}", ha="center", va="bottom",
                    fontsize=8, color=TEKS)
    ax.set_xticks(range(len(skenario)))
    ax.set_xticklabels([LABEL_GRAFIK[s] for s in skenario], fontsize=9, color=TEKS)
    ax.set_ylim(0, 118)
    ax.set_yticks(range(0, 101, 20))
    ax.set_yticklabels([f"{v}%" for v in range(0, 101, 20)])
    ax.yaxis.grid(True, color=GRID, linewidth=0.8, zorder=0)
    ax.set_ylabel("Kejadian tertangkap (recall)", color=TEKS_2, fontsize=10)
    ax.set_title("Deteksi per skenario, dengan interval kepercayaan 95% (Wilson)", color=TEKS, fontsize=13, loc="left")
    ax.legend(loc="lower right", bbox_to_anchor=(1.0, 1.0), ncol=2, frameon=False, fontsize=9, labelcolor=TEKS)
    fig.text(0.01, 0.01, "Data tiruan. Angka di atas batang = tertangkap/jumlah kejadian.", fontsize=8, color=TEKS_2)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(path, facecolor=PERMUKAAN)
    plt.close(fig)


def matriks_prioritas(data: dict, path: Path, judul: str) -> None:
    matriks = data["prioritas"]["matriks_prioritas_kondisi"]
    nilai = [[matriks[p][c] for c in m.KONDISI] for p in m.PRIORITAS]
    puncak = max(max(r) for r in nilai) or 1
    peta = LinearSegmentedColormap.from_list("biru", RAMPA_BIRU)
    fig, ax = plt.subplots(figsize=(8.5, 4.2), dpi=150)
    fig.patch.set_facecolor(PERMUKAAN)
    ax.imshow([[v / puncak for v in r] for r in nilai], cmap=peta, vmin=0, vmax=1, aspect="auto")
    for i, r in enumerate(nilai):
        for j, v in enumerate(r):
            gelap = v / puncak > 0.55
            ax.text(j, i, str(v), ha="center", va="center", fontsize=14, fontweight="bold",
                    color="#ffffff" if gelap else TEKS)
    ax.set_xticks(range(len(m.KONDISI)))
    ax.set_xticklabels([LABEL_KONDISI[c].replace(" (", "\n(") for c in m.KONDISI], fontsize=9, color=TEKS)
    ax.set_yticks(range(len(m.PRIORITAS)))
    ax.set_yticklabels([f"Prioritas {p}" for p in m.PRIORITAS], fontsize=10, color=TEKS)
    ax.tick_params(length=0)
    for sisi in ax.spines.values():
        sisi.set_visible(False)
    ax.set_xticks([x - 0.5 for x in range(1, len(m.KONDISI))], minor=True)
    ax.set_yticks([y - 0.5 for y in range(1, len(m.PRIORITAS))], minor=True)
    ax.grid(which="minor", color=PERMUKAAN, linewidth=3)
    ax.tick_params(which="minor", length=0)
    ax.set_title(judul, color=TEKS, fontsize=12, loc="left")
    fig.text(0.01, 0.01, "Jumlah RS-periode (rumah sakit × bulan). Data tiruan.", fontsize=8, color=TEKS_2)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(path, facecolor=PERMUKAAN)
    plt.close(fig)
