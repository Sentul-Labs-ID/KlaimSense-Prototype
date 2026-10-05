"""Aplikasi FastAPI KlaimSense."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from sentinel import __version__
from sentinel.api.dashboard import router as router_dashboard
from sentinel.api.demo import router as router_demo
from sentinel.api.keputusan import router as router_keputusan
from sentinel.api.sensor import router as router_sensor

app = FastAPI(
    title="KlaimSense",
    version=__version__,
    description="Prototype pemeriksaan klaim rumah sakit. Seluruh data adalah data tiruan.",
)

TERJEMAHAN_HTTP = {
    "Not Found": "Alamat tidak ditemukan.",
    "Method Not Allowed": "Metode tidak diizinkan untuk alamat ini.",
    "Internal Server Error": "Terjadi galat di server.",
}


def _pesan_validasi(galat: dict) -> str:
    kolom = ".".join(str(x) for x in galat.get("loc", ()) if x not in ("body", "query", "path"))
    jenis = galat.get("type", "")
    ctx = galat.get("ctx") or {}
    if jenis == "missing":
        teks = "wajib diisi"
    elif jenis == "value_error":
        teks = str(ctx.get("error") or galat.get("msg", "")).removeprefix("Value error, ")
    elif jenis == "literal_error":
        teks = f"nilai tidak dikenal; pilihan: {ctx.get('expected', '')}"
    elif jenis in ("greater_than_equal", "less_than_equal", "greater_than", "less_than"):
        batas = {"greater_than_equal": "minimal", "less_than_equal": "maksimal",
                 "greater_than": "harus lebih dari", "less_than": "harus kurang dari"}[jenis]
        nilai = next(iter(ctx.values()), "")
        teks = f"{batas} {nilai}"
    elif jenis.endswith("_parsing") or jenis.endswith("_type"):
        teks = "format tidak valid"
    else:
        teks = "tidak valid"
    return f"{kolom}: {teks}" if kolom else teks


@app.exception_handler(RequestValidationError)
async def galat_validasi(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": "; ".join(_pesan_validasi(g) for g in exc.errors())})


@app.exception_handler(StarletteHTTPException)
async def galat_http(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    detail = TERJEMAHAN_HTTP.get(exc.detail, exc.detail) if isinstance(exc.detail, str) else exc.detail
    return JSONResponse(status_code=exc.status_code, content={"detail": detail})


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "versi": __version__}


app.include_router(router_sensor)
app.include_router(router_dashboard)
app.include_router(router_keputusan)
app.include_router(router_demo)
