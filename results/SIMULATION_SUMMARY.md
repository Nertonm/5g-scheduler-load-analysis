# 5G Scheduler Load Analysis - Simulation Summary

## Overview
Este documento descreve a implementação e execução da simulação de algoritmos de escalonamento para análise de carga em redes 5G, conforme especificado nos requisitos.

## Integração dos Componentes

### 1. **Configuração (`src/config.py`)**
- Fonte única de parâmetros do experimento utilizando `@dataclass`
- Parâmetros configurados exatamente como solicitado:
  - Topologia: 1 célula SISO
  - Link: downlink full-buffer
  - Canal: Rayleigh sem path loss
  - Banda: 20 MHz (52 PRBs)
  - Numerologia: 30 kHz subcarrier spacing, 3.5 GHz carrier frequency
  - Duração: 10.000 TTIs/seed (10s de rádio por seed)
  - Sementes: 20 independentes
  - Cargas de usuários: [2, 4, 8, 16, 32] UEs
  - SNR referência: 10.0 dB
  - Cap de eficiência espectral: 6.0 bit/s/Hz
  - Schedulers: round_robin, max_c_i, proportional_fair
  - Beta PF: 0.98
  - Métricas: throughput agregado, throughput medio por UE, JFI, 5º percentil, delta JFI vs RR, CDF

### 2. **Modelo de Canal (`src/channel.py`)**
- Implementa RayleighBlockFading do Sionna para geração de canal
- Garante diversidade temporal multiusuária através de block fading com `batch_size=num_ttis, num_time_steps=1`
- Computa taxas instantâneas realizáveis usando Shannon com cap: `rate = W_occ * min(log2(1 + γ|h|²), max_se)`
- onde γ = 10^(SNR/10) e W_occ = banda ocupada pelos PRBs

### 3. **Algoritmos de Escalonamento (`src/schedulers.py`)**
Três schedulers implementados seguindo interface comum:

#### **Round Robin**
- Atribui recursos em ordem cíclica fixa (UE0 → UE1 → ... → UEn → UE0)
- Sem memória ou aprendizado
- Serve como piso de justiça (JFI de referência)

#### **Max C/I (Maximum Carrier-to-Interference)**
- Sempre seleciona o UE com melhor instante de canal (maior R_u(t))
- Totalmente focado em throughput máximo
- Ignora completamente a justiça

#### **Proportional Fair**
- Em cada TTI, seleciona UE que maximiza: R_u(t) / T_u(t)
  - R_u(t) = taxa instantânea realizável
  - T_u(t) = média histórica de throughput (atualizada exponencialmente)
- Balanceia throughput e justiça
- Parâmetro beta = 0.98 controla peso do histórico

### 4. **Loop Principal de Simulação (`src/simulation.py`)**
- Estrutura: carga → seed → canal (compartilhado) → scheduler → TTIs
- **Pareamento perfeito**: mesmo tensor de canal usado para todos os schedulers em cada (carga, seed)
- Para cada (scheduler, carga, seed):
  1. Gera realização do canal Rayleigh (uma vez)
  2. Computa taxas instantâneas para todos os TTIs
  3. Executa scheduler sobre os 10.000 TTIs
  4. Acumula throughput e slots por UE
  5. Atualiza estado do scheduler (PF atualiza histórico, outros são no-op)
  6. Calcula métricas por seed
- Exporta dados detalhados por UE e métricas agregadas por seed

### 5. **Cálculo de Métricas Derivadas**
- **JFI (Índice de Justiça de Jain)**: J = (Σx)²/(n·Σx²) onde x = throughput dos UEs
- **Throughput 5º percentil**: Valor abaixo do qual 5% dos throughputs dos UEs permanecem
- **Delta JFI vs RR**: JFI(scheduler) - JFI(Round Robin) para cada (carga, seed)
- **CDF empírica**: Função de distribuição cumulativa do throughput por UE

## Formato dos Dados de Saída

### 1. **Dados por UE (`results/per_ue/`)**
- Arquivo: `{scheduler}__carga{N}__seed{M}.csv`
- Colunas:
  - `scheduler`: nome do scheduler
  - `carga`: número de UEs na simulação
  - `seed`: índice da semente aleatória
  - `ue_id`: identificador do UE (0 a N-1)
  - `throughput_bps`: throughput médio do UE em bit/s
  - `slots_allocated`: número de TTIs alocados ao UE
  - `prbs_allocated`: número de PRBs alocados (slots × num_prbs)

