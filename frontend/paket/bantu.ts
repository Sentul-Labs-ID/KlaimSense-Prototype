// Bantuan bersama untuk tangkapan layar dan video demo.
import path from "node:path";
import type { APIRequestContext, Page } from "@playwright/test";

export const ASSETS = path.resolve(__dirname, "../../assets");
export const REPORTS = path.resolve(__dirname, "../../reports");
export const API = process.env.API_URL ?? "http://localhost:8000";

type Baris = {
  rs_id: string;
  periode: string;
  skor: number;
  prioritas: string;
  nama_samaran: string;
  punya_sensor: boolean;
  temuan_per_aturan: Record<string, number>;
};

async function daftar(request: APIRequestContext, query: string): Promise<Baris[]> {
  const r = await request.get(`${API}/rs?dataset=demo&${query}`);
  return (await r.json()).data as Baris[];
}

/** RS prioritas rendah di Agustus 2026, skor < 5, belum ada temuan KAP-01: sisipan KAP 3 hari
 * akan menaikkannya ke "tinggi" murni karena lantai bukti fisik. */
export async function rsTargetDemo(request: APIRequestContext): Promise<Baris> {
  const rendah = await daftar(request, "periode=2026-08&prioritas=rendah");
  const target = rendah.find((b) => b.skor < 5 && !("KAP-01" in b.temuan_per_aturan));
  if (!target) throw new Error("Tidak ada RS prioritas rendah yang cocok di dataset demo.");
  return target;
}

/** RS prioritas tinggi yang punya temuan kapasitas (KAP-01/KAP-02) dan SEN-01 (bersensor). */
export async function rsTinggiKapasitasSensor(request: APIRequestContext): Promise<Baris> {
  const tinggi = await daftar(request, "prioritas=tinggi");
  const rs = tinggi.find(
    (b) => ("KAP-01" in b.temuan_per_aturan || "KAP-02" in b.temuan_per_aturan) && "SEN-01" in b.temuan_per_aturan,
  );
  if (!rs) throw new Error("Tidak ada RS prioritas tinggi dengan temuan kapasitas dan sensor.");
  return rs;
}

/** Gulir halaman sehingga elemen berada dekat bagian atas layar. */
export async function gulirKe(page: Page, selector: string, jarak = 90): Promise<void> {
  const kotak = await page.locator(selector).first().boundingBox();
  const sekarang = await page.evaluate(() => window.scrollY);
  if (kotak) await page.evaluate((y) => window.scrollTo({ top: y, behavior: "instant" }), sekarang + kotak.y - jarak);
}

export const ALASAN_KLARIFIKASI =
  "Mohon penjelasan jumlah sesi fisioterapi yang melebihi kapasitas terapis selama tiga hari.";
