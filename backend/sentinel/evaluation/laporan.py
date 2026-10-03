"""Menulis reports/evaluasi.md dari hasil evaluasi (tanpa menghitung ulang apa pun)."""

from sentinel.evaluation import metrik as m

LABEL_SKENARIO = {
    "KAP_FISIO": "Fisioterapi melebihi kapasitas terapis",
    "KAP_HD": "Hemodialisa melebihi kapasitas mesin",
    "ULANG_IDENTIK": "Tagihan duplikat persis",
    "ULANG_HARI": "Dua sesi HD sehari, pasien sama",
    "HARGA_LEBIH": "Harga di atas harga acuan",
    "ABD_DINI": "Alat bantu dengar sebelum masa ganti",
    "SENSOR_PALSU": "HD ditagih tanpa kerja mesin",
    "TAMPER_SIG": "Pesan sensor palsu",
    "TAMPER_GAP": "Sensor dicabut",
}
LABEL_KONDISI = {
    "bermasalah": "bermasalah (ada kecurangan)",
    "gangguan_sensor": "hanya gangguan sensor",
    "hanya_kasus_sah": "hanya kasus sah",
    "bersih": "bersih",
}
LABEL_PROFIL = {
    "jujur": "jujur",
    "jujur_sibuk": "jujur tapi sibuk",
    "jujur_volume_tinggi": "kelas A volume tinggi (sah)",
    "disisipi": "disisipi kecurangan",
}


def persen(x: float | None, desimal: int = 1) -> str:
    return "–" if x is None else f"{x * 100:.{desimal}f}".replace(".", ",") + "%"


def p(x: dict | None) -> str:
    """'13/14 (92,9%; IK95% 68,5–98,7%)'. Tidak pernah persentase tanpa jumlahnya."""
    if not x:
        return "–"
    if x["penyebut"] == 0:
        return "0/0 (tidak ada)"
    lo, hi = x["ci95"]
    return f"{x['pembilang']}/{x['penyebut']} ({persen(x['nilai'])}; IK95% {persen(lo)}–{persen(hi)})"


def p_singkat(x: dict | None) -> str:
    if not x or x["penyebut"] == 0:
        return "0/0"
    return f"{x['pembilang']}/{x['penyebut']} ({persen(x['nilai'], 0)})"


def _kolom(hasil: dict, kunci) -> tuple[str, str]:
    u = kunci(hasil["utama"]) if hasil.get("utama") else None
    h = kunci(hasil["hidden"]) if hasil.get("hidden") else None
    return p(u), (p(h) if hasil.get("hidden") else "belum dijalankan")


def kalimat_slide(hidden: dict, proposal: dict) -> str:
    """Kalimat siap tempel untuk slide, disusun dari angka hidden (tidak melebih-lebihkan)."""
    k = proposal["kecurangan_tertangkap"]
    periksa = hidden["prioritas"]["tinggi_sedang"]["recall"]
    ditandai = proposal["tuduhan_keliru"]
    keliru = ditandai["pembilang"]
    tuduhan = "tidak ada tuduhan keliru" if keliru == 0 else f"{keliru} merupakan tuduhan keliru"
    return (
        f"Pada data uji tersembunyi (data tiruan), JKN-Sentinel mendeteksi {k['pembilang']} dari {k['penyebut']} "
        f"kejadian kecurangan ({persen(k['nilai'])}) dan memasukkan {periksa['pembilang']} dari {periksa['penyebut']} "
        f"periode rumah sakit bermasalah ke daftar periksa petugas ({persen(periksa['nilai'], 0)}). "
        f"Dari {ditandai['penyebut']} periode yang diprioritaskan, {tuduhan}; "
        f"{proposal['kasus_sah_perlu_klarifikasi']['pembilang']} merupakan kasus sah yang perlu klarifikasi dan "
        f"{proposal['gangguan_sensor_ditandai']['pembilang']} merupakan gangguan sensor. "
        f"Klasifikasi Edge AI pada sensor akurat {persen(proposal['akurasi_edge_ai']['nilai'])}."
    )


