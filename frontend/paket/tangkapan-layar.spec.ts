// Tangkapan layar 1920x1080 untuk proposal. Jalankan lewat `make tangkapan-layar`.
import fs from "node:fs";
import path from "node:path";
import { expect, test } from "@playwright/test";
import { ALASAN_KLARIFIKASI, ASSETS, gulirKe, REPORTS, rsTargetDemo, rsTinggiKapasitasSensor } from "./bantu";

test("tangkapan layar proposal", async ({ page, request }) => {
  fs.mkdirSync(ASSETS, { recursive: true });
  const simpan = (nama: string) => path.join(ASSETS, nama);

  // 01 Daftar periksa
  await page.goto("/?dataset=demo");
  await expect(page.getByRole("heading", { name: "Daftar periksa" })).toBeVisible();
  await page.screenshot({ path: simpan("01_daftar-periksa.png") });

  // 02 Detail RS prioritas tinggi dengan temuan kapasitas dan sensor.
  const rs = await rsTinggiKapasitasSensor(request);
  await page.goto(`/rs/${rs.rs_id}?dataset=demo&periode=${rs.periode}`);
  await expect(page.getByRole("heading", { name: "Rincian skor" })).toBeVisible();
  // 02 penuh (untuk README): dari atas halaman sampai kartu grafik harian, lebar 1920.
  const grafik = await page.getByRole("heading", { name: "Sesi harian dibanding kapasitas" }).locator("xpath=ancestor::section").boundingBox();
  await page.screenshot({
    path: simpan("02_detail-rs-penuh.png"),
    fullPage: true,
    clip: { x: 0, y: 0, width: 1920, height: Math.ceil((grafik?.y ?? 1000) + (grafik?.height ?? 600) + 24) },
  });
  // 02 (1920x1080): kartu skor, alasan prioritas, dan daftar temuan.
  await gulirKe(page, "h2:has-text('Rincian skor')", 40);
  await page.screenshot({ path: simpan("02_detail-rs.png") });
  // 02b (1920x1080): kartu grafik harian sesi vs kapasitas dengan hari temuan ditandai.
  await gulirKe(page, "h2:has-text('Sesi harian dibanding kapasitas')", 40);
  await page.screenshot({ path: simpan("02b_grafik-harian.png") });

  // 03 Grid sensor dengan hasil verifikasi tanda tangan.
  await gulirKe(page, "text=Sensor mesin hemodialisa");
  await page.getByRole("button", { name: "Verifikasi tanda tangan" }).first().click();
  await expect(page.getByText(/pesan bertanda tangan sah|gagal verifikasi/).first()).toBeVisible({ timeout: 30_000 });
  await gulirKe(page, "text=Sensor mesin hemodialisa");
  await page.screenshot({ path: simpan("03_grid-sensor.png") });

  // 04 Panel demo: sisipkan KAP_FISIO 3 hari, skor dan prioritas sebelum/sesudah.
  const target = await rsTargetDemo(request);
  await page.goto("/demo");
  await page.locator("select").nth(0).selectOption("2026-08");
  await page.locator("select").nth(1).selectOption(target.rs_id);
  await page.locator("select").nth(2).selectOption("KAP_FISIO");
  await page.locator('input[type="range"]').fill("3");
  await page.getByRole("button", { name: "Sisipkan kecurangan" }).click();
  await expect(page.getByText("Sesudah")).toBeVisible({ timeout: 90_000 });
  await page.screenshot({ path: simpan("04_demo-sebelum-sesudah.png") });

  // 05 Keputusan "Minta klarifikasi" tercatat.
  await page.getByRole("link", { name: /Lihat detail rumah sakit/ }).click();
  await expect(page.getByRole("heading", { name: "Rincian skor" })).toBeVisible();
  await page.locator("textarea").fill(ALASAN_KLARIFIKASI);
  await page.getByPlaceholder("Nama verifikator").fill("Verifikator Demo");
  await page.getByRole("button", { name: "Minta klarifikasi" }).click();
  await expect(page.getByText("tercatat dan dirantai")).toBeVisible();
  await expect(page.getByText("Keputusan sebelumnya")).toBeVisible();
  await page.screenshot({ path: simpan("05_keputusan.png") });

  // 06 Audit dengan rantai utuh dan waktu WIB.
  await page.goto("/audit?dataset=demo");
  await expect(page.getByText("Rantai keputusan utuh")).toBeVisible();
  await expect(page.getByText(/WIB/).first()).toBeVisible();
  await page.screenshot({ path: simpan("06_audit.png") });

  // Grafik evaluasi (hanya disalin; reports/ tidak diubah).
  for (const nama of ["recall_per_skenario.png", "prioritas_hidden.png"]) {
    fs.copyFileSync(path.join(REPORTS, nama), simpan(nama));
  }
});
