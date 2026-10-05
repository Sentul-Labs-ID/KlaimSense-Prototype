// Akses backend dari sisi server Next.js. Di docker-compose BACKEND_URL=http://backend:8000;
// di luar Docker default ke http://localhost:8000.
export const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

export type Prioritas = "tinggi" | "sedang" | "rendah";
export type Dataset = "demo" | "utama";

export type Meta = {
  dataset: Dataset;
  dataset_tersedia: Dataset[];
  dataset_dapat_diubah: boolean;
  periode: string[];
  rumah_sakit: { id: string; nama_samaran: string; kelas: string; provinsi: string }[];
  mode_demo: boolean;
};

export type BarisRs = {
  rs_id: string;
  periode: string;
  skor: number;
  prioritas: Prioritas;
  alasan_prioritas: string;
  nama_samaran: string;
  kelas: string;
  provinsi: string;
  punya_sensor: boolean;
  temuan_per_aturan: Record<string, number>;
  jumlah_temuan: number;
};

export type DaftarRs = {
  dataset: Dataset;
  periode: string | null;
  ringkasan: {
    jumlah_rs_periode: number;
    per_prioritas: Record<Prioritas, number>;
    jumlah_tagihan_diperiksa: number;
  };
  data: BarisRs[];
};

export type RincianAturan = {
  bobot: number;
  keparahan: number;
  kontribusi: number;
  jumlah_temuan?: number;
  titik_jenuh?: number;
  selisih?: { jumlah_temuan: number; titik_jenuh: number; keparahan: number };
  integritas?: { jumlah_temuan: number; titik_jenuh: number; keparahan: number };
  per_layanan?: Record<string, { utilisasi: number; z: number | null; kelompok: string | null; jumlah_pembanding: number }>;
};

export type Temuan = {
  id: number;
  aturan_id: string;
  kategori: string | null;
  tanggal: string | null;
  layanan: string;
  nilai_teramati: number;
  batas: number;
  selisih: number;
  penjelasan: string;
  jumlah_tagihan: number;
};

export type Harian = {
  tanggal: string;
  fisioterapi: number;
  kapasitas_fisioterapi: number;
  hemodialisa: number;
  kapasitas_hemodialisa: number;
  aturan_temuan: string[];
};

export type StatusHarian = {
  mesin_id: string;
  tanggal: string;
  shift: number;
  menit_terapi: number;
  menit_standby: number;
  menit_mati: number;
  menit_tanpa_data: number;
};

export type Keputusan = {
  id: number;
  keputusan: string;
  alasan: string;
  petugas: string;
  waktu: string;
  hash: string;
};

export type DetailRs = {
  dataset: Dataset;
  rumah_sakit: { id: string; nama_samaran: string; kelas: string; provinsi: string; kab_kota: string; punya_sensor: boolean };
  kapasitas: {
    jumlah_fisioterapis: number;
    sesi_per_terapis: number;
    kapasitas_fisioterapi_harian: number;
    jumlah_mesin_hd: number;
    shift_hd_per_hari: number;
    kapasitas_hemodialisa_harian: number;
    hari_operasional_hd: number;
    durasi_sesi_hd_jam: number;
  };
  periode: string;
  periode_tersedia: { periode: string; skor: number; prioritas: Prioritas }[];
  skor: {
    skor: number;
    prioritas: Prioritas;
    alasan_prioritas: string;
    rincian_per_aturan: Record<string, RincianAturan>;
    versi_aturan: string;
    hash_parameter: string;
  };
  temuan: Temuan[];
  harian: Harian[];
  sensor: {
    bersensor: boolean;
    perangkat: { device_id: string; mesin_id: string }[];
    status_harian: StatusHarian[];
    anomali: { jenis: string; device_id: string; waktu: string; durasi_menit: number | null; keterangan: string }[];
  };
  keputusan: Keputusan[];
};

export type Audit = {
  dataset: Dataset;
  rantai: { status: "utuh" | "rusak"; entri_rusak: number | null; keterangan: string };
  entri: (Keputusan & { rs_id: string; nama_samaran?: string; periode: string; label_keputusan: string; prev_hash: string })[];
};

export class GalatBackend extends Error {}

export async function ambil<T>(jalur: string, params: Record<string, string | undefined> = {}): Promise<T> {
  const query = new URLSearchParams(Object.entries(params).filter(([, v]) => v) as [string, string][]);
  const url = `${BACKEND_URL}${jalur}${query.size ? `?${query}` : ""}`;
  let respons: Response;
  try {
    respons = await fetch(url, { cache: "no-store", signal: AbortSignal.timeout(15000) });
  } catch {
    throw new GalatBackend("Tidak dapat terhubung ke server KlaimSense. Pastikan layanan backend berjalan.");
  }
  if (!respons.ok) {
    const isi = await respons.json().catch(() => ({}));
    throw new GalatBackend(typeof isi.detail === "string" ? isi.detail : `Server mengembalikan galat ${respons.status}.`);
  }
  return respons.json() as Promise<T>;
}

export function datasetDari(nilai: string | string[] | undefined): Dataset {
  return nilai === "utama" ? "utama" : "demo";
}
