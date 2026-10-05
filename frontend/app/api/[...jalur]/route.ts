// Proksi tipis dari peramban ke backend untuk aksi yang dipicu pengguna.
// Hanya jalur yang tercantum di bawah yang diteruskan.
import { BACKEND_URL } from "@/lib/api";

const JALUR_POST = new Set(["keputusan", "sensor/verifikasi", "demo/sisipkan"]);

export async function POST(request: Request, { params }: RouteContext<"/api/[...jalur]">) {
  const jalur = (await params).jalur.join("/");
  if (!JALUR_POST.has(jalur)) {
    return Response.json({ detail: "Alamat tidak ditemukan." }, { status: 404 });
  }
  try {
    const respons = await fetch(`${BACKEND_URL}/${jalur}`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: await request.text(),
      cache: "no-store",
      signal: AbortSignal.timeout(120000),
    });
    return new Response(await respons.text(), {
      status: respons.status,
      headers: { "content-type": respons.headers.get("content-type") ?? "application/json" },
    });
  } catch {
    return Response.json({ detail: "Tidak dapat terhubung ke server KlaimSense." }, { status: 502 });
  }
}