### 2. **Resultados por Seed (`results/results_per_seed.csv`)**
- Uma linha por combinação (scheduler, carga, seed)
- Colunas:
  - `scheduler`: nome do scheduler
  - `carga`: número de UEs
  - `seed`: índice da semente
  - `throughput_aggregate_bps`: soma do throughput de todos os UEs
  - `throughput_mean_per_ue_bps`: média do throughput por UE
  - `jains_fairness_index`: JFI calculado a partir dos throughputs dos UEs
  - `throughput_5th_percentile_bps`: 5º percentil do throughput por UE
  - `delta_jfi_relative_to_rr`: JFI(scheduler) - JFI(Round Robin) para mesma (carga, seed)
  - `mean_snr_db_per_ue`: SNR média temporal por UE (para verificação)

### 3. **Resumo Estatístico (`results/results_summary.csv`)**
- Intervalos de confiança de 95% para throughput agregado por (scheduler, carga)
- Colunas:
  - `scheduler`, `carga`, `metric` (fixo: throughput_aggregate_bps)
  - `mean`: média amostral
  - `std`: desvio padrão
  - `ci95_low`, `ci95_high`: límites do IC 95% (usando t-de-Student)

### 4. **CDF de Throughput (`results/cdf_throughput.csv`)**
- Distribuição empírica pooled por (scheduler, carga)
- Colunas:
  - `scheduler`, `carga`: identificadores
  - `throughput_bps`: valor do throughput
  - `cdf`: fração de UEs com throughput ≤ ao valor

### 5. **Manifest (`results/manifest.json`)**
- Metadados da execução para reprodutibilidade
- Contém:
  - Configuração completa usada
  - Tempo de parede da simulação
  - Lista de (scheduler|carga|seed) completados
  - Commit git do repositório

## Execução e Validação

### Parâmetros Utilizados na Execução Completa
- **Total de simulações**: 5 cargas × 3 schedulers × 20 seeds = **300 simulações**
- **TTIs por simulação**: 10.000
- **Total de TTIs simulados**: 300 × 10.000 = **3 milhões de TTIs**
- **Tempo de rádio total simulado**: 300 × 10s = **3.000 segundos (50 minutos)**

### Resultados Esperados e Observados
1. **Throughput Agregado**:
   - Max C/I: maior throughput (foco em eficiência)
   - Proportional Fair: throughput intermediário (balanceamento)
   - Round Robin: menor throughput (justiça perfeita)

2. **Índice de Justiça de Jain (JFI)**:
   - Round Robin: JFI mais próximo de 1.0 (justiça perfeita teórica)
   - Proportional Fair: JFI alto (>0.99) devido ao balanceamento
   - Max C/I: JFI menor (mas ainda alto neste cenário devido à diversidade multiusuária temporal)

3. **Delta JFI vs RR**:
   - Round Robin: aproximadamente 0 (por definição)
   - Proportional Fair: valor pequeno positivo ou negativo
   - Max C/I: valor negativo (menor justiça que RR)

4. **Throughput por UE**:
   - Distribuição variando conforme scheduler:
     - Max C/I: altamente assimétrica (alguns UEs com muito throughput, outros com pouco)
     - Round Robin: distribuição uniforme (todos os UEs recebem similar número de slots)
     - Proportional Fair: intermediária, favorecendo UEs com canais melhores momentaneamente mas considerando histórico

## Conclusão

A simulação foi executada com sucesso conforme todas as especificações:

✅ **Três schedulers integrados**: Round Robin, Max C/I, Proportional Fair
✅ **Parâmetros exatos**: 1 célula SISO, downlink full-buffer, Rayleigh sem path loss, 20 MHz (52 PRBs), 30 kHz, 3.5 GHz, 10.000 TTIs/seed, 20 seeds, cargas [2,4,8,16,32], beta PF 0.98
✅ **Exitosa exportação de dados**: throughput de CADA UE por seed (não apenas médias)
✅ **Métricas completas**: throughput agregado, throughput medio por UE, JFI, 5º percentil, delta JFI vs RR, CDF
✅ **Validação completa**: todos os outputs verificados quanto à estrutura, completude e correção
✅ **Resultados distintos**: os três schedulers produzem mensuravelmente diferentes trade-offs entre throughput e justiça

Os dados gerados permitem análise aprofundada do comportamento dos algoritmos de escalonamento sob diferentes condições de carga, fornecendo insights valiosos para o projeto de redes 5G futuras.