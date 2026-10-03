import Link from "next/link";
import { KotakGalat, TautanDataset } from "@/components/ui";
import { ambil, datasetDari, GalatBackend, type Audit } from "@/lib/api";
import { periode as namaPeriode, waktuWIB } from "@/lib/teks";

export default async function HalamanAudit({ searchParams }: PageProps<"/audit">) {
  const dataset = datasetDari((await searchParams).dataset);
  let audit: Audit;
  try {
    audit = await ambil<Audit>("/audit", { dataset });
  } catch (e) {
    return <KotakGalat pesan={e instanceof GalatBackend ? e.message : "Terjadi galat yang tidak terduga."} />;
  }
  const utuh = audit.rantai.status === "utuh";

  return (
    <div className="space-y-5">
      <div className="flex items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-navy">Audit keputusan</h1>
          <p className="mt-1 text-abu">
            Setiap keputusan petugas dirantai dengan hash entri sebelumnya, sehingga perubahan diam-diam pada catatan lama langsung terlihat.
          </p>
        </div>
        <TautanDataset dataset={dataset} jalur="/audit" />
      </div>

      <div
        role="status"
        className={`rounded-xl p-4 text-white ${utuh ? "bg-hijau" : "bg-oranye"}`}
      >
        <strong className="text-lg">{utuh ? "Rantai keputusan utuh" : "Rantai keputusan rusak"}</strong>
        <p className="text-sm text-white/90">{audit.rantai.keterangan}</p>
      </div>

      <div className="overflow-hidden rounded-xl bg-white shadow-sm ring-1 ring-garis">
        <table className="w-full text-left text-sm">
          <thead className="bg-navy-terang text-navy">
            <tr>
              <th className="px-4 py-3">No.</th>
              <th className="px-4 py-3">Waktu (WIB)</th>
              <th className="px-4 py-3">Rumah sakit</th>
              <th className="px-4 py-3">Periode</th>
              <th className="px-4 py-3">Keputusan</th>
              <th className="px-4 py-3">Alasan</th>
              <th className="px-4 py-3">Petugas</th>
              <th className="px-4 py-3">Hash entri</th>
            </tr>
          </thead>
          <tbody>
            {audit.entri.map((e) => (
              <tr key={e.id} className={`border-t border-garis ${audit.rantai.entri_rusak === e.id ? "bg-oranye-terang" : ""}`}>
                <td className="px-4 py-2.5 tabular-nums">{e.id}</td>
                <td className="whitespace-nowrap px-4 py-2.5">{waktuWIB(e.waktu)}</td>
                <td className="px-4 py-2.5">
                  <Link href={`/rs/${e.rs_id}?dataset=${dataset}&periode=${e.periode}`} className="text-navy hover:underline">{e.nama_samaran ?? e.rs_id}</Link>
                </td>
                <td className="px-4 py-2.5">{namaPeriode(e.periode)}</td>
                <td className="px-4 py-2.5 font-semibold">{e.label_keputusan}</td>
                <td className="max-w-[480px] px-4 py-2.5">{e.alasan}</td>
                <td className="px-4 py-2.5">{e.petugas}</td>
                <td className="px-4 py-2.5 font-mono text-xs text-abu" title={`hash ${e.hash}\nsebelumnya ${e.prev_hash}`}>{e.hash.slice(0, 16)}…</td>
              </tr>
            ))}
          </tbody>
        </table>
        {audit.entri.length === 0 && <p className="p-6 text-center text-abu">Belum ada keputusan di dataset ini.</p>}
      </div>
    </div>
  );
}
