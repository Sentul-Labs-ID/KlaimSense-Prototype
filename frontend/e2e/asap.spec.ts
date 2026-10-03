import { expect, test, type Page } from "@playwright/test";

// Uji asap: beranda -> detail RS -> audit, tanpa galat di konsol maupun di halaman.
function pantauGalat(page: Page): string[] {
  const galat: string[] = [];
  page.on("pageerror", (e) => galat.push(`pageerror: ${e.message}`));
  page.on("console", (m) => {
    if (m.type() === "error") galat.push(`console: ${m.text()}`);
  });
  page.on("response", (r) => {
    if (r.status() >= 500) galat.push(`HTTP ${r.status()}: ${r.url()}`);
  });
  return galat;
}

test("beranda, detail RS, dan audit tampil tanpa galat", async ({ page }) => {
  const galat = pantauGalat(page);

  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Daftar periksa" })).toBeVisible();
  await expect(page.getByText("Tagihan yang diperiksa")).toBeVisible();
  await expect(page.getByText("Data belum dapat ditampilkan")).toHaveCount(0);

  await page.locator("tbody a").first().click();
  await expect(page.getByRole("heading", { name: "Rincian skor" })).toBeVisible();
  await expect(page.getByText("Ringkasan otomatis (template)")).toBeVisible();
  await expect(page.getByText("Skor adalah prioritas pemeriksaan, bukan penetapan kecurangan.").first()).toBeVisible();

  await page.goto("/audit");
  await expect(page.getByRole("heading", { name: "Audit keputusan" })).toBeVisible();
  await expect(page.getByText(/Rantai keputusan (utuh|rusak)/)).toBeVisible();
  await expect(page.getByRole("columnheader", { name: "Waktu (WIB)" })).toBeVisible();

  expect(galat).toEqual([]);
});
