import { PanelDemo } from "@/components/PanelDemo";
import { KotakGalat } from "@/components/ui";
import { ambil, GalatBackend, type DaftarRs, type Meta } from "@/lib/api";

export default async function HalamanDemo() {
  let meta: Meta, daftar: DaftarRs;
  try {
    [meta, daftar] = await Promise.all([ambil<Meta>("/meta", { dataset: "demo" }), ambil<DaftarRs>("/rs", { dataset: "demo" })]);
  } catch (e) {
    return <KotakGalat pesan={e instanceof GalatBackend ? e.message : "Terjadi galat yang tidak terduga."} />;
  }
  if (!meta.mode_demo) {
    return <KotakGalat pesan="Panel demo hanya tersedia bila mode demo dinyalakan (DEMO_MODE=true)." />;
  }
  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-3xl font-bold text-navy">Panel demo</h1>
        <p className="mt-1 text-abu">
          Sisipkan tagihan bermasalah ke dataset demo, lalu lihat bagaimana skor dan prioritas berubah. Dataset utama tidak tersentuh;
          jalankan <code>make demo-reset</code> untuk mengembalikan dataset demo ke keadaan awal.
        </p>
      </div>
      <PanelDemo baris={daftar.data} periode={meta.periode} />
    </div>
  );
}
