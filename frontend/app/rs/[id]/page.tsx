import Link from "next/link";
import { GrafikHarian } from "@/components/GrafikHarian";
import { GridSensor } from "@/components/GridSensor";
import { PanelKeputusan } from "@/components/PanelKeputusan";
import { CatatanTetap, Kartu, KotakGalat, LabelPrioritas, TautanDataset } from "@/components/ui";
import { ambil, datasetDari, GalatBackend, type DetailRs, type Temuan } from "@/lib/api";
import { alasanPrioritas, angka, judulAturan, NAMA_ATURAN, periode as namaPeriode, tanggal, waktuWIB } from "@/lib/teks";

const LABEL_KEPUTUSAN: Record<string, string> = {
  setujui: "Setujui",
  minta_klarifikasi: "Minta klarifikasi",
  rujuk_audit: "Rujuk ke audit",
};

function ringkasanTemplate(d: DetailRs): string[] {
  const kalimat = [
    `${d.rumah_sakit.nama_samaran} (kelas ${d.rumah_sakit.kelas}, ${d.rumah_sakit.provinsi}) pada ${namaPeriode(d.periode)} ` +
      `mendapat skor ${angka(d.skor.skor, 1)} dari 100 dengan prioritas ${d.skor.prioritas}.`,
  ];
  if (d.temuan.length === 0) {
    kalimat.push("Tidak ada temuan aturan pada periode ini.");
    return kalimat;
  }
  const per = new Map<string, Temuan[]>();
  for (const t of d.temuan) per.set(t.aturan_id, [...(per.get(t.aturan_id) ?? []), t]);
  for (const [aturan, daftar] of per) {
    const hari = daftar.filter((t) => t.tanggal).length;
    kalimat.push(
      `${judulAturan(aturan)}: ${daftar.length} temuan${hari ? ` pada ${new Set(daftar.map((t) => t.tanggal)).size} hari` : ""}. ` +
        `Contoh: ${daftar[0].penjelasan}`,
    );
  }
  kalimat.push(`Alasan prioritas: ${alasanPrioritas(d.skor.alasan_prioritas)}.`);
  return kalimat;
}

