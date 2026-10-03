# Arsitektur JKN-Sentinel

> Seluruh data adalah data tiruan. Sistem memberi prioritas pemeriksaan, bukan vonis.

## Alur empat langkah

| Langkah | Nama | Pertanyaan | Siapa yang mengerjakan |
|---|---|---|---|
| 1 | **Hitung** | Apakah tagihan mungkin terjadi dan wajar menurut kapasitas dan aturan? | Mesin aturan deterministik (`sentinel/rules/`) |
| 2 | **Cek sensor** | Apakah mesin benar-benar dipakai sebanyak sesi yang ditagih? | Sensor IoT + Edge AI simulasi (`sentinel/sensor/`) |
| 3 | **Rangkum** | Apa temuannya dan apa dasar aturannya, dalam bahasa sederhana? | Agen perangkum + RAG korpus lokal (`sentinel/agents/`) |
| 4 | **Putuskan** | Perlu diperiksa lebih lanjut atau tidak? | Petugas BPJS di dashboard (`frontend/`) |

Skor hanya dihasilkan langkah 1 dan 2. Langkah 3 (AI) hanya merangkum dan mengutip, tidak mengubah skor. Langkah 4 selalu manusia.

## Diagram

```
                    config/parameter.yaml (batas & bobot, ilustratif)
                                   │
                                   ▼
 ┌──────────────┐   tagihan   ┌──────────────┐  temuan +  ┌──────────────┐
 │  Generator   │────────────▶│ 1. HITUNG    │──skor─────▶│              │
 │  data tiruan │  kapasitas  │ mesin aturan │            │              │
 │  (berseed)   │             └──────────────┘            │  PostgreSQL  │
 │              │   sinyal    ┌──────────────┐  SEN-01 +  │  (temuan,    │
 │              │────────────▶│ 2. CEK SENSOR│──tamper───▶│   skor,      │
 └──────┬───────┘   sensor    │ Ed25519+hash │            │   audit)     │
        │                     └──────────────┘            │              │
        │ ground_truth                                    └──────┬───────┘
        │ (hanya untuk evaluasi)                                 │
        ▼                                                        ▼
 ┌──────────────┐                                  ┌──────────────────────┐
 │  Evaluasi    │                                  │ 3. RANGKUM           │
 │  recall,     │                                  │ agen + RAG           │
 │  presisi,FPR │                                  │ data/regulasi/       │
 └──────────────┘                                  └──────────┬───────────┘
                                                              ▼
                                                 ┌──────────────────────┐
                                                 │ 4. PUTUSKAN          │
                                                 │ dashboard petugas    │
                                                 │ (FastAPI ⇄ Next.js)  │
                                                 └──────────────────────┘
```

## Layanan

| Layanan | Teknologi | Port |
|---|---|---|
| `db` | PostgreSQL 16 | 5432 |
| `backend` | Python 3.11+, FastAPI, SQLAlchemy 2.x, psycopg | 8000 |
| `frontend` | Next.js (App Router, TypeScript, Tailwind) | 3000 |

Konfigurasi rahasia dan koneksi dibaca dari environment (`sentinel/config.py`, lihat `.env.example`). Parameter aturan dibaca dari `config/parameter.yaml` dan divalidasi oleh `sentinel/parameter.py`.

## Tabel dan batas akses

| Kelompok | Tabel | Boleh dibaca |
|---|---|---|
| Master (`models/master.py`) | `rumah_sakit`, `kapasitas`, `pasien`, `harga_acuan` | Semua modul |
| Transaksi (`models/transaksi.py`) | `tagihan`, `riwayat_alat_bantu_dengar` | Semua modul |
| Kenyataan (`models/kenyataan.py`) | `sesi_aktual` (sesi yang benar-benar terjadi) | Hanya sensor (fase 3) dan evaluasi (fase 4) |
| Evaluasi (`models/evaluasi.py`) | `ground_truth`, `profil_rs`, `kasus_sah` | Hanya evaluasi (fase 4); tidak boleh diekspos API dashboard |

Semua tabel punya `dataset_id` (`utama` atau `hidden`). Mesin aturan hanya melihat apa yang dilihat BPJS di dunia nyata: tagihan dan data master. Batas ini dijaga oleh `tests/test_batas_akses.py`.

`kasus_sah` berisi kejadian sah di area batas aturan (shift hemodialisa darurat, terapis lembur, harga acuan lama) di rumah sakit jujur. Mesin aturan memang diharapkan menandainya; evaluasi menghitungnya sebagai tuduhan keliru dan melaporkannya terpisah sebagai "kasus sah yang perlu klarifikasi". Kasus ini juga menjadi bahan demo human-in-the-loop: sistem menandai, petugas mengklarifikasi.

## Modul per fase

| Fase | Modul | Isi |
|---|---|---|
| 0 | `sentinel/main.py`, `config.py`, `db.py`, `parameter.py` | Kerangka API, `/health`, settings, loader parameter |
| 1 | `sentinel/models/`, `sentinel/generator/` | Skema tabel; generator data tiruan berseed, `sesi_aktual`, `ground_truth`, dataset `--hidden` |
| 2 | `sentinel/rules/` | KAP-01, KAP-02, ULG-01, ULG-02, WJR-01, WJR-02, BAND-01; skor 0–100 |
| 3 | `sentinel/sensor/` | Simulator arus, klasifikasi Edge AI, Ed25519 + hash chain, SEN-01, TAMPER_* |
| 4 | `sentinel/evaluation/` | Recall, presisi, FPR per skenario; satu-satunya modul yang membaca ground truth |
| 5 | `sentinel/api/`, `frontend/` | Endpoint dashboard, halaman beranda/detail/audit, panel demo |
| 6 | `sentinel/agents/` | RAG BM25, empat agen, validator kutipan verbatim, fallback tanpa API key |
| 7 | `Makefile`, `assets/`, `docs/NASKAH_DEMO.md` | `make demo`, screenshot, naskah video |
