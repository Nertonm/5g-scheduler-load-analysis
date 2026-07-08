# Projeto de Análise de Algoritmos de Escalonamento em Redes Sem Fio

Este repositório contém o desenvolvimento de uma primeira entrega de projeto focada na análise comparativa de algoritmos de escalonamento em sistemas de comunicação sem fio utilizando a plataforma NVIDIA Sionna.

---

## 1. Tema
Análise comparativa de algoritmos de escalonamento de pacotes (*scheduling*) em redes de comunicação sem fio via simulação computacional.

## 2. Justificativa
Com a evolução das redes móveis (como o 5G e tecnologias subsequentes), a gestão eficiente dos recursos de rádio tornou-se um fator crítico para garantir a qualidade de serviço (QoS). A escolha do algoritmo de escalonamento impacta diretamente o equilíbrio entre a capacidade máxima da rede e a experiência dos usuários situados nas bordas de cobertura. Este projeto se justifica pela necessidade de mapear o comportamento de abordagens clássicas e consagradas da literatura quando submetidas a diferentes cenários de densidade de usuários, servindo como referência para o entendimento do compromisso entre eficiência e justiça na alocação de recursos.

## 3. Objetivos

### Geral
Avaliar e comparar o desempenho de diferentes algoritmos de escalonamento de pacotes em cenários de enlace descendente (*downlink*).

### Específicos
* Configurar o ambiente de simulação utilizando a plataforma de código aberto NVIDIA Sionna.
* Implementar e integrar os algoritmos de *scheduling* clássicos necessários para a análise comparativa.
* Analisar o impacto da variação da densidade de usuários nos indicadores de desempenho do sistema.
* Avaliar os resultados obtidos por meio de métricas estatísticas e representações gráficas de distribuição.

## 4. Metodologia
O projeto adotará uma abordagem quantitativa fundamentada em simulação computacional a nível de link e sistema através da biblioteca NVIDIA Sionna. O cenário de referência consistirá em uma célula única (*single-cell*) operando em regime de tráfego contínuo (*full-buffer*) sob condições de canal com desvanecimento (como o modelo Rayleigh).

Para garantir a confiabilidade e a validade estatística dos resultados, as simulações serão executadas ao longo de um número representativo de intervalos de tempo de transmissão (TTIs) utilizando múltiplas sementes aleatórias (*seeds*) para a geração de intervalos de confiança adequados.

### Métricas de Desempenho Avaliadas
* **Vazão Total (Throughput Agregado):** Medição da capacidade máxima escoada pela célula.
* **Vazão Individual:** Avaliação da taxa de dados média entregue por dispositivo conectado.
* **Índices de Justiça (Fairness):** Utilização de métricas canônicas para quantificar a equidade na distribuição dos recursos.
* **Desempenho de Borda:** Análise estatística dos usuários sob piores condições de canal (percentis inferiores de vazão).
* **Distribuição Cumulativa (CDF):** Análise do comportamento probabilístico global das taxas de transmissão na rede.

## 5. Breve Levantamento Bibliográfico
* **JAIN, R.; CHIU, D.; HAWE, W.** *A Quantitative Measure of Fairness and Discrimination for Resource Allocation in Shared Computer Systems.* DEC Research Report TR-301, 1984.
* **MAMANE, A. et al.** *Scheduling Algorithms for 5G Networks and Beyond: Classification and Survey.* IEEE Access, v. 10, p. 51643–51661, 2022.
* **NVIDIA.** *Sionna Documentation: PFSchedulerSUMIMO.*
* **NVIDIA.** *Sionna Documentation: RayleighBlockFading.*

## 6. Progresso Inicial e Bloqueios

### Progresso Inicial
* Alinhamento do escopo do projeto e definição dos algoritmos a serem estudados.
* Levantamento bibliográfico inicial das métricas de desempenho e do estado da arte de *scheduling* em redes 5G.
* Escolha e estudo inicial da plataforma de simulação NVIDIA Sionna, que já conta com a implementação nativa de estruturas base para algoritmos de justiça proporcional (*Proportional Fair*).

### Principais Bloqueios
* Curva de aprendizado inicial com a biblioteca Sionna e integração com o ecossistema TensorFlow.
* Desafio técnico no desenvolvimento e acoplamento customizado dos algoritmos adicionais necessários dentro da estrutura de classes do simulador.
