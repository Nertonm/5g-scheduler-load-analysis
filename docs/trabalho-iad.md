# Trabalho IAD - Análise Estatística do Trade-off Eficiência-Justiça em Schedulers 5G

**Disciplinas:** IAD (CC0052) + Redes Sem Fio (CC0048)
**Fonte de dados:** simulação Sionna do projeto [[5g-scheduler-load-analysis]]
**Status:** proposta revisada v2 (crítica técnica incorporada)

---

## Pergunta central (revisada)

"Em que carga o Max C/I se torna injusto?" não tem resposta única. A resposta depende de
**como se define justiça**. O trabalho responde:

> **Quanto a resposta depende da definição de justiça (métrica), do desenho (protocolo) e
> do cenário (validação externa)?**

Três camadas de incerteza, todas quantificadas:
- **Amostral** - IC via bootstrap (JFI/throughput são assimétricos; não assumir t cego)
- **Conceitual** - a resposta muda se a métrica de justiça muda (JFI vs Gini vs família de Chiang)
- **Cenário** - nossos números validados contra benchmarks publicados (Tetcos, SBRC, Telkom)

---

## Eixo 1 - Robustez à definição de justiça (Jain / Chiang / Shi)

### Correção técnica aplicada (obrigatória)

Chiang (2009) define a família \( J_\beta(x) = \frac{1}{n} f_\beta(x) \) com domínio
\( \beta \le 1 \), e o **índice de Jain clássico é recuperado em \( \beta = -1 \)** (média
harmônica, Axioma 4). A família α-fairness (Atkinson/PF/max-min) é um **eixo separado**,
parametrizado por α: PF corresponde a α=1, max-min a α→∞. As duas famílias se relacionam
via fatoração \( F_{\beta,\lambda} \), mas **não são o mesmo parâmetro**.

**Consequência para o desenho:**
- A varredura de robustez usa a família axiomática de Chiang com \( \beta \in (-\infty, 1] \),
  pontos típicos: −3, −2, −1 (Jain), 0, 0,5.
- O α-fairness (utilidade) é tratado em análise separada e declarada, **não** misturado com β.
- NÃO usar β ∈ (1, 3) como "aversão crescente": inválido no domínio de Chiang.

### Procedimento

1. Para cada seed × scheduler × carga, calcular a justiça segundo:
   - JFI (β = −1 de Chiang; métrica dominante, Jain 1984)
   - Gini (Shi 2005): desigualdade instantânea, sensível a filas; **atenção: interpretação
     invertida** (Gini alto = mais desigual), harmonizar na modelagem
   - \( J_\beta \) para β ∈ {−3, −2, 0, 0,5}
2. Definir **antes da análise** o que é "colapso" em cada métrica (JFI < 0,5; Gini > 0,5;
   \( J_\beta \) abaixo do análogo ao limiar de Jain para aquele β).
2b. **Calibrar o limiar de colapso por β ANTES da coleta** (ponto remanescente obrigatório):
   o limiar 0,5 é válido apenas para Jain (β=−1). A escala f_β(x)/n muda de resolução com β;
   derivar o limiar análogo por β usando os corolários de Chiang sobre limites de usuários
   "starved" vs fairness value (Corolário 5), nunca definir ad hoc durante a análise.
3. Estimar o ponto de meia resposta (analogia LD50) por métrica, com IC via bootstrap
   não-paramétrico (2000 reamostragens por condição).
4. Resultado esperado: **a ordenação dos schedulers e o ponto crítico mudam conforme a
   métrica**. A incerteza não é só amostral, é conceitual (qual definição de justiça usar).
5. **Inversão de ordenação (antecipar, não só deslocamento):** Chiang mostra que a ordenação
   de justiça entre dois vetores pode se INVERTER conforme β (Fig. 2 do paper: mudança de
   ordenação fora do domínio de Jain, mas o fenômeno vale dentro dele). O protocolo deve
   reportar a **matriz completa de ordenação dos schedulers por β**, não apenas o N crítico.
   É possível que RR e PF troquem de posição relativa em β alto; isso já é um resultado.

---

## Eixo 2 - Decomposição do ganho do Max C/I (Tse & Viswanath)

A teoria (Cap. 6) prevê **como o ganho acontece**, não só o scaling: o ganho do Max C/I vem de
\( E[\max_k |h_k|^2] \) relativo à média dos canais. Decompor empiricamente:

```
ganho_total = ganho_de_diversidade (seleção do melhor) + ganho_de_média
```

1. Para cada carga, estimar o throughput do Max C/I "real" (seleção oportunística).
2. Estimar o contrafactual "sem diversidade" usando o **RR simulado do próprio
   experimento** (alocação round-robin pura = ausência de oportunismo). Isso evita
   computação redundante, amarra a decomposição aos dados já coletados e é o baseline
   teoricamente correto. NÃO usar "seleção aleatória sobre a média do canal", que
   mistura dois conceitos (ausência de seleção oportunística + suavização estatística).
3. A diferença é o ganho de diversidade; o resto é ganho de média.
4. Comparar a razão observada com a prevista pela teoria (Ban et al. confirma esse comportamento
   empiricamente).

**Hipótese a testar (não fato):** divergências da decomposição teórica podem se dever a
parâmetros do Sionna SYS (β do PF nativo, `num_freq_res`, grade OFDM, abstração PHY via
BLER/SINR, topologia). Documentar os parâmetros reais usados e tratá-los como fatores
potenciais de divergência: verificar, não assumir.

---

## Eixo 3 - Replicação histórica (3GPP R1-00-1388)

