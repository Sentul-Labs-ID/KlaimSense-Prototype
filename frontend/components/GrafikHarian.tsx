import type { Harian } from "@/lib/api";
import { tanggalPendek } from "@/lib/teks";

// Grafik garis harian: sesi ditagih vs kapasitas. Hari dengan temuan kapasitas ditandai
// lingkaran oranye. Tooltip bawaan peramban (<title>) pada setiap titik.
const NAVY = "#0e2a47";
const HIJAU = "#1e7a52";
const ORANYE = "#a8540f";
const GARIS = "#dde2e8";
const TEKS_2 = "#5b6675";

export function GrafikHarian({
  judul,
  data,
  kunci,
  kunciKapasitas,
  aturan,
}: {
  judul: string;
  data: Harian[];
  kunci: "fisioterapi" | "hemodialisa";
  kunciKapasitas: "kapasitas_fisioterapi" | "kapasitas_hemodialisa";
  aturan: string;
}) {
  const lebar = 820;
  const tinggi = 260;
  const kiri = 44;
  const bawah = 34;
  const atas = 16;
  const kanan = 12;
  const titik = data.filter((d) => d[kunci] > 0 || d[kunciKapasitas] > 0);
  if (titik.length === 0) {
    return <p className="text-sm text-abu">Tidak ada sesi {kunci} di periode ini.</p>;
  }
  const maks = Math.max(...titik.map((d) => Math.max(d[kunci], d[kunciKapasitas]))) * 1.12 || 1;
  const x = (i: number) => kiri + (i * (lebar - kiri - kanan)) / Math.max(1, titik.length - 1);
  const y = (v: number) => atas + (1 - v / maks) * (tinggi - atas - bawah);
  const jalur = (f: (d: Harian) => number) => titik.map((d, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(f(d)).toFixed(1)}`).join(" ");
  const sumbuY = [0, 0.25, 0.5, 0.75, 1].map((r) => Math.round(r * maks));
  const label = titik.filter((_, i) => i % Math.ceil(titik.length / 10) === 0);

  return (
    <figure>
      <figcaption className="mb-2 flex items-center justify-between text-sm">
        <span className="font-semibold text-navy">{judul}</span>
        <span className="flex gap-4 text-abu">
          <span className="flex items-center gap-1.5"><span className="inline-block h-0.5 w-5" style={{ background: NAVY }} />Sesi ditagih</span>
          <span className="flex items-center gap-1.5"><span className="inline-block h-0.5 w-5 border-t-2 border-dashed" style={{ borderColor: HIJAU }} />Kapasitas</span>
          <span className="flex items-center gap-1.5"><span className="inline-block h-3 w-3 rounded-full border-2" style={{ borderColor: ORANYE }} />Hari dengan temuan</span>
        </span>
      </figcaption>
      <svg viewBox={`0 0 ${lebar} ${tinggi}`} className="w-full" role="img" aria-label={judul}>
        {sumbuY.map((v) => (
          <g key={v}>
            <line x1={kiri} x2={lebar - kanan} y1={y(v)} y2={y(v)} stroke={GARIS} />
            <text x={kiri - 6} y={y(v) + 4} textAnchor="end" fontSize="11" fill={TEKS_2}>{v}</text>
          </g>
        ))}
        {label.map((d) => {
          const i = titik.indexOf(d);
          return <text key={d.tanggal} x={x(i)} y={tinggi - 10} textAnchor="middle" fontSize="11" fill={TEKS_2}>{tanggalPendek(d.tanggal)}</text>;
        })}
        <path d={jalur((d) => d[kunciKapasitas])} fill="none" stroke={HIJAU} strokeWidth={2} strokeDasharray="6 4" />
        <path d={jalur((d) => d[kunci])} fill="none" stroke={NAVY} strokeWidth={2} />
        {titik.map((d, i) => {
          const temuan = d.aturan_temuan.includes(aturan) || (aturan === "KAP-02" && d.aturan_temuan.includes("SEN-01"));
          return (
            <g key={d.tanggal}>
              {temuan && <circle cx={x(i)} cy={y(d[kunci])} r={7} fill="none" stroke={ORANYE} strokeWidth={2.5} />}
              <circle cx={x(i)} cy={y(d[kunci])} r={temuan ? 4 : 2.5} fill={temuan ? ORANYE : NAVY} />
              <circle cx={x(i)} cy={y(d[kunci])} r={10} fill="transparent">
                <title>{`${tanggalPendek(d.tanggal)}: ${d[kunci]} sesi ditagih, kapasitas ${d[kunciKapasitas]}${d.aturan_temuan.length ? ` (temuan: ${d.aturan_temuan.join(", ")})` : ""}`}</title>
              </circle>
            </g>
          );
        })}
      </svg>
    </figure>
  );
}
