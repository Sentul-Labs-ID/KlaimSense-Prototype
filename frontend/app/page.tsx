import { connection } from "next/server";

// Dipanggil dari server Next.js. Di docker-compose BACKEND_URL=http://backend:8000;
// di luar Docker default ke http://localhost:8000.
const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

type StatusBackend =
  | { terhubung: true; versi: string }
  | { terhubung: false; galat: string };

async function cekBackend(): Promise<StatusBackend> {
  try {
    const respons = await fetch(`${BACKEND_URL}/health`, {
      cache: "no-store",
      signal: AbortSignal.timeout(3000),
    });
    if (!respons.ok) {
      return { terhubung: false, galat: `HTTP ${respons.status}` };
    }
    const data: { status: string; versi: string } = await respons.json();
    if (data.status !== "ok") {
      return { terhubung: false, galat: `status ${data.status}` };
    }
    return { terhubung: true, versi: data.versi };
  } catch (e) {
    return { terhubung: false, galat: e instanceof Error ? e.message : String(e) };
  }
}

export default async function Beranda() {
  await connection(); // status dicek per permintaan, bukan saat build
  const status = await cekBackend();

  return (
    <main className="flex flex-1 items-center justify-center bg-zinc-50 px-6 py-24">
      <div className="w-full max-w-2xl rounded-2xl bg-white p-10 shadow-sm ring-1 ring-zinc-200">
        <h1 className="text-4xl font-semibold tracking-tight text-zinc-900">JKN-Sentinel</h1>
        <p className="mt-3 text-lg text-zinc-600">
          Setiap klaim harus mungkin terjadi dan wajar tagihannya
        </p>

        <div className="mt-8 flex items-center gap-3 rounded-lg bg-zinc-50 px-4 py-3 text-sm">
          <span
            aria-hidden
            className={`h-2.5 w-2.5 rounded-full ${status.terhubung ? "bg-emerald-500" : "bg-red-500"}`}
          />
          <span className="text-zinc-700">Status backend:</span>
          {status.terhubung ? (
            <span data-testid="status-backend" className="font-medium text-emerald-700">
              terhubung (versi {status.versi})
            </span>
          ) : (
            <span data-testid="status-backend" className="font-medium text-red-700">
              tidak terhubung ({status.galat})
            </span>
          )}
        </div>

        <p className="mt-8 text-xs text-zinc-500">
          Prototipe untuk proposal BPJS Kesehatan Healthkathon 2026. Seluruh data adalah data tiruan.
        </p>
      </div>
    </main>
  );
}
