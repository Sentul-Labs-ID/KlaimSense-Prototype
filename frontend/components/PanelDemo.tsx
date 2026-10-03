"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import type { BarisRs } from "@/lib/api";
import { alasanPrioritas, angka, periode as namaPeriode, tanggal } from "@/lib/teks";
import { LabelPrioritas } from "./ui";

const SISIPAN = [
  { id: "KAP_FISIO", label: "Fisioterapi melebihi kapasitas terapis" },
  { id: "KAP_HD", label: "Hemodialisa melebihi kapasitas mesin" },
  { id: "ULANG_HARI", label: "Dua sesi hemodialisa sehari untuk pasien yang sama" },
  { id: "HARGA_LEBIH", label: "Harga obat/alat di atas harga acuan" },
];

type Skor = { skor: number; prioritas: string; alasan_prioritas: string } | null;
type Hasil = {
  rs_id: string;
  nama_samaran: string;
  sisipan: string;
  tanggal: string[];
  tagihan_baru: number;
  tagihan_diubah: number;
  perubahan: { periode: string; sebelum: Skor; sesudah: Skor }[];
  pesan: string;
};

function KotakSkor({ judul, s }: { judul: string; s: Skor }) {
  return (
    <div className="flex-1 rounded-lg bg-background p-4">
      <div className="text-sm text-abu">{judul}</div>
      {s ? (
        <>
          <div className="mt-1 flex items-center gap-3">
            <span className="text-4xl font-bold text-navy tabular-nums">{angka(s.skor, 1)}</span>
            <LabelPrioritas prioritas={s.prioritas} />
          </div>
          <p className="mt-1 text-sm text-abu">{alasanPrioritas(s.alasan_prioritas)}</p>
        </>
      ) : (
        <p className="text-abu">–</p>
      )}
    </div>
  );
}

export function PanelDemo({ baris, periode }: { baris: BarisRs[]; periode: string[] }) {
  const [periodeDipilih, setPeriode] = useState(periode[1] ?? periode[0] ?? "");
  const pilihanRs = useMemo(
    () => baris.filter((b) => b.periode === periodeDipilih).sort((a, b) => a.nama_samaran.localeCompare(b.nama_samaran)),
    [baris, periodeDipilih],
  );
  const [rsId, setRsId] = useState(pilihanRs.find((b) => b.prioritas === "rendah")?.rs_id ?? pilihanRs[0]?.rs_id ?? "");
  const [jenis, setJenis] = useState("KAP_FISIO");
  const [hari, setHari] = useState(3);
  const [hasil, setHasil] = useState<Hasil | null>(null);
  const [galat, setGalat] = useState<string | null>(null);
  const [sibuk, setSibuk] = useState(false);

  async function sisipkan() {
    setSibuk(true);
    setGalat(null);
    try {
      const r = await fetch("/api/demo/sisipkan", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ dataset: "demo", rs_id: rsId, skenario: jenis, jumlah_hari: hari, periode: periodeDipilih }),
      });
      const isi = await r.json();
      if (r.ok) setHasil(isi);
      else setGalat(String(isi.detail ?? "Sisipan gagal."));
    } catch {
      setGalat("Tidak dapat terhubung ke server.");
    } finally {
      setSibuk(false);
    }
  }

  return (
    <div className="grid grid-cols-5 gap-5">
      <section className="col-span-2 space-y-4 rounded-xl bg-white p-5 shadow-sm ring-1 ring-garis">
        <h2 className="text-lg font-semibold text-navy">Sisipkan kecurangan</h2>
        <label className="block text-sm text-abu">
          Periode
          <select value={periodeDipilih} onChange={(e) => setPeriode(e.target.value)} className="mt-1 w-full rounded-md border border-garis px-3 py-2 text-foreground">
            {periode.map((p) => <option key={p} value={p}>{namaPeriode(p)}</option>)}
          </select>
        </label>
        <label className="block text-sm text-abu">
          Rumah sakit
          <select value={rsId} onChange={(e) => setRsId(e.target.value)} className="mt-1 w-full rounded-md border border-garis px-3 py-2 text-foreground">
            {pilihanRs.map((b) => (
              <option key={b.rs_id} value={b.rs_id}>
                {b.nama_samaran} (kelas {b.kelas}) · prioritas {b.prioritas}, skor {angka(b.skor, 1)}
              </option>
            ))}
          </select>
        </label>
        <label className="block text-sm text-abu">
          Jenis kecurangan
          <select value={jenis} onChange={(e) => setJenis(e.target.value)} className="mt-1 w-full rounded-md border border-garis px-3 py-2 text-foreground">
            {SISIPAN.map((s) => <option key={s.id} value={s.id}>{s.label}</option>)}
          </select>
        </label>
        <label className="block text-sm text-abu">
          Jumlah hari: <strong className="text-foreground">{hari}</strong>
          <input type="range" min={1} max={5} value={hari} onChange={(e) => setHari(Number(e.target.value))} className="mt-1 w-full accent-[#0e2a47]" />
        </label>
        <button
          type="button"
          onClick={sisipkan}
          disabled={sibuk || !rsId}
          className="w-full rounded-md bg-oranye px-5 py-3 font-semibold text-white hover:bg-oranye/90 disabled:opacity-50"
        >
          {sibuk ? "Menyisipkan dan menghitung ulang…" : "Sisipkan kecurangan"}
        </button>
        {galat && <p role="alert" className="text-sm text-oranye">{galat}</p>}
      </section>

      <section className="col-span-3 rounded-xl bg-white p-5 shadow-sm ring-1 ring-garis">
        <h2 className="text-lg font-semibold text-navy">Hasil</h2>
        {!hasil ? (
          <p className="mt-2 text-abu">Pilih rumah sakit dan jenis kecurangan, lalu tekan &ldquo;Sisipkan kecurangan&rdquo;.</p>
        ) : (
          <div className="mt-3 space-y-4">
            <p>
              <strong>{hasil.nama_samaran}</strong>: {hasil.sisipan} disisipkan pada {hasil.tanggal.map(tanggal).join(", ")} (
              {hasil.tagihan_baru} tagihan baru{hasil.tagihan_diubah ? `, ${hasil.tagihan_diubah} tagihan diubah` : ""}).
            </p>
            {hasil.perubahan.map((u) => (
              <div key={u.periode} className="space-y-2">
                <h3 className="font-semibold text-navy">{namaPeriode(u.periode)}</h3>
                <div className="flex items-stretch gap-3">
                  <KotakSkor judul="Sebelum" s={u.sebelum} />
                  <div className="self-center text-2xl text-abu">→</div>
                  <KotakSkor judul="Sesudah" s={u.sesudah} />
                </div>
                <Link
                  href={`/rs/${hasil.rs_id}?dataset=demo&periode=${u.periode}`}
                  className="inline-block rounded-md bg-navy px-4 py-2 text-sm font-semibold text-white hover:bg-navy/90"
                >
                  Lihat detail rumah sakit →
                </Link>
              </div>
            ))}
            <p className="text-xs text-abu">{hasil.pesan}</p>
          </div>
        )}
      </section>
    </div>
  );
}
