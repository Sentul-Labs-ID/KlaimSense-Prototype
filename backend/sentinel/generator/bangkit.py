"""Pembangkit data tiruan berseed.

Urutan kerja:
1. Rumah sakit disebar ke kombinasi kelas-provinsi (minimal 3 per kombinasi), lalu
   diberi peran: kontrol (jujur, jujur-sibuk, volume tinggi) atau disisipi skenario.
2. Kenyataan fisik dibangkitkan dulu (`sesi_aktual`) beserta tagihan jujurnya.
3. Skenario kecurangan disisipkan per kejadian (rumah sakit, tanggal) dan dicatat
   di ground truth.
   Lalu kasus sah di area batas (shift darurat, lembur, harga acuan lama) ditambahkan
   di rumah sakit jujur dan jujur-sibuk, dicatat di `kasus_sah`. Kasus ini memang akan
   tertandai aturan; evaluasi menghitungnya sebagai tuduhan keliru agar angka false
   positive tidak terlalu bersih.
4. ID tagihan diberikan SETELAH semua penyisipan, berurutan menurut tanggal dan
   rumah sakit dengan urutan acak di dalamnya, sehingga ID tidak membocorkan
   tagihan mana yang disisipkan.

Seluruh keacakan berasal dari satu `random.Random(seed)` dan tidak ada iterasi atas
`set`, sehingga hasil identik untuk seed yang sama di proses mana pun.
"""

from __future__ import annotations

import math
import random
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Callable

from sentinel.generator import katalog
from sentinel.generator.profil import PROFIL, UMUM, ProfilDataset
from sentinel.models.evaluasi import JENIS_KASUS_SAH, SKENARIO
from sentinel.parameter import Parameter, muat_parameter

MULAI_DEFAULT = date(2026, 7, 1)
HARI_DEFAULT = 90
RS_DEFAULT = 30
RS_MINIMUM = 20
HARI_MINIMUM = 28
TAHUN_RIWAYAT_ABD = 6
SABTU, MINGGU = 5, 6
SISI = ("kiri", "kanan")

# Pola jadwal hemodialisa (weekday: 0 = Senin).
POLA_HD_DUA = [(0, 3), (1, 4), (2, 5)]
POLA_HD_TIGA = [(0, 2, 4), (1, 3, 5)]
POLA_HD_MINGGU = [(6, 3)]  # tambahan untuk unit yang buka 7 hari

URUTAN_TABEL = (
    "rumah_sakit",
    "kapasitas",
    "pasien",
    "harga_acuan",
    "riwayat_alat_bantu_dengar",
    "tagihan",
    "sesi_aktual",
    "ground_truth",
    "kasus_sah",
    "profil_rs",
)


@dataclass
class DataTiruan:
    dataset_id: str
    seed: int
    mulai: date
    hari: int
    tabel: dict[str, list[dict]]


@dataclass
class _PasienHD:
    id: str
    pola: tuple[int, ...]
    mesin: int
    shift: int
    mulai: date
    selesai: date | None

    def aktif(self, tgl: date) -> bool:
        return self.mulai <= tgl and (self.selesai is None or tgl < self.selesai)


@dataclass
class _RS:
    baris: dict
    profil: str = "jujur"
    skenario: list[str] = field(default_factory=list)
    kap: dict = field(default_factory=dict)
    utilisasi: float = 0.0
    utilisasi_hd: float = 0.0
    pasien_fisio: list[str] = field(default_factory=list)
    pasien_hd: list[_PasienHD] = field(default_factory=list)
    pasien_hd_semua: list[str] = field(default_factory=list)
    pasien_hd_tidak_aktif: list[str] = field(default_factory=list)
    pasien_abd: list[str] = field(default_factory=list)
    hari_hd: tuple[int, ...] = ()
    kapasitas_fisio: int = 0
    kapasitas_hd: int = 0

    @property
    def id(self) -> str:
        return self.baris["id"]

    @property
    def kelas(self) -> str:
        return self.baris["kelas"]


