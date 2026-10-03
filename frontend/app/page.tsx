import Link from "next/link";
import { CatatanTetap, KotakGalat, LabelPrioritas, TautanDataset } from "@/components/ui";
import { ambil, datasetDari, GalatBackend, type DaftarRs, type Meta } from "@/lib/api";
import { alasanPrioritas, angka, judulAturan, periode as namaPeriode } from "@/lib/teks";

const PRIORITAS = ["tinggi", "sedang", "rendah"] as const;

export default async function DaftarPeriksa({ searchParams }: PageProps<"/">) {
  const sp = await searchParams;
  const dataset = datasetDari(sp.dataset);
  const periode = typeof sp.periode === "string" && sp.periode ? sp.periode : undefined;
  const prioritas = typeof sp.prioritas === "string" && sp.prioritas ? sp.prioritas : undefined;

  let meta: Meta, daftar: DaftarRs;
  try {
    [meta, daftar] = await Promise.all([
      ambil<Meta>("/meta", { dataset }),
      ambil<DaftarRs>("/rs", { dataset, periode, prioritas }),
    ]);
  } catch (e) {
    return <KotakGalat pesan={e instanceof GalatBackend ? e.message : "Terjadi galat yang tidak terduga."} />;
  }
  const r = daftar.ringkasan;

  return (
    <div className="space-y-5">
      <div className="flex items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-navy">Daftar periksa</h1>
          <p className="mt-1 text-abu">
            Rumah sakit per bulan, diurutkan dari prioritas pemeriksaan tertinggi.{" "}
            {periode ? `Periode ${namaPeriode(periode)}.` : "Semua periode."}
          </p>
        </div>
        <TautanDataset dataset={dataset} jalur="/" />
      </div>

      <div className="grid grid-cols-4 gap-4">
        {PRIORITAS.map((p) => (
          <div key={p} className="rounded-xl bg-white p-4 shadow-sm ring-1 ring-garis">
            <div className="flex items-center justify-between">
              <span className="text-sm text-abu">Prioritas</span>
              <LabelPrioritas prioritas={p} />
            </div>
            <div className="mt-2 text-3xl font-bold text-navy">{r.per_prioritas[p]}</div>
            <div className="text-sm text-abu">rumah sakit-periode</div>
          </div>
        ))}
        <div className="rounded-xl bg-white p-4 shadow-sm ring-1 ring-garis">
          <span className="text-sm text-abu">Tagihan yang diperiksa</span>
          <div className="mt-2 text-3xl font-bold text-navy">{angka(r.jumlah_tagihan_diperiksa)}</div>
          <div className="text-sm text-abu">tagihan, {r.jumlah_rs_periode} rumah sakit-periode</div>
        </div>
      </div>

      <form className="flex flex-wrap items-end gap-4 rounded-xl bg-white p-4 shadow-sm ring-1 ring-garis" method="get">
        <input type="hidden" name="dataset" value={dataset} />
        <label className="flex flex-col text-sm text-abu">
          Periode
          <select name="periode" defaultValue={periode ?? ""} className="mt-1 rounded-md border border-garis px-3 py-2 text-foreground">
            <option value="">Semua periode</option>
            {meta.periode.map((p) => (
              <option key={p} value={p}>{namaPeriode(p)}</option>
            ))}
          </select>
        </label>
        <label className="flex flex-col text-sm text-abu">
          Prioritas
          <select name="prioritas" defaultValue={prioritas ?? ""} className="mt-1 rounded-md border border-garis px-3 py-2 text-foreground">
            <option value="">Semua prioritas</option>
            {PRIORITAS.map((p) => (
              <option key={p} value={p}>{p[0].toUpperCase() + p.slice(1)}</option>
            ))}
          </select>
        </label>
        <button type="submit" className="rounded-md bg-navy px-5 py-2 text-sm font-semibold text-white hover:bg-navy/90">
          Terapkan filter
        </button>
        {!meta.dataset_dapat_diubah && (
          <span className="ml-auto text-sm text-abu">Dataset utama hanya untuk dilihat; keputusan dicatat di dataset demo.</span>
        )}
      </form>

      <div className="overflow-hidden rounded-xl bg-white shadow-sm ring-1 ring-garis">
        <table className="w-full text-left text-sm">
          <thead className="bg-navy-terang text-navy">
            <tr>
              <th className="px-4 py-3">Rumah sakit</th>
              <th className="px-4 py-3">Kelas</th>
              <th className="px-4 py-3">Provinsi</th>
              <th className="px-4 py-3">Periode</th>
              <th className="px-4 py-3 text-right">Skor</th>
              <th className="px-4 py-3">Prioritas</th>
              <th className="px-4 py-3">Alasan prioritas</th>
              <th className="px-4 py-3">Temuan</th>
            </tr>
          </thead>
          <tbody>
            {daftar.data.map((b) => (
              <tr key={`${b.rs_id}-${b.periode}`} className="border-t border-garis hover:bg-background">
                <td className="whitespace-nowrap px-4 py-2.5">
                  <Link
                    href={`/rs/${b.rs_id}?dataset=${dataset}&periode=${b.periode}`}
                    className="font-semibold text-navy underline-offset-2 hover:underline"
                  >
                    {b.nama_samaran}
                  </Link>
                </td>
                <td className="px-4 py-2.5">{b.kelas}</td>
                <td className="whitespace-nowrap px-4 py-2.5">{b.provinsi}</td>
                <td className="whitespace-nowrap px-4 py-2.5">{namaPeriode(b.periode)}</td>
                <td className="px-4 py-2.5 text-right font-semibold tabular-nums">{angka(b.skor, 1)}</td>
                <td className="px-4 py-2.5"><LabelPrioritas prioritas={b.prioritas} /></td>
                <td className="max-w-[420px] px-4 py-2.5 text-abu">{alasanPrioritas(b.alasan_prioritas)}</td>
                <td className="px-4 py-2.5">
                  {b.jumlah_temuan === 0 ? (
                    <span className="text-abu">Tidak ada</span>
                  ) : (
                    <span title={Object.entries(b.temuan_per_aturan).map(([a, n]) => `${judulAturan(a)}: ${n}`).join("\n")}>
                      {b.jumlah_temuan} temuan
                      <span className="text-abu"> ({Object.keys(b.temuan_per_aturan).map(judulAturan).join(", ")})</span>
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {daftar.data.length === 0 && <p className="p-6 text-center text-abu">Tidak ada data untuk filter ini.</p>}
      </div>
      <CatatanTetap />
    </div>
  );
}
