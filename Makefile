# JKN-Sentinel — perintah utama.
# Resep ditulis sederhana agar jalan di shell Unix maupun Windows.

COMPOSE = docker compose

.PHONY: up down reset-db test generate rules sensor eval demo demo-reset e2e

## Bangun dan jalankan db, backend (port 8000), frontend (port 3000).
up:
	$(COMPOSE) up -d --build --wait

## Hentikan semua layanan (data database tetap tersimpan di volume).
down:
	$(COMPOSE) down

## Hapus volume database lalu nyalakan ulang database kosong.
reset-db:
	$(COMPOSE) rm -s -f db
	docker volume rm -f jkn-sentinel_pgdata
	$(COMPOSE) up -d --wait db

## Jalankan seluruh tes pytest backend di dalam container.
test:
	$(COMPOSE) build backend
	$(COMPOSE) run --rm --no-deps -v ./frontend:/repo/frontend:ro backend python -m pytest

## Bangkitkan dataset utama (seed 42) dan hidden (seed 2026); data lama dataset yang sama diganti.
generate:
	$(COMPOSE) build backend
	$(COMPOSE) run --rm backend python -m sentinel.generator --dataset utama --seed 42 --days 90 --rs 30
	$(COMPOSE) run --rm backend python -m sentinel.generator --hidden

## Jalankan mesin aturan untuk dataset utama dan hidden; cetak 10 RS dengan skor tertinggi.
rules:
	$(COMPOSE) build backend
	$(COMPOSE) run --rm backend python -m sentinel.rules --dataset utama
	$(COMPOSE) run --rm backend python -m sentinel.rules --dataset hidden

## Simulasi sensor (simulator -> edge -> ingest -> ringkasan harian) untuk kedua dataset,
## lalu jalankan ulang mesin aturan agar SEN-01 ikut dihitung.
sensor:
	$(COMPOSE) build backend
	$(COMPOSE) run --rm backend python -m sentinel.sensor --dataset utama
	$(COMPOSE) run --rm backend python -m sentinel.sensor --dataset hidden
	$(MAKE) rules

## Evaluasi akurasi: dataset utama lalu hidden; tulis reports/evaluasi.md, .json, dan grafik.
## Setiap jalan evaluasi hidden tercatat di reports/log_evaluasi_hidden.json.
eval:
	$(COMPOSE) build backend
	$(COMPOSE) run --rm backend python -m sentinel.evaluation

## Bangun ulang dataset demo (kembar utama, seed 42) lengkap dengan sensor, temuan, dan skor.
## Keputusan dan sisipan demo sebelumnya ikut terhapus. Dataset utama dan hidden tidak disentuh.
demo-reset:
	$(COMPOSE) build backend
	$(COMPOSE) run --rm backend sh -c "python -m sentinel.generator --dataset demo --seed 42 --days 90 --rs 30 && python -m sentinel.sensor --dataset demo && python -m sentinel.rules --dataset demo"

## Uji asap Playwright terhadap dashboard yang sedang berjalan (make up).
e2e:
	cd frontend && npx playwright test

demo:
	@echo Belum tersedia: diimplementasikan di fase 7
