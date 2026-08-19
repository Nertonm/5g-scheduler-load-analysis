# Dicionário de dados dos arquivos de saída da simulação

Este documento descreve o schema dos arquivos gerados em `results/` pela rotina de execução em [src/simulation.py](../src/simulation.py#L137-L266). Ele cobre todos os artefatos exportados: `per_ue/*.csv`, `results_per_seed.csv`, `results_summary.csv`, `cdf_throughput.csv` e `manifest.json`.

## Convenções gerais

- Unidade de throughput: `bit/s` (bps), salvo indicação em contrário.
- `NaN`: utilizado quando a métrica não é definida matematicamente (ex.: fairness em cenário all-zero).
- `scheduler`: identificador textual da política de alocação; nomes esperados no card 1: `empty` e `max_c_i`. Nos cards futuros, `round_robin` e `proportional_fair` também podem aparecer.
- `carga`: número de UEs ativos na simulação do arquivo.
- `seed`: semente aleatória usada para gerar o canal e a amostra estatística daquele cenário.
- `TTI`: Transmission Time Interval, com duração nominal de `1 ms` (`cfg.tti_duration = 1e-3 s`).

---

## 1) Histórico: `results/legado/per_ue/*.csv`

Arquivo histórico por cenário: `results/legado/per_ue/<scheduler>__cargaN__seedM.csv`

Cada linha representa um usuário `ue_id` em um cenário específico `(scheduler, carga, seed)`. O dado bruto é a acumulação de throughput por UE ao longo dos TTIs.

| Nome da coluna | Tipo | Unidade | Significado | Como foi calculada |
| --- | --- | --- | --- | --- |
| `scheduler` | string | — | Nome do scheduler usado na simulação. | Valor passado para `run_seed_on_rates(...)` e copiado para o DataFrame. |
| `carga` | int | UE | Quantidade de usuários simultâneos na simulação. | `carga` informado no loop do grid. |
| `seed` | int | — | Semente aleatória do canal e da amostra. | `seed` informado no loop do grid. |
| `ue_id` | int | — | Identificador do usuário dentro da carga. | `np.arange(num_ues)`; indexa os UEs de 0 a `carga - 1`. |
| `throughput_bps` | float | bit/s | Taxa média realizada por UE na seed, ao longo da simulação. | `bits[ue] / cfg.sim_duration_per_seed_s`, onde `bits[ue]` é a soma de `rates[t, ue] * cfg.tti_duration` em todos os TTIs em que o UE foi selecionado. |
| `slots_allocated` | int | TTIs recebidos | Número de TTIs em que a UE foi selecionada. | `slots[ue] += 1` cada vez que `sched.select(...)` retorna esse UE. |
| `prbs_allocated` | int | PRBs | Total de PRBs atribuídos ao UE na seed. | `slots_allocated * cfg.num_prbs` (o código usa `cfg.num_prbs` do experimento; default `52`). |

Observações:

- A granularidade é por UE e por seed, não por TTI.
- `throughput_bps` é a média temporal de taxa entregue ao UE, não a taxa instantânea por TTI.
- Quando o scheduler não aloca nenhum recurso, os valores se tornam zero para todas as UEs e a fairness correspondente (`jains_fairness_index`) vira `NaN` no agregado por seed.

---

## 2) `results/legado/results_per_seed.csv`

Arquivo agregado por cenário `(scheduler, carga, seed)`.

| Nome da coluna | Tipo | Unidade | Significado | Como foi calculada |
| --- | --- | --- | --- | --- |
| `scheduler` | string | — | Scheduler do cenário. | Copiado da linha do DataFrame por UE. |
| `carga` | int | UE | Número de usuários da simulação. | `carga` do cenário. |
| `seed` | int | — | Semente da amostra. | `seed` do cenário. |
| `throughput_aggregate_bps` | float | bit/s | Soma do throughput de todos os UEs na seed. | `float(thr.sum())`, onde `thr` é o vetor `throughput_bps` dos UEs. |
| `throughput_mean_per_ue_bps` | float | bit/s | Média por UE do throughput agregado da seed. | `throughput_aggregate_bps / n_ues`. |
| `jains_fairness_index` | float | [0, 1] | Medida de justiça de Jain entre os UEs da seed. | `J = (sum x)^2 / (n * sum x^2)`; se `sum x == 0`, retorna `NaN` para evitar divisão por zero. |
| `throughput_5th_percentile_bps` | float | bit/s | Percentil 5% do throughput por UE no cenário. | `np.percentile(thr, 5)` sobre a distribuição dos `throughput_bps` dos UEs. |
| `delta_jfi_relative_to_rr` | float | unidade relativa | Diferença de justiça relativa ao baseline Round Robin. | Campo reservado no schema; no card 1 mantém `NaN` porque a comparação com RR ainda não está implementada. |
| `mean_snr_db_per_ue` | float | dB | SNR médio por UE em dB, agregado pela seed. | `float(real.mean_snr_db_per_ue(cfg.snr_db).mean())`, onde a média do canal é convertida para dB por `mean_snr_db_per_ue`. |

Observações:

- Esta é a tabela principal para análise por seed e para comparação entre políticas.
- `jains_fairness_index` é a métrica de equidade clássica; como o cenário é full-buffer, valores baixos indicam concentração de recursos.
- `delta_jfi_relative_to_rr` foi incluído no schema desde o início para estabilizar o contrato de dados entre os cards e não quebrar downstream de análise.

---

## 3) `results/legado/results_summary.csv`

Arquivo de resumo estatístico por `(scheduler, carga)`, agregando as amostras de seed. A unidade amostral é a `seed`.

| Nome da coluna | Tipo | Unidade | Significado | Como foi calculada |
| --- | --- | --- | --- | --- |
| `scheduler` | string | — | Scheduler da comparação. | Agrupamento por `scheduler`. |
| `carga` | int | UE | Quantidade de usuários. | Agrupamento por `carga`. |
| `metric` | string | — | Nome da métrica resumida. | No card 1, apenas `"throughput_aggregate_bps"` é agregado para IC 95%. |
| `mean` | float | unidade da métrica | Média entre as seeds. | `grp["throughput_aggregate_bps"].mean()`. |
| `std` | float | unidade da métrica | Desvio padrão amostral entre as seeds. | `grp["throughput_aggregate_bps"].std(ddof=1)`. |
| `ci95_low` | float | unidade da métrica | Limite inferior do intervalo de confiança de 95%. | `mean - tcrit * se`, com `se = std / sqrt(n)` e `tcrit` calculado via `scipy.stats.t.ppf(0.975, df=n-1)` quando disponível; caso contrário, usa `1.96` como aproximação assintótica. |
| `ci95_high` | float | unidade da métrica | Limite superior do intervalo de confiança de 95%. | `mean + tcrit * se`. |

Observações:

- O resumo é feito sobre o throughput agregado por seed, não sobre o throughput por UE individual.
- O número de amostras `n` é o número de seeds disponíveis para esse `(scheduler, carga)`.
- Esse arquivo é o input natural para gráficos de barras com intervalos de confiança ou para a discussão estatística do relatório.

---

## 4) `results/legado/cdf_throughput.csv`

Arquivo empírico de distribuição cumulativa de throughput por UE, organizado por `(scheduler, carga)`.

| Nome da coluna | Tipo | Unidade | Significado | Como foi calculada |
| --- | --- | --- | --- | --- |
| `scheduler` | string | — | Scheduler do cenário. | Agrupamento por `scheduler`. |
| `carga` | int | UE | Número de usuários do cenário. | Agrupamento por `carga`. |
| `throughput_bps` | float | bit/s | Valor de throughput por UE ordenado. | `np.sort(grp["throughput_bps"].to_numpy())` dentro do grupo. |
| `cdf` | float | [0, 1] | Probabilidade acumulada empírica de throughput menor ou igual a esse valor. | `(i + 1) / m`, em que `m` é o número total de observações no grupo e `i` é o índice ordenado. |

Observações:

- Este arquivo não contém uma linha por cenário, e sim uma linha por observação de throughput por UE, depois de empilhar todos os cenários.
- É útil para traçar curvas CDF comparando a distribuição dos UEs entre schedulers e cargas.
- Os valores de `throughput_bps` neste arquivo são os mesmos dados brutos do per-UE, apenas reordenados e com a CDF empírica adicionada.

---

## 5) `results/legado/manifest.json`

Arquivo de metadados e reprodutibilidade. Não é um CSV, mas é parte do conjunto de outputs e deve acompanhar o resultado experimental.

| Chave no JSON | Tipo | Unidade | Significado | Como foi calculada |
| --- | --- | --- | --- | --- |
| `config` | objeto | — | Snapshot da configuração do experimento. | `asdict(cfg)` da dataclass `Config` em tempo de execução. |
| `wall_time_s` | float | s | Tempo total de execução da simulação. | `round(time.time() - started, 2)` no início e fim do `run()`. |
| `completed` | lista de strings | — | Registros dos jobs executados no formato `"<scheduler>|<carga>|<seed>"`. | Acumulado no loop da simulação para cada arquivo por UE gerado. |
| `git_commit` | string | — | SHA do HEAD do repositório no momento da execução. | `_git_commit()` via `git rev-parse HEAD`. |

Observações:

- O manifesto permite rastrear reprodutibilidade e reproduzir a configuração exata de execução.
- Se `git` não estiver disponível ou o repositório não for um Git checkout, `git_commit` pode ficar vazio.

---

## 6) Resumo executivo do schema

Os dados exportados seguem um desenho em três camadas:

1. `per_ue/*.csv`: dados brutos de throughput por UE e recursação de slots/PRBs.
2. `results_per_seed.csv`: agregação por `(scheduler, carga, seed)` para comparação estatística e fairness.
3. `results_summary.csv` e `cdf_throughput.csv`: estatísticas resumidas e distribuição empírica para análise e relatório.
4. `manifest.json`: reprodutibilidade e contexto de execução.

Essa estrutura foi concebida para apoiar tanto a análise quantitativa dos cards 8-9 quanto a redação do relatório do card 11.


---

## 6) Path loss log-distance (cena heterogenea near/far)

O schema dos CSV **nao muda** quando o path loss esta habilitado: a rotina
gera os mesmos `per_ue.csv`, `results_per_seed.csv`, `results_summary.csv`,
`cdf_throughput.csv` e `manifest.json`. A diferenca esta **no canal** que
alimenta as metricas: o vetor `h` e escalado por UE.

Parametros de cena (em `src/config.py`):

| Campo | Default | Efeito |
|-------|---------|--------|
| `enable_pathloss` | `False` | `False` (decisao do Card 1): SNR media identica entre UEs. `True`: aplica path loss log-distance por posicao de UE. |
| `pathloss_alpha` | `3.0` | Expoente de perda (alpha do modelo `P(d)=P0*(d0/d)^alpha`; redes sem fio: 2 a 4). |
| `pathloss_d0_m` | `10.0` | Distancia de referencia (m) do modelo log-distance. |
| `pathloss_radius_m` | `500.0` | Raio da celula (m) usado para posicionar os UEs no disco. |

As posicoes dos UEs sao deterministicas da seed (`positions_from_seed` em
`src/channel.py`): mesma seed -> mesma geometria. O canal com path loss usa
`generate_channel_with_pathloss` em `src/channel.py`.

> O default segue com path loss **desligado** (Card 1: SNR homogenea). O
> gerador canônico `scripts/estudo_consolidado.py` percorre tanto o braço
> homogêneo quanto os braços log-distance pareados por seed.
## 7) CSVs dos estudos de injustica (results/estudo_*.csv)

> O `results/legado/manifest.json` (secao 5) e o receipt do **card 1** (pipeline base)
> e esta **LEGADO**: descreve o smoke grid (16 TTIs/1 seed) e nao cobre os
> estudos de injustica. O receipt dos estudos e `results/manifest-estudos.json`
> (secao 7.4), gerado por `make receipt` com fingerprint do candidate. Nao use
> `manifest.json` para documentar os estudos de 50 seeds.

A fonte canônica dos estudos é `results/estudo_per_seed.csv`: uma linha por
`(sched, carga, pathloss, alpha, seed)` e a mesma grade de seeds em todos os
braços sem/com path loss. `results/estudo_consolidado.csv` é derivado dele e
agrega **todas** as métricas com média, desvio e IC95. Os arquivos
`estudo_expandido.csv` e `estudo_robusto.csv` permanecem apenas como materiais
históricos de auditoria, não como saída final.

As métricas `starv_p95` e `starv_max` são gaps internos observados: não incluem
UEs nunca/uma vez atendidos nem as bordas do horizonte. Interpretá-las junto de
`nunca`; elas não são latência máxima censurada.

### 7.1 Histórico: `results/legado/estudo_expandido.csv`

Media sobre **50 seeds**, 7 cenarios (homogeneo + log-distance alpha
1.5/2.0/2.5/3.0/3.5/4.0), cargas [2,4,8,16,32], 10.000 TTIs. Colunas:

| Coluna | Descricao |
|--------|-----------|
| `sched` | `RR`, `MaxCI` ou `PF` |
| `carga` | numero de UEs (2, 4, 8, 16, 32) |
| `pathloss` | `False` (homogeneo) ou `True` (log-distance) |
| `alpha` | expoente de perda do log-distance (NaN no homogeneo) |
| `jfi_slots` | Jain sobre a fracao de slots por UE (justica de tempo) |
| `jfi_throughput` | Jain sobre o throughput acumulado por UE (justica de vazao) |
| `jfi_win` | Jain por sliding window (justica de curto prazo) |
| `starv_p95` | percentil 95 dos gaps entre alocacoes (so UEs com >=2 alocacoes) |
| `starv_max` | maior gap entre alocacoes de um mesmo UE |
| `thr_5pct` | 5o percentil da vazao media por UE (bit/s; soma de taxas / T) |
| `nunca_mean` / `nunca_max` | media/maximo de UEs sem nenhuma alocacao (por seed) |

### 7.1b `results/legado/estudo_robusto.csv`

Mesma estrutura (50 seeds, 7 cenarios, 10.000 TTIs), porem **sem** `starv_max`
nem `thr_5pct`. Colunas: `sched`, `carga`, `pathloss`, `alpha`, `jfi_slots`,
`jfi_slots_std`, `jfi_slots_ci95`, `jfi_throughput`, `jfi_throughput_ci95`,
`jfi_win`, `starv_p95`, `nunca_mean`, `nunca_max`. IC95 = 1.96*std/sqrt(n).

### 7.1 Fonte canônica: `results/estudo_per_seed.csv`

Dados por seed do estudo canônico, gerado exclusivamente por
`scripts/estudo_consolidado.py`: uma linha por `(sched, carga, cenário, seed)`
contendo JFI slots/vazão/janela, Gini slots/vazão, todos os `j_beta_*`, gaps
observados, vazão p5, exclusão e vetores por UE. É a única entrada para
comparação pareada, bootstrap e resumos.

### 7.1d Resumo canônico: `results/estudo_consolidado.csv`

Uma linha por `(sched, carga, pathloss, alpha)`, derivada somente do per-seed.
Para cada métrica escalar há colunas `_mean`, `_std` e `_ci95`, além de
`seed_count`. Assim os braços homogêneo e log-distance usam exatamente as
mesmas métricas e a mesma população de seeds.

> `jfi_slots` e `jfi_throughput` sao metricas distintas: sob heterogeneidade
> near/far, tempo igual (RR) nao garante vazao igual. Reportar ambas.

### 7.2 `results/estudo_umi_nlos.csv`

Corrida **ilustrativa** UMi NLOS (TR 38.901 eq 7.4-7), **1 seed de posicao por
carga** (nao media). Usa `generate_channel` (Rayleigh do pipeline) + sqrt(gamma)
na amplitude + `compute_rates`. Nao validar quantitativamente o cenario
principal; somente mostrar o comportamento.

### 7.3 `results/estudo_hetero_4x.csv`

Corrida isolada (seed 0) com N=8 e UE0 dominante (path loss fixo 4x). Mostra o
dominador; nao media sobre seeds.

### 7.4 `results/manifest-estudos.json`

Receipt experimental: para **cada arquivo**, seu protocolo (corrida, taxa,
canal, cenarios, num_ttis), SHA-256, numero de linhas e git_commit. Gerado por
`scripts/write_manifest.py`. Observar que cada CSV declara o proprio numero de
seeds (o global nao existe mais - auditoria).
