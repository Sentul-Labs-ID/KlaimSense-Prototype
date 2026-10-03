"use client";

import { useMemo, useState } from "react";
import type { StatusHarian } from "@/lib/api";
import { tanggal as formatTanggal } from "@/lib/teks";

const SHIFT = [
  { no: 1, label: "Shift 1", jam: "05:00–09:50" },
  { no: 2, label: "Shift 2", jam: "09:50–14:40" },
  { no: 3, label: "Shift 3", jam: "14:40–19:30" },
  { no: 4, label: "Shift darurat", jam: "19:30–24:00" },
];
const STATUS = [
  { kunci: "menit_terapi", label: "Terapi", kelas: "bg-hijau" },
  { kunci: "menit_standby", label: "Siaga (standby)", kelas: "bg-navy/40" },
  { kunci: "menit_mati", label: "Mati", kelas: "bg-[#c9ced6]" },
  { kunci: "menit_tanpa_data", label: "Tanpa data", kelas: "bg-oranye" },
] as const;

type HasilVerifikasi = {
  status: string;
  keterangan: string;
  jumlah_pesan: number;
  valid: number;
  rantai_putus: number;
  tanda_tangan_gagal: number;
  rincian: string[];
};

export function GridSensor({
  dataset,
  perangkat,
  status,
  anomali,
}: {
  dataset: string;
  perangkat: { device_id: string; mesin_id: string }[];
  status: StatusHarian[];
  anomali: { jenis: string; device_id: string; waktu: string; keterangan: string }[];
}) {
  const daftarTanggal = useMemo(() => [...new Set(status.map((s) => s.tanggal))].sort(), [status]);
  const tanggalAnomali = useMemo(() => new Set(anomali.map((a) => a.waktu.slice(0, 10))), [anomali]);
  const [tanggal, setTanggal] = useState(
    daftarTanggal.find((t) => tanggalAnomali.has(t)) ?? daftarTanggal[Math.min(14, daftarTanggal.length - 1)] ?? "",
  );
  const [hasil, setHasil] = useState<Record<string, HasilVerifikasi | string>>({});
  const [sibuk, setSibuk] = useState<string | null>(null);

  const sel = useMemo(() => {
    const m = new Map<string, StatusHarian>();
    for (const s of status) if (s.tanggal === tanggal) m.set(`${s.mesin_id}|${s.shift}`, s);
    return m;
  }, [status, tanggal]);

  async function verifikasi(device_id: string) {
    setSibuk(device_id);
    try {
      const r = await fetch("/api/sensor/verifikasi", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ dataset, device_id, tanggal }),
      });
      const isi = await r.json();
      setHasil((h) => ({ ...h, [device_id]: r.ok ? isi : String(isi.detail ?? "Verifikasi gagal.") }));
    } catch {
      setHasil((h) => ({ ...h, [device_id]: "Tidak dapat terhubung ke server." }));
    } finally {
      setSibuk(null);
    }
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-4 text-sm">
        <label className="flex items-center gap-2 text-abu">
          Tanggal
          <select
            value={tanggal}
            onChange={(e) => { setTanggal(e.target.value); setHasil({}); }}
            className="rounded-md border border-garis px-3 py-1.5 text-foreground"
          >
            {daftarTanggal.map((t) => (
              <option key={t} value={t}>{formatTanggal(t)}{tanggalAnomali.has(t) ? " (ada anomali)" : ""}</option>
            ))}
          </select>
        </label>
        <span className="flex flex-wrap gap-3 text-abu">
          {STATUS.map((s) => (
            <span key={s.kunci} className="flex items-center gap-1.5"><span className={`inline-block h-3 w-3 rounded-sm ${s.kelas}`} />{s.label}</span>
          ))}
        </span>
      </div>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-abu">
            <th className="py-1.5 pr-3 font-medium">Mesin</th>
            {SHIFT.map((s) => (
              <th key={s.no} className="px-1.5 py-1.5 font-medium">{s.label}<span className="block text-xs font-normal">{s.jam}</span></th>
            ))}
            <th className="py-1.5 pl-3 font-medium">Bukti pesan</th>
          </tr>
        </thead>
        <tbody>
          {perangkat.map((p) => {
            const h = hasil[p.device_id];
            return (
              <tr key={p.device_id} className="border-t border-garis align-middle">
                <td className="py-2 pr-3 font-semibold text-navy">{p.mesin_id.split("-").pop()}</td>
                {SHIFT.map((s) => {
                  const c = sel.get(`${p.mesin_id}|${s.no}`);
                  const total = c ? c.menit_terapi + c.menit_standby + c.menit_mati + c.menit_tanpa_data : 0;
                  return (
                    <td key={s.no} className="px-1.5 py-2">
                      {c && total > 0 ? (
                        <div
                          className="flex h-7 overflow-hidden rounded ring-1 ring-garis"
                          title={STATUS.map((st) => `${st.label}: ${c[st.kunci]} menit`).join("\n")}
                        >
                          {STATUS.map((st) => c[st.kunci] > 0 && (
                            <div key={st.kunci} className={st.kelas} style={{ width: `${(100 * c[st.kunci]) / total}%` }} />
                          ))}
                        </div>
                      ) : (
                        <div className="h-7 rounded bg-background" />
                      )}
                    </td>
                  );
                })}
                <td className="py-2 pl-3">
                  <button
                    type="button"
                    onClick={() => verifikasi(p.device_id)}
                    disabled={sibuk !== null}
                    className="rounded-md border border-navy px-3 py-1 text-xs font-semibold text-navy hover:bg-navy-terang disabled:opacity-50"
                  >
                    {sibuk === p.device_id ? "Memeriksa…" : "Verifikasi tanda tangan"}
                  </button>
                  {h && (
                    <p className={`mt-1 text-xs ${typeof h !== "string" && h.status === "utuh" ? "text-hijau" : "text-oranye"}`}>
                      {typeof h === "string" ? h : `${h.status === "utuh" ? "✓" : "⚠"} ${h.keterangan}`}
                    </p>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <p className="text-xs text-abu">
        Setiap kotak menunjukkan proporsi menit dalam shift: terapi, siaga, mati, atau tanpa data dari sensor. Tombol verifikasi
        memeriksa ulang tanda tangan digital dan rantai hash semua pesan sensor mesin itu pada tanggal terpilih.
      </p>
    </div>
  );
}
