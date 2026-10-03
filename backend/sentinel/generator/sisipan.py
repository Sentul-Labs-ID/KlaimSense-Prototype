"""Sisipan kecurangan untuk panel demo dashboard, langsung ke basis data dataset "demo".

Memakai logika generator (tarif paket, besaran lewat kapasitas dari profil, harga acuan
dan toleransi dari parameter.yaml), tetapi bekerja pada data yang sudah tersimpan.
Hanya membaca tabel master dan transaksi; tidak menulis label evaluasi apa pun.
"""

import random
from collections import defaultdict
from dataclasses import dataclass
from datetime import date

from sqlalchemy import Engine, func, insert, select, update

from sentinel.generator import katalog
from sentinel.generator.profil import PROFIL
from sentinel.models.master import HargaAcuan, Kapasitas, RumahSakit
from sentinel.models.transaksi import Tagihan
from sentinel.parameter import Parameter

JENIS_SISIPAN = ("KAP_FISIO", "KAP_HD", "ULANG_HARI", "HARGA_LEBIH")
DATASET_DEMO = "demo"


@dataclass
class HasilSisipan:
    tanggal: list[date]
    tagihan_baru: int
    tagihan_diubah: int


class SisipanDitolak(ValueError):
    pass


def sisipkan(
    engine: Engine, p: Parameter, rs_id: str, jenis: str, jumlah_hari: int, periode: str | None = None, seed: int = 0,
) -> HasilSisipan:
    if jenis not in JENIS_SISIPAN:
        raise SisipanDitolak(f"Jenis sisipan tidak dikenal: {jenis}.")
    if not 1 <= jumlah_hari <= 5:
        raise SisipanDitolak("Jumlah hari harus 1 sampai 5.")
    rng = random.Random(f"{seed}:{rs_id}:{jenis}:{periode}")
    t, r, k = Tagihan.__table__, RumahSakit.__table__, Kapasitas.__table__
    with engine.connect() as conn:
        rs = conn.execute(select(r).where(r.c.id == rs_id, r.c.dataset_id == DATASET_DEMO)).mappings().first()
        if rs is None:
            raise SisipanDitolak(f"Rumah sakit {rs_id} tidak ada di dataset demo.")
        kap = conn.execute(select(k).where(k.c.rs_id == rs_id)).mappings().one()
        query = select(t).where(t.c.dataset_id == DATASET_DEMO, t.c.rs_id == rs_id).order_by(t.c.id)
        tagihan = [dict(x) for x in conn.execute(query).mappings()]
        acuan = {x.kode_item: x.harga for x in conn.execute(
            select(HargaAcuan.kode_item, HargaAcuan.harga).where(HargaAcuan.dataset_id == DATASET_DEMO)
        )}
        id_berikut = (conn.execute(select(func.max(t.c.id)).where(t.c.dataset_id == DATASET_DEMO)).scalar() or 0) + 1

    if periode:
        tagihan_periode = [x for x in tagihan if x["tanggal"].strftime("%Y-%m") == periode]
    else:
        tagihan_periode = tagihan
    per_hari: dict[tuple[str, date], list[dict]] = defaultdict(list)
    for x in tagihan_periode:
        per_hari[(x["layanan"], x["tanggal"])].append(x)
    pasien = defaultdict(list)
    for x in tagihan:
        if x["pasien_id"] not in pasien[x["layanan"]]:
            pasien[x["layanan"]].append(x["pasien_id"])

    profil = PROFIL[DATASET_DEMO]

    def besaran(kapasitas: int) -> int:
        if rng.random() < profil.kap_porsi_halus:
            return rng.randint(1, 2)
        return max(1, round(kapasitas * rng.uniform(*profil.kap_lebih_persen) / 100))

    def tagihan_baru(layanan: str, tgl: date, pasien_id: str, harga: int) -> dict:
        nonlocal id_berikut
        baris = {
            "id": id_berikut, "dataset_id": DATASET_DEMO, "rs_id": rs_id, "pasien_id": pasien_id, "tanggal": tgl,
            "layanan": layanan, "kode_item": None, "sisi_telinga": None, "jumlah": 1, "harga_satuan": harga,
            "total": harga,
        }
        id_berikut += 1
        return baris

    baru: list[dict] = []
    diubah: list[tuple[int, int, int]] = []
    hari_dipakai: list[date] = []

    if jenis in ("KAP_FISIO", "KAP_HD", "ULANG_HARI"):
        layanan = "fisioterapi" if jenis == "KAP_FISIO" else "hemodialisa"
        kapasitas = (
            kap["jumlah_fisioterapis"] * p.kapasitas.fisioterapi_sesi_per_terapis_per_hari
            if layanan == "fisioterapi" else kap["jumlah_mesin_hd"] * kap["shift_hd_per_hari"]
        )
        tarif = (katalog.TARIF_FISIOTERAPI if layanan == "fisioterapi" else katalog.TARIF_HEMODIALISA)[rs["kelas"]]
        calon = sorted(tg for (lay, tg) in per_hari if lay == layanan)
        if jenis != "ULANG_HARI":
            calon = [tg for tg in calon if len(per_hari[(layanan, tg)]) <= kapasitas]  # hari yang belum lewat kapasitas
        rng.shuffle(calon)
        for tgl in calon[:jumlah_hari]:
            ada = per_hari[(layanan, tgl)]
            ditagih = {x["pasien_id"] for x in ada}
            if jenis == "ULANG_HARI":
                for x in rng.sample(ada, min(len(ada), rng.randint(1, 2))):
                    baru.append({**x, "id": None})
            else:
                n = kapasitas - len(ada) + besaran(kapasitas)
                bebas = [pid for pid in pasien[layanan] if pid not in ditagih]
                for pid in rng.sample(bebas, min(n, len(bebas))):
                    baru.append(tagihan_baru(layanan, tgl, pid, tarif))
            hari_dipakai.append(tgl)
        for x in baru:
            if x["id"] is None:
                x["id"] = id_berikut
                id_berikut += 1
    else:  # HARGA_LEBIH: harga satuan obat/ABD dinaikkan di atas acuan + toleransi
        lo, hi = profil.harga_lebih_persen
        calon = sorted({tg for (lay, tg) in per_hari if lay in ("obat_kronis", "alat_bantu_dengar")})
        rng.shuffle(calon)
        for tgl in calon[:jumlah_hari]:
            pilihan = per_hari[("obat_kronis", tgl)] + per_hari[("alat_bantu_dengar", tgl)]
            for x in rng.sample(pilihan, min(len(pilihan), rng.randint(1, 3))):
                harga = round(acuan[x["kode_item"]] * (1 + rng.uniform(lo, hi) / 100))
                diubah.append((x["id"], harga, harga * x["jumlah"]))
            hari_dipakai.append(tgl)

    if not hari_dipakai:
        raise SisipanDitolak("Tidak ada hari yang cocok untuk sisipan ini di periode yang dipilih.")
    with engine.begin() as conn:
        if baru:
            conn.execute(insert(t), baru)
        for tid, harga, total in diubah:
            conn.execute(update(t).where(t.c.id == tid).values(harga_satuan=harga, total=total))
    return HasilSisipan(sorted(hari_dipakai), len(baru), len(diubah))
