FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Struktur di dalam container mengikuti repo: /repo/backend dan /repo/config
# (config di-mount dari docker-compose), sehingga path relatif sama dengan lokal.
WORKDIR /repo/backend

# Dependensi dipasang dulu (layer di-cache selama pyproject.toml tidak berubah),
# baru kemudian kode sumber disalin.
COPY pyproject.toml ./
RUN mkdir -p sentinel && touch sentinel/__init__.py && pip install -e ".[dev]"

COPY sentinel ./sentinel
COPY tests ./tests

EXPOSE 8000
CMD ["uvicorn", "sentinel.main:app", "--host", "0.0.0.0", "--port", "8000"]