Comparar a forma da curva throughput vs N com o documento fundacional de 2000 é honesto,
mas de **baixo poder comparativo**: o documento usa numerologia, canal, largura de banda e
MIMO/diversidade de transmissão distintos dos 5G NR modernos.

**Protocolo obrigatório antes de qualquer conclusão:**
1. Tabela explícita de parâmetros comparáveis vs incomparáveis (terminais testados, modelo
   de fading, janela do PF, BW, antenas).
2. Divergência de forma esperada; o valor analítico está em **atribuir a divergência a
   mudanças nomeáveis** (ex.: Sionna sem HARQ, grade simplificada, numerologia 30 kHz).
3. Nenhuma afirmação de "replicação" sem essa atribuição.

---

## Eixo 4 - Validação externa contra benchmarks

Os números já coletados mostram sensibilidade real ao cenário:

| Estudo | Cenário | RR JFI | PF JFI | Max C/I JFI |
|---|---|---|---|---|
| Tetcos (NetSim) | multi-célula, mobilidade, 30 UEs | 0,71 | 0,74 | 0,29 |
| SBRC 2025 (Lopes) | célula única, 3 UEs, MCS real | 0,92 | 0,74 | 0,34 |
| Telkom | LTE, multipath, HARQ | sem dado | 0,83 | 0,59 (com multipath) |

**Leitura:** PF é estável (0,74 nos dois primeiros); RR varia 0,71 a 0,92 e
Max C/I 0,29 a 0,34. Isso mostra que o ponto crítico depende do cenário
(número de UEs, canal, HARQ): apoia o eixo de robustez.

**Procedimento:** posicionar nossos resultados na mesma tabela, explicar divergências por
diferenças nomeáveis de cenário, e usar os benchmarks como **validação externa** (não enfeite).

---

## Eixo 5 - Mamane como hipótese derivada + evidência empírica de PF-buffer

**Correção aplicada:** a taxonomia de Mamane 2022 é **descritiva** (classifica por métrica de
entrada: CQI, taxa média, PLR), não é previsão quantitativa de ordenação de JFI por carga.
Tratar "PF intermediário em toda a faixa" como **hipótese derivada do enquadramento**, não
como afirmação da survey.

**Evidência numérica citável (Mamane 2021):**

| Scheduler | JFI |
|---|---|
| Best-CQI | 50% |
| PF simples | 84,11% |
| PF-Buffer (proposto) | 91,28% |
| RR | >98% |

Isso confirma empiricamente "PF é uma política, não um ceiling": a variante com buffer se
aproxima do RR em justiça sem sacrificar throughput. **Hipótese testável no nosso dado:**
a ordenação PF simples vs PF-Buffer se mantém sob carga crescente?

---

## Modelagem (seção revisada: risco de overfitting declarado)

Com apenas 5 níveis de carga (2, 4, 8, 16, 32), **seleção formal de modelo com AIC/BIC é
arriscada**. Decisão:

- **Eixo central** (LD50 por métrica + bootstrap): inferência formal, suficiente.
- **Forma da curva** (throughput vs carga): tratada como **exploratória/qualitativa**,
  com candidatos definidos a priori pela teoria do Eixo 2 (log(N), potência, saturação
  exponencial) e comparação por R² ajustado + inspeção de resíduos, **sem** seleção formal
  por AIC/BIC com 5 pontos.
- Se houver tempo: aumentar níveis de carga (ex.: 6, 12, 24, 48) para dar mais pontos à
  modelagem de forma: registrar como extensão, não requisito.

**Modelo misto** (efeitos fixos scheduler + carga + interação; seed aleatório) permanece
para a inferência de efeito do scheduler: trata a estrutura aninhada sem inflar significância.

---

## Estrutura final do relatório

1. **Pergunta e decisão** - o ponto crítico depende da definição de justiça; como estimá-lo
   com incerteza (amostral + conceitual + cenário)
2. **Dados e desenho** - unidade amostral = seed; por que o design controlado permite
   causalidade; parâmetros reais do Sionna (β do PF, num_freq_res) declarados
3. **Calibração contra benchmarks** - Tetcos/SBRC/Telkom (validação externa)
4. **Decomposição do ganho** - diversidade vs média (Tse & Viswanath), com hipótese de
   divergência por parâmetros do simulador (a testar, não assumida)
5. **Robustez à métrica** - LD50 por JFI / Gini / Chiang \( J_\beta \) com bootstrap;
   varredura β ∈ (−∞, 1], Jain = β −1 (correção aplicada)
6. **Replicação histórica** - 3GPP R1-00-1388 com tabela de parâmetros comparáveis/incomparáveis
7. **Modelagem** - misto (inferência) + forma da curva exploratória (candidatos a priori,
   sem seleção formal com 5 pontos)
8. **Conclusão** - o que a estatística afirma, com incerteza amostral E conceitual, e o que
   ficou fora do desenho

## Referências-chave

- Jain, Chiu & Hawe (1984) - JFI; base da métrica dominante
- Lan & Chiang (2009) - família axiomática \( J_\beta \), β ≤ 1, Jain em β = −1 (Tabela III); https://www.princeton.edu/~chiangm/fairness.pdf
- Shi (2005) - Gini para fair schedulers; sensibilidade a filas
- Tse & Viswanath (2005) Cap. 6 - decomposição E[max] vs média; diversidade multiusuário
- Ban et al. - confirmação empírica da diversidade multiusuário
- 3GPP R1-00-1388 (2000) - replicação histórica (baixo poder; atribuição nomeável)
- Tetcos NetSim - benchmark multi-célula
- Lopes et al. (SBRC 2025) - benchmark célula única
- Mamane et al. (2022) - taxonomia descritiva (hipótese derivada)
- Mamane et al. (2021) - PF-Buffer: evidência numérica de PF como família
