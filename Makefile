# Makefile: Ambiente Sionna
#
# Interface única para as operações do ambiente. Cada alvo encapsula o comando
# docker compose equivalente, para que ninguém precise lembrar a sintaxe do
# compose. O serviço padrão é 'sionna' 
#
# Uso comum:
#   make build    # 1a vez: constrói a imagem 
#   make up       # sobe o container em background
#   make shell    # entra no bash do container
#   make test     # roda pytest (smoke tests)
#   make jupyter  # sobe Jupyter Lab em http://localhost:8888

COMPOSE ?= docker compose
SERVICE ?= sionna

.PHONY: build up down shell jupyter test clean logs

## build: constrói a imagem Docker com Sionna e dependências
# O build é cacheado por camada: mudar só o código não reinstala dependências.
build:
	$(COMPOSE) build $(SERVICE)

## up: sobe o container (CPU por padrão; GPU exige toolkit + descomentar compose)
up:
	$(COMPOSE) up -d $(SERVICE)

## down: derruba o container (mantém a imagem e os volumes)
down:
	$(COMPOSE) down

## shell: entra no bash do container (para rodar simulações manualmente)
shell:
	$(COMPOSE) exec $(SERVICE) bash

## jupyter: sobe o Jupyter Lab na porta 8888
# --ip=0.0.0.0: escuta fora do container (necessário para o port mapping).
# --no-browser: o container não tem browser; o host acessa localhost:8888.
# --allow-root: o container roda como root; sem isso o Jupyter recusa.
jupyter:
	$(COMPOSE) exec $(SERVICE) jupyter lab --ip=0.0.0.0 --port=8888 --no-browser --allow-root

## test: roda os testes do projeto dentro do container
# Executa pytest com o código montado por volume (não a cópia da imagem).
test:
	$(COMPOSE) exec $(SERVICE) python -m pytest tests/ -v

## logs: acompanha os logs do container
logs:
	$(COMPOSE) logs -f $(SERVICE)

## clean: remove containers, volumes e imagens locais
# CUIDADO: `--rmi local` apaga as imagens construídas; o próximo build refaz
# tudo do zero (demorado). Use só quando quiser zerar o ambiente.
clean:
	$(COMPOSE) down -v --rmi local