def _bagian_proposal(hasil: dict) -> list[str]:
    a = hasil.get("proposal")
    if not a:
        return ["_Dataset hidden belum dijalankan; angka proposal belum tersedia._", ""]
    pr = hasil["hidden"]["prioritas"]
    kalimat = kalimat_slide(hasil["hidden"], a)
    bermasalah = pr["jumlah_per_kondisi"]["bermasalah"]
    masuk_daftar = pr["tinggi_sedang"]["recall"]
    rendah = m.proporsi(pr["matriks_prioritas_kondisi"]["rendah"]["bermasalah"], bermasalah)
    return [
        "**Kecurangan yang tertangkap**: " + p(a["kecurangan_tertangkap"]),
        "",
        "> Dari semua kejadian kecurangan yang disisipkan di data uji tersembunyi (tidak termasuk gangguan sensor), "
        "berapa yang ditandai oleh aturan yang memang dirancang untuk jenis kecurangan itu, pada rumah sakit dan "
        "tanggal (atau tagihan) yang sama.",
        "",
        "**Periode bermasalah yang masuk daftar periksa petugas (prioritas tinggi atau sedang)**: " + p(masuk_daftar),
        "",
        "> Dari semua periode rumah sakit (rumah sakit × bulan) yang memuat kecurangan, berapa yang diberi prioritas "
        "tinggi atau sedang sehingga masuk daftar yang diperiksa petugas.",
        "",
        "**Periode bermasalah yang terdeteksi tetapi berprioritas rendah**: " + p(rendah),
        "",
        "> Dari semua periode rumah sakit yang memuat kecurangan, berapa yang punya temuan tetapi skornya terlalu "
        "rendah untuk masuk daftar periksa.",
        "",
        "Perbedaannya: sebuah kejadian **terdeteksi** bila ada temuan aturan yang menandainya, sedangkan sebuah periode "
        "**masuk daftar periksa** hanya bila temuan-temuannya cukup untuk membuat prioritasnya tinggi atau sedang.",
        "",
        "**Tuduhan yang keliru**[^harfiah]: " + p(a["tuduhan_keliru"]),
        "",
        "> Dari semua periode rumah sakit (rumah sakit × bulan) yang diberi prioritas tinggi atau sedang, berapa yang "
        "sebenarnya tidak berisi kecurangan, bukan kasus sah, dan bukan gangguan sensor.",
        "",
        "**Kasus sah yang perlu klarifikasi**: " + p(a["kasus_sah_perlu_klarifikasi"]),
        "",
        "> Dari periode rumah sakit berprioritas tinggi atau sedang, berapa yang hanya berisi kejadian sah di dekat "
        "batas aturan (shift darurat, lembur, harga acuan lama). Ini bukan kecurangan; petugas cukup meminta klarifikasi.",
        "",
        "**Rumah sakit jujur yang ikut ditandai**: " + p(a["rs_jujur_ikut_ditandai"]),
        "",
        "> Dari semua periode rumah sakit jujur (termasuk yang sangat sibuk dan kelas A bervolume tinggi), berapa yang "
        "mendapat prioritas tinggi atau sedang. Sebagian berasal dari kasus sah atau gangguan sensor yang memang perlu dicek.",
        "",
        "**Akurasi Edge AI**: " + p(a["akurasi_edge_ai"]),
        "",
        "> Dari jendela 10 menit data uji simulasi yang tidak dipakai melatih, berapa yang status mesinnya "
        "(mati/standby/terapi) diklasifikasikan benar oleh perangkat (dikutip dari fase 3).",
        "",
        "Catatan: periode rumah sakit berprioritas yang hanya berisi gangguan sensor: " + p(a["gangguan_sensor_ditandai"])
        + " (dilaporkan terpisah, tidak dihitung sebagai tuduhan keliru).",
        "",
        "[^harfiah]: Definisi harfiah (periode yang hanya berisi gangguan sensor dihitung sebagai 'bersih', sehingga "
        "masuk tuduhan keliru): " + p(hasil["hidden"]["prioritas_definisi_harfiah"]["ditandai"]["tuduhan_keliru"]) + ".",
        "",
        "**Kalimat siap tempel untuk slide:**",
        "",
        f"> {kalimat}",
        "",
    ]


