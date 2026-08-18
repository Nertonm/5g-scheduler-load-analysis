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

## 1) `results/per_ue/*.csv`

Arquivo por cenário: `per_ue/<scheduler>__cargaN__seedM.csv`

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

## 2) `results/results_per_seed.csv`

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

## 3) `results/results_summary.csv`

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

## 4) `results/cdf_throughput.csv`

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

## 5) `results/manifest.json`

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
