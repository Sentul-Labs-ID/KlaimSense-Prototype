// Teks bahasa Indonesia untuk dashboard: nama aturan sederhana, tanggal, angka.

export const BULAN = [
  "Januari", "Februari", "Maret", "April", "Mei", "Juni",
  "Juli", "Agustus", "September", "Oktober", "November", "Desember",
];
const BULAN_PENDEK = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"];

export const NAMA_ATURAN: Record<string, { judul: string; arti: string }> = {
  "KAP-01": { judul: "Kapasitas fisioterapi", arti: "Sesi fisioterapi sehari melebihi jumlah terapis × sesi wajar per terapis." },
  "KAP-02": { judul: "Kapasitas cuci darah", arti: "Sesi hemodialisa sehari melebihi mesin × shift, atau ada sesi saat unit tutup." },
  "ULG-01": { judul: "Tagihan kembar", arti: "Tagihan yang sama persis dikirim lebih dari sekali." },
  "ULG-02": { judul: "Cuci darah dua kali sehari", arti: "Satu pasien ditagih lebih dari satu sesi hemodialisa di hari yang sama." },
  "WJR-01": { judul: "Harga di atas acuan", arti: "Harga obat atau alat melebihi harga acuan ditambah toleransi." },
  "WJR-02": { judul: "Alat bantu dengar terlalu cepat", arti: "Alat bantu dengar untuk telinga yang sama ditagih sebelum masa penggantian." },
  "BAND-01": { judul: "Jauh di atas RS sejenis", arti: "Utilisasi jauh lebih tinggi daripada rumah sakit sekelas. Sinyal pendukung, bukan bukti." },
  "SEN-01": { judul: "Jam kerja mesin (sensor)", arti: "Jam terapi yang tercatat sensor tidak cukup untuk sesi yang ditagih, atau data sensor tidak utuh." },
};

export const LABEL_PRIORITAS: Record<string, string> = { tinggi: "Tinggi", sedang: "Sedang", rendah: "Rendah" };

export function judulAturan(kode: string): string {
  return NAMA_ATURAN[kode]?.judul ?? kode;
}

export function periode(p: string): string {
  const [tahun, bulan] = p.split("-");
  return `${BULAN[Number(bulan) - 1]} ${tahun}`;
}

export function tanggal(t: string): string {
  const [tahun, bulan, hari] = t.slice(0, 10).split("-");
  return `${Number(hari)} ${BULAN[Number(bulan) - 1]} ${tahun}`;
}

export function tanggalPendek(t: string): string {
  const [, bulan, hari] = t.slice(0, 10).split("-");
  return `${Number(hari)} ${BULAN_PENDEK[Number(bulan) - 1]}`;
}

export function angka(n: number, desimal = 0): string {
  return n.toLocaleString("id-ID", { minimumFractionDigits: desimal, maximumFractionDigits: desimal });
}

/** "lantai: KAP-01 jenuh, SEN-01-selisih jenuh" / "ambang skor ≥ 20" -> kalimat sederhana. */
export function alasanPrioritas(alasan: string): string {
  return alasan
    .split("; ")
    .map((bagian) => {
      if (bagian.startsWith("lantai: ")) {
        const aturan = bagian
          .slice("lantai: ".length)
          .split(", ")
          .map((x) => x.replace(" jenuh", ""))
          .map((x) => (x === "SEN-01-selisih" ? "jam kerja mesin (sensor)" : judulAturan(x).toLowerCase()));
        return `Bukti fisik berulang: ${aturan.join(" dan ")} terlampaui berkali-kali dalam sebulan`;
      }
      if (bagian.startsWith("ambang skor ≥ ")) return `Skor mencapai ambang ${bagian.slice("ambang skor ≥ ".length)}`;
      if (bagian.startsWith("skor di bawah ambang sedang")) return "Skor di bawah ambang pemeriksaan";
      return bagian;
    })
    .join("; ");
}

const FORMAT_WIB = new Intl.DateTimeFormat("id-ID", {
  timeZone: "Asia/Jakarta",
  day: "numeric",
  month: "long",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
});

/** Waktu dari API (UTC, tanpa zona) -> "3 Oktober 2026 13.44 WIB". Penyimpanan dan API tetap UTC. */
export function waktuWIB(iso: string): string {
  const utc = /[zZ]|[+-]\d{2}:?\d{2}$/.test(iso) ? iso : `${iso}Z`;
  const d = new Date(utc);
  if (Number.isNaN(d.getTime())) return iso;
  return `${FORMAT_WIB.format(d).replace(" pukul ", " ")} WIB`;
}
