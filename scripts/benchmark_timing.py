#!/usr/bin/env python3
"""
Script para medir o tempo de execução de uma seed de simulação
e estimar o custo total do grid.

Uso:
    python scripts/benchmark_timing.py [--ttis TTIS] [--seeds SEEDS]

Argumentos:
    --ttis: Número de TTIs para o teste de benchmark (padrão: 100)
    --seeds: Número de seeds para medição e média (padrão: 1)
"""
import time
import sys
import argparse
from pathlib import Path

# Adiciona o diretório raiz ao path para importar os módulos do projeto
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config import load_config
from src.simulation import run


def benchmark_grid(cfg, test_ttis):
    """
    Mede o tempo de execução do grid reduzido (1 carga, 1 scheduler, 1 seed)
    com o número de TTIs especificado.
    Retorna o tempo em segundos.
    """
    import copy
    test_cfg = copy.deepcopy(cfg)
    test_cfg.num_ttis = test_ttis
    # Reduzir o grid para medição rápida: 1 carga, 1 scheduler (vazio), 1 seed
    test_cfg.user_counts = [2]          # menor carga
    test_cfg.schedulers = ["empty"]     # scheduler vazio (mais rápido)
    test_cfg.num_seeds = 1              # apenas uma seed
    test_cfg.save_results = False       # não salvar arquivos durante benchmark

    start = time.perf_counter()
    run(test_cfg)
    elapsed = time.perf_counter() - start
    return elapsed


def main():
    parser = argparse.ArgumentParser(description='Benchmark de tempo de simulação')
    parser.add_argument('--ttis', type=int, default=100,
                        help='Número de TTIs para o teste de benchmark (padrão: 100)')
    parser.add_argument('--seeds', type=int, default=1,
                        help='Number of seeds to average over (default: 1)')
    args = parser.parse_args()

    print(f"Carregando configuração padrão...")
    cfg = load_config()

    print(f"Executando benchmark com {args.seeds} repetições de grid reduzido "
          f"(1 carga, 1 scheduler, 1 seed) com {args.ttis} TTIs cada...")
    times = []
    for i in range(args.seeds):
        print(f"  Repetição {i+1}/{args.seeds}...", end=' ', flush=True)
        elapsed = benchmark_grid(cfg, args.ttis)
        times.append(elapsed)
        print(f"{elapsed:.2f}s")

    avg_time = sum(times) / len(times)
    # Este é o tempo para: 1 carga x 1 scheduler x 1 seed com test_ttis TTIs
    # Queremos o tempo por TTI:
    time_per_tti = avg_time / args.ttis
    # Tempo para uma seed completa (10.000 TTIs) com um scheduler e uma carga:
    time_per_seed_full_tti = time_per_tti * 10000
    # Agora, o grid completo tem: 5 cargas x 3 schedulers x 20 seeds = 300 simulações
    # Cada simulação é uma (carga, scheduler, seed) com 10.000 TTIs
    total_seeds_grid = 5 * 3 * 20
    total_time_grid = time_per_seed_full_tti * total_seeds_grid

    # Resultados
    print("\n" + "="*60)
    print("RESULTADOS DO BENCHMARK")
    print("="*60)
    print(f"Tempo médio do grid reduzido ({args.ttis} TTIs): {avg_time:.2f} s")
    print(f"Tempo médio por TTI: {time_per_tti:.4f} s/TTI")
    print(f"Tempo estimado por seed (10.000 TTIs, 1 carga, 1 scheduler): {time_per_seed_full_tti:.2f} s")
    print(f"Número total de simulações no grid (5 cargas × 3 schedulers × 20 seeds): {total_seeds_grid}")
    print(f"Tempo total estimado para o grid: {total_time_grid:.2f} s")
    print(f"Tempo total estimado para o grid: {total_time_grid/60:.2f} min")
    print(f"Tempo total estimado para o grid: {total_time_grid/3600:.2f} h")
    print("="*60)

    # Salvar em arquivo para uso na documentação
    output_lines = [
        "# Benchmark de Tempo de Simulação\n",
        "\n",
        f"**Data da medição:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n",
        "\n",
        f"**Configuração do teste:**\n",
        f"- TTIs por seed no teste: {args.ttis}\n",
        f"- Número de repetições do grid reduzido: {args.seeds}\n",
        f"- Grid reduzido: 1 carga (2 UEs), 1 scheduler (empty), 1 seed\n",
        "\n",
        f"**Resultados:**\n",
        f"- Tempo médio por seed reduzido ({args.ttis} TTIs): {avg_time:.2f} s\n",
        f"- Tempo médio por TTI: {time_per_tti:.4f} s/TTI\n",
        f"- Tempo estimado por seed completa (10.000 TTIs, 1 carga, 1 scheduler): {time_per_seed_full_tti:.2f} s\n",
        f"- Número total de simulações no grid completo (5 cargas × 3 schedulers × 20 seeds): {total_seeds_grid}\n",
        f"- Tempo total estimado para o grid completo: {total_time_grid:.2f} s "
        f"({total_time_grid/60:.2f} min, {total_time_grid/3600:.2f} h)\n",
        "\n",
        "**Recomendações:**\n",
        "- Se o tempo total estimado for inviável para execução interativa, considere rodar em background com `nohup` ou em um cluster.\n",
        "- Para testes rápidos, reduza o número de TTIs na configuração (ex.: 1000 TTIs para resultados preliminares).\n",
        "- O tempo por TTI é aproximadamente constante, então a escala é linear.\n",
    ]

    output_path = Path(__file__).resolve().parents[1] / "docs" / "benchmark.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        f.writelines(output_lines)

    print(f"\nResultados salvos em {output_path}")


if __name__ == "__main__":
    main()