class _Pembangkit:
    def __init__(
        self,
        param: Parameter,
        profil: ProfilDataset,
        seed: int,
        mulai: date,
        hari: int,
        jumlah_rs: int,
    ):
        if jumlah_rs < RS_MINIMUM:
            raise ValueError(f"jumlah rumah sakit minimal {RS_MINIMUM}, diberikan {jumlah_rs}")
        if hari < HARI_MINIMUM:
            raise ValueError(f"jumlah hari minimal {HARI_MINIMUM}, diberikan {hari}")

        self.param = param
        self.profil = profil
        self.dataset_id = profil.dataset_id
        self.seed = seed
        self.rng = random.Random(seed)
        self.mulai = mulai
        self.hari = hari
        self.akhir = mulai + timedelta(days=hari)  # eksklusif
        self.jumlah_rs = jumlah_rs
        self.daftar_tanggal = [mulai + timedelta(days=i) for i in range(hari)]
        self.hari_kerja = [t for t in self.daftar_tanggal if t.weekday() != MINGGU]

        self.toleransi = param.kewajaran.toleransi_harga_di_atas_acuan_persen / 100
        self.masa_abd_tahun = param.kewajaran.alat_bantu_dengar_masa_penggantian_tahun
        self.masa_abd_hari = round(self.masa_abd_tahun * 365.25)
        self.abd_per_telinga = param.kewajaran.alat_bantu_dengar_per_telinga
        # Besaran HARGA_LEBIH selalu di atas toleransi, walau toleransi di parameter.yaml diubah.
        lo, hi = profil.harga_lebih_persen
        batas_bawah = param.kewajaran.toleransi_harga_di_atas_acuan_persen + 5
        self.harga_lebih = (max(lo, batas_bawah), max(hi, batas_bawah + 1))

        self.harga = {kode: harga for kode, _, _, harga in katalog.HARGA_ACUAN}
        self.item_obat = [k for k, _, j, _ in katalog.HARGA_ACUAN if j == "obat_kronis"]
        self.item_abd = [k for k, _, j, _ in katalog.HARGA_ACUAN if j == "alat_bantu_dengar"]

        self.rs: list[_RS] = []
        self.pasien: list[dict] = []
        self.tagihan: list[dict] = []
        self.sesi: list[dict] = []
        self.riwayat: list[dict] = []
        self.kejadian: list[tuple[str, str, date, list[dict], str]] = []
        self.kasus_sah: list[tuple[str, str, date, list[dict], str]] = []

        self._indeks: dict[tuple[str, str, date], list[dict]] = defaultdict(list)
        self._abd_terakhir: dict[tuple, date] = {}
        self._abd_ditagih: set[tuple] = set()
        self._terpakai: dict[tuple[str, str], set[date]] = defaultdict(set)

    # ------------------------------------------------------------------ utilitas

    def _uniform(self, rentang: tuple[float, float]) -> float:
        return self.rng.uniform(*rentang)

    def _pasien_baru(self, rs: _RS, kelompok: str) -> str:
        nomor = self.profil.offset_pasien + len(self.pasien) + 1
        pid = f"P-{nomor:06d}"
        r = self.rng
        if kelompok == "hemodialisa":
            umur = round(r.triangular(25, 80, 55))
        elif kelompok == "obat_kronis":
            umur = r.randint(40, 85)
        elif kelompok == "alat_bantu_dengar":
            umur = r.randint(50, 90) if r.random() < 0.7 else r.randint(5, 17)
        else:
            umur = r.randint(8, 85)
        provinsi = rs.baris["provinsi"]
        if r.random() < 0.05:
            provinsi = r.choice([p for p in katalog.PROVINSI if p != provinsi])
        self.pasien.append(
            {
                "id_pseudonim": pid,
                "dataset_id": self.dataset_id,
                "umur": umur,
                "jenis_kelamin": r.choice(("L", "P")),
                "provinsi": provinsi,
            }
        )
        return pid

    def _tambah_tagihan(self, t: dict) -> dict:
        self.tagihan.append(t)
        self._indeks[(t["rs_id"], t["layanan"], t["tanggal"])].append(t)
        return t

    def _tagihan(
        self,
        rs: _RS,
        pasien_id: str,
        tgl: date,
        layanan: str,
        harga_satuan: int,
        kode_item: str | None = None,
        sisi: str | None = None,
        jumlah: int = 1,
    ) -> dict:
        return self._tambah_tagihan(
            {
                "id": None,
                "dataset_id": self.dataset_id,
                "rs_id": rs.id,
                "pasien_id": pasien_id,
                "tanggal": tgl,
                "layanan": layanan,
                "kode_item": kode_item,
                "sisi_telinga": sisi,
                "jumlah": jumlah,
                "harga_satuan": harga_satuan,
                "total": jumlah * harga_satuan,
            }
        )

    def _sesi(self, rs: _RS, pasien_id: str, tgl: date, layanan: str, mesin=None, shift=None):
        self.sesi.append(
            {
                "id": None,
                "dataset_id": self.dataset_id,
                "rs_id": rs.id,
                "pasien_id": pasien_id,
                "tanggal": tgl,
                "layanan": layanan,
                "mesin_id": mesin,
                "shift": shift,
            }
        )

    def _harga_normal(self, kode: str) -> int:
        atas = UMUM.harga_normal_porsi_toleransi * self.toleransi
        return round(self.harga[kode] * (1 + self.rng.uniform(UMUM.harga_normal_bawah, atas)))

    def _tagihan_hari(self, rs: _RS, layanan: str, tgl: date) -> list[dict]:
        return self._indeks.get((rs.id, layanan, tgl), [])

    def _kunci_abd(self, pasien_id: str, sisi: str) -> tuple:
        return (pasien_id, sisi) if self.abd_per_telinga else (pasien_id,)

    def _riwayat_baru(self, pasien_id: str, sisi: str, tgl: date) -> None:
        self.riwayat.append(
            {
                "id": None,
                "dataset_id": self.dataset_id,
                "pasien_id": pasien_id,
                "sisi_telinga": sisi,
                "tanggal_diberikan": tgl,
            }
        )
        kunci = self._kunci_abd(pasien_id, sisi)
        if kunci not in self._abd_terakhir or self._abd_terakhir[kunci] < tgl:
            self._abd_terakhir[kunci] = tgl

    def _abd_boleh_normal(self, pasien_id: str, sisi: str, tgl: date) -> bool:
        kunci = self._kunci_abd(pasien_id, sisi)
        if kunci in self._abd_ditagih:
            return False
        terakhir = self._abd_terakhir.get(kunci)
        return terakhir is None or (tgl - terakhir).days >= self.masa_abd_hari + UMUM.margin_abd_hari

    # ------------------------------------------------------- rumah sakit & peran

    def _buat_rumah_sakit(self) -> None:
        r = self.rng
        n = self.jumlah_rs
        k = max(1, min(len(katalog.PRIORITAS_KOMBINASI), (n - 3) // 3))
        kombinasi = katalog.PRIORITAS_KOMBINASI[:k]
        jatah = {c: 3 for c in kombinasi}
        bobot = [katalog.BOBOT_SISA_KELAS[kelas] for _, kelas in kombinasi]
        for _ in range(n - 3 * k):
            jatah[r.choices(kombinasi, weights=bobot)[0]] += 1
        daftar = [c for c in kombinasi for _ in range(jatah[c])]
        r.shuffle(daftar)
        for i, (indeks_prov, kelas) in enumerate(daftar):
            nomor = self.profil.offset_rs + i + 1
            provinsi = katalog.PROVINSI[indeks_prov]
            self.rs.append(
                _RS(
                    baris={
                        "id": f"RS-{nomor:03d}",
                        "dataset_id": self.dataset_id,
                        "nama_samaran": f"RS Tiruan {nomor:03d}",
                        "kelas": kelas,
                        "provinsi": provinsi,
                        "kab_kota": r.choice(katalog.KAB_KOTA[provinsi]),
                        "punya_sensor": False,
                    }
                )
            )

    def _tetapkan_peran(self) -> None:
        r = self.rng
        prof = self.profil

        r.choice([x for x in self.rs if x.kelas == "A"]).profil = "jujur_volume_tinggi"
        calon_sibuk = [x for x in self.rs if x.kelas in ("B", "C") and x.profil == "jujur"]
        sibuk = r.sample(calon_sibuk, UMUM.kontrol_sibuk)
        for x in sibuk:
            x.profil = "jujur_sibuk"

        calon = [x for x in self.rs if x.profil == "jujur"]
        disisipi = r.sample(calon, prof.jumlah_rs_disisipi)
        for x in disisipi:
            x.profil = "disisipi"
        for skenario in SKENARIO:
            k = r.randint(*prof.rs_per_skenario)
            # Utamakan rumah sakit dengan skenario paling sedikit agar semua kebagian.
            urut = sorted(disisipi, key=lambda x: (len(x.skenario), r.random()))
            for x in urut[:k]:
                x.skenario.append(skenario)

        # Sensor: semua rumah sakit SENSOR_PALSU, minimal N kontrol jujur (termasuk
        # satu yang sibuk), sisanya acak.
        sensor = [x for x in disisipi if "SENSOR_PALSU" in x.skenario]
        satu_sibuk = r.choice(sibuk)
        jujur_lain = [x for x in self.rs if x.profil != "disisipi" and x is not satu_sibuk]
        sensor += [satu_sibuk] + r.sample(jujur_lain, prof.jumlah_kontrol_sensor_min - 1)
        terpilih = {x.id for x in sensor}
        sisa = [x for x in self.rs if x.id not in terpilih]
        sensor += r.sample(sisa, max(0, prof.jumlah_rs_sensor - len(sensor)))
        for x in sensor:
            x.baris["punya_sensor"] = True

    def _buat_kapasitas(self, rs: _RS) -> None:
        r = self.rng
        kunci = "A_volume_tinggi" if rs.profil == "jujur_volume_tinggi" else rs.kelas
        rentang = UMUM.kapasitas_kelas[kunci]
        fisioterapis = r.randint(*rentang["fisioterapis"])
        mesin = r.randint(*rentang["mesin_hd"])
        shift = self.param.kapasitas.hemodialisa_shift_per_hari
        tujuh_hari = rs.profil != "jujur_sibuk" and r.random() < UMUM.peluang_hd_tujuh_hari
        hari_operasional = 7 if tujuh_hari else 6
        rs.kap = {
            "rs_id": rs.id,
            "dataset_id": self.dataset_id,
            "jumlah_fisioterapis": fisioterapis,
            "jumlah_mesin_hd": mesin,
            "shift_hd_per_hari": shift,
            "hari_operasional_hd": hari_operasional,
        }
        rs.kapasitas_fisio = fisioterapis * self.param.kapasitas.fisioterapi_sesi_per_terapis_per_hari
        rs.kapasitas_hd = mesin * shift
        rs.hari_hd = tuple(range(hari_operasional))

        if rs.profil == "jujur_sibuk":
            dasar = UMUM.utilisasi_sibuk
        elif rs.profil == "jujur_volume_tinggi":
            dasar = UMUM.utilisasi_volume_tinggi
        else:
            dasar = UMUM.utilisasi_normal
        rs.utilisasi = self._uniform(dasar)
        rs.utilisasi_hd = self._uniform(dasar)

    def _batas_harian(self, rs: _RS) -> tuple[float, float]:
        return UMUM.utilisasi_sibuk_harian if rs.profil == "jujur_sibuk" else UMUM.utilisasi_normal_harian

    # ----------------------------------------------------------- perilaku normal

    def _bangkitkan_fisioterapi(self, rs: _RS) -> None:
        r = self.rng
        kapasitas = rs.kapasitas_fisio
        rs.pasien_fisio = [self._pasien_baru(rs, "fisioterapi") for _ in range(max(10, kapasitas * 3))]
        lo, hi = self._batas_harian(rs)
        tarif = katalog.TARIF_FISIOTERAPI[rs.kelas]
        for tgl in self.hari_kerja:
            u = min(hi, max(lo, rs.utilisasi + r.gauss(0, UMUM.sebaran_harian)))
            faktor = UMUM.faktor_sabtu_fisioterapi if tgl.weekday() == SABTU else 1.0
            n = min(kapasitas, math.floor(kapasitas * u * faktor))
            for pid in r.sample(rs.pasien_fisio, n):
                self._sesi(rs, pid, tgl, "fisioterapi")
                self._tagihan(rs, pid, tgl, "fisioterapi", harga_satuan=tarif)

    def _bangkitkan_hemodialisa(self, rs: _RS) -> None:
        """Setiap pasien mendapat slot tetap (mesin, shift) pada hari polanya, seperti
        jadwal unit hemodialisa sungguhan. Satu slot satu pasien, jadi kapasitas
        mesin x shift tidak mungkin terlampaui oleh sesi nyata."""
        r = self.rng
        mesin, shift = rs.kap["jumlah_mesin_hd"], rs.kap["shift_hd_per_hari"]
        pola_dua = POLA_HD_DUA + (POLA_HD_MINGGU if len(rs.hari_hd) == 7 else [])
        slot = [(m, s) for m in range(mesin) for s in range(shift)]
        terisi: set[tuple[int, int, int]] = set()
        target = rs.utilisasi_hd * len(rs.hari_hd) * mesin * shift
        sibuk = rs.profil == "jujur_sibuk"
        # Rumah sakit normal paling banyak terisi 95% per hari; kontrol sibuk boleh penuh.
        batas_per_hari = rs.kapasitas_hd if sibuk else math.floor(
            UMUM.utilisasi_normal_harian[1] * rs.kapasitas_hd
        )
        per_hari: Counter[int] = Counter()

        while len(terisi) < target:
            dua_kali = r.random() < UMUM.porsi_hd_dua_kali
            utama = list(pola_dua if dua_kali else POLA_HD_TIGA)
            cadangan = list(POLA_HD_TIGA if dua_kali else pola_dua)
            r.shuffle(utama)
            r.shuffle(cadangan)
            urutan_slot = list(slot)
            r.shuffle(urutan_slot)
            tempat = next(
                (
                    (pola, m, s)
                    for pola in utama + cadangan
                    for m, s in urutan_slot
                    if all((hari, m, s) not in terisi and per_hari[hari] < batas_per_hari for hari in pola)
                ),
                None,
            )
            if tempat is None:
                break
            pola, m, s = tempat
            terisi.update((hari, m, s) for hari in pola)
            per_hari.update(pola)
            mulai, selesai = self.mulai, None
            if not sibuk and r.random() < UMUM.porsi_hd_mulai_tengah:
                mulai = self.mulai + timedelta(days=r.randrange(self.hari))
            if not sibuk and r.random() < UMUM.porsi_hd_berhenti_tengah:
                selesai = self.mulai + timedelta(days=r.randrange(1, self.hari))
            rs.pasien_hd.append(
                _PasienHD(self._pasien_baru(rs, "hemodialisa"), pola, m, s, mulai, selesai)
            )

        # Pasien terdaftar yang sedang tidak menjalani hemodialisa (rujuk balik, rawat inap).
        jumlah_tidak_aktif = max(
            round(UMUM.porsi_hd_tidak_aktif * len(rs.pasien_hd)),
            2 * rs.kapasitas_hd - len(rs.pasien_hd),
        )
        rs.pasien_hd_tidak_aktif = [self._pasien_baru(rs, "hemodialisa") for _ in range(jumlah_tidak_aktif)]
        rs.pasien_hd_semua = [p.id for p in rs.pasien_hd] + rs.pasien_hd_tidak_aktif

        absen = UMUM.absen_hd_sibuk if sibuk else UMUM.absen_hd
        tarif = katalog.TARIF_HEMODIALISA[rs.kelas]
        for tgl in self.daftar_tanggal:
            hari = tgl.weekday()
            if hari not in rs.hari_hd:
                continue
            for p in rs.pasien_hd:
                if hari in p.pola and p.aktif(tgl) and r.random() >= absen:
                    mesin_id = f"{rs.id}-HD{p.mesin + 1:02d}"
                    self._sesi(rs, p.id, tgl, "hemodialisa", mesin=mesin_id, shift=p.shift + 1)
                    self._tagihan(rs, p.id, tgl, "hemodialisa", harga_satuan=tarif)

    def _faktor_volume(self, rs: _RS) -> float:
        return UMUM.faktor_volume_tinggi if rs.profil == "jujur_volume_tinggi" else 1.0

    def _bangkitkan_obat(self, rs: _RS) -> None:
        r = self.rng
        jumlah_pasien = round(r.randint(*UMUM.pasien_obat_kelas[rs.kelas]) * self._faktor_volume(rs))
        for _ in range(jumlah_pasien):
            pid = self._pasien_baru(rs, "obat_kronis")
            regimen = r.sample(self.item_obat, r.randint(1, 3))
            jumlah = {
                kode: r.choice(katalog.JUMLAH_OBAT_KHUSUS.get(kode, katalog.JUMLAH_OBAT_PER_RESEP))
                for kode in regimen
            }
            interval = r.randint(28, 31)
            tgl = self.mulai + timedelta(days=r.randrange(30))
            while tgl < self.akhir:
                kunjungan = tgl + timedelta(days=1) if tgl.weekday() == MINGGU else tgl
                if kunjungan < self.akhir:
                    for kode in regimen:
                        self._tagihan(
                            rs, pid, kunjungan, "obat_kronis",
                            harga_satuan=self._harga_normal(kode), kode_item=kode, jumlah=jumlah[kode],
                        )
                tgl += timedelta(days=interval)

    def _bangkitkan_abd(self, rs: _RS) -> None:
        r = self.rng
        # Riwayat pemberian alat bantu dengar dalam 6 tahun sebelum periode.
        jumlah_riwayat = round(UMUM.riwayat_abd_kelas[rs.kelas] * self._faktor_volume(rs))
        rentang_hari = TAHUN_RIWAYAT_ABD * 365
        for _ in range(jumlah_riwayat):
            pid = self._pasien_baru(rs, "alat_bantu_dengar")
            u = r.random()
            sisi = ["kiri"] if u < 0.3 else ["kanan"] if u < 0.6 else list(SISI)
            dasar = self.mulai - timedelta(days=r.randint(1, rentang_hari))
            for sd in sisi:
                tgl = dasar if r.random() < 0.8 else self.mulai - timedelta(days=r.randint(1, rentang_hari))
                self._riwayat_baru(pid, sd, tgl)
            rs.pasien_abd.append(pid)

        # Pemberian normal selama periode: pasien baru, atau pasien lama yang sudah
        # melewati masa penggantian (termasuk telinga lain yang belum pernah diberi).
        jumlah = round(r.randint(*UMUM.abd_baru_kelas[rs.kelas]) * self._faktor_volume(rs))
        for _ in range(jumlah):
            tgl = r.choice(self.hari_kerja)
            sisi: list[str] = []
            pid = None
            if r.random() < 0.6:
                layak = []
                for kandidat in rs.pasien_abd:
                    boleh = [sd for sd in SISI if self._abd_boleh_normal(kandidat, sd, tgl)]
                    if boleh:
                        layak.append((kandidat, boleh))
                if layak:
                    pid, boleh = r.choice(layak)
                    sisi = [r.choice(boleh)] if (len(boleh) == 1 or r.random() < 0.5) else boleh
                    if not self.abd_per_telinga:
                        sisi = sisi[:1]
            if pid is None:
                pid = self._pasien_baru(rs, "alat_bantu_dengar")
                sisi = r.choice([["kiri"], ["kanan"], list(SISI)])
                if not self.abd_per_telinga:
                    sisi = sisi[:1]
            kode = r.choice(self.item_abd)
            for sd in sisi:
                self._tagihan(
                    rs, pid, tgl, "alat_bantu_dengar",
                    harga_satuan=self._harga_normal(kode), kode_item=kode, sisi=sd,
                )
                self._abd_ditagih.add(self._kunci_abd(pid, sd))

    # ------------------------------------------------------- skenario kecurangan

    def _sisipkan(
        self,
        rs: _RS,
        skenario: str,
        kelompok: str,
        kandidat: list[date],
        jumlah: int,
        fungsi: Callable[[_RS, date], tuple[list[dict], str] | None],
    ) -> None:
        """Pilih hari acak (bukan pola tetap) dan sisipkan kejadian sampai `jumlah`.
        Hari yang sudah dipakai skenario lain di kelompok layanan yang sama dilewati,
        agar setiap kejadian punya satu penyebab yang jelas."""
        terpakai = self._terpakai[(rs.id, kelompok)]
        hari = [t for t in kandidat if t not in terpakai]
        self.rng.shuffle(hari)
        berhasil = 0
        for tgl in hari:
            if berhasil >= jumlah:
                break
            hasil = fungsi(rs, tgl)
            if hasil is None:
                continue
            terpakai.add(tgl)
            self.kejadian.append((skenario, rs.id, tgl, hasil[0], hasil[1]))
            berhasil += 1

    def _besaran_kap(self, kapasitas: int) -> int:
        if self.rng.random() < self.profil.kap_porsi_halus:
            return self.rng.randint(1, 2)
        persen = self._uniform(self.profil.kap_lebih_persen) / 100
        return max(1, round(kapasitas * persen))

    def _calon_fiktif(self, kumpulan: list[str], sudah: list[dict], n: int) -> list[str]:
        ditagih = {t["pasien_id"] for t in sudah}
        calon = [p for p in kumpulan if p not in ditagih]
        return self.rng.sample(calon, min(n, len(calon)))

    def _kap_fisio(self, rs: _RS, tgl: date):
        kapasitas = rs.kapasitas_fisio
        ada = self._tagihan_hari(rs, "fisioterapi", tgl)
        lebih = self._besaran_kap(kapasitas)
        pasien = self._calon_fiktif(rs.pasien_fisio, ada, kapasitas - len(ada) + lebih)
        if len(ada) + len(pasien) <= kapasitas:
            return None
        nyata = len(ada)
        tarif = katalog.TARIF_FISIOTERAPI[rs.kelas]
        fiktif = [self._tagihan(rs, p, tgl, "fisioterapi", harga_satuan=tarif) for p in pasien]
        total = nyata + len(fiktif)
        return fiktif, (
            f"Fisioterapi: {nyata} sesi nyata + {len(fiktif)} tagihan fiktif = {total} tagihan; "
            f"kapasitas {kapasitas} sesi ({rs.kap['jumlah_fisioterapis']} terapis x "
            f"{self.param.kapasitas.fisioterapi_sesi_per_terapis_per_hari}). "
            f"Lebih {total - kapasitas} sesi ({(total - kapasitas) / kapasitas:.0%})."
        )

    def _kap_hd(self, rs: _RS, tgl: date):
        kapasitas = rs.kapasitas_hd
        ada = self._tagihan_hari(rs, "hemodialisa", tgl)
        lebih = self._besaran_kap(kapasitas)
        pasien = self._calon_fiktif(rs.pasien_hd_semua, ada, kapasitas - len(ada) + lebih)
        if len(ada) + len(pasien) <= kapasitas:
            return None
        nyata = len(ada)
        tarif = katalog.TARIF_HEMODIALISA[rs.kelas]
        fiktif = [self._tagihan(rs, p, tgl, "hemodialisa", harga_satuan=tarif) for p in pasien]
        total = nyata + len(fiktif)
        return fiktif, (
            f"Hemodialisa: {nyata} sesi nyata + {len(fiktif)} tagihan fiktif = {total} tagihan; "
            f"kapasitas {kapasitas} sesi ({rs.kap['jumlah_mesin_hd']} mesin x "
            f"{rs.kap['shift_hd_per_hari']} shift). "
            f"Lebih {total - kapasitas} sesi ({(total - kapasitas) / kapasitas:.0%})."
        )

    def _sensor_palsu(self, rs: _RS, tgl: date):
        kapasitas = rs.kapasitas_hd
        ada = self._tagihan_hari(rs, "hemodialisa", tgl)
        sisa = kapasitas - len(ada)
        if not ada or sisa < 1:
            return None
        n = min(sisa, max(1, round(len(ada) * self._uniform(self.profil.sensor_palsu_porsi))))
        pasien = self._calon_fiktif(rs.pasien_hd_semua, ada, n)
        if not pasien:
            return None
        nyata = len(ada)
        tarif = katalog.TARIF_HEMODIALISA[rs.kelas]
        fiktif = [self._tagihan(rs, p, tgl, "hemodialisa", harga_satuan=tarif) for p in pasien]
        return fiktif, (
            f"Hemodialisa: {nyata} sesi nyata + {len(fiktif)} tagihan tanpa sesi = "
            f"{nyata + len(fiktif)} tagihan; kapasitas {kapasitas} tidak terlampaui, "
            f"hanya terlihat dari jam-mesin sensor."
        )

    def _ulang_hari(self, rs: _RS, tgl: date):
        ada = self._tagihan_hari(rs, "hemodialisa", tgl)
        sisa = rs.kapasitas_hd - len(ada)
        if not ada or sisa < 1:
            return None
        asal = self.rng.sample(ada, min(sisa, self.rng.randint(1, 2), len(ada)))
        ganda = [self._tambah_tagihan(dict(t)) for t in asal]
        pasien = ", ".join(t["pasien_id"] for t in ganda)
        return ganda, f"{len(ganda)} pasien ditagih 2 sesi hemodialisa pada hari yang sama: {pasien}."

    def _ulang_identik(self, layanan: str):
        def fungsi(rs: _RS, tgl: date):
            ada = self._tagihan_hari(rs, layanan, tgl)
            n = self.rng.randint(1, 2)
            if layanan == "fisioterapi":
                n = min(n, rs.kapasitas_fisio - len(ada))
            if not ada or n < 1:
                return None
            asal = self.rng.sample(ada, min(n, len(ada)))
            ganda = [self._tambah_tagihan(dict(t)) for t in asal]
            return ganda, f"{len(ganda)} tagihan {layanan} diduplikasi persis (semua kolom sama kecuali ID)."

        return fungsi

    def _harga_lebih_fungsi(self, rs: _RS, tgl: date):
        kandidat = self._tagihan_hari(rs, "obat_kronis", tgl) + self._tagihan_hari(
            rs, "alat_bantu_dengar", tgl
        )
        if not kandidat:
            return None
        dipilih = self.rng.sample(kandidat, min(len(kandidat), self.rng.randint(1, 3)))
        rincian = []
        for t in dipilih:
            persen = self._uniform(self.harga_lebih) / 100
            acuan = self.harga[t["kode_item"]]
            t["harga_satuan"] = round(acuan * (1 + persen))
            t["total"] = t["jumlah"] * t["harga_satuan"]
            rincian.append(f"{t['kode_item']} {t['harga_satuan'] / acuan - 1:+.0%}")
        return dipilih, f"{len(dipilih)} tagihan di atas harga acuan: {', '.join(rincian)}."

    def _abd_dini(self, rs: _RS, tgl: date):
        r = self.rng
        batas_atas = self.masa_abd_hari - UMUM.margin_abd_hari
        if r.random() < self.profil.abd_dini_porsi_halus:
            jarak_min, jarak_maks = self.masa_abd_hari - 150, batas_atas
        else:
            lo, hi = self.profil.abd_dini_tahun
            jarak_min, jarak_maks = round(lo * 365.25), min(round(hi * 365.25), batas_atas)

        calon = []
        for pid in rs.pasien_abd:
            for sd in SISI:
                kunci = self._kunci_abd(pid, sd)
                terakhir = self._abd_terakhir.get(kunci)
                if terakhir is None or kunci in self._abd_ditagih:
                    continue
                if jarak_min <= (tgl - terakhir).days <= jarak_maks:
                    calon.append((pid, sd))
        if calon:
            pid, sd = r.choice(calon)
        else:
            pid, sd = self._pasien_baru(rs, "alat_bantu_dengar"), r.choice(SISI)
            rs.pasien_abd.append(pid)
            self._riwayat_baru(pid, sd, tgl - timedelta(days=r.randint(jarak_min, jarak_maks)))
        terakhir = self._abd_terakhir[self._kunci_abd(pid, sd)]
        kode = r.choice(self.item_abd)
        t = self._tagihan(
            rs, pid, tgl, "alat_bantu_dengar",
            harga_satuan=self._harga_normal(kode), kode_item=kode, sisi=sd,
        )
        self._abd_ditagih.add(self._kunci_abd(pid, sd))
        jarak = (tgl - terakhir).days / 365.25
        return [t], (
            f"Alat bantu dengar telinga {sd} untuk {pid}: pemberian terakhir {terakhir.isoformat()} "
            f"({jarak:.2f} tahun lalu), masa penggantian {self.masa_abd_tahun:g} tahun."
        )

    def _sisipkan_skenario(self, rs: _RS) -> None:
        r = self.rng
        n = {sk: r.randint(*self.profil.kejadian_per_rs[sk]) for sk in rs.skenario}
        hari_hd = [t for t in self.daftar_tanggal if t.weekday() in rs.hari_hd]
        if "KAP_FISIO" in n:
            self._sisipkan(rs, "KAP_FISIO", "fisioterapi", self.hari_kerja, n["KAP_FISIO"], self._kap_fisio)
        if "KAP_HD" in n:
            self._sisipkan(rs, "KAP_HD", "hemodialisa", hari_hd, n["KAP_HD"], self._kap_hd)
        if "SENSOR_PALSU" in n:
            self._sisipkan(rs, "SENSOR_PALSU", "hemodialisa", hari_hd, n["SENSOR_PALSU"], self._sensor_palsu)
        if "ULANG_HARI" in n:
            self._sisipkan(rs, "ULANG_HARI", "hemodialisa", hari_hd, n["ULANG_HARI"], self._ulang_hari)
        if "ULANG_IDENTIK" in n:
            n_fisio = sum(r.random() < 0.5 for _ in range(n["ULANG_IDENTIK"]))
            n_obat = n["ULANG_IDENTIK"] - n_fisio
            self._sisipkan(rs, "ULANG_IDENTIK", "fisioterapi", self.hari_kerja, n_fisio,
                           self._ulang_identik("fisioterapi"))
            self._sisipkan(rs, "ULANG_IDENTIK", "obat", self.hari_kerja, n_obat,
                           self._ulang_identik("obat_kronis"))
        if "HARGA_LEBIH" in n:
            self._sisipkan(rs, "HARGA_LEBIH", "obat", self.hari_kerja, n["HARGA_LEBIH"],
                           self._harga_lebih_fungsi)
        if "ABD_DINI" in n:
            self._sisipkan(rs, "ABD_DINI", "abd", self.hari_kerja, n["ABD_DINI"], self._abd_dini)

    # ------------------------------------------------- kasus sah di area batas

    def _hd_shift_tambahan(self, rs: _RS, tgl: date):
        """Shift darurat: sesi nyata (ada di sesi_aktual) melewati kapasitas 1-2 sesi.
        Satu shift darurat paling banyak satu sesi per mesin."""
        kapasitas = rs.kapasitas_hd
        ada = self._tagihan_hari(rs, "hemodialisa", tgl)
        lebih = self.rng.randint(*UMUM.kasus_hd_lebih_sesi)
        tambahan = kapasitas - len(ada) + lebih
        if tambahan > rs.kap["jumlah_mesin_hd"]:
            return None
        # Pasien terdaftar yang tidak terjadwal hari itu (rujukan darurat).
        pasien = self._calon_fiktif(rs.pasien_hd_tidak_aktif, ada, tambahan)
        if len(pasien) < tambahan:
            return None
        shift = rs.kap["shift_hd_per_hari"] + 1
        tarif = katalog.TARIF_HEMODIALISA[rs.kelas]
        tagihan = []
        for i, pid in enumerate(pasien):
            self._sesi(rs, pid, tgl, "hemodialisa", mesin=f"{rs.id}-HD{i + 1:02d}", shift=shift)
            tagihan.append(self._tagihan(rs, pid, tgl, "hemodialisa", harga_satuan=tarif))
        return tagihan, (
            f"Shift darurat ke-{shift}: {tambahan} sesi tambahan yang benar-benar terjadi; "
            f"total {len(ada) + tambahan} sesi, kapasitas {kapasitas} "
            f"({rs.kap['jumlah_mesin_hd']} mesin x {rs.kap['shift_hd_per_hari']} shift). Lebih {lebih} sesi."
        )

    def _fisio_lembur(self, rs: _RS, tgl: date):
        """Terapis lembur: sesi nyata melewati kapasitas 1-3 sesi."""
        kapasitas = rs.kapasitas_fisio
        ada = self._tagihan_hari(rs, "fisioterapi", tgl)
        lebih = self.rng.randint(*UMUM.kasus_fisio_lebih_sesi)
        tambahan = kapasitas - len(ada) + lebih
        if tambahan > UMUM.kasus_fisio_lembur_per_terapis * rs.kap["jumlah_fisioterapis"]:
            return None
        pasien = self._calon_fiktif(rs.pasien_fisio, ada, tambahan)
        if len(pasien) < tambahan:
            return None
        tarif = katalog.TARIF_FISIOTERAPI[rs.kelas]
        tagihan = []
        for pid in pasien:
            self._sesi(rs, pid, tgl, "fisioterapi")
            tagihan.append(self._tagihan(rs, pid, tgl, "fisioterapi", harga_satuan=tarif))
        return tagihan, (
            f"Terapis lembur: {tambahan} sesi tambahan yang benar-benar terjadi; "
            f"total {len(ada) + tambahan} sesi, kapasitas {kapasitas} "
            f"({rs.kap['jumlah_fisioterapis']} terapis x "
            f"{self.param.kapasitas.fisioterapi_sesi_per_terapis_per_hari}). Lebih {lebih} sesi."
        )

    def _kasus_kapasitas(self, jenis: str, rs_sah: list[_RS], jumlah: int, kelompok: str, fungsi) -> None:
        if kelompok == "fisioterapi":
            calon = [(rs, tgl) for rs in rs_sah for tgl in self.hari_kerja]
        else:
            calon = [(rs, tgl) for rs in rs_sah for tgl in self.daftar_tanggal if tgl.weekday() in rs.hari_hd]
        self.rng.shuffle(calon)
        berhasil = 0
        for rs, tgl in calon:
            if berhasil >= jumlah:
                break
            terpakai = self._terpakai[(rs.id, kelompok)]
            if tgl in terpakai:
                continue
            hasil = fungsi(rs, tgl)
            if hasil is None:
                continue
            terpakai.add(tgl)
            self.kasus_sah.append((jenis, rs.id, tgl, hasil[0], hasil[1]))
            berhasil += 1

    def _harga_acuan_lama(self, rs_sah: list[_RS], jumlah: int) -> None:
        """Harga sedikit di atas toleransi (maksimal toleransi + 5 poin persen) karena
        harga acuan di sistem belum diperbarui."""
        ids = {rs.id for rs in rs_sah}
        calon = [t for t in self.tagihan if t["kode_item"] and t["rs_id"] in ids]
        per_hari: dict[tuple[str, date], list[dict]] = {}
        for t in self.rng.sample(calon, min(jumlah, len(calon))):
            acuan = self.harga[t["kode_item"]]
            persen = self.toleransi + self._uniform(UMUM.harga_acuan_lama_di_atas_toleransi_pp) / 100
            t["harga_satuan"] = math.ceil(acuan * (1 + persen))
            t["total"] = t["jumlah"] * t["harga_satuan"]
            per_hari.setdefault((t["rs_id"], t["tanggal"]), []).append(t)
        for (rs_id, tgl), daftar in per_hari.items():
            rincian = ", ".join(
                f"{t['kode_item']} {t['harga_satuan'] / self.harga[t['kode_item']] - 1:+.1%}" for t in daftar
            )
            self.kasus_sah.append((
                "HARGA_ACUAN_LAMA", rs_id, tgl, daftar,
                f"Harga acuan belum diperbarui; {len(daftar)} tagihan sedikit di atas toleransi "
                f"{self.toleransi:.0%}: {rincian}.",
            ))

    def _sisipkan_kasus_sah(self) -> None:
        r = self.rng
        rs_sah = [x for x in self.rs if x.profil in ("jujur", "jujur_sibuk")]
        self._kasus_kapasitas(
            "HD_SHIFT_TAMBAHAN", rs_sah, r.randint(*UMUM.kasus_hd_shift_tambahan),
            "hemodialisa", self._hd_shift_tambahan,
        )
        self._kasus_kapasitas(
            "FISIO_LEMBUR", rs_sah, r.randint(*UMUM.kasus_fisio_lembur), "fisioterapi", self._fisio_lembur,
        )
        self._harga_acuan_lama(rs_sah, r.randint(*UMUM.kasus_harga_acuan_lama))

    # ------------------------------------------------------------------- rakit

    def _rakit(self) -> DataTiruan:
        r = self.rng
        dasar = self.profil.offset_baris

        tagihan = list(self.tagihan)
        r.shuffle(tagihan)
        tagihan.sort(key=lambda t: (t["tanggal"], t["rs_id"]))
        for i, t in enumerate(tagihan):
            t["id"] = dasar + i + 1

        sesi = sorted(
            self.sesi,
            key=lambda s: (s["tanggal"], s["rs_id"], s["layanan"], s["shift"] or 0, s["mesin_id"] or "", s["pasien_id"]),
        )
        for i, s in enumerate(sesi):
            s["id"] = dasar + i + 1

        riwayat = sorted(self.riwayat, key=lambda x: (x["pasien_id"], x["sisi_telinga"], x["tanggal_diberikan"]))
        for i, x in enumerate(riwayat):
            x["id"] = dasar + i + 1

        kejadian = sorted(self.kejadian, key=lambda k: (k[2], k[1], k[0]))
        ground_truth = [
            {
                "id": dasar + i + 1,
                "dataset_id": self.dataset_id,
                "skenario": skenario,
                "rs_id": rs_id,
                "tanggal": tgl,
                "tagihan_ids": sorted(t["id"] for t in daftar),
                "keterangan": keterangan,
            }
            for i, (skenario, rs_id, tgl, daftar, keterangan) in enumerate(kejadian)
        ]

        kasus = sorted(self.kasus_sah, key=lambda k: (k[2], k[1], JENIS_KASUS_SAH.index(k[0])))
        kasus_sah = [
            {
                "id": dasar + i + 1,
                "dataset_id": self.dataset_id,
                "jenis": jenis,
                "rs_id": rs_id,
                "tanggal": tgl,
                "tagihan_ids": sorted(t["id"] for t in daftar),
                "keterangan": keterangan,
            }
            for i, (jenis, rs_id, tgl, daftar, keterangan) in enumerate(kasus)
        ]

        harga_acuan = [
            {"dataset_id": self.dataset_id, "kode_item": kode, "nama_item": nama, "jenis": jenis, "harga": harga}
            for kode, nama, jenis, harga in katalog.HARGA_ACUAN
        ]
        profil_rs = [{"rs_id": x.id, "dataset_id": self.dataset_id, "profil": x.profil} for x in self.rs]

        tabel = {
            "rumah_sakit": [x.baris for x in self.rs],
            "kapasitas": [x.kap for x in self.rs],
            "pasien": self.pasien,
            "harga_acuan": harga_acuan,
            "riwayat_alat_bantu_dengar": riwayat,
            "tagihan": tagihan,
            "sesi_aktual": sesi,
            "ground_truth": ground_truth,
            "kasus_sah": kasus_sah,
            "profil_rs": profil_rs,
        }
        return DataTiruan(self.dataset_id, self.seed, self.mulai, self.hari, {k: tabel[k] for k in URUTAN_TABEL})

    def jalankan(self) -> DataTiruan:
        self._buat_rumah_sakit()
        self._tetapkan_peran()
        for rs in self.rs:
            self._buat_kapasitas(rs)
        for rs in self.rs:
            self._bangkitkan_fisioterapi(rs)
            self._bangkitkan_hemodialisa(rs)
            self._bangkitkan_obat(rs)
            self._bangkitkan_abd(rs)
        for rs in self.rs:
            self._sisipkan_skenario(rs)
        self._sisipkan_kasus_sah()
        return self._rakit()


def bangkitkan(
    dataset_id: str = "utama",
    seed: int | None = None,
    hari: int = HARI_DEFAULT,
    jumlah_rs: int = RS_DEFAULT,
    mulai: date = MULAI_DEFAULT,
    parameter: Parameter | None = None,
) -> DataTiruan:
    """Bangkitkan satu dataset tiruan di memori (belum disimpan ke database)."""
    if dataset_id not in PROFIL:
        raise ValueError(f"dataset tidak dikenal: {dataset_id!r} (pilihan: {', '.join(PROFIL)})")
    profil = PROFIL[dataset_id]
    seed = profil.seed_default if seed is None else seed
    parameter = parameter or muat_parameter()
    return _Pembangkit(parameter, profil, seed, mulai, hari, jumlah_rs).jalankan()
