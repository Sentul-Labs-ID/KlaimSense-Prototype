"""Penjaga prinsip 6: batas akses tabel kenyataan dan evaluasi.

- Mesin aturan (`sentinel/rules/`) tidak boleh menyentuh kenyataan fisik
  (`sesi_aktual`) maupun tabel evaluasi (`ground_truth`, `profil_rs`, `kasus_sah`).
- API dashboard (`sentinel/api/`) tidak boleh mengekspos tabel evaluasi.

Tes ini sudah ada sejak fase 1 supaya pelanggaran di fase berikutnya langsung tertangkap.
"""

from pathlib import Path

import pytest

PAKET = Path(__file__).resolve().parents[1] / "sentinel"
EVALUASI = (
    "sentinel.models.evaluasi",
    "GroundTruth",
    "ProfilRS",
    "KasusSah",
    "ground_truth",
    "profil_rs",
    "kasus_sah",
)
KENYATAAN = ("sentinel.models.kenyataan", "SesiAktual", "sesi_aktual")
TERLARANG = {
    "rules": KENYATAAN + EVALUASI,
    "api": EVALUASI,
}


@pytest.mark.parametrize("modul", sorted(TERLARANG))
def test_modul_tidak_menyentuh_tabel_terlarang(modul):
    for berkas in sorted((PAKET / modul).rglob("*.py")):
        isi = berkas.read_text(encoding="utf-8")
        for kata in TERLARANG[modul]:
            assert kata not in isi, f"{berkas.relative_to(PAKET)} menyebut {kata!r}"
