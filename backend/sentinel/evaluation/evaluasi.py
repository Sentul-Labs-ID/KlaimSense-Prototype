"""Menyusun seluruh metrik evaluasi untuk satu dataset."""

import json
from collections import Counter

from sentinel.evaluation import metrik as m
from sentinel.evaluation.data import DataEvaluasi
from sentinel.sensor import konfigurasi as konfigurasi_sensor


def evaluasi(d: DataEvaluasi) -> dict:
    kondisi = m.kondisi_rs_periode(d.skor, d.ground_truth, d.kasus_sah)
    kondisi_harfiah = m.kondisi_rs_periode(d.skor, d.ground_truth, d.kasus_sah, pisahkan_tamper=False)
    prioritas = m.metrik_prioritas(d.skor, kondisi, d.profil)
    harfiah = m.metrik_prioritas(d.skor, kondisi_harfiah, d.profil)
    indeks = m.Indeks(d.temuan)
    kecurangan = [g for g in d.ground_truth if g["skenario"] in m.SKENARIO_KECURANGAN]
    return {
        "dataset_id": d.dataset_id,
        "hash_parameter": sorted({s["hash_parameter"] for s in d.skor}),
        "versi_aturan": sorted({s["versi_aturan"] for s in d.skor}),
        "jumlah_kejadian": {s: sum(g["skenario"] == s for g in d.ground_truth) for s in m.PEMETAAN},
        "skenario_tanpa_pemetaan": sorted({g["skenario"] for g in d.ground_truth} - set(m.PEMETAAN)),
        "jumlah_kasus_sah": dict(Counter(k["jenis"] for k in d.kasus_sah)),
        "jumlah_temuan": dict(sorted(Counter(t["aturan_id"] for t in d.temuan).items())),
        "recall_per_skenario": m.recall_per_skenario(d.ground_truth, d.temuan),
        "recall_gabungan_kecurangan": m.recall_gabungan(d.ground_truth, d.temuan, m.SKENARIO_KECURANGAN),
        "recall_gabungan_kecurangan_aturan_apa_pun": m.proporsi(
            sum(m.tertangkap_apa_pun(g, indeks) for g in kecurangan), len(kecurangan)
        ),
        "presisi_per_aturan": m.presisi_per_aturan(d.temuan, d.ground_truth, d.kasus_sah),
        "prioritas": prioritas,
        "prioritas_definisi_harfiah": {
            "catatan": "RS-periode yang hanya berisi gangguan sensor (TAMPER) dihitung 'bersih'.",
            "ditandai": harfiah["ditandai"],
            "matriks_prioritas_kondisi": harfiah["matriks_prioritas_kondisi"],
        },
        "integritas_sensor": m.integritas_sensor(d.ground_truth, d.temuan, d.anomali, d.rs_perangkat),
        "band_01": m.ringkasan_band(d.temuan, kondisi, d.profil),
    }


def edge_ai() -> dict:
    """Akurasi edge AI DIKUTIP dari metadata model fase 3 (tidak dihitung ulang)."""
    meta = json.loads(
        (konfigurasi_sensor.DIREKTORI_MODEL / konfigurasi_sensor.NAMA_MODEL).with_suffix(".json").read_text(encoding="utf-8")
    )
    cm = meta["confusion_matrix_uji"]
    benar = sum(cm[i][i] for i in range(len(cm)))
    total = sum(sum(baris) for baris in cm)
    return {
        "sumber": "backend/sentinel/sensor/model/edge_pohon_keputusan.json (fase 3)",
        "akurasi_uji": m.proporsi(benar, total),
        "akurasi_tercatat": meta["akurasi_uji"],
        "confusion_matrix_uji": cm,
        "label": meta["label"],
        "seed_latih": meta["seed_latih"],
        "jumlah_mesin_hari": meta["jumlah_mesin_hari"],
        "sha256_model": meta["sha256"],
    }


def angka_proposal(hidden: dict, edge: dict) -> dict:
    p = hidden["prioritas"]
    return {
        "kecurangan_tertangkap": hidden["recall_gabungan_kecurangan"],
        "tuduhan_keliru": p["ditandai"]["tuduhan_keliru"],
        "kasus_sah_perlu_klarifikasi": p["ditandai"]["kasus_sah_perlu_klarifikasi"],
        "gangguan_sensor_ditandai": p["ditandai"]["gangguan_sensor"],
        "rs_jujur_ikut_ditandai": p["rs_jujur_ikut_ditandai"],
        "akurasi_edge_ai": edge["akurasi_uji"],
    }
