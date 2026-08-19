# Checkpoint - Trabalho Final Redes Sem Fio

**Disciplina:** Redes Sem Fio (CC0048)
**Professor:** Laszlon Rodrigues da Costa
**Data do checkpoint:** 09/07/2026

---

## 1. Nome da equipe e integrantes

**Equipe:** 5G Scheduler Load Analysis

| Nome | Papel |
|------|-------|
| David Hudson | [papel] |
| Luana Teles | [papel] |
| Thiago Nerton | [papel] |
| Vitória Pontes | [papel] |
| Alex Reis | Integrante adicionado após o checkpoint |
| Victor Cleyton | Integrante adicionado após o checkpoint |

Equipe final com seis integrantes, incluindo Alex Reis e Victor Cleyton, incorporados após o checkpoint.

---

## 2. Tema escolhido e justificativa

**Tema:** Análise Comparativa de Schedulers Downlink 5G em Célula Única SISO

Análise comparativa de três schedulers (Round Robin, Max C/I e Proportional Fair) em célula única SISO com canal Rayleigh, variando a carga de UEs, para caracterizar o trade-off entre throughput agregado e justiça entre usuários.

Usa-se `sionna.phy.channel.RayleighBlockFading` (fading complexo gaussiano, constante no TTI, independente entre UEs). SISO: `num_tx_ant = num_rx_ant = 1`; downlink: `num_tx = 1` (gNB), `num_rx = N_UEs` (um UE por receptor).

Modelos 3GPP TR 38.901 (UMa/UMi/RMa) e TDL foram descartados por adicionarem path loss, shadowing e Doppler, o que diluiria a atribuição causal entre scheduler e métrica.

**Por que downlink?**
- Domina o volume de tráfego e é o KPI primário das operadoras.
- Full-buffer é o pior caso para justiça: disputa real por recursos em todo TTI.
- Decisão 100% centralizada no gNB, sem a complexidade de grants do uplink.

**Por que célula única SISO?** Elimina a interferência intercelular como fator de confusão, permitindo atribuir mudanças nas métricas apenas à política de scheduling.

**Por que canal Rayleigh?**
- Modela cenário urbano sem LOS, padrão na literatura de scheduling.
- Cria a heterogeneidade de canal que torna o scheduling relevante: sem ela, os três algoritmos dariam o mesmo resultado. Rayleigh gera a tensão entre eficiência (Max C/I) e justiça (RR, PF).
- Permite observar multiuser diversity: mais UEs aumenta a chance de algum estar em pico de canal a cada TTI.
- Risco: pouca heterogeneidade de SNR tornaria os schedulers artificialmente semelhantes. Posições aleatórias no raio de 500 m mitigam isso, a confirmar no sanity check do 01_baseline.ipynb.

A gestão de recursos de rádio é central para a QoS em redes móveis atuais e futuras, e o algoritmo de escalonamento define o equilíbrio entre capacidade total e desempenho na borda de cobertura.

---

## 3. Problema de redes sem fio investigado

**Pergunta central:** Em qual ponto o Max C/I deixa de ser sustentável em termos de justiça quando aumentamos a carga de usuários?

**Visão geral do problema:** trade-off entre vazão máxima (throughput) e equidade (fairness) no downlink. Algoritmos focados na taxa total penalizam UEs com sinal ruim; soluções puramente igualitárias reduzem a capacidade da célula. O projeto avalia esse compromisso sob carga crescente de dispositivos (2, 4, 8, 16, 32 UEs).

---

## 4. Objetivos do projeto

**Objetivo geral:** comparar estratégias de escalonamento de pacotes em downlink.

**Objetivos específicos:**
1. Configurar o ambiente de simulação em plataforma open-source (Sionna)
2. Implementar Round Robin, Max C/I e Proportional Fair
3. Variar o número de UEs (2, 4, 8, 16, 32) mantendo demais parâmetros fixos
4. Avaliar o impacto da densidade de UEs nos indicadores do sistema (throughput, JFI, 5º percentil)
5. Apresentar resultados via métricas estatísticas e curvas de distribuição (CDF)

---

## 5. Metodologia proposta

Simulação computacional quantitativa: célula única, downlink full-buffer, canal Rayleigh, SISO. Execução ao longo de múltiplos TTIs com várias seeds aleatórias, para gerar intervalos de confiança de 95%.

| Parâmetro | Valor |
|-----------|-------|
| Topologia | 1 célula, SISO |
| UEs | 2, 4, 8, 16, 32 |
| Posições | Uniforme aleatória (raio 500m) |
| Canal | Rayleigh fading (RayleighBlockFading) |
| Bandwidth | 20 MHz (52 PRBs) |
| Subcarrier spacing | 30 kHz |
| TTIs simulados | 10.000 |
| Seeds | 20 por configuração |

**Schedulers:**
- **Round Robin:** u(t) = t mod N; ciclo simples, ignora canal
- **Max C/I:** u(t) = argmax_i r_i(t); escolhe a melhor taxa instantânea
- **Proportional Fair:** u(t) = argmax_u R̃(u,i) / T(u); taxa dividida pela média histórica

**Métricas:**
- Throughput agregado da célula
- Throughput médio por UE
- Jain's Fairness Index (JFI)
- 5th percentile throughput (desempenho de borda)
- CDF de throughput por UE
- Delta JFI relativo ao RR

