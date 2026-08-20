# Instruções de execução

Este documento descreve o fluxo recomendado para executar os testes, notebooks e estudos de simulação do projeto.

## Pré-requisitos

- Docker Engine instalado e em execução.
- Docker Compose disponível como `docker compose`.
- GNU Make instalado.
- Pelo menos 2 GB de memória compartilhada disponíveis para o container. O `docker-compose.yml` já configura `shm_size: 2g`.

Execute os comandos a partir da raiz do repositório.

## Preparar o ambiente

Construa a imagem Docker:

```bash
make build
```

Inicie o serviço:

```bash
make up
```

O código do repositório é montado em `/workspace` no container. Portanto, alterações feitas no host ficam disponíveis sem reconstruir a imagem.

## Validar a instalação

Execute toda a suíte de testes dentro do container:

```bash
make test
```

O comando inicia o serviço automaticamente se ele ainda não estiver em execução.

## Executar o estudo canônico

Para gerar o estudo pareado completo, com 50 seeds por condição:

```bash
make estudo
```

Esse comando executa os schedulers Round Robin, MaxCI e Proportional Fair nos cenários homogêneo e com path loss, para cargas de 2, 4, 8, 16 e 32 UEs. Ao final, gera ou atualiza em `results/`:

- `estudo_per_seed.csv`: fonte de verdade, com resultados por seed;
- `estudo_consolidado.csv`: resumo estatístico das métricas;
- `estudo_robustez_beta.csv`: análise de robustez do parâmetro beta;
- `estudo_bootstrap_ic.csv`: intervalos de confiança bootstrap;
- `estudo_ld50.csv`: análise exploratória de carga;
- `estudo_umi_nlos.csv` e `estudo_hetero_4x.csv`: análises ilustrativas;
- `manifest-estudos.json`: receipt com hashes e metadados dos artefatos.

A execução pode ser longa. Os arquivos são persistidos no diretório `results/` do host.

## Atualizar somente o receipt

Depois de alterar ou regenerar artefatos, atualize o manifesto sem executar a simulação novamente:

```bash
make receipt
```

## Usar o shell do container

Para executar comandos Python manualmente no ambiente configurado:

```bash
make shell
```

Exemplos dentro do container:

```bash
python -m pytest tests/test_simulation.py -v
python scripts/estudo_consolidado.py --seeds 1
```

## Abrir os notebooks

Inicie o Jupyter Lab:

```bash
make jupyter
```

Abra [http://localhost:8888](http://localhost:8888) no navegador. Os notebooks ficam no diretório `notebooks/`.

## Monitorar e encerrar

Acompanhe os logs do serviço:

```bash
make logs
```

Pare os containers:

```bash
make down
```

Para remover também volumes e a imagem local do projeto:

```bash
make clean
```

`make clean` é destrutivo para o ambiente Docker local, mas não remove os arquivos do repositório nem os resultados persistidos em `results/`.
