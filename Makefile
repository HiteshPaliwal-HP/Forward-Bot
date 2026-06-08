.PHONY: build run auth

build:
	docker build -t forward-bot:latest .

run:
	docker compose up -d

auth:
	docker compose exec app uv run python -m forward_bot.auth
