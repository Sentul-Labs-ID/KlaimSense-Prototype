// Video demo 1920x1080 dengan keterangan di layar (bahasa Indonesia). Jalankan lewat `make rekam-demo`.
// Hasil: assets/demo.webm, dan assets/demo_waktu.json (detik mulai tiap langkah, untuk naskah).
import fs from "node:fs";
import path from "node:path";
import { expect, test, type Page } from "@playwright/test";
import { ALASAN_KLARIFIKASI, ASSETS, gulirKe, rsTargetDemo, rsTinggiKapasitasSensor } from "./bantu";

async function keterangan(page: Page, teks: string) {
  await page.evaluate((t) => {
    let el = document.getElementById("keterangan-demo");
    if (!el) {
      el = document.createElement("div");
      el.id = "keterangan-demo";
      Object.assign(el.style, {
        position: "fixed", left: "50%", bottom: "48px", transform: "translateX(-50%)", zIndex: "9999",
        background: "rgba(14, 42, 71, 0.94)", color: "#ffffff", padding: "16px 32px", borderRadius: "14px",
        fontSize: "28px", fontWeight: "600", lineHeight: "1.35", maxWidth: "1500px", textAlign: "center",
        boxShadow: "0 8px 30px rgba(0,0,0,0.25)", fontFamily: "system-ui, 'Segoe UI', Roboto, sans-serif",
      });
      document.body.appendChild(el);
    }
    el.textContent = t;
  }, teks);
}

async function gulirHalus(page: Page, ke: number, langkah = 12) {
  const dari = await page.evaluate(() => window.scrollY);
  for (let i = 1; i <= langkah; i++) {
    await page.evaluate((y) => window.scrollTo({ top: y, behavior: "instant" }), dari + ((ke - dari) * i) / langkah);
    await page.waitForTimeout(60);
  }
}

