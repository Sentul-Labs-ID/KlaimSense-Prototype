import Link from "next/link";
import type { ReactNode } from "react";
import { LABEL_PRIORITAS } from "@/lib/teks";

const WARNA_PRIORITAS: Record<string, string> = {
  tinggi: "bg-oranye text-white",
  sedang: "bg-navy-terang text-navy ring-1 ring-navy/30",
  rendah: "bg-hijau-terang text-hijau",
};

export function LabelPrioritas({ prioritas }: { prioritas: string }) {
  return (
    <span className={`inline-block rounded-full px-3 py-0.5 text-sm font-semibold ${WARNA_PRIORITAS[prioritas] ?? ""}`}>
      {LABEL_PRIORITAS[prioritas] ?? prioritas}
    </span>
  );
}

export function Kartu({ judul, children, aksi }: { judul?: ReactNode; children: ReactNode; aksi?: ReactNode }) {
  return (
    <section className="rounded-xl bg-white p-5 shadow-sm ring-1 ring-garis">
      {judul && (
        <div className="mb-3 flex items-center justify-between gap-4">
          <h2 className="text-lg font-semibold text-navy">{judul}</h2>
          {aksi}
        </div>
      )}
      {children}
    </section>
  );
}

export function KotakGalat({ pesan }: { pesan: string }) {
  return (
    <div role="alert" className="rounded-lg border border-oranye/40 bg-oranye-terang p-4 text-oranye">
      <strong>Data belum dapat ditampilkan.</strong> {pesan}
    </div>
  );
}

export function CatatanTetap() {
  return (
    <p className="rounded-lg bg-navy px-4 py-3 text-sm text-white">
      Skor adalah prioritas pemeriksaan, bukan penetapan kecurangan. Rumah sakit diberi kesempatan menjelaskan sebelum audit.
    </p>
  );
}

export function TautanDataset({ dataset, jalur }: { dataset: string; jalur: string }) {
  return (
    <div className="flex items-center gap-1 rounded-lg bg-white p-1 text-sm ring-1 ring-garis" aria-label="Pilih dataset">
      {[
        { id: "demo", label: "Demo (dapat diubah)" },
        { id: "utama", label: "Utama (baca-saja)" },
      ].map((d) => (
        <Link
          key={d.id}
          href={`${jalur}?dataset=${d.id}`}
          className={`rounded-md px-3 py-1 ${dataset === d.id ? "bg-navy text-white" : "text-navy hover:bg-navy-terang"}`}
        >
          {d.label}
        </Link>
      ))}
    </div>
  );
}