def render(hasil: dict, catatan_pasca_hidden: str | None = None) -> str:
    u, h = hasil.get("utama"), hasil.get("hidden")
    log = hasil.get("log_hidden") or {}
    baris = [
        "# Laporan evaluasi akurasi JKN-Sentinel",
        "",
        "> **Seluruh data adalah data tiruan.** Angka di laporan ini mengukur prototipe pada data simulasi, "
        "bukan kinerja pada klaim JKN asli.",
        "",
        f"Dibuat: {hasil['dibuat_pada']} · versi aturan {', '.join(u['versi_aturan']) if u else '–'} · "
        f"hash parameter `{(u['hash_parameter'] or ['–'])[0][:12] if u else '–'}`",
        "",
        "## Ringkasan",
        "",
        "- **Dataset utama** dipakai untuk mengembangkan dan memeriksa kode evaluasi.",
        "- **Dataset hidden** (seed dan distribusi penyisipan berbeda) dievaluasi setelah kode selesai; "
        "angka untuk proposal diambil dari hidden.",
        f"- **Perbandingan pertama keluaran hidden terhadap label**: {log.get('pertama', 'belum dijalankan')} "
        f"(jumlah jalan evaluasi hidden: {len(log.get('jalan', []))}). Tidak ada parameter, bobot, ambang, atau aturan "
        "yang diubah berdasarkan hasil hidden.",
        "",
        "## Angka untuk proposal (dataset hidden)",
        "",
        *_bagian_proposal(hasil),
        "## Deteksi per skenario (recall)",
        "",
        "Kejadian tertangkap bila aturan pasangannya menandai rumah sakit dan tanggal yang sama "
        "(untuk aturan per tagihan: temuan memuat tagihan kejadian itu).",
        "",
        "| Skenario | Aturan | Utama | Hidden | Hidden, aturan apa pun |",
        "|---|---|---|---|---|",
    ]
    for s in m.PEMETAAN:
        ru = u["recall_per_skenario"][s] if u else None
        rh = h["recall_per_skenario"][s] if h else None
        baris.append(
            f"| {LABEL_SKENARIO[s]} (`{s}`) | {(ru or rh)['aturan']} | {p(ru and ru['recall'])} | "
            f"{p(rh['recall']) if rh else 'belum dijalankan'} | {p_singkat(rh['tertangkap_aturan_apa_pun']) if rh else '–'} |"
        )
    gu, gh = _kolom(hasil, lambda x: x["recall_gabungan_kecurangan"])
    baris += [
        f"| **Gabungan kecurangan (tanpa gangguan sensor)** | | **{gu}** | **{gh}** | "
        f"{p_singkat(h['recall_gabungan_kecurangan_aturan_apa_pun']) if h else '–'} |",
        "",
        "![Recall per skenario](recall_per_skenario.png)",
        "",
        "## Presisi per aturan",
        "",
        "Setiap temuan diklasifikasikan: **benar** (memuat tagihan kecurangan, atau temuan integritas pada hari "
        "gangguan sensor), **kasus sah** (memuat tagihan kasus sah: perlu klarifikasi, bukan kecurangan), "
        "atau **keliru**.",
        "",
        "| Aturan | Utama: benar / kasus sah / keliru | Hidden: benar / kasus sah / keliru |",
        "|---|---|---|",
    ]
    for aturan in (u or h)["presisi_per_aturan"]:
        def sel(x):
            if not x:
                return "belum dijalankan"
            r = x["presisi_per_aturan"][aturan]
            if r["jumlah_temuan"] == 0:
                return "tidak ada temuan"
            return f"{p_singkat(r['benar'])} / {p_singkat(r['kasus_sah'])} / {p_singkat(r['keliru'])}"
        baris.append(f"| {aturan} | {sel(u)} | {sel(h)} |")

    baris += ["", "## Prioritas (level rumah sakit × bulan)", "",
              "Kondisi RS-periode: **bermasalah** (memuat kecurangan), **hanya gangguan sensor** (TAMPER, dilaporkan "
              "terpisah), **hanya kasus sah**, atau **bersih**. Urutan petugas: prioritas, lalu skor.", "",
              "| Metrik | Utama | Hidden |", "|---|---|---|"]
    for label, f in [
        ("Presisi prioritas tinggi", lambda x: x["prioritas"]["tinggi"]["presisi"]),
        ("Recall prioritas tinggi", lambda x: x["prioritas"]["tinggi"]["recall"]),
        ("Presisi tinggi + sedang", lambda x: x["prioritas"]["tinggi_sedang"]["presisi"]),
        ("Recall tinggi + sedang", lambda x: x["prioritas"]["tinggi_sedang"]["recall"]),
        ("Presisi top-5", lambda x: x["prioritas"]["top_5"]),
        ("Presisi top-10", lambda x: x["prioritas"]["top_10"]),
        ("Ditandai (tinggi+sedang) tetapi bersih: tuduhan keliru", lambda x: x["prioritas"]["ditandai"]["tuduhan_keliru"]),
        ("Ditandai, hanya kasus sah", lambda x: x["prioritas"]["ditandai"]["kasus_sah_perlu_klarifikasi"]),
        ("Ditandai, hanya gangguan sensor", lambda x: x["prioritas"]["ditandai"]["gangguan_sensor"]),
        ("RS jujur (termasuk sibuk dan volume tinggi) ikut ditandai", lambda x: x["prioritas"]["rs_jujur_ikut_ditandai"]),
    ]:
        a, b = _kolom(hasil, f)
        baris.append(f"| {label} | {a} | {b} |")
    ha, hb = _kolom(hasil, lambda x: x["prioritas_definisi_harfiah"]["ditandai"]["tuduhan_keliru"])
    baris += ["", f"Definisi harfiah (gangguan sensor dihitung 'bersih'): tuduhan keliru utama {ha}, hidden {hb}.", ""]

    for nama, data in (("Hidden", h), ("Utama", u)):
        if not data:
            continue
        pr = data["prioritas"]
        baris += [f"### Matriks prioritas × kondisi ({nama})", "",
                  "| Prioritas | " + " | ".join(LABEL_KONDISI[c] for c in m.KONDISI) + " |",
                  "|---|" + "---|" * len(m.KONDISI)]
        for pri in m.PRIORITAS:
            baris.append(f"| {pri} | " + " | ".join(str(pr["matriks_prioritas_kondisi"][pri][c]) for c in m.KONDISI) + " |")
        baris += ["", f"Sebaran prioritas per profil rumah sakit ({nama}, jumlah RS-periode tinggi / sedang / rendah):", "",
                  "| Profil | Tinggi | Sedang | Rendah |", "|---|---|---|---|"]
        for prof, c in sorted(pr["sebaran_per_profil"].items()):
            baris.append(f"| {LABEL_PROFIL.get(prof, prof)} | {c['tinggi']} | {c['sedang']} | {c['rendah']} |")
        baris += ["", f"RS-periode prioritas tinggi beserta alasannya ({nama}):", "",
                  "| RS | Periode | Skor | Alasan prioritas | Kondisi |", "|---|---|---|---|---|"]
        for x in pr["daftar_tinggi"]:
            skor = f"{x['skor']:.2f}".replace(".", ",")
            baris.append(f"| {x['rs_id']} | {x['periode']} | {skor} | {x['alasan_prioritas']} | {LABEL_KONDISI[x['kondisi']]} |")
        baris.append("")
        if nama == "Hidden":
            baris += ["![Matriks prioritas hidden](prioritas_hidden.png)", ""]

    baris += ["## Integritas sensor", "", "| Metrik | Utama | Hidden |", "|---|---|---|"]
    for label, f in [
        ("Pesan sensor palsu (TAMPER_SIG) terdeteksi", lambda x: x["integritas_sensor"]["TAMPER_SIG"]),
        ("Sensor dicabut (TAMPER_GAP) terdeteksi", lambda x: x["integritas_sensor"]["TAMPER_GAP"]),
    ]:
        a, b = _kolom(hasil, f)
        baris.append(f"| {label} | {a} | {b} |")
    for label, kunci in (("Jumlah anomali tercatat", "jumlah_anomali"), ("Anomali tanpa kejadian", "anomali_tanpa_kejadian")):
        baris.append(f"| {label} | {u['integritas_sensor'][kunci] if u else '–'} | "
                     f"{h['integritas_sensor'][kunci] if h else 'belum dijalankan'} |")

    e = hasil["edge_ai"]
    baris += ["", "## Edge AI (dikutip dari fase 3, tidak dihitung ulang)", "",
              f"Akurasi uji: {p(e['akurasi_uji'])}; {e['jumlah_mesin_hari']['uji']} mesin-hari uji yang tidak dipakai "
              f"melatih; seed latih {e['seed_latih']}; model `{e['sha256_model'][:12]}`.", "",
              "| Asli \\ Prediksi | " + " | ".join(e["label"]) + " |", "|---|" + "---|" * len(e["label"])]
    for lbl, row in zip(e["label"], e["confusion_matrix_uji"]):
        baris.append(f"| {lbl} | " + " | ".join(f"{v:,}".replace(",", ".") for v in row) + " |")

    baris += ["", "## BAND-01 (sinyal pendukung, tidak dipetakan ke skenario)", "",
              "| | Utama | Hidden |", "|---|---|---|"]
    a, b = _kolom(hasil, lambda x: x["band_01"]["pada_rs_periode_bermasalah"])
    baris.append(f"| Temuan BAND-01 pada RS-periode bermasalah | {a} | {b} |")
    for label, kunci in (("per kondisi RS-periode", "per_kondisi_rs_periode"), ("per profil RS", "per_profil_rs")):
        def fmt(x):
            return ", ".join(f"{k} {v}" for k, v in sorted(x["band_01"][kunci].items())) or "–"
        baris.append(f"| Sebaran {label} | {fmt(u) if u else '–'} | {fmt(h) if h else 'belum dijalankan'} |")

    baris += ["", "## Data yang dievaluasi", "", "| | Utama | Hidden |", "|---|---|---|"]
    for s in m.PEMETAAN:
        baris.append(f"| Kejadian `{s}` | {u['jumlah_kejadian'][s] if u else '–'} | {h['jumlah_kejadian'][s] if h else '–'} |")
    for label, f in (("Kasus sah", lambda x: sum(x["jumlah_kasus_sah"].values())),
                     ("Temuan", lambda x: sum(x["jumlah_temuan"].values())),
                     ("RS-periode", lambda x: x["prioritas"]["jumlah_rs_periode"])):
        baris.append(f"| {label} | {f(u) if u else '–'} | {f(h) if h else '–'} |")

    if catatan_pasca_hidden and h:
        baris += ["", "## Analisis pasca-jalan hidden", "", catatan_pasca_hidden.strip()]

    rt = h["prioritas"]["tinggi"]["recall"] if h else None
    baris += ["", "## Keterbatasan", "",
              "1. **Data tiruan.** Seluruh rumah sakit, pasien, tagihan, sinyal sensor, dan kecurangan adalah simulasi. "
              "Parameter aturan, bobot, ambang, dan nilai ampere sensor bersifat ilustratif dan belum divalidasi bersama "
              "BPJS maupun organisasi profesi. Sistem belum diuji pada data asli.",
              "2. **Margin aman pada data non-sah.** Generator (fase 1) memberi jarak aman dari batas aturan pada data "
              "normal maupun kecurangan (harga normal ≤60% toleransi; alat bantu dengar normal ≥ masa penggantian + 60 hari; "
              "ABD_DINI ≤ masa − 60 hari). Ketepatan aturan tepat di titik batas tidak teruji, kecuali lewat kasus sah.",
              "3. **Jumlah kejadian kecil.** Tiap skenario hanya punya belasan kejadian, sehingga interval kepercayaan 95% "
              "lebar. Selisih beberapa kejadian bisa mengubah persentase secara mencolok.",
              "4. **Pembanding BAND-01 terbatas.** Dengan 3 RS per kombinasi kelas-provinsi, leave-one-out hanya menyisakan "
              "2 pembanding, sehingga sebagian besar penilaian turun ke pembanding kelas; di hidden, kelas A hanya 3 RS "
              "sehingga sebagian penilaian dilewati (catatan fase 2).",
              "5. **Paparan label hidden di fase 1.** Saat memvalidasi generator (sebelum mesin aturan ada), profil per RS, "
              "daftar skenario per RS, dan besaran kejadian KAP dataset hidden pernah dicetak sekali; ringkasan jumlah "
              "kejadian hidden juga dilaporkan di fase 1. Tidak ada parameter yang berasal dari label hidden.",
              "6. **Kalibrasi sensor memakai label utama.** Pemeriksaan kewarasan kalibrasi sensor di fase 3 membuka "
              "`sesi_aktual` dan `ground_truth` dataset utama; tidak ada parameter yang diubah karenanya.",
              "7. **Aturan deterministik.** Aturan dengan ambang tegas diharapkan menangkap kasus yang jelas melewati "
              "batas. Angka tinggi pada aturan seperti WJR-01 atau WJR-02 mencerminkan desain aturan dan generator, "
              "bukan kecerdasan model. Kecurangan yang halus (misalnya SENSOR_PALSU di bawah toleransi sensor) memang "
              "bisa lolos.",
              f"8. **Recall prioritas tinggi rendah.** Hanya {p_singkat(rt) if rt else '–'} periode bermasalah di "
              "hidden yang mendapat prioritas tinggi, karena ambang prioritas dan lantai bukti fisik ditetapkan tanpa "
              "kalibrasi terhadap label. Kalibrasi ambang bersama BPJS adalah rencana tahap hackathon, dan hasilnya harus "
              "diuji dengan dataset hidden **baru** (seed baru), bukan dataset hidden ini yang labelnya sudah dibandingkan.",
              "9. **Pemalsuan sensor di bawah toleransi sengaja tidak ditandai.** SEN-01 tidak menandai kekurangan "
              "jam-mesin di bawah toleransi 10%, agar derau sensor tidak berubah menjadi tuduhan. Akibatnya pemalsuan "
              "kecil (beberapa sesi dari puluhan) bisa lolos. Ini pertukaran yang disadari.",
              ""]
    return "\n".join(baris)
