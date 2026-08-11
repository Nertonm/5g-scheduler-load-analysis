# Ambiente Sionna para simulação de schedulers 5G NR 

FROM python:3.11-slim

# DEBIAN_FRONTEND=noninteractive: evita prompts interativos do apt.
# PYTHONUNBUFFERED=1: stdout do Python sai na hora (logs de simulação longa).
# PIP_NO_CACHE_DIR=1: não guarda cache de wheel (imagem menor).
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Dependências de sistema necessárias para compilar extensões do Sionna e
# das bibliotecas científicas (numpy/scipy/matplotlib baixam wheels, mas
# algumas deps compilam da fonte).
RUN apt-get update && apt-get install -y --no-install-recommends \
        git make \
        build-essential \
        libgomp1 libgfortran5 \
    && rm -rf /var/lib/apt/lists/*

# WORKDIR /workspace: diretório de trabalho do container; o compose monta o
# código do projeto aqui (volume .:/workspace), então edições no host aparecem
# imediatamente no container sem rebuild.
WORKDIR /workspace

# COPY requirements.txt primeiro (antes do código): o Docker cacheia camadas
# por conteúdo. Se só o código mudar, esta camada (pip install) é reutilizada
# e o build não reinstala dependências (build rápido em iterações).
COPY requirements.txt /workspace/requirements.txt

# venv isolado em /opt/venv: separa as deps do projeto do Python do sistema,
# evitando conflitos com pacotes da imagem base.
RUN python3.11 -m venv /opt/venv \
    && . /opt/venv/bin/activate \
    && pip install --upgrade pip \
    && pip install -r /workspace/requirements.txt

# PATH aponta para o venv primeiro: qualquer comando python/pip/jupyter
# executa do ambiente do projeto por padrão.
ENV PATH="/opt/venv/bin:$PATH"

# Código-fonte montado via volume (ver docker-compose.yml); este COPY é o
# fallback para builds standalone (sem volume), não o caminho de edição.
COPY . /workspace

# Comando padrão: bash interativo (make shell). O compose sobrepõe se preciso.
CMD ["bash"]
