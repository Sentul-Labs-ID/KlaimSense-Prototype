"""Aplikasi FastAPI JKN-Sentinel."""

from fastapi import FastAPI

from sentinel import __version__

app = FastAPI(
    title="JKN-Sentinel",
    version=__version__,
    description="Prototype pemeriksaan klaim rumah sakit. Seluruh data adalah data tiruan.",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "versi": __version__}
