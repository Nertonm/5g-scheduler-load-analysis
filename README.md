# Projeto de Análise de Algoritmos de Escalonamento em Redes Sem Fio

Este repositório contém o projeto final de análise comparativa de algoritmos de escalonamento (*scheduling*) em redes sem fio, com foco em um cenário de enlace descendente (*downlink*) inspirado em redes 5G. A simulação utiliza a plataforma NVIDIA Sionna para geração do canal e compara os algoritmos Round Robin (RR), Max C/I (operacionalizado como seleção da maior taxa instantânea) e Proportional Fair (PF).

O objetivo principal é estudar o compromisso entre **eficiência**, **justiça na distribuição de recursos** e **exclusão de usuários** quando a carga da célula e as condições médias de canal variam.

---

## Sumário

1. [Objetivos](#1-objetivos)
2. [Cenário de simulação](#2-cenário-de-simulação)
3. [Schedulers comparados](#3-schedulers-comparados)
4. [Métricas avaliadas](#4-métricas-avaliadas)
5. [Estrutura do repositório](#5-estrutura-do-repositório)
6. [Pré-requisitos](#6-pré-requisitos)
7. [Preparar o ambiente](#7-preparar-o-ambiente)
8. [Validar a instalação](#8-validar-a-instalação)
9. [Executar o estudo canônico](#9-executar-o-estudo-canônico)
10. [Atualizar somente o receipt](#10-atualizar-somente-o-receipt)
11. [Usar o shell do container](#11-usar-o-shell-do-container)
12. [Abrir os notebooks](#12-abrir-os-notebooks)
13. [Monitorar e encerrar o ambiente](#13-monitorar-e-encerrar-o-ambiente)
14. [Artigo técnico](#14-artigo-técnico)
15. [Reprodutibilidade](#15-reprodutibilidade)
16. [Referências principais](#16-referências-principais)

---

## 1. Objetivos

### Objetivo geral

Avaliar e comparar o desempenho de diferentes algoritmos de escalonamento em cenários de enlace descendente.

### Objetivos específicos

- Configurar um ambiente reprodutível de simulação com NVIDIA Sionna.
- Implementar e integrar os schedulers Round Robin, Max C/I e Proportional Fair.
- Avaliar o impacto do aumento do número de usuários sobre eficiência e justiça.
- Comparar cenários homogêneos e heterogêneos de canal.
- Medir vazão, justiça, concentração e sinais de exclusão/starvation.
- Gerar resultados, figuras e artefatos reproduzíveis para análise e apresentação.

---

## 2. Cenário de simulação

O cenário-base considera:

| Parâmetro | Valor |
|---|---|
| Célula | Única |
| Enlace | Descendente (*downlink*) |
| Antenas | SISO |
| Tráfego | Contínuo (*full-buffer*) |
| Canal | Rayleigh |
| Duração | 10.000 TTIs por seed |
| Cargas avaliadas | 2, 4, 8, 16 e 32 UEs |
| Seeds | 50 seeds pareadas por condição no estudo canônico |

São avaliados dois regimes principais:

1. **Cenário homogêneo:** todos os UEs possuem a mesma distribuição média de canal; as diferenças instantâneas decorrem do fading Rayleigh.
2. **Cenário heterogêneo:** é adicionado path loss log-distance dependente da distância do UE à estação-base, criando diferenças persistentes de qualidade média de canal.

No estudo heterogêneo, são avaliados expoentes de path loss entre 1.5 e 4.0.

> **Nota:** o modelo é deliberadamente simplificado e voltado à comparação relativa entre schedulers. Os valores absolutos de vazão não devem ser interpretados como previsão completa de desempenho de uma rede 5G NR real.

---

## 3. Schedulers comparados

### 3.1 Round Robin (RR)

Distribui os TTIs ciclicamente entre os usuários, sem considerar o estado instantâneo do canal.

Em chamadas sequenciais:

```text
u(t) = t mod N
```

O RR funciona como referência de alta regularidade na distribuição de oportunidades de transmissão.

### 3.2 Max C/I

Seleciona, a cada TTI, o UE com a maior taxa instantânea disponível:

```text
u(t) = argmax_i r_i(t)
```

Neste projeto, o nome **Max C/I** corresponde operacionalmente a uma política de **Max Rate / Best Channel**, pois a implementação compara diretamente as taxas instantâneas dos UEs.

A política tende a maximizar a eficiência agregada, mas pode concentrar recursos em usuários com melhores condições médias de canal.

### 3.3 Proportional Fair (PF)

Seleciona o UE que maximiza a razão entre taxa instantânea e histórico de throughput:

```text
u(t) = argmax_u R_u(t) / T_u(t)
```

O histórico é atualizado por média móvel exponencial:

```text
T_u(t+1) = beta * T_u(t) + (1 - beta) * R_u(t)
```

com `beta = 0.98`.

O PF busca um compromisso entre eficiência e justiça.

---

## 4. Métricas avaliadas

O projeto utiliza métricas complementares, pois uma única medida de justiça não captura todos os comportamentos de escalonamento.

Principais métricas:

- **Throughput agregado:** vazão total entregue pela célula.
- **Throughput médio por UE:** vazão média individual.
- **5º percentil de throughput:** desempenho dos usuários com menores vazões.
- **Jain's Fairness Index (JFI) de slots:** justiça na distribuição das oportunidades de transmissão.
- **JFI de throughput:** justiça na distribuição da vazão efetivamente obtida.
- **Sliding-window JFI:** justiça observada em janelas menores de tempo.
- **Coeficiente de Gini:** concentração da distribuição de recursos ou vazão.
- **Família J_beta:** análise de robustez da noção de justiça.
- **Gaps de atendimento / starvation:** intervalos entre alocações consecutivas.
- **UEs nunca atendidos:** quantidade de usuários que não recebem nenhum TTI dentro da janela simulada.

---

## 5. Estrutura do repositório

```text
.
├── article/        # artigo técnico em LaTeX e PDF
├── docs/           # documentação complementar
├── notebooks/      # notebooks de validação e análise
├── results/        # CSVs, manifest e figuras geradas
├── scripts/        # estudo canônico e scripts auxiliares
├── src/            # canal, schedulers, simulação e métricas
├── tests/          # testes automatizados
├── Dockerfile
├── docker-compose.yml
├── Makefile
├── requirements.txt
└── README.md
```

**Arquivos centrais:**

| Arquivo | Descrição |
|---|---|
| `src/channel.py` | Geração do canal Rayleigh, cálculo de taxas e aplicação opcional de path loss |
| `src/schedulers.py` | Implementações de RR, Max C/I e PF |
| `src/simulation.py` | Pipeline geral de simulação |
| `src/analysis_metrics.py` | Métricas adicionais de justiça e exclusão |
| `scripts/estudo_consolidado.py` | Execução do estudo canônico pareado |
| `scripts/write_manifest.py` | Geração do receipt/manifest dos resultados |
| `article/main.pdf` | Versão compilada do artigo técnico |

---

## 6. Pré-requisitos

A forma recomendada de execução é via Docker.

É necessário ter:

- Docker Engine instalado e em execução;
- Docker Compose disponível pelo comando `docker compose`;
- GNU Make;
- pelo menos 2 GB de memória compartilhada disponíveis para o container.

O `docker-compose.yml` já configura:

```text
shm_size: 2g
```

A imagem do projeto utiliza Python 3.11 e instala as dependências listadas em `requirements.txt`, incluindo Sionna 2.0.1, NumPy, pandas, SciPy, Matplotlib, Seaborn, statsmodels, scikit-learn, JupyterLab e pytest.

> Todos os comandos abaixo devem ser executados a partir da raiz do repositório.

---

## 7. Preparar o ambiente

Construa a imagem Docker:

```bash
make build
```

Inicie o serviço:

```bash
make up
```

O código do repositório é montado em `/workspace` dentro do container. Assim, alterações feitas no host ficam disponíveis no container sem necessidade de reconstruir a imagem.

---

## 8. Validar a instalação

Execute a suíte de testes:

```bash
make test
```

O comando inicia o serviço automaticamente caso ele ainda não esteja em execução.

---

## 9. Executar o estudo canônico

Para executar o estudo completo:

```bash
make estudo
```

Esse comando executa o estudo pareado com 50 seeds por condição para:

- Round Robin;
- Max C/I;
- Proportional Fair;
- cargas de 2, 4, 8, 16 e 32 UEs;
- cenário homogêneo;
- cenários com path loss log-distance.

A execução completa pode levar algum tempo.

Os resultados são persistidos em `results/`.

### Principais arquivos gerados

| Arquivo | Descrição |
|---|---|
| `results/estudo_per_seed.csv` | Fonte de verdade com os resultados por seed |
| `results/estudo_consolidado.csv` | Resumo estatístico das métricas |
| `results/estudo_robustez_beta.csv` | Análise da família de métricas J_beta |
| `results/estudo_bootstrap_ic.csv` | Intervalos de confiança via bootstrap |
| `results/estudo_ld50.csv` | Análise exploratória de carga |
| `results/estudo_umi_nlos.csv` | Contraste ilustrativo com modelo UMi NLOS relativo |
| `results/estudo_hetero_4x.csv` | Cenário ilustrativo com heterogeneidade controlada |
| `results/manifest-estudos.json` | Receipt com hashes e metadados dos artefatos |
| `results/figuras/` | Figuras geradas pelo estudo |

---

## 10. Atualizar somente o receipt

Após alterações relevantes no candidate ou após regenerar artefatos, atualize o manifest sem executar novamente toda a simulação:

```bash
make receipt
```

O receipt registra hashes dos artefatos canônicos e um fingerprint do estado relevante do projeto, auxiliando a verificação de reprodutibilidade.

---

## 11. Usar o shell do container

Para abrir um shell no ambiente configurado:

```bash
make shell
```

Exemplos de comandos dentro do container:

```bash
python -m pytest tests/test_simulation.py -v
python scripts/estudo_consolidado.py --seeds 1
```

---

## 12. Abrir os notebooks

Inicie o Jupyter Lab:

```bash
make jupyter
```

Depois, abra no navegador:

```text
http://localhost:8888
```

Os notebooks ficam no diretório `notebooks/`.

---

## 13. Monitorar e encerrar o ambiente

Acompanhar logs:

```bash
make logs
```

Parar os containers:

```bash
make down
```

Remover containers, volumes e a imagem local do projeto:

```bash
make clean
```

> `make clean` é destrutivo para o ambiente Docker local, mas não remove os arquivos versionados do repositório nem os resultados persistidos em `results/`.

---

## 14. Artigo técnico

O artigo final do projeto está disponível em:

- `article/main.tex`
- `article/main.pdf`

O artigo apresenta a fundamentação dos schedulers, metodologia, resultados, limitações e conclusões do estudo.

---

## 15. Reprodutibilidade

O estudo canônico utiliza seeds pareadas: sob uma mesma condição, os schedulers são avaliados sobre as mesmas realizações de canal. Isso permite comparações diretas e reduz diferenças causadas apenas por amostragem aleatória.

O arquivo `results/manifest-estudos.json` registra os hashes dos principais resultados e o fingerprint dos arquivos relevantes do projeto.

Para validar o candidate atual:

```bash
make test
```

Para regenerar apenas o receipt depois de alterações que não exigem uma nova simulação:

```bash
make receipt
```

---

## 16. Referências principais

- **JAIN, R.; CHIU, D.; HAWE, W.** *A Quantitative Measure of Fairness and Discrimination for Resource Allocation in Shared Computer Systems.* DEC Research Report TR-301, 1984.
- **MAMANE, A. et al.** *Scheduling Algorithms for 5G Networks and Beyond: Classification and Survey.* IEEE Access, 2022.
- **LAN, T.; KAO, D.; CHIANG, M.; SABHARWAL, A.** *An Axiomatic Theory of Fairness in Network Resource Allocation.* IEEE INFOCOM, 2010.
- **NVIDIA Sionna.** Documentação do `RayleighBlockFading` e recursos de scheduling.

As referências completas utilizadas no artigo estão em `article/referencias.bib`.