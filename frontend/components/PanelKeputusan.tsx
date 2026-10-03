"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

const PILIHAN = [
  { id: "setujui", label: "Setujui", kelas: "bg-hijau hover:bg-hijau/90" },
  { id: "minta_klarifikasi", label: "Minta klarifikasi", kelas: "bg-navy hover:bg-navy/90" },
  { id: "rujuk_audit", label: "Rujuk ke audit", kelas: "bg-oranye hover:bg-oranye/90" },
] as const;

export function PanelKeputusan({ dataset, rsId, periode }: { dataset: string; rsId: string; periode: string }) {
  const router = useRouter();
  const [alasan, setAlasan] = useState("");
  const [petugas, setPetugas] = useState("");
  const [pesan, setPesan] = useState<{ ok: boolean; teks: string } | null>(null);
  const [sibuk, setSibuk] = useState(false);
  const bolehUbah = dataset === "demo";

  async function kirim(keputusan: string) {
    if (alasan.trim().length < 10) {
      setPesan({ ok: false, teks: "Alasan wajib diisi, minimal 10 karakter." });
      return;
    }
    if (!petugas.trim()) {
      setPesan({ ok: false, teks: "Nama petugas wajib diisi." });
      return;
    }
    setSibuk(true);
    try {
      const r = await fetch("/api/keputusan", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ dataset, rs_id: rsId, periode, keputusan, alasan, petugas }),
      });
      const isi = await r.json();
      if (r.ok) {
        setPesan({ ok: true, teks: `${isi.label_keputusan}: tercatat dan dirantai ke entri sebelumnya.` });
        setAlasan("");
        router.refresh();
      } else {
        setPesan({ ok: false, teks: String(isi.detail ?? "Keputusan gagal disimpan.") });
      }
    } catch {
      setPesan({ ok: false, teks: "Tidak dapat terhubung ke server." });
    } finally {
      setSibuk(false);
    }
  }

  if (!bolehUbah) {
    return <p className="text-sm text-abu">Dataset utama hanya untuk dilihat. Pindah ke dataset demo untuk mencatat keputusan.</p>;
  }
  return (
    <div className="space-y-3">
      <label className="block text-sm text-abu">
        Alasan keputusan (wajib, minimal 10 karakter)
        <textarea
          value={alasan}
          onChange={(e) => setAlasan(e.target.value)}
          rows={3}
          className="mt-1 w-full rounded-md border border-garis px-3 py-2 text-foreground"
          placeholder="Contoh: Mohon penjelasan jumlah sesi fisioterapi yang melebihi kapasitas terapis."
        />
      </label>
      <label className="block text-sm text-abu">
        Nama petugas
        <input
          value={petugas}
          onChange={(e) => setPetugas(e.target.value)}
          className="mt-1 w-full rounded-md border border-garis px-3 py-2 text-foreground"
          placeholder="Nama verifikator"
        />
      </label>
      <div className="flex flex-wrap gap-2">
        {PILIHAN.map((p) => (
          <button
            key={p.id}
            type="button"
            disabled={sibuk}
            onClick={() => kirim(p.id)}
            className={`rounded-md px-4 py-2 text-sm font-semibold text-white disabled:opacity-50 ${p.kelas}`}
          >
            {p.label}
          </button>
        ))}
      </div>
      {pesan && <p role="status" className={`text-sm ${pesan.ok ? "text-hijau" : "text-oranye"}`}>{pesan.teks}</p>}
    </div>
  );
}
