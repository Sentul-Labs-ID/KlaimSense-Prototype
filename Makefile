# JKN-Sentinel — perintah utama.
# Resep ditulis sederhana agar jalan di shell Unix maupun Windows.

COMPOSE = docker compose

.PHONY: up down reset-db test generate rules sensor eval demo demo-reset e2e verifikasi-reproduksi tangkapan-layar rekam-demo

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
	cd frontend && npm install --no-audit --no-fund && npx playwright install chromium && npx playwright test

## Paket demo dari repo bersih (setelah salin .env.example ke .env): build, layanan dengan DEMO_MODE=true,
## data utama dan hidden, sensor, aturan, lalu dataset demo. TIDAK menjalankan evaluasi dan TIDAK menulis ke reports/.
demo: export DEMO_MODE=true
demo:
	$(COMPOSE) up -d --build --wait
	$(COMPOSE) run --rm backend sh -c "python -m sentinel.generator --dataset utama --seed 42 --days 90 --rs 30 && python -m sentinel.generator --hidden && python -m sentinel.sensor --dataset utama && python -m sentinel.sensor --dataset hidden && python -m sentinel.rules --dataset utama && python -m sentinel.rules --dataset hidden"
	$(MAKE) demo-reset
	@echo =====================================================================
	@echo  JKN-Sentinel siap. Buka dashboard: http://localhost:3000
	@echo  Langkah demo singkat:
	@echo   1. Daftar periksa: rumah sakit diurutkan dari prioritas tertinggi.
	@echo   2. Panel demo: pilih RS prioritas rendah, sisipkan fisioterapi melebihi kapasitas 3 hari.
	@echo   3. Prioritas naik menjadi tinggi: buka detail RS, lihat temuan dan grafik.
	@echo   4. Catat keputusan Minta klarifikasi, lalu buka Audit keputusan: rantai utuh.
	@echo  Seluruh data adalah data tiruan. Kembalikan dataset demo dengan: make demo-reset
	@echo =====================================================================

## Pemeriksaan kepercayaan: bangkitkan ulang semua data di basis data terpisah, hitung ulang, dan
## bandingkan dengan reports/evaluasi.json. Hanya menulis reports/verifikasi_reproduksi.json.
verifikasi-reproduksi:
	$(COMPOSE) build backend
	$(COMPOSE) up -d --wait db
	$(COMPOSE) run --rm -e KOMIT=$(shell git describe --always --dirty) backend python -m sentinel.reproduksi

## Tangkapan layar 1920x1080 ke assets/ (dataset demo di-reset dulu agar hasilnya bersih dan dapat diulang).
tangkapan-layar: export DEMO_MODE=true
tangkapan-layar:
	$(COMPOSE) up -d --build --wait
	$(MAKE) demo-reset
	cd frontend && npm install --no-audit --no-fund && npx playwright install chromium && npx playwright test --config playwright.paket.config.ts tangkapan-layar

## Video demo 1920x1080 ke assets/demo.webm (dataset demo di-reset dulu).
rekam-demo: export DEMO_MODE=true
rekam-demo:
	$(COMPOSE) up -d --build --wait
	$(MAKE) demo-reset
	cd frontend && npm install --no-audit --no-fund && npx playwright install chromium && npx playwright test --config playwright.paket.config.ts rekam-demo
