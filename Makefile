COMPOSE ?= docker compose
SERVICE ?= sionna

.PHONY: build up down shell jupyter test estudo receipt clean logs

build:
	$(COMPOSE) build $(SERVICE)

up:
	$(COMPOSE) up -d $(SERVICE)

down:
	$(COMPOSE) down

shell:
	$(COMPOSE) exec $(SERVICE) bash

jupyter:
	$(COMPOSE) exec $(SERVICE) jupyter lab --ip=0.0.0.0 --port=8888 --no-browser --allow-root

test:
	@docker compose ps -q $(SERVICE) | grep -q . || $(COMPOSE) up -d $(SERVICE)
	$(COMPOSE) exec $(SERVICE) python -m pytest tests/ -v

# Uma única entrada canônica: gera o estudo pareado completo sem/com path loss,
# o CSV por seed, o resumo de todas as métricas e o receipt correspondente.
estudo:
	@docker compose ps -q $(SERVICE) | grep -q . || $(COMPOSE) up -d $(SERVICE)
	$(COMPOSE) exec $(SERVICE) python scripts/estudo_consolidado.py --seeds 50
	$(COMPOSE) exec $(SERVICE) python scripts/write_manifest.py

receipt:
	$(COMPOSE) exec $(SERVICE) python scripts/write_manifest.py

logs:
	$(COMPOSE) logs -f $(SERVICE)

clean:
	$(COMPOSE) down -v --rmi local
