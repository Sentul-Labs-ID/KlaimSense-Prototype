import type { Metadata } from "next";
import Link from "next/link";
import { connection } from "next/server";
import { ambil, type Meta } from "@/lib/api";
import "./globals.css";

export const metadata: Metadata = {
  title: "JKN-Sentinel",
  description: "Setiap klaim harus mungkin terjadi dan wajar tagihannya",
};

async function modeDemo(): Promise<boolean> {
  try {
    return (await ambil<Meta>("/meta")).mode_demo;
  } catch {
    return false;
  }
}

export default async function RootLayout({ children }: LayoutProps<"/">) {
  await connection();
  const demo = await modeDemo();
  const menu = [
    { href: "/", label: "Daftar periksa" },
    { href: "/audit", label: "Audit keputusan" },
    ...(demo ? [{ href: "/demo", label: "Panel demo" }] : []),
  ];
  return (
    <html lang="id" className="h-full antialiased">
      <body className="flex min-h-full flex-col">
        <header className="bg-navy text-white">
          <div className="mx-auto flex max-w-[1760px] items-center justify-between px-8 py-4">
            <Link href="/" className="flex items-baseline gap-3">
              <span className="text-2xl font-bold tracking-tight">JKN-Sentinel</span>
              <span className="text-sm text-white/70">Setiap klaim harus mungkin terjadi dan wajar tagihannya</span>
            </Link>
            <nav className="flex gap-2">
              {menu.map((m) => (
                <Link key={m.href} href={m.href} className="rounded-md px-4 py-2 text-sm font-medium hover:bg-white/10">
                  {m.label}
                </Link>
              ))}
            </nav>
          </div>
        </header>
        <main className="mx-auto w-full max-w-[1760px] flex-1 px-8 py-6">{children}</main>
        <footer className="border-t border-garis bg-white">
          <div className="mx-auto max-w-[1760px] px-8 py-3 text-xs text-abu">
            Prototipe untuk proposal BPJS Kesehatan Healthkathon 2026 oleh Sentul Labs. Seluruh data adalah data tiruan.
          </div>
        </footer>
      </body>
    </html>
  );
}