export default async function DetailRumahSakit({ params, searchParams }: PageProps<"/rs/[id]">) {
  const { id } = await params;
  const sp = await searchParams;
  const dataset = datasetDari(sp.dataset);
  const periodeDiminta = typeof sp.periode === "string" ? sp.periode : undefined;

  let d: DetailRs;
  try {
    d = await ambil<DetailRs>(`/rs/${encodeURIComponent(id)}`, { dataset, periode: periodeDiminta });
  } catch (e) {
    return <KotakGalat pesan={e instanceof GalatBackend ? e.message : "Terjadi galat yang tidak terduga."} />;
  }
  const rincian = Object.entries(d.skor.rincian_per_aturan);
  const kelompok = new Map<string, Temuan[]>();
  for (const t of d.temuan) kelompok.set(t.aturan_id, [...(kelompok.get(t.aturan_id) ?? []), t]);
  const k = d.kapasitas;

  return (
    <div className="space-y-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <Link href={`/?dataset=${dataset}`} className="text-sm text-navy hover:underline">← Kembali ke daftar periksa</Link>
          <h1 className="mt-1 text-3xl font-bold text-navy">{d.rumah_sakit.nama_samaran}</h1>
          <p className="text-abu">
            Kelas {d.rumah_sakit.kelas} · {d.rumah_sakit.kab_kota}, {d.rumah_sakit.provinsi} ·{" "}
            {d.rumah_sakit.punya_sensor ? "Mesin hemodialisa bersensor" : "Tanpa sensor"}
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            {d.periode_tersedia.map((p) => (
              <Link
                key={p.periode}
                href={`/rs/${id}?dataset=${dataset}&periode=${p.periode}`}
                className={`flex items-center gap-2 rounded-md px-3 py-1.5 text-sm ring-1 ${p.periode === d.periode ? "bg-navy text-white ring-navy" : "bg-white text-navy ring-garis hover:bg-navy-terang"}`}
              >
                {namaPeriode(p.periode)} <LabelPrioritas prioritas={p.prioritas} />
              </Link>
            ))}
          </div>
        </div>
        <TautanDataset dataset={dataset} jalur={`/rs/${id}`} />
      </div>

      <div className="grid grid-cols-3 gap-5">
        <div className="col-span-2 space-y-5">
          <Kartu judul="Rincian skor">
            <div className="mb-4 flex items-center gap-6">
              <div>
                <div className="text-5xl font-bold text-navy tabular-nums">{angka(d.skor.skor, 1)}</div>
                <div className="text-sm text-abu">dari 100</div>
              </div>
              <div className="space-y-1">
                <LabelPrioritas prioritas={d.skor.prioritas} />
                <p className="text-sm text-abu">{alasanPrioritas(d.skor.alasan_prioritas)}</p>
              </div>
            </div>
            <table className="w-full text-sm">
              <thead className="text-left text-abu">
                <tr>
                  <th className="py-1.5 font-medium">Aturan</th>
                  <th className="py-1.5 font-medium">Apa yang diperiksa</th>
                  <th className="py-1.5 pl-4 text-right font-medium">Temuan</th>
                  <th className="py-1.5 pl-4 text-right font-medium">Bobot</th>
                  <th className="py-1.5 pl-4 text-right font-medium">Sumbangan skor</th>
                </tr>
              </thead>
              <tbody>
                {rincian.map(([aturan, r]) => {
                  const jumlah = r.jumlah_temuan ?? (r.selisih ? r.selisih.jumlah_temuan + (r.integritas?.jumlah_temuan ?? 0) : kelompok.get(aturan)?.length ?? 0);
                  return (
                    <tr key={aturan} className={`border-t border-garis ${r.kontribusi > 0 ? "font-semibold" : "text-abu"}`}>
                      <td className="py-1.5 pr-3">{judulAturan(aturan)} <span className="font-normal text-abu">({aturan})</span></td>
                      <td className="py-1.5 pr-3 font-normal text-abu">{NAMA_ATURAN[aturan]?.arti}</td>
                      <td className="py-1.5 pl-4 text-right tabular-nums">{jumlah}</td>
                      <td className="py-1.5 pl-4 text-right tabular-nums">{r.bobot}</td>
                      <td className="py-1.5 pl-4 text-right tabular-nums">{angka(r.kontribusi, 1)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            <p className="mt-3 text-xs text-abu">
              Skor = jumlah (bobot aturan × keparahan). Keparahan naik sesuai jumlah temuan dalam sebulan dan penuh pada
              titik jenuhnya. Aturan versi {d.skor.versi_aturan}; parameter <code>{d.skor.hash_parameter.slice(0, 12)}</code>.
            </p>
          </Kartu>

          <Kartu judul={`Temuan (${d.temuan.length})`}>
            {d.temuan.length === 0 && <p className="text-sm text-abu">Tidak ada temuan pada periode ini.</p>}
            <div className="space-y-4">
              {[...kelompok.entries()].map(([aturan, daftar]) => (
                <div key={aturan}>
                  <h3 className="font-semibold text-navy">{judulAturan(aturan)} <span className="font-normal text-abu">· {daftar.length} temuan</span></h3>
                  <ul className="mt-1 space-y-1 text-sm">
                    {daftar.map((t) => (
                      <li key={t.id} className="rounded-md bg-background px-3 py-2">{t.penjelasan}</li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          </Kartu>

          <Kartu judul="Sesi harian dibanding kapasitas">
            <div className="space-y-6">
              <GrafikHarian
                judul={`Fisioterapi: kapasitas ${k.kapasitas_fisioterapi_harian} sesi/hari (${k.jumlah_fisioterapis} terapis × ${k.sesi_per_terapis})`}
                data={d.harian} kunci="fisioterapi" kunciKapasitas="kapasitas_fisioterapi" aturan="KAP-01"
              />
              <GrafikHarian
                judul={`Hemodialisa: kapasitas ${k.kapasitas_hemodialisa_harian} sesi/hari (${k.jumlah_mesin_hd} mesin × ${k.shift_hd_per_hari} shift), unit buka ${k.hari_operasional_hd} hari/minggu`}
                data={d.harian} kunci="hemodialisa" kunciKapasitas="kapasitas_hemodialisa" aturan="KAP-02"
              />
            </div>
          </Kartu>

          {d.sensor.bersensor && (
            <Kartu judul="Sensor mesin hemodialisa">
              {d.sensor.anomali.length > 0 && (
                <ul className="mb-3 space-y-1 text-sm text-oranye">
                  {d.sensor.anomali.slice(0, 5).map((a, i) => (
                    <li key={i}>⚠ {tanggal(a.waktu)}: {a.keterangan}</li>
                  ))}
                </ul>
              )}
              <GridSensor dataset={dataset} perangkat={d.sensor.perangkat} status={d.sensor.status_harian} anomali={d.sensor.anomali} />
            </Kartu>
          )}
        </div>

        <div className="space-y-5">
          <Kartu judul="Ringkasan">
            <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-abu">Ringkasan otomatis (template)</p>
            <ul className="space-y-2 text-sm">
              {ringkasanTemplate(d).map((k_, i) => <li key={i}>{k_}</li>)}
            </ul>
            <div className="mt-4 rounded-md border border-dashed border-garis p-3 text-sm text-abu">
              Ringkasan AI dengan kutipan regulasi bersumber akan tampil di sini (tahap berikutnya).
            </div>
          </Kartu>

          <Kartu judul="Keputusan petugas">
            <PanelKeputusan dataset={dataset} rsId={d.rumah_sakit.id} periode={d.periode} />
            {d.keputusan.length > 0 && (
              <div className="mt-4 border-t border-garis pt-3">
                <h3 className="text-sm font-semibold text-navy">Keputusan sebelumnya</h3>
                <ul className="mt-2 space-y-2 text-sm">
                  {[...d.keputusan].reverse().map((kp) => (
                    <li key={kp.id} className="rounded-md bg-background px-3 py-2">
                      <strong>{LABEL_KEPUTUSAN[kp.keputusan] ?? kp.keputusan}</strong> oleh {kp.petugas}, {waktuWIB(kp.waktu)}
                      <span className="block text-abu">{kp.alasan}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </Kartu>
          <CatatanTetap />
        </div>
      </div>
    </div>
  );
}
