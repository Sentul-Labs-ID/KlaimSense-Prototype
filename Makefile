# JKN-Sentinel — perintah utama.
# Resep ditulis sederhana agar jalan di shell Unix maupun Windows.

COMPOSE = docker compose

.PHONY: up down reset-db test generate rules sensor eval demo

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
	$(COMPOSE) run --rm --no-deps backend python -m pytest

generate:
	@echo Belum tersedia: diimplementasikan di fase 1

rules:
	@echo Belum tersedia: diimplementasikan di fase 2

sensor:
	@echo Belum tersedia: diimplementasikan di fase 3

eval:
	@echo Belum tersedia: diimplementasikan di fase 4

demo:
	@echo Belum tersedia: diimplementasikan di fase 7