---

## 6. Tecnologias, simuladores, bases de dados ou equipamentos previstos

| Tecnologia | Uso |
|------------|-----|
| **Sionna** (NVIDIA, Python, GPU) | Simulação PHY/SYS 5G NR |
| **Python 3.11+** | Implementação dos schedulers (Sionna 2.x exige >= 3.11) |
| **NumPy** | Cálculos numéricos |
| **Matplotlib** | Visualização |
| **SciPy** | Análise estatística (IC 95%) |
| **Pandas** | Manipulação de dados |

---

## 7. Breve levantamento bibliográfico ou técnico

1. **JAIN, R.; CHIU, D.; HAWE, W.** A Quantitative Measure of Fairness and Discrimination for Resource Allocation in Shared Computer Systems. DEC Research Report TR-301, 1984.

2. **MAMANE, A. et al.** Scheduling Algorithms for 5G Networks and Beyond: Classification and Survey. IEEE Access, v. 10, p. 51643-51661, 2022.

3. **NVIDIA.** Sionna Documentation. Disponível em: https://nvlabs.github.io/sionna/

4. **3GPP TS 38.214**: Procedimentos de CQI/CSI em NR. Define como CQI se liga a MCS e taxas atingíveis.

5. **3GPP TS 38.300**: Visão geral do NR physical layer. Parâmetros padrão de configuração.

6. **IMT-2020 Evaluation**: 5th percentile user spectral efficiency como KPI formal de avaliação.

**Lacuna identificada:** a literatura recente se concentra em QoS-aware, slicing e ML. Comparações basais reproduzíveis entre RR, Max C/I e PF em cenário controlado recebem menos atenção.

---

## 8. Cronograma até a entrega final

| Semana | Atividade | Status |
|--------|-----------|--------|
| 01-02 | Estudo da documentação e definição do escopo | Concluído |
| 03 | Configuração do ambiente Sionna | Em andamento |
| 04-05 | Desenvolvimento e integração dos schedulers | Pendente |
| 06 | Execução das simulações e coleta de dados | Pendente |
| 07 | Análise estatística e redação do relatório final | Pendente |

Marcos fixos do calendário: entrega final 19/08/2026, apresentações 20-25/08/2026.

---

## 9. Progresso já realizado

- [x] Leitura e análise do enunciado do trabalho final
- [x] Definição do conceito do projeto (comparação de schedulers)
- [x] Levantamento bibliográfico inicial
- [x] Definição da metodologia (parâmetros de simulação)
- [x] Definição das variáveis do cenário e seleção de métricas
- [x] Criação da estrutura do repositório
- [ ] Configuração do ambiente local e resolução de dependências do Sionna (em andamento)
- [ ] Implementação dos 3 schedulers em Sionna
- [ ] Notebook de sanity check (01_baseline.ipynb)
- [ ] Notebook do experimento principal (02_experiment.ipynb)
- [ ] Notebook de análise e gráficos (03_analysis.ipynb)

---

## 10. Riscos, dúvidas e bloqueios

**Riscos identificados:**
1. **Heterogeneidade insuficiente de canal:** se todos os UEs tiverem SNR parecido, os 3 schedulers ficam artificialmente semelhantes
2. **Tempo de simulação:** 10⁴ TTIs pode não ser suficiente para convergência estatística em PF
3. **Implementação do scheduler:** RR e Max C/I precisam ser implementados do zero (PF já existe no Sionna)
4. **Curva de aprendizado:** integração dos componentes do Sionna com TensorFlow é a principal etapa de adaptação técnica
5. **Ajuste de escopo:** algoritmos customizados no simulador podem exigir mais tempo do que o previsto

**Dúvidas:**
- A configuração SISO é suficientemente representativa para conclusões úteis?
- Quantos UEs são necessários para observar saturação clara?

**Bloqueios:**
- Nenhum no momento

---

## 11. Resultados esperados (variação de UEs: 2, 4, 8, 16, 32)

**Round Robin**
- JFI: constante em 1.0 (todos recebem N_TTI / N_UE slots).
- Throughput agregado: cai com mais UEs, pois ignora o canal.
- 5º percentil: previsível, ditado pelo pior UE; não piora com a carga.
- Conclusão: piso de justiça e teto de ineficiência.

**Max C/I**
- Throughput agregado: cresce com mais UEs (multiuser diversity), até saturar.
- JFI: colapsa com mais UEs; tende a zero assintoticamente.
- 5º percentil: cai drasticamente, UEs em posição ruim ficam sem serviço.
- Pergunta central: existe um N crítico onde o JFI cruza um limiar de aceitabilidade (ex.: JFI < 0,5)?

**Proportional Fair**
- Throughput agregado: intermediário entre RR e Max C/I; aproxima-se do Max C/I em baixa carga e do RR em alta carga.
- JFI: alto em toda a faixa, decaimento suave.
- Conclusão-chave: PF não é um ponto fixo no espectro eficiência-justiça; sua posição varia com a carga.

---

## Entregáveis previstos

1. Notebook Jupyter completo com implementação e gráficos
2. Relatório técnico (formato IEEE/SBC)
3. Slides da apresentação (10-12 slides)
4. README.md com instruções de reprodução

---

**Status:** Em andamento
**Próxima ação:** Configurar o ambiente Sionna, resolver dependências e validar o sanity check