test("rekam video demo", async ({ browser, request }) => {
  fs.mkdirSync(ASSETS, { recursive: true });
  const target = await rsTargetDemo(request);
  const bersensor = await rsTinggiKapasitasSensor(request);
  const dirVideo = path.join(__dirname, "../test-results/video-demo");
  const konteks = await browser.newContext({
    baseURL: "http://localhost:3000",
    viewport: { width: 1920, height: 1080 },
    recordVideo: { dir: dirVideo, size: { width: 1920, height: 1080 } },
    locale: "id-ID",
    timezoneId: "Asia/Jakarta",
  });
  const page = await konteks.newPage();
  const mulai = Date.now();
  const waktu: { detik: number; langkah: string; keterangan: string }[] = [];
  async function langkah(nama: string, teks: string) {
    waktu.push({ detik: Math.round((Date.now() - mulai) / 100) / 10, langkah: nama, keterangan: teks });
    await keterangan(page, teks);
  }

  // 1. Daftar periksa
  await page.goto("/?dataset=demo");
  await expect(page.getByRole("heading", { name: "Daftar periksa" })).toBeVisible();
  await langkah("daftar-periksa", "Daftar periksa: semua tagihan tiruan sudah dihitung otomatis dan diurutkan dari prioritas tertinggi.");
  await page.waitForTimeout(6500);
  await gulirHalus(page, 420);
  await page.waitForTimeout(3000);

  // 2. RS prioritas rendah
  await page.goto(`/rs/${target.rs_id}?dataset=demo&periode=2026-08`);
  await expect(page.getByRole("heading", { name: "Rincian skor" })).toBeVisible();
  await langkah("rs-rendah", `${target.nama_samaran}, Agustus 2026: prioritas rendah, belum ada temuan kapasitas fisioterapi.`);
  await page.waitForTimeout(7000);

  // 3. Panel demo: sisipkan KAP_FISIO 3 hari
  await page.goto("/demo");
  await langkah("panel-demo", "Panel demo: kita sisipkan tagihan fisioterapi fiktif yang melebihi kapasitas terapis selama 3 hari.");
  await page.waitForTimeout(2500);
  await page.locator("select").nth(0).selectOption("2026-08");
  await page.waitForTimeout(800);
  await page.locator("select").nth(1).selectOption(target.rs_id);
  await page.waitForTimeout(800);
  await page.locator("select").nth(2).selectOption("KAP_FISIO");
  await page.waitForTimeout(800);
  await page.locator('input[type="range"]').fill("3");
  await page.waitForTimeout(1500);
  await page.getByRole("button", { name: "Sisipkan kecurangan" }).click();
  await expect(page.getByText("Sesudah")).toBeVisible({ timeout: 90_000 });
  await langkah("prioritas-naik", "Skor dihitung ulang: prioritas naik dari rendah menjadi tinggi karena bukti fisik berulang.");
  await page.waitForTimeout(8000);

  // 4. Detail RS: temuan, grafik, alasan prioritas
  await page.getByRole("link", { name: /Lihat detail rumah sakit/ }).click();
  await expect(page.getByRole("heading", { name: "Rincian skor" })).toBeVisible();
  await langkah("detail-rs", "Detail rumah sakit: alasan prioritas dan temuan, dengan penjelasan yang bisa dibaca siapa pun.");
  await page.waitForTimeout(6000);
  const posGrafik = await page.getByRole("heading", { name: "Sesi harian dibanding kapasitas" }).boundingBox();
  await gulirHalus(page, (posGrafik?.y ?? 900) - 90);
  await langkah("grafik", "Grafik harian: pada hari bertanda oranye, sesi yang ditagih melampaui garis kapasitas.");
  await page.waitForTimeout(7000);

  // 5. Grid sensor dan verifikasi tanda tangan pada RS bersensor
  await page.goto(`/rs/${bersensor.rs_id}?dataset=demo&periode=${bersensor.periode}`);
  await expect(page.getByRole("heading", { name: "Rincian skor" })).toBeVisible();
  await gulirKe(page, "text=Sensor mesin hemodialisa");
  await langkah("sensor", `Sensor di mesin cuci darah ${bersensor.nama_samaran}: hijau berarti mesin benar-benar menjalankan terapi.`);
  await page.waitForTimeout(6000);
  await page.getByRole("button", { name: "Verifikasi tanda tangan" }).first().click();
  await expect(page.getByText(/pesan bertanda tangan sah|gagal verifikasi/).first()).toBeVisible({ timeout: 30_000 });
  await langkah("verifikasi", "Setiap pesan sensor bertanda tangan digital dan berantai: data mesin tidak bisa dipalsukan diam-diam.");
  await page.waitForTimeout(7000);

  // 6. Keputusan "Minta klarifikasi"
  await page.goto(`/rs/${target.rs_id}?dataset=demo&periode=2026-08`);
  await expect(page.getByRole("heading", { name: "Rincian skor" })).toBeVisible();
  await langkah("keputusan", "Keputusan tetap di tangan petugas: minta klarifikasi kepada rumah sakit, dengan alasan tertulis.");
  await page.locator("textarea").pressSequentially(ALASAN_KLARIFIKASI, { delay: 18 });
  await page.getByPlaceholder("Nama verifikator").pressSequentially("Verifikator Demo", { delay: 30 });
  await page.waitForTimeout(800);
  await page.getByRole("button", { name: "Minta klarifikasi" }).click();
  await expect(page.getByText("tercatat dan dirantai")).toBeVisible();
  await page.waitForTimeout(4000);

  // 7. Audit
  await page.goto("/audit?dataset=demo");
  await expect(page.getByText("Rantai keputusan utuh")).toBeVisible();
  await langkah("audit", "Audit: setiap keputusan dirantai hash. Rantai utuh berarti tidak ada catatan yang diubah diam-diam.");
  await page.waitForTimeout(7000);
  await langkah("penutup", "Skor adalah prioritas pemeriksaan, bukan penetapan kecurangan. Keputusan selalu di tangan petugas.");
  await page.waitForTimeout(6000);

  const durasi = Math.round((Date.now() - mulai) / 100) / 10;
  const video = page.video();
  await konteks.close();
  fs.copyFileSync(await video!.path(), path.join(ASSETS, "demo.webm"));
  fs.writeFileSync(path.join(ASSETS, "demo_waktu.json"), JSON.stringify({ durasi_detik: durasi, langkah: waktu }, null, 2) + "\n");
  console.log(`Video: assets/demo.webm, durasi ±${durasi} detik`);
  expect(durasi).toBeGreaterThanOrEqual(75);
  expect(durasi).toBeLessThanOrEqual(100);
});
