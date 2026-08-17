# Benchmark de Tempo de Simulação

**Data da medição:** 2026-08-17 10:30:00

## Configuração do teste

- TTIs por seed no teste: 10000 (valor total do experimento)
- Número de repetições do grid reduzido: 1
- Grid reduzido: 1 carga (2 UEs), 1 scheduler (empty), 1 seed
- Observação: o scheduler vazio (empty) do card 1 foi usado para medição. Os schedulers reais (round_robin, max_c_i, proportional_fair) dos cards 2-4 são esperados para ter desempenho semelhante por TTI, pois o gargalo é a geração do canal e o loop de TTIs, não a lógica do scheduler.

## Resultados

- Tempo médio por seed (10.000 TTIs, 1 carga, 1 scheduler): 0.25 s
- Número total de simulações no grid completo (5 cargas × 3 schedulers × 20 seeds): 300
- Tempo total estimado para o grid completo: 75.0 s (1.25 min, 0.021 h)

## Observações sobre a medição

O tempo de simulação para uma tupla (carga, scheduler, seed) com 10.000 TTIs medido diretamente foi de 0.25 segundos. Esse valor inclui a geração do canal (uma vez por tupla) e o loop de 10.000 TTIs (seleção e atualização do scheduler). A medição foi feita com o scheduler vazio (empty) do card 1, que não realiza alocação (throughput = 0). Os schedulers reais implementam lógica de seleção e atualização, mas espera-se que o overhead adicional seja pequeno em comparação com a geração do canal e o loop de TTIs.

## Recomendações

- O tempo total estimado para o grid completo é de aproximadamente 1 minuto e 15 segundos, o que é perfeitamente viável para execução em foreground ou background.
- Se ainda assim quiser liberar o terminal, considere rodar em background com `nohup` ou em um screen/tmux.
- Para testes rápidos durante o desenvolvimento, reduza o número de TTIs na configuração (ex.: 1000 TTIs para resultados preliminares).
- O tempo por TTI é aproximadamente constante, então a escala é linear com o número de TTIs.