#!/usr/bin/env python3
"""
Script de teste para verificar que todos os três schedulers funcionam e produzem resultados distintos.
"""

import numpy as np
import pandas as pd
import sys
import os

# Adiciona src ao caminho
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.config import load_config
from src.simulation import run

def test_schedulers():
    """Testa se todos os três schedulers funcionam e produzem resultados distintos."""
    print("Testando schedulers...")

    # Carrega configuração e sobrescreve para teste rápido
    cfg = load_config()
    cfg.save_results = False  # Não salvar em disco para este teste
    cfg.num_ttis = 100        # Reduz TTIs para teste rápido
    cfg.num_seeds = 2         # Reduz sementes para teste rápido
    cfg.user_counts = [2, 4]  # Reduz contagem de usuários para teste rápido
    cfg.schedulers = ["round_robin", "max_c_i", "proportional_fair"]

    print(f"Config: {cfg.num_ttis} TTIs, {cfg.num_seeds} seeds, contagem de usuários {cfg.user_counts}")
    print(f"Schedulers para teste: {cfg.schedulers}")

    # Executa simulação
    results = run(
        cfg=cfg,
        schedulers=cfg.schedulers,
        cargas=cfg.user_counts,
        seeds=list(range(cfg.num_seeds))
    )

    # Verifica resultados
    per_ue = results["per_ue"]
    per_seed = results["per_seed"]
    summary = results["summary"]

    print("\n=== RESULTADOS ===")
    print(f"Forma dos dados por UE: {per_ue.shape}")
    print(f"Forma dos dados por semente: {per_seed.shape}")
    print(f"Forma dos dados de resumo: {summary.shape}")

    print("\nDados por semente (primeiras linhas):")
    print(per_seed.head(10))

    print("\nDados de resumo:")
    print(summary)

    # Verifica se temos dados para todos os schedulers
    schedulers_in_data = per_seed['scheduler'].unique()
    print(f"\nSchedulers encontrados nos dados: {schedulers_in_data}")

    # Verifica se temos dados de throughput por UE (não apenas zeros)
    throughput_cols = [col for col in per_ue.columns if 'throughput' in col]
    print(f"\nColunas de throughput: {throughput_cols}")

    # Verifica se temos throughput não-zero (pelo menos para alguns UEs)
    max_throughput = per_ue['throughput_bps'].max()
    print(f"Throughput máximo por UE: {max_throughput:.2f} bit/s")

    if max_throughput > 0:
        print("✓ Throughput não-zero detectado - schedulers estão alocando recursos!")
    else:
        print("✗ Aviso: Todos os valores de throughput são zero - verifique a implementação do scheduler")

    # Verifica se temos valores diferentes de JFI para diferentes schedulers (para mesma carga/semente)
    # Isso indicaria que os schedulers estão se comportando de forma diferente
    if len(per_seed) >= 3:  # Devemos ter pelo menos 3 linhas (um por scheduler) para cada carga/semente
        # Agrupa por carga e semente e verifica se o JFI varia
        jfi_variation = per_seed.groupby(['carga', 'seed'])['jains_fairness_index'].std()
        avg_jfi_variation = jfi_variation.mean()
        print(f"\nDesvio padrão médio do JFI entre os grupos (carga,semente): {avg_jfi_variation:.6f}")

        if avg_jfi_variation > 1e-10:  # Muito pequeno limite para levar em conta ponto flutuante
            print("✓ JFI varia entre schedulers - schedulers estão produzindo diferentes resultados de justiça!")
        else:
            print("⚠ JFI não varia significativamente entre schedulers - pode precisar de investigação")

    print("\n=== TESTE COMPLETO ===")
    return results

if __name__ == "__main__":
    test_schedulers